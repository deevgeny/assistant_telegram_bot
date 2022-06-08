class ApiEndpointFatalException(Exception):
    """Custom API endpoint fatal exception."""

    ...


class ApiEndpointHttpResponseException(Exception):
    """Custom API endpoint fatal exception."""

    ...


class ApiResponseException(Exception):
    """Custom API response exception."""

    ...


class ApiHomeworkStatusException(Exception):
    """Custom API homework exception."""

    ...


class TelegramSendMessageException(Exception):
    """Custom telegram send message exception."""

    ...
