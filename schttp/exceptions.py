class RequestException(Exception):
    pass

class EmptyResponse(RequestException):
    pass

class ProxyError(RequestException):
    pass