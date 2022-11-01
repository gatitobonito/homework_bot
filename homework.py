import logging, os, requests, time, sys
from logging import StreamHandler
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

# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s %(levelname)s %(message)s'
# )
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s'
)

logger = logging.StreamHandler()
logger.setStream(sys.stdout)
logger.setLevel(logging.INFO)
logger.setFormatter(formatter)

logger.debug('Новых статусов нет')
logger.info('Сообщение отправлено')
logger.warning('Большая нагрузка!')
logger.error('Бот не смог отправить сообщение')
logger.critical('Отсутствуют переменные окружения!')

def send_message(bot, message):
    """Отправка сообщения пользователю."""
    bot.send_message(TELEGRAM_CHAT_ID, HOMEWORK_STATUSES[message])


def get_api_answer(current_timestamp):
    """Запрос к API Практикум.Домашка"""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    check_response(requests.get(ENDPOINT, headers=HEADERS, params=params))
#     логируем словарь, распаковываем словарь


def check_response(response):
    """Проверка ответа API Практикум.Домашка на корректность."""
    resp_list = response.get('homeworks')
    if isinstance(resp_list, list):
        logging.info('В ответе получен валидный список')
        return resp_list[0]
    else:
        logging.error('В ответе не список')


def parse_status(homework):
    """Извлекает из ответа о домашней работе ее статус."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
        logging.info('Статус работы получен')
    except Exception as error:
        logging.error(f'Полученный список пуст.{error}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    tokens=[PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    return all(x is not None for x in tokens)

def main():
    """Основная логика работы бота."""

    # main_logger = logging.getLogger()
    # main_logger.setLevel(logging.INFO)

    check_tokens()
    old_status ={}
    current_status={}
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()-30*24*60*60)

    get_api_answer(current_timestamp)

    while True:
        try:
            response = get_api_answer(current_timestamp)

            resp = check_response(response)
            message = parse_status(resp)
            send_message(bot, message)
            current_timestamp = int(time.time())
            if current_status != old_status:
                send_message(bot, current_status)
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        else:
            ...


if __name__ == '__main__':
    main()
