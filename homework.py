import logging
import os
import requests
import sys
import time

import telegram

from http import HTTPStatus
from dotenv import load_dotenv

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

# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s %(levelname)s %(message)s'
# )
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s'
)

# logger = logging.StreamHandler()
# logger.setStream(sys.stdout)
# logger.setLevel(logging.DEBUG)
# logger.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


# logger.debug('Новых статусов нет')
# logger.info('Сообщение отправлено')
# logger.warning('Большая нагрузка!')
# logger.error('Бот не смог отправить сообщение')
# logger.critical('Отсутствуют переменные окружения!')

def send_message(bot, message):
    """Отправка сообщения пользователю."""
    bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp):
    """Запрос к API Практикум.Домашка"""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            raise Exception
        return response.json()
    except Exception:
        raise ConnectionError('Ошибка запроса к API Практикум')


def check_response(response):
    """Проверка ответа API Практикум.Домашка на корректность."""
    resp_list = response['homeworks']
    if not isinstance(resp_list, list):
        logging.error('В ответе не список')
        raise TypeError('В ответе не список')
    else:
        logging.info('В ответе получен валидный список')
        return resp_list


def parse_status(homework):
    """Извлекает из ответа о домашней работе ее статус."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    print(HOMEWORK_STATUSES[homework_status])
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
        logging.info('Статус работы получен')
    except Exception as error:
        logging.error(f'Полученный список пуст.{error}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    return all(x is not None for x in tokens)


def main():
    """Основная логика работы бота."""

    check_tokens()
    old_status = {}
    current_status = {}
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
                            # -30*24*60*60)

    while True:
        try:
            response = get_api_answer(current_timestamp)

            resp = check_response(response)
            message = parse_status(resp[0])
            current_status = message
            current_timestamp = resp.get('current_date')
            if current_status != old_status:
                send_message(bot, current_status)
                old_status = current_status
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logger.error(message)
            time.sleep(RETRY_TIME)
        else:
            ...


if __name__ == '__main__':
    main()
