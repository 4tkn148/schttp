from .models import URL
from .structures import CaseInsensitiveDict
from functools import lru_cache
from socket import socket, gethostbyname
from base64 import b64encode
from gzip import decompress as gzip_decompress
from zlib import decompress as zlib_decompress
from brotli import decompress as brotli_decompress

default_ports = {
    "http": 80,
    "https": 443
}

def tunnel_connect(conn, proxy_url, address):
    conn.connect((proxy_url.hostname, proxy_url.port))

    if proxy_url.scheme in ("http", "https"):
        # HTTP proxy
        proxy_headers = CaseInsensitiveDict()
        if proxy_url.auth:
            proxy_headers["Proxy-Authorization"] = "Basic " + b64encode(proxy_url.auth.encode()).decode()
        
        # Send initial CONNECT request to proxy server.
        conn.sendall(craft_request("CONNECT", f"{address[0]}:{address[1]}", tuple(proxy_headers.items())))

        if not (resp := conn.recv(4096)).partition(b" ")[2].startswith(b"200"):
            # Proxy server did not return status 200 for initial CONNECT request.
            raise ProxyError(
                f"Malformed CONNECT response: {resp.splitlines()[0]}")
        
        return True

def stream_body(
        conn, headers,
        initial_body=None, chunk_size=None):
    chunk_size = chunk_size or 262144
    body = initial_body or b""

    if (exp_length := headers.get("content-length")):
        # Content-Length
        exp_length = int(exp_length)
        while exp_length > len(body):
            body += conn.recv(chunk_size)
        return body

    elif headers.get("transfer-encoding") == "chunked":
        # Transfer-Encoding: chunked
        while not body.endswith(b"0\r\n\r\n"):
            body += conn.recv(chunk_size)
        temp_body = b""
        index = 0
        while True:
            new_index = body.find(b"\r\n", index)
            length = int(body[index : new_index], 16)
            if not length:
                break
            index = new_index + 2 + length + 2
            temp_body += body[new_index + 2 : index - 2]
        return temp_body

    else:
        # No transfer header specified.
        # Stream chunks until an empty one is received.
        while True:
            if (chunk := conn.recv(chunk_size)):
                body += chunk
            else:
                break
        return body

def craft_request(method, path, headers, body=None):
    return b"".join((
        # Status line
        (method + " " + path + " HTTP/1.1\r\n").encode(),
        # Headers
        "".join([
            name + ": " + str(value) + "\r\n"
            for name, value in headers
            if value is not None
        ]).encode(),
        # Body separator
        b"\r\n",
        # Body
        body is not None and body or b""
    ))
    
@lru_cache()
def ip_from_hostname(hostname):
    return gethostbyname(hostname)

def parse_url(url):
    scheme, _, url = url.partition(":")
    url, _, path = url[2:].partition("/")
    auth, _, url = url.rpartition("@")
    hostname, _, port = url.partition(":")

    scheme = scheme.lower()
    auth = auth if auth else None
    hostname = hostname.lower()
    port = port and int(port) or default_ports.get(scheme)
    path = "/" + path.partition("#")[0]

    return URL(
        scheme=scheme,
        auth=auth,
        hostname=hostname,
        port=port,
        path=path
    )

def decode_content(data, encoding):
    if encoding == "gzip":
        return gzip_decompress(data)

    elif encoding == "deflate":
        return zlib_decompress(data, -15)

    elif encoding == "br":
        return brotli_decompress(data)

    return data
