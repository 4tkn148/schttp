from collections import namedtuple

Response = namedtuple(
    typename="Response",
    field_names=["status", "message", "headers", "body"]
)

URL = namedtuple(
    typename="URL",
    field_names=["scheme", "auth", "hostname", "port", "path"]
)