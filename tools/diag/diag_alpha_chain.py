#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最小实验：确定"参考图 alpha → 输出 alpha"这条链上每一步的真实取值。

不跑扩散（秒级完成），只用 LoadImage 的 MASK（= 参考图 alpha）做实验。
参考图用的是"透明区角上有明确 alpha 标记"的图，逐点核对而不是看统计量。

用法：python tools/diag/diag_alpha_chain.py
"""
import json
import os
import struct
import sys
import time
import urllib.request
import urllib.error
import uuid
import zlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

COMFY = "http://127.0.0.1:8188"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
COMFY_OUT = os.path.join(_os.environ.get("QWEN21_COMFY_ROOT"),
                         "ComfyUI", "output")
HERE = os.path.dirname(os.path.abspath(__file__))

# 探针图：只有 4 个区域，alpha 依次是 0 / 85 / 170 / 255，横排四等分
LEVELS = [0, 85, 170, 255]


def make_probe(path, w=256, h=64):
    raw = bytearray()
    seg = w // len(LEVELS)
    for y in range(h):
        raw.append(0)
        for x in range(w):
            a = LEVELS[min(x // seg, len(LEVELS) - 1)]
            raw.extend((200, 60, 60, a))
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += chunk(b"IEND", b"")
    open(path, "wb").write(png)


def alpha_row(path, y=2):
    """读第 y 行，返回按四段取样的 (alpha) 四个值。"""
    d = open(path, "rb").read()
    pos, w, h, ct, idat = 8, None, None, None, b""
    while pos + 12 <= len(d):
        ln = struct.unpack(">I", d[pos:pos + 4])[0]
        tag = d[pos + 4:pos + 8]
        body = d[pos + 8:pos + 8 + ln]
        if tag == b"IHDR":
            w, h, _, ct = struct.unpack(">IIBB", body[:10])
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break
        pos += 12 + ln
    ch = {0: 1, 2: 3, 4: 2, 6: 4}[ct]
    raw = zlib.decompress(idat)
    stride = w * ch
    prev = bytearray(stride)
    for yy in range(min(h, y + 1)):
        off = yy * (stride + 1)
        f = raw[off]
        line = bytearray(raw[off + 1: off + 1 + stride])
        for i in range(stride):
            a = line[i - ch] if i >= ch else 0
            b = prev[i]
            c = prev[i - ch] if i >= ch else 0
            if f == 1:
                pr = a
            elif f == 2:
                pr = b
            elif f == 3:
                pr = (a + b) // 2
            elif f == 4:
                pp = a + b - c
                pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
            else:
                pr = 0
            line[i] = (line[i] + pr) & 0xFF
        prev = line
    seg = w // len(LEVELS)
    out = []
    for k in range(len(LEVELS)):
        x = k * seg + seg // 2
        out.append(line[x * ch + (ch - 1)] if ch > 1 else line[x])
    return f"ct={ct}", out


def upload(path, name):
    b = "----chain" + uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{name}\"\r\n"
            "Content-Type: image/png\r\n\r\n").encode()
    body += open(path, "rb").read()
    body += f"\r\n--{b}\r\n".encode()
    body += (f"Content-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--{b}--\r\n").encode()
    req = urllib.request.Request(COMFY + "/upload/image", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    with OPENER.open(req, timeout=60) as r:
        return json.loads(r.read().decode())


def run(wf, label):
    req = urllib.request.Request(COMFY + "/prompt",
                                 data=json.dumps({"prompt": wf, "client_id": str(uuid.uuid4())}).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        res = json.loads(OPENER.open(req, timeout=60).read().decode())
    except urllib.error.HTTPError as e:
        print(f"  {label}: 提交被拒 {e.read().decode('utf-8', 'replace')[:200]}")
        return
    pid = res.get("prompt_id")
    for _ in range(180):
        time.sleep(1)
        h = json.loads(OPENER.open(f"{COMFY}/history/{pid}", timeout=30).read().decode())
        if pid in h:
            break
    e = h.get(pid, {})
    st = (e.get("status") or {})
    errs = [f"{ (m[1] or {}).get('node_type') }: {(m[1] or {}).get('exception_message')}"
            for m in (st.get("messages") or [])
            if isinstance(m, list) and m[0] == "execution_error"]
    print(f"  {label}: {st.get('status_str')}" + (("  ERR " + "; ".join(errs)) if errs else ""))
    for node, o in sorted((e.get("outputs") or {}).items()):
        for im in o.get("images") or []:
            p = os.path.join(COMFY_OUT, im.get("subfolder", ""), im["filename"])
            if os.path.exists(p):
                ct, vals = alpha_row(p)
                print(f"      node{node} {im['filename']}  {ct}  四段alpha={vals}")


def main():
    probe = os.path.join(HERE, "_alpha_chain_probe.png")
    make_probe(probe)
    ct, vals = alpha_row(probe)
    print(f"探针图：四段 alpha 应为 {LEVELS}  →  实测 {vals}")
    name = upload(probe, "dsh_alpha_chain.png")["name"]
    print(f"已上传 {name}\n")

    L = {"1": {"class_type": "LoadImage", "inputs": {"image": name}}}

    print("每一步的四段值（对照 L=0/85/170/255）：")
    run(dict(L, **{"2": {"class_type": "MaskToImage", "inputs": {"mask": ["1", 1]}},
                   "3": {"class_type": "SaveImage",
                         "inputs": {"images": ["2", 0], "filename_prefix": "ch1_mask2img"}}}),
        "1) LoadImage.MASK -> MaskToImage  （=参考图 alpha 的灰度）")

    run(dict(L, **{"2": {"class_type": "InvertMask", "inputs": {"mask": ["1", 1]}},
                   "3": {"class_type": "MaskToImage", "inputs": {"mask": ["2", 0]}},
                   "4": {"class_type": "SaveImage",
                         "inputs": {"images": ["3", 0], "filename_prefix": "ch2_invert"}}}),
        "2) LoadImage.MASK -> InvertMask -> MaskToImage")

    run(dict(L, **{"2": {"class_type": "JoinImageWithAlpha",
                         "inputs": {"image": ["1", 0], "alpha": ["1", 1]}},
                   "3": {"class_type": "SaveImage",
                         "inputs": {"images": ["2", 0], "filename_prefix": "ch3_join_direct"}}}),
        "3) JoinImageWithAlpha(mask 直接)  -> 输出 alpha")

    run(dict(L, **{"2": {"class_type": "InvertMask", "inputs": {"mask": ["1", 1]}},
                   "3": {"class_type": "JoinImageWithAlpha",
                         "inputs": {"image": ["1", 0], "alpha": ["2", 0]}},
                   "4": {"class_type": "SaveImage",
                         "inputs": {"images": ["3", 0], "filename_prefix": "ch4_join_inverted"}}}),
        "4) JoinImageWithAlpha(mask 先取反) -> 输出 alpha")

    run(dict(L, **{"2": {"class_type": "ImageToMask",
                         "inputs": {"image": ["1", 0], "channel": "alpha"}},
                   "3": {"class_type": "MaskToImage", "inputs": {"mask": ["2", 0]}},
                   "4": {"class_type": "SaveImage",
                         "inputs": {"images": ["3", 0], "filename_prefix": "ch5_img2mask"}}}),
        "5) ImageToMask(IMAGE, alpha)  （与 mask 输出对比）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
