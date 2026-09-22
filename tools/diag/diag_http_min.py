#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最小复现：ThreadingHTTPServer + BaseHTTPRequestHandler 在同一进程内自测。

排除网络/浏览器因素，只验证「HTTP 层能不能写出响应」。
用法：python tools/diag/diag_http_min.py
"""
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 18642


class H(BaseHTTPRequestHandler):
    server_version = "MinTest/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        print("  [srv-log]", fmt % args, flush=True)

    def do_GET(self):
        body = b"<h1>hello</h1>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def server_thread(httpd):
    try:
        httpd.serve_forever()
    except Exception as e:
        print("!! serve_forever 退出:", type(e).__name__, e, flush=True)


def main():
    print(f"python {sys.version.split()[0]}  ({sys.executable})")
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    t = threading.Thread(target=server_thread, args=(httpd,), daemon=True)
    t.start()
    time.sleep(0.3)

    req = b"GET / HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n"
    last_err = None
    for attempt in range(3):
        try:
            s = socket.create_connection(("127.0.0.1", PORT), timeout=5)
            s.settimeout(5)
            s.sendall(req)
            chunks = []
            while True:
                b = s.recv(4096)
                if not b:
                    break
                chunks.append(b)
            s.close()
            data = b"".join(chunks)
            print(f"尝试{attempt + 1}: 收到 {len(data)} 字节")
            if data:
                print(data[:200].decode("utf-8", "replace"))
                print("=> 结论：标准库 HTTP 层正常")
                httpd.shutdown()
                return 0
            print("=> 收到 0 字节！标准库层就有问题")
        except Exception as e:
            last_err = e
            print(f"尝试{attempt + 1}: 客户端异常 {type(e).__name__}: {e}")
        time.sleep(0.3)

    print("=> 结论：复现失败（服务端没有正常响应）", last_err or "")
    httpd.shutdown()
    return 1


if __name__ == "__main__":
    sys.exit(main())
