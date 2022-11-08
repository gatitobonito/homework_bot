class BaseError(Exception):
    def __init__(self, msg, code):
        self.msg = msg
        self.code = code


class APIResponseError(BaseError):
    pass


class HTTPStatusError(BaseError):
    pass


class CheckTokenError(BaseError):
    pass
