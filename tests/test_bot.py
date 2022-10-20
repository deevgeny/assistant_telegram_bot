import os
from http import HTTPStatus

import requests
import telegram
import utils


class MockResponseGET:

    def __init__(self, url, params=None, random_timestamp=None,
                 current_timestamp=None, http_status=HTTPStatus.OK, **kwargs):
        assert (
            url.startswith(
                'https://practicum.yandex.ru/api/user_api/homework_statuses'
            )
        ), (
            'API endpoint is incorrect.'
        )
        assert 'headers' in kwargs, (
            'No `headers` in API request.'
        )
        assert 'Authorization' in kwargs['headers'], (
            '`Authorization` argument is missing in API request `headers`'
        )
        assert kwargs['headers']['Authorization'].startswith('OAuth '), (
            '`Authorization` argument in API request `headers` should start '
            'with `OAuth`'
        )
        assert params is not None, (
            '`params` argument is missing in API request'
        )
        assert 'from_date' in params, (
            '`from_date` argument is missing in API request `params`'
        )
        assert params['from_date'] == current_timestamp, (
            '`from_date` argument should be a timestamp'
        )
        self.random_timestamp = random_timestamp
        self.status_code = http_status

    def json(self):
        data = {
            "homeworks": [],
            "current_date": self.random_timestamp
        }
        return data


class MockTelegramBot:

    def __init__(self, token=None, random_timestamp=None, **kwargs):
        assert token is not None, (
            'Telegram bot token is missing'
        )
        self.random_timestamp = random_timestamp

    def send_message(self, chat_id=None, text=None, **kwargs):
        assert chat_id is not None, (
            'Telegram chat id is missing'
        )
        assert text is not None, (
            '`text` argument is missing in telegram message'
        )
        return self.random_timestamp


