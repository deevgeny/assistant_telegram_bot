import os
import time
import logging
import sys
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

import telegram
import requests
from dotenv import load_dotenv

from exceptions import ApiEndpointFatalException, ApiResponseException
from exceptions import ApiHomeworkStatusException, TelegramSendMessageException
from exceptions import ApiEndpointHttpResponseException

# Load tokens
load_dotenv()

# Get tokens from environment variables
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Prepare constants
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
VERDICTS = {
    'approved': 'The homework has been checked and approved by the reviewer.',
    'reviewing': 'The homework hase been taken for code review.',
    'rejected': 'The homework has been checked and rejected by the reviewer.'
}

# Set up logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# Heroku service handler
handler = logging.StreamHandler()
# VPS handler
extra_handler = RotatingFileHandler(
    'main.log',
    maxBytes=50000000,
    backupCount=5
)
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(funcName)s %(lineno)d %(message)s'
)
handler.setFormatter(formatter)
extra_handler.setFormatter(formatter)
handler.setStream(sys.stdout)
logger.addHandler(handler)
logger.addHandler(extra_handler)


def check_tokens():
    """Check environment variables are available.

    Return True or False. Send log if some of variables are missing.
    """
    # Prepare validation data and error message
    result = True
    required_tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    error_message = ('Missing required environment variable {}.')
    # Check tokens
    for key, value in required_tokens.items():
        if not value:
            logger.critical(error_message.format(repr(key)))
            result = False
    return result


def get_api_answer(current_timestamp):
    """Get answer from endpoint.

    Raise exceptions: for any unexpected failure
    or response.status_code != 200.
    """
    # Prepare request data
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    # Run request
    try:
        logger.debug('Start api request.')
        response = requests.get(ENDPOINT, params=params, headers=HEADERS)
    except Exception as error:
        raise ApiEndpointFatalException(
            f'API reqeust failed with error: {error}. '
            f'Parameters: {params}.')
    # Check response status
    if response.status_code != HTTPStatus.OK:
        raise ApiEndpointHttpResponseException(
            f'Endpoint {ENDPOINT} failure. Status code: {response.status_code}'
            f' Parameters: {params}'
        )
    # Return api response json data
    return response.json()


def check_response(response):
    """Check API response.

    Raise exceptions: api response keys are missing,
    api response is dict and is not empty,
    api response['homeworks'] is a list.
    """
    # Prepare valid response keys
    keys = ['current_date', 'homeworks']
    logger.debug('Start api response check.')
    # Check api response is a dictionary and it is not empty
    if isinstance(response, dict) and len(response) == 0:
        raise ApiResponseException('API response is not dictionary or empty.')
    # Check response is a dictionary
    if not isinstance(response, dict):
        raise TypeError('API response is not a dict')
    # Check api response keys
    for key in keys:
        if key not in response:
            raise KeyError(f'Missing key {key} in api response.')

    # Check api response['homeworks'] is a list
    if not isinstance(response.get('homeworks'), list):
        raise ApiResponseException("API response['homeworks'] is not list.")
    # Return list of homeworks from api response (even if it is empty)
    return response.get('homeworks')


def parse_status(homework):
    """Parse homework status.

    Raise exceptions: if any key is missing or homework status is invalid.
    """
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
    if homework_status not in VERDICTS:
        raise ApiHomeworkStatusException(
            f'Incorrect home work status: {homework_status}.'
        )
    # Prepare and return status message
    verdict = VERDICTS.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot, message):
    """Send telegram message.

    Raise exception for any unexpected error.
    """
    try:
        logger.debug('Send telegram message.')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Message sent to telegram: {message}.')
    except Exception as error:
        raise TelegramSendMessageException(f'Telegram message error: {error}.')


def main():
    """Bot main function."""
    logger.debug('Start main() function.')

    # If tokens are missing exit programm
    if not check_tokens():
        logger.critical('Interrupt main() function.')
        sys.exit('Missing required tokens. Update .env file.')

    # Prepare telegram bot and other variables
    raised_exceptions = []
    status_tracking = {}
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            # Make api request and check response
            logger.debug('Start api task.')
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            # Check updates
            logger.debug('Check status updates.')
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
        except TelegramSendMessageException as error:
            logger.error(f'Proram failure: {error}')
            logger.debug('End api task with errors.')
        except Exception as error:
            # Log Exception error
            message = f'Program failure: {error}'
            logging.error(error, exc_info=True)
            # Remember exception error and send message to telegram
            if error not in raised_exceptions:
                send_message(bot, message)
                raised_exceptions.append(error)
            logger.debug('End api task with errors.')
        else:
            logger.debug('End api task successfully.')
        finally:
            # Suspend for RETRY_TIME seconds
            logger.debug(f'Suspend for {RETRY_TIME} seconds.')
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
