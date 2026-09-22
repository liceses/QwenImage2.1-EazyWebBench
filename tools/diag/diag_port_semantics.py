#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""隔离实验：Windows loopback 上 SO_REUSEADDR / 双绑 / 空闲端口 connect 的真实语义。

结论用于决定"怎么可靠地判断端口是否已被占用"。
用法：python tools/diag/diag_port_semantics.py [port]
"""
import socket
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 18660
HOST = "127.0.0.1"


def try_bind(port, reuse, exclusive=False):
    """返回 (ok, 描述)。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if exclusive:
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        except (AttributeError, OSError) as e:
            return False, f"SO_EXCLUSIVEADDRUSE 不可用: {e}"
    if reuse:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind((HOST, port))
        s.listen(8)
        return True, s
    except OSError as e:
        s.close()
        return False, f"{type(e).__name__}(errno={e.errno}, winerror={getattr(e, 'winerror', None)}): {e}"


def try_connect(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    t0 = time.time()
    try:
        s.connect((HOST, port))
        return f"CONNECTED ({time.time() - t0:.2f}s)"
    except Exception as e:
        return f"{type(e).__name__}: {e} ({time.time() - t0:.2f}s)"
    finally:
        s.close()


def main():
    print(f"python {sys.version.split()[0]}  port={PORT}\n")

    print("[1] 空闲端口 connect 行为（用于判断能否用 connect 探针）")
    print("    ", try_connect(PORT))

    print("\n[2] 第一个监听者：SO_REUSEADDR=True（= ThreadingHTTPServer 默认）")
    ok1, h1 = try_bind(PORT, reuse=True)
    print("     bind:", ok1 if ok1 else h1)
    if not ok1:
        return 1
    print("     listen 已建立，pid 内第一个 socket")

    print("\n[3] 第二个 socket 再绑同一端口 —— reuse=True")
    ok2, h2 = try_bind(PORT, reuse=True)
    print("     bind:", "成功（双绑！）" if ok2 else h2)

    print("\n[4] 第二个 socket —— reuse=False")
    ok3, h3 = try_bind(PORT, reuse=False)
    print("     bind:", "成功" if ok3 else h3)

    print("\n[5] 第三个 socket —— SO_EXCLUSIVEADDRUSE")
    ok4, h4 = try_bind(PORT, reuse=False, exclusive=True)
    print("     bind:", "成功" if ok4 else h4)

    print("\n[6] 此时 connect 一次:", try_connect(PORT))

    print("\n[7] 关闭第一个监听者后，再绑 —— reuse=False")
    h1.close()
    time.sleep(0.5)
    ok5, h5 = try_bind(PORT, reuse=False)
    print("     bind:", "成功" if ok5 else h5)

    for h in (h2, h3, h4, h5):
        try:
            if isinstance(h, socket.socket):
                h.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