class TestAssistantBot:
    HOMEWORK_STATUSES = {
        'approved': 
        'The homework has been checked and approved by the reviewer.',
        'reviewing':
        'The homework hase been taken for code review.',
        'rejected': 
        'The homework has been checked and rejected by the reviewer.'
    }
    ENV_VARS = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']
    for v in ENV_VARS:
        try:
            os.environ.pop(v)
        except KeyError:
            pass
    try:
        import assistant_bot
    except KeyError as e:
        for arg in e.args:
            if arg in ENV_VARS:
                assert False, (
                    'No `SystemExit` or environment variables have not been '
                    'checked properly\n'
                    f'{repr(e)}'
                )
            else:
                raise
    except SystemExit:
        for v in ENV_VARS:
            os.environ[v] = ''

    def test_check_tokens_false(self):
        for v in self.ENV_VARS:
            try:
                os.environ.pop(v)
            except KeyError:
                pass

        import assistant_bot

        for v in self.ENV_VARS:
            utils.check_default_var_exists(assistant_bot, v)

        assistant_bot.PRACTICUM_TOKEN = None
        assistant_bot.TELEGRAM_TOKEN = None
        assistant_bot.TELEGRAM_CHAT_ID = None

        func_name = 'check_tokens'
        utils.check_function(assistant_bot, func_name, 0)
        tokens = assistant_bot.check_tokens()
        assert not tokens, (
            f'Function {func_name} does not return False when environment '
            ' variables are missing.'
        )

    def test_check_tokens_true(self):
        for v in self.ENV_VARS:
            try:
                os.environ.pop(v)
            except KeyError:
                pass

        import assistant_bot

        for v in self.ENV_VARS:
            utils.check_default_var_exists(assistant_bot, v)

        assistant_bot.PRACTICUM_TOKEN = 'sometoken'
        assistant_bot.TELEGRAM_TOKEN = '1234:abcdefg'
        assistant_bot.TELEGRAM_CHAT_ID = 12345

        func_name = 'check_tokens'
        utils.check_function(assistant_bot, func_name, 0)
        tokens = assistant_bot.check_tokens()
        assert tokens, (
            f'Function {func_name} does not return True when environment '
            'variables are NOT missing.'
        )

    def test_bot_init_not_global(self):
        import assistant_bot

        assert not (hasattr(assistant_bot, 'bot') and isinstance(getattr(assistant_bot, 'bot'), telegram.Bot)), (
            'Telegram bot should be defined only inside main() function'
        )

    def test_logger(self, monkeypatch, random_timestamp):
        def mock_telegram_bot(*args, **kwargs):
            return MockTelegramBot(*args, random_timestamp=random_timestamp, **kwargs)

        monkeypatch.setattr(telegram, "Bot", mock_telegram_bot)

        import assistant_bot

        assert hasattr(assistant_bot, 'logging'), (
            'Loggin is not defined'
        )

    def test_send_message(self, monkeypatch, random_timestamp):
        def mock_telegram_bot(*args, **kwargs):
            return MockTelegramBot(*args, random_timestamp=random_timestamp, **kwargs)

        monkeypatch.setattr(telegram, "Bot", mock_telegram_bot)

        import assistant_bot
        utils.check_function(assistant_bot, 'send_message', 2)

    def test_get_api_answers(self, monkeypatch, random_timestamp,
                             current_timestamp, api_url):
        def mock_response_get(*args, **kwargs):
            return MockResponseGET(
                *args, random_timestamp=random_timestamp,
                current_timestamp=current_timestamp, **kwargs
            )

        monkeypatch.setattr(requests, 'get', mock_response_get)

        import assistant_bot

        func_name = 'get_api_answer'
        utils.check_function(assistant_bot, func_name, 1)

        result = assistant_bot.get_api_answer(current_timestamp)
        assert type(result) == dict, (
            f'Function `{func_name}` should return dictionary'
        )
        keys_to_check = ['homeworks', 'current_date']
        for key in keys_to_check:
            assert key in result, (
                f'Function `{func_name}` should return dictionary '
                f'with {key} key'
            )
        assert type(result['current_date']) == int, (
            f'Function `{func_name}` should return API response with '
            '`current_date` key which value should be of `int` type'
        )
        assert result['current_date'] == random_timestamp, (
            f'Function `{func_name}` should return correct value in API '
            'response `current_date` key'
        )

    def test_get_500_api_answer(self, monkeypatch, random_timestamp,
                                current_timestamp, api_url):
        def mock_500_response_get(*args, **kwargs):
            response = MockResponseGET(
                *args, random_timestamp=random_timestamp,
                current_timestamp=current_timestamp,
                http_status=HTTPStatus.INTERNAL_SERVER_ERROR, **kwargs
            )

            def json_invalid():
                data = {
                }
                return data

            response.json = json_invalid
            return response

        monkeypatch.setattr(requests, 'get', mock_500_response_get)

        import assistant_bot

        func_name = 'get_api_answer'
        try:
            assistant_bot.get_api_answer(current_timestamp)
        except:
            pass
        else:
            assert False, (
                f'Function `{func_name}` should process API response with '
                'status code other than 200'
            )

    def test_parse_status(self, random_timestamp):
        test_data = {
            "id": 123,
            "status": "approved",
            "homework_name": str(random_timestamp),
            "reviewer_comment": "Everything is OK.",
            "date_updated": "2020-02-13T14:40:57Z",
            "lesson_name": "Final project"
        }

        import assistant_bot

        func_name = 'parse_status'

        utils.check_function(assistant_bot, func_name, 1)

        result = assistant_bot.parse_status(test_data)
        assert result.startswith(
            f'Изменился статус проверки работы "{random_timestamp}"'
        ), (
            f'Function `{func_name}` output should have homework name'
        )
        status = 'approved'
        assert result.endswith(self.HOMEWORK_STATUSES[status]), (
            f' Function `{func_name}` output should have `{status}` value'
        )

        test_data['status'] = status = 'rejected'
        result = assistant_bot.parse_status(test_data)
        assert result.startswith(
            f'Изменился статус проверки работы "{random_timestamp}"'
        ), (
            'Function parse_status() output should have homework name'
        )
        assert result.endswith(
            self.HOMEWORK_STATUSES[status]
        ), (
            f'Function parse_status() output should have `{status}` value'
        )

    def test_check_response(self, monkeypatch, random_timestamp,
                            current_timestamp, api_url):
        def mock_response_get(*args, **kwargs):
            response = MockResponseGET(
                *args, random_timestamp=random_timestamp,
                current_timestamp=current_timestamp,
                **kwargs
            )

            def valid_response_json():
                data = {
                    "homeworks": [
                        {
                            'homework_name': 'hw123',
                            'status': 'approved'
                        }
                    ],
                    "current_date": random_timestamp
                }
                return data

            response.json = valid_response_json
            return response

        monkeypatch.setattr(requests, 'get', mock_response_get)

        import assistant_bot

        func_name = 'check_response'
        response = assistant_bot.get_api_answer(current_timestamp)
        status = assistant_bot.check_response(response)
        assert status, (
            f'Function `{func_name} works incorrectly with correct API '
            'response'
        )

    def test_parse_status_unknown_status(self, monkeypatch, random_timestamp,
                                         current_timestamp, api_url):
        def mock_response_get(*args, **kwargs):
            response = MockResponseGET(
                *args, random_timestamp=random_timestamp,
                current_timestamp=current_timestamp,
                **kwargs
            )

            def valid_response_json():
                data = {
                    "homeworks": [
                        {
                            'homework_name': 'hw123',
                            'status': 'unknown'
                        }
                    ],
                    "current_date": random_timestamp
                }
                return data

            response.json = valid_response_json
            return response

        monkeypatch.setattr(requests, 'get', mock_response_get)

        import assistant_bot

        func_name = 'parse_status'
        response = assistant_bot.get_api_answer(current_timestamp)
        homeworks = assistant_bot.check_response(response)
        for hw in homeworks:
            status_message = None
            try:
                status_message = assistant_bot.parse_status(hw)
            except:
                pass
            else:
                assert False, (
                    f'Function `{func_name}` should raise error for '
                    'unknown homework status in API response'
                )
            if status_message is not None:
                for hw_status in self.HOMEWORK_STATUSES:
                    assert not status_message.endswith(hw_status), (
                        f'Function `{func_name} should not return correct '
                        'output for homework with unknown status'
                    )

    def test_parse_status_no_status_key(self, monkeypatch, random_timestamp,
                                        current_timestamp, api_url):
        def mock_response_get(*args, **kwargs):
            response = MockResponseGET(
                *args, random_timestamp=random_timestamp,
                current_timestamp=current_timestamp,
                **kwargs
            )

            def valid_response_json():
                data = {
                    "homeworks": [
                        {
                            'homework_name': 'hw123',
                        }
                    ],
                    "current_date": random_timestamp
                }
                return data

            response.json = valid_response_json
            return response

        monkeypatch.setattr(requests, 'get', mock_response_get)

        import assistant_bot

        func_name = 'parse_status'
        response = assistant_bot.get_api_answer(current_timestamp)
        homeworks = assistant_bot.check_response(response)
        for hw in homeworks:
            status_message = None
            try:
                status_message = assistant_bot.parse_status(hw)
            except:
                pass
            else:
                assert False, (
                    f'Function `{func_name}` should raise error for missing '
                    '`homework_status` key in API response'
                )
            if status_message is not None:
                for hw_status in self.HOMEWORK_STATUSES:
                    assert not status_message.endswith(hw_status), (
                        f'Function `{func_name} should not return correct '
                        'output for API response with missing '
                        '`homework_status` key'
                    )

    def test_parse_status_no_homework_name_key(self, monkeypatch, random_timestamp,
                                               current_timestamp, api_url):
        def mock_response_get(*args, **kwargs):
            response = MockResponseGET(
                *args, random_timestamp=random_timestamp,
                current_timestamp=current_timestamp,
                **kwargs
            )

            def valid_response_json():
                data = {
                    "homeworks": [
                        {
                            'status': 'unknown'
                        }
                    ],
                    "current_date": random_timestamp
                }
                return data

            response.json = valid_response_json
            return response

        monkeypatch.setattr(requests, 'get', mock_response_get)

        import assistant_bot

        func_name = 'parse_status'
        response = assistant_bot.get_api_answer(current_timestamp)
        homeworks = assistant_bot.check_response(response)
        try:
            for hw in homeworks:
                assistant_bot.parse_status(hw)
        except KeyError:
            pass
        else:
            assert False, (
                f'Function `{func_name}` should work correctly with '
                'missing `homework_name` key in API response'
            )

    def test_check_response_no_homeworks(self, monkeypatch, random_timestamp,
                                         current_timestamp, api_url):
        def mock_no_homeworks_response_get(*args, **kwargs):
            response = MockResponseGET(
                *args, random_timestamp=random_timestamp,
                current_timestamp=current_timestamp,
                **kwargs
            )

            def json_invalid():
                data = {
                    "current_date": random_timestamp
                }
                return data

            response.json = json_invalid
            return response

        monkeypatch.setattr(requests, 'get', mock_no_homeworks_response_get)

        import assistant_bot

        func_name = 'check_response'
        result = assistant_bot.get_api_answer(current_timestamp)
        try:
            assistant_bot.check_response(result)
        except:
            pass
        else:
            assert False, (
                f'Function `{func_name} should raise error for missing '
                '`homeworks` key in API response'
            )

    def test_check_response_not_dict(self, monkeypatch, random_timestamp,
                                     current_timestamp, api_url):
        def mock_response_get(*args, **kwargs):
            response = MockResponseGET(
                *args, random_timestamp=random_timestamp,
                current_timestamp=current_timestamp,
                **kwargs
            )

            def valid_response_json():
                data = [{
                    "homeworks": [
                        {
                            'homework_name': 'hw123',
                            'status': 'approved'
                        }
                    ],
                    "current_date": random_timestamp
                }]
                return data

            response.json = valid_response_json
            return response

        monkeypatch.setattr(requests, 'get', mock_response_get)

        import assistant_bot

        func_name = 'check_response'
        response = assistant_bot.get_api_answer(current_timestamp)
        try:
            status = assistant_bot.check_response(response)
        except TypeError:
            pass
        else:
            assert status, (
                f'Function `{func_name} should process API response of '
                'incorrect type'
            )

    def test_check_response_homeworks_not_in_list(self, monkeypatch, random_timestamp,
                                                  current_timestamp, api_url):
        def mock_response_get(*args, **kwargs):
            response = MockResponseGET(
                *args, random_timestamp=random_timestamp,
                current_timestamp=current_timestamp,
                **kwargs
            )

            def valid_response_json():
                data = {
                    "homeworks":
                        {
                            'homework_name': 'hw123',
                            'status': 'approved'
                        },
                    "current_date": random_timestamp
                }
                return data

            response.json = valid_response_json
            return response

        monkeypatch.setattr(requests, 'get', mock_response_get)

        import assistant_bot

        func_name = 'check_response'
        response = assistant_bot.get_api_answer(current_timestamp)
        try:
            homeworks = assistant_bot.check_response(response)
        except:
            pass
        else:
            assert not homeworks, (
                f'Function `{func_name} should process API response with '
                '`homeworks` key of not list type'
            )

    def test_check_response_empty(self, monkeypatch, random_timestamp,
                                  current_timestamp, api_url):
        def mock_empty_response_get(*args, **kwargs):
            response = MockResponseGET(
                *args, random_timestamp=random_timestamp,
                current_timestamp=current_timestamp,
                **kwargs
            )

            def json_invalid():
                data = {
                }
                return data

            response.json = json_invalid
            return response

        monkeypatch.setattr(requests, 'get', mock_empty_response_get)

        import assistant_bot

        func_name = 'check_response'
        result = assistant_bot.get_api_answer(current_timestamp)
        try:
            assistant_bot.check_response(result)
        except:
            pass
        else:
            assert False, (
                f'Function `{func_name} should raise error for API response '
                'with empty dictionary'
            )

    def test_api_response_timeout(self, monkeypatch, random_timestamp,
                                  current_timestamp, api_url):
        def mock_response_get(*args, **kwargs):
            response = MockResponseGET(
                *args, random_timestamp=random_timestamp,
                current_timestamp=current_timestamp,
                http_status=HTTPStatus.REQUEST_TIMEOUT, **kwargs
            )
            return response

        monkeypatch.setattr(requests, 'get', mock_response_get)

        import assistant_bot

        func_name = 'check_response'
        try:
            assistant_bot.get_api_answer(current_timestamp)
        except:
            pass
        else:
            assert False, (
                f'Function `{func_name}` should process API response with '
                'response status other than 200'
            )
