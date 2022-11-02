import logging
import os
import requests
import sys
import time

import telegram

from http import HTTPStatus
from dotenv import load_dotenv

from exceptions import EmptyAPIResponseError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

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
    logger.info('Сообщение отправлено в Телеграмм')
    bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp):
    """Запрос к API Практикум.Домашка"""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            raise EmptyAPIResponseError('Пустой ответ от API')
        return response.json()
    except Exception:
        raise ConnectionError('Ошибка запроса к API Практикум')


def check_response(response):
    """Проверка ответа API Практикум.Домашка на корректность."""
    resp_list = response['homeworks']
    if not isinstance(resp_list, list):
        logger.error('В ответе не список')
        raise TypeError('В ответе не список')
    else:
        logger.info('В ответе получен валидный список')
        return resp_list


def parse_status(homework):
    """Извлекает из ответа о домашней работе ее статус."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_name is None:
        raise KeyError('В ответе не найдено имя')
    if homework_status is None:
        raise KeyError('В ответе не найден статус')
    # if HOMEWORK_STATUSES[homework_status] is None:
    #     raise KeyError('Пустой список')
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
        logger.info('Статус работы получен')
    except Exception as error:
        logger.error(f'Полученный список пуст.{error}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    return all(x is not None for x in tokens)


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('С переменными окружения что-то не так')
        sys.exit()
    old_status = ''
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    # -30*24*60*60)

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
            send_message(bot, message)
            logger.error(message)
            time.sleep(RETRY_TIME)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
