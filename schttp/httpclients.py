from .models import Response, URL
from .exceptions import *
from .structures import CaseInsensitiveDict
from .utils import parse_url, ip_from_hostname, craft_request, \
    decode_content, stream_body, tunnel_connect
from typing import Optional
from base64 import b64encode
from socket import socket

default_context = __import__("ssl").create_default_context()
unverified_context = __import__("ssl")._create_unverified_context()

class HTTPClient:
    def __init__(self,
            timeout: float = 30,
            proxy_url: Optional[str] = None,
            remote_dns: bool = True,
            ssl_verify: bool = True):
        self.timeout = float(timeout)
        self.remote_dns = remote_dns
        self.ssl_verify = ssl_verify
        self._proxy_url = parse_url(proxy_url) if proxy_url else None
        self._conn_map = {}

    def __enter__(self):
        return self
    
    def __exit__(self, *_):
        self.clear()

    def clear(self):
        for address in tuple(self._conn_map.keys()):
            self._close_connection(address)
    
    def request(self,
            method: str,
            url: str,
            body: Optional[bytes] = None,
            headers: Optional[dict] = None,
            chunk_size: Optional[int] = None,
            context=None) -> Response:
        if not isinstance(url, URL):
            url = parse_url(url)

        if not isinstance(headers, CaseInsensitiveDict):
            headers = CaseInsensitiveDict(headers)

        address = (
            url.hostname \
                if self.remote_dns \
                else ip_from_hostname(url.hostname),
            url.port
        )

        if not "Host" in headers:
            headers["Host"] = url.hostname
        
        if body is not None and not "Content-Length" in headers:
            headers["Content-Length"] = str(len(body))

        if url.auth and not "Authorization" in headers:
            headers["Authorization"] = "Basic " + b64encode(url.auth.encode()).decode()
        
        if not context and url.scheme == "https":
            context = default_context if self.ssl_verify else unverified_context
        
        try:
            conn = self._get_connection(address, context, url.hostname)
        except Exception as err:
            raise RequestException(err)

        try:
            # The code below crafts and sends the HTTP request to the server.
            conn.sendall(craft_request(method, url.path, tuple(headers.items()), body))

            # The code below processes the server's response.
            resp, _, resp_body = conn.recv(49152).partition(b"\r\n\r\n")
            if not resp:
                raise EmptyResponse("Empty response received")
            status_line, _, resp_headers = resp.decode().partition("\r\n")
            status, message = status_line.split(" ", 2)[1:]
            status = int(status)
            resp_headers = CaseInsensitiveDict(
                line.split(": ", 1)
                for line in resp_headers.splitlines()
            )
            resp_body = stream_body(
                conn, resp_headers,
                initial_body=resp_body,
                chunk_size=chunk_size)

            if (encoding := resp_headers.get("Content-Encoding")):
                resp_body = decode_content(resp_body, encoding)
            
            # If an `EmptyResponse` error occurs in a future request attempt
            # this value will be checked before creating another connection.
            conn._sent_request = True

            return Response(
                status=status,
                message=message,
                headers=resp_headers,
                body=resp_body)
        
        except Exception as err:
            self._close_connection(address)

            if isinstance(err, EmptyResponse) and conn._sent_request:
                # Retry request if previous request was successful.
                conn._sent_request = False
                return self.request(
                    method, url, body, headers,
                    chunk_size=chunk_size,
                    context=context)
            
            if not isinstance(err, RequestException):
                # Wrap foreign exceptions.
                err = RequestException(err)
            
            raise err

    def _get_connection(self,
            address,
            ssl_context=None, ssl_hostname=None):
        # Return cached connection for address.
        if (conn := self._conn_map.get(address)):
            return conn
        
        conn = socket()
        # Disable Nagle's algorithm on socket.
        conn.setsockopt(6, 1, 1)
        conn.settimeout(self.timeout)

        if self._proxy_url is None:
            conn.connect(address)
        else:
            tunnel_connect(conn, self._proxy_url, address)
        
        if ssl_context:
            conn = ssl_context.wrap_socket(
                conn,
                do_handshake_on_connect=False,
                suppress_ragged_eofs=False,
                server_hostname=ssl_hostname)
            conn.settimeout(self.timeout)
            conn.do_handshake()

        conn._sent_request = False
        self._conn_map[address] = conn
        return conn

    def _close_connection(self, address):
        conn = self._conn_map.pop(address)
        try:
            conn.shutdown(2)
        except OSError:
            pass
        conn.close()
