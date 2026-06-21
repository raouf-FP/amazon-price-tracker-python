import base64
import select
import socket
import threading
from urllib.parse import urlparse

def parse_proxy(url):
    u = urlparse(url)
    return u.username, u.password, u.hostname, u.port

def _pipe(a, b):
    sockets = [a, b]
    try:
        while True:
            r, _, _ = select.select(sockets, [], [], 120)
            if not r:
                break
            for s in r:
                data = s.recv(65536)
                if not data:
                    return
                (b if s is a else a).sendall(data)
    except OSError:
        pass
    finally:
        for s in sockets:
            try:
                s.close()
            except OSError:
                pass

def _make_handler(up_host, up_port, auth_header):
    def handle(client):
        try:
            data = b""
            while b"\r\n\r\n" not in data:
                chunk = client.recv(65536)
                if not chunk:
                    client.close()
                    return
                data += chunk
            header_blob, _, rest = data.partition(b"\r\n\r\n")
            first_line = header_blob.split(b"\r\n", 1)[0].decode("latin-1", "replace")
            parts = first_line.split(" ")
            method = parts[0].upper() if parts else ""

            up = socket.create_connection((up_host, up_port), timeout=30)

            if method == "CONNECT":
                target = parts[1]
                req = (f"CONNECT {target} HTTP/1.1\r\n"
                       f"Host: {target}\r\n{auth_header}\r\n")
                up.sendall(req.encode("latin-1"))
                resp = b""
                while b"\r\n\r\n" not in resp:
                    c = up.recv(65536)
                    if not c:
                        break
                    resp += c
                status_line = resp.split(b"\r\n", 1)[0]
                if b" 200" in status_line:
                    client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                    _pipe(client, up)
                else:
                    client.sendall(resp)
                    client.close()
                    up.close()
            else:
                forwarded = header_blob + b"\r\n" + auth_header.encode("latin-1") + b"\r\n" + rest
                up.sendall(forwarded)
                _pipe(client, up)
        except OSError:
            try:
                client.close()
            except OSError:
                pass

    return handle

def start_local_forwarder(upstream_url):
    user, password, up_host, up_port = parse_proxy(upstream_url)
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    auth_header = f"Proxy-Authorization: Basic {token}\r\n"
    handle = _make_handler(up_host, up_port, auth_header)

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(128)
    local_port = srv.getsockname()[1]

    def serve():
        while True:
            try:
                client, _ = srv.accept()
            except OSError:
                break
            threading.Thread(target=handle, args=(client,), daemon=True).start()

    threading.Thread(target=serve, daemon=True).start()
    start_local_forwarder._servers = getattr(start_local_forwarder, "_servers", [])
    start_local_forwarder._servers.append(srv)
    return local_port

def apply_proxy(options, proxy_url):
    if not proxy_url:
        return options
    user, password, host, port = parse_proxy(proxy_url)
    if user and password:
        local_port = start_local_forwarder(proxy_url)
        options.add_argument(f"--proxy-server=http://127.0.0.1:{local_port}")
    else:
        options.add_argument(f"--proxy-server=http://{host}:{port}")
    return options
