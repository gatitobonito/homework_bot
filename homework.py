import logging, os, requests, time

import telegram
from telegram.ext import CommandHandler, Updater

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

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

def send_message(bot, message):
    bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    check_response(requests.get(ENDPOINT, headers=HEADERS, params=params))


def check_response(response):
    if response.json().exists():
        parse_status(response.json().get('homeworks'))


def parse_status(homework):
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    ...

    verdict = HOMEWORK_STATUSES[homework_status]

    ...

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    # if PRACTICUM_TOKEN.


def main():
    """Основная логика работы бота."""

    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    get_api_answer(current_timestamp)

    while True:
        try:
            response = get_api_answer(current_timestamp)

            check_response(response)

            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        else:
            ...


if __name__ == '__main__':
    main()
