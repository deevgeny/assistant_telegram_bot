class ApiEndpointFatalException(Exception):
    """API endpoint fatal exception."""

    ...


class ApiEndpointHttpResponseException(Exception):
    """API endpoint http response exception."""

    ...


class ApiResponseException(Exception):
    """API response exception."""

    ...


class ApiHomeworkStatusException(Exception):
    """API homework status exception."""

    ...


class TelegramSendMessageException(Exception):
    """Telegram send message exception."""

    ...
