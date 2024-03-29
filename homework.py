import logging
import os
import requests
import sys
import telegram
import time

from dotenv import load_dotenv
from http import HTTPStatus
from telegram import TelegramError

from exceptions import APIResponseError, CheckTokenError, HTTPStatusError
from exceptions import NoHomeworkStatusInResponse

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

TOKEN_NAMES = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


def send_message(bot, message) -> None:
    """Отправка сообщения пользователю."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Сообщение отправлено в Телеграмм: {message}')
    except TelegramError:
        logger.error(f'Не удалось отправить в Telegram сообщение: {message}')


def get_api_answer(current_timestamp: int) -> int:
    """Запрос к API Практикум.Домашка."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.RequestException as exc:
        logger.error(f'Ошибка {exc}')
        raise requests.ConnectionError('Ошибка подключения к API Практикум')
    resp_json = response.json()
    if response.status_code != HTTPStatus.OK:
        error_keys = {'error', 'code'}
        for k in error_keys:
            if k in resp_json:
                resp_error = resp_json['error']
                resp_code = resp_json['code']
                logger.error(f'Ответ от API {resp_error},{resp_code}')
                raise APIResponseError(
                    msg=resp_error, code=resp_code
                )
        logger.error(f'Ответ от API {response.status_code}')
        raise HTTPStatusError(
            msg='код ответа от API:', code=response.status_code
        )
    return resp_json


def check_response(response: dict) -> list:
    """Проверка ответа API Практикум.Домашка на корректность."""
    if not isinstance(response, dict):
        logger.error('В ответе не словарь')
        raise TypeError('В ответе не словарь')
    if "homeworks" not in response:
        logger.error('В словаре нет ключа homeworks')
        raise KeyError('В словаре нет ключа homeworks')
    resp_list = response['homeworks']
    if not isinstance(resp_list, list):
        logger.error('В ответе не список')
        raise TypeError('В ответе не список')
    logger.info('В ответе получен валидный список')
    return resp_list


def parse_status(homework: dict) -> str:
    """Извлекает из ответа о домашней работе ее статус."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        logger.error(f'В ответе нет статуса работы: {homework_status}')
        raise NoHomeworkStatusInResponse(
            msg=f'Незнакомый статус: {homework_status}', code=''
        )
    verdict = HOMEWORK_STATUSES[homework_status]
    logger.info('Статус работы получен')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Проверка доступности переменных окружения."""
    for name in TOKEN_NAMES:
        if not globals()[name]:
            logger.critical(f'Переменная {name} не найдена')
            return False
    return True


def main() -> None:
    """Основная логика работы бота."""
    if not check_tokens():
        raise CheckTokenError(
            msg='Переменная не найдена', code=''
        )
    old_status = ''
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            resp = check_response(response)
            if not resp:
                message = 'Обновлений статуса домашки нет'
            else:
                message = parse_status(resp[0])
                current_timestamp = resp[0].get(
                    'current_date', current_timestamp
                )
            if old_status != message:
                send_message(bot, message)
                old_status = message
            else:
                logger.debug('Статус не изменился')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if old_status != message:
                send_message(bot, message)
                old_status = message
            logger.error(message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
