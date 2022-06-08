import os
import time
import logging
import sys
from http import HTTPStatus

import telegram
import requests
from dotenv import load_dotenv

from exceptions import ApiEndpoinException, ApiResponseException
from exceptions import ApiHomeworkException, TelegramSendMessageException

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

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
handler.setStream(sys.stdout)
logger.addHandler(handler)


def check_tokens():
    """Check environment variables are available.

    Return True or False. Send log if some of variables are missing.
    """
    result = True
    required_tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    error_message = ('Missing required environment variable {}')
    for key, value in required_tokens.items():
        if not value:
            logger.critical(error_message.format(repr(key)))
            result = False
    return result


def get_api_answer(current_timestamp):
    """Get answer from Yandex api."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, params=params, headers=HEADERS)
    if response.status_code != HTTPStatus.OK:
        raise ApiEndpoinException(
            f'Endpoint {ENDPOINT} failure. Status code: {response.status_code}'
        )
    return response.json()


def check_response(response):
    """Check API response."""
    keys = ['current_date', 'homeworks']
    if isinstance(response, list):
        response = response[0]
    for key in keys:
        if key not in response:
            raise ApiResponseException(f'Missing key {key} in api response')
    if isinstance(response, dict) and len(response) == 0:
        raise ApiResponseException("Empty API response dictionary")
    if not isinstance(response.get('homeworks'), list):
        raise ApiResponseException("API 'homeworks' key incorrect datatype")
    return response.get('homeworks')


def parse_status(homework):
    """Parse homework status."""
    # Prepare variables
    keys = ['homework_name', 'status']
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    # Check keys in api response
    for key in keys:
        if key not in homework:
            raise KeyError(
                f'Missing {repr(key)} key in api response.'
            )
    # Check homework status is valid
    if homework_status not in HOMEWORK_STATUSES:
        raise ApiHomeworkException(
            f'Incorrect home work status: {homework_status}'
        )
    # Prepare and return status message
    verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot, message):
    """Send telegram message."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.INFO(f'Message sent to telegram: {message}')
    except Exception as error:
        raise TelegramSendMessageException(f'Telegram message error: {error}')


def main():
    """Bot main function."""
    logger.debug('Start main() function.')
    # If tokens are missing exit programm
    if not check_tokens():
        logger.debug('Interrupt main() function.')
        return
    # Prepare telegram bot, timestamp and list of errors
    raised_exceptions = []
    status_tracking = {}
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            logger.debug('Start api task.')
            # Make api request and check response
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            logger.debug('Check status updates.')
            # Check updates
            for homework in homeworks:
                hw_name = homework.get('homework_name')
                hw_status = homework.get('status')
                if hw_name not in status_tracking:
                    status_tracking[hw_name] = hw_status
                    message = parse_status(homework)
                    send_message(bot, message)
                elif status_tracking[hw_name] != hw_status:
                    status_tracking[hw_name] = hw_status
                    message = parse_status(homework)
                    send_message(bot, message)
                else:
                    logger.DEBUG(f'No new status in api response {message}')
            current_timestamp = response.get('current_date')
            logger.debug('Countdown start.')
            time.sleep(RETRY_TIME)
            logger.debug('Countdown end.')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(error, exc_info=True)
            if not isinstance(error, TelegramSendMessageException) and \
                    error not in raised_exceptions:
                send_message(bot, message)
                raised_exceptions.append(error)
            logger.debug('Countdown start.')
            time.sleep(RETRY_TIME)
            logger.debug('Countdown end.')
            logger.debug('End api task with errors.')
        else:
            logger.debug('End api task successfully.')


if __name__ == '__main__':
    main()
