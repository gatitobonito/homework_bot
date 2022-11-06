import logging
import os
import requests
import sys
import telegram
import time

from exceptions import APIResponseError, CheckTokenError, HTTPStatusError
from dotenv import load_dotenv
from http import HTTPStatus
from telegram import TelegramError

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


def send_message(bot, message):
    """Отправка сообщения пользователю."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение отправлено в Телеграмм')
    except TelegramError:
        logger.error('Не удалось отправить сообщение в Telegram')


def get_api_answer(current_timestamp):
    """Запрос к API Практикум.Домашка."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            logger.error(f'Ответ от API {response.status_code}')
            raise HTTPStatusError(f'Ответ от API {response.status_code}')
        resp_json = response.json()
        error_keys = {'error', 'code'}
        for k in error_keys:
            if k in list(resp_json):
                resp_error = resp_json['error']
                resp_code = resp_json['code']
                raise APIResponseError(
                    f'Ошибка {resp_error}, код:{resp_code}'
                )
        return resp_json
    except requests.RequestException as exc:
        logger.error(f'Ошибка {exc}')
        raise requests.ConnectionError('Ошибка подключения к API Практикум')


def check_response(response):
    """Проверка ответа API Практикум.Домашка на корректность."""
    if not isinstance(response, dict):
        logger.error('В ответе не словарь')
        raise TypeError('В ответе не словарь')
    try:
        resp_list = response['homeworks']
    except KeyError:
        logger.error('В словаре нет ключа homeworks')
        raise KeyError('В словаре нет ключа homeworks')
    if not isinstance(resp_list, list):
        logger.error('В ответе не список')
        raise TypeError('В ответе не список')
    logger.info('В ответе получен валидный список')
    return resp_list


def parse_status(homework):
    """Извлекает из ответа о домашней работе ее статус."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if HOMEWORK_STATUSES[homework_status] is None:
        logger.error('В ответе нет статуса работы')
        raise KeyError('Незнакомый статус')
    verdict = HOMEWORK_STATUSES[homework_status]
    logger.info('Статус работы получен')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    for name in TOKEN_NAMES:
        if not globals()[name]:
            return False
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('С переменными окружения что-то не так')
        raise CheckTokenError('С переменными окружения что-то не так')
    old_status = ''
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            resp = check_response(response)
            message = parse_status(resp[0])
            if message is None:
                raise KeyError('Получен пустой список')
            current_timestamp = resp[0].get('current_date')
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
