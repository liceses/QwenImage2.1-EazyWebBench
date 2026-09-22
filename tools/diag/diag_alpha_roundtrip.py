#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""实测 ComfyUI 的 LoadImage / SaveImage 是否保留 alpha 通道。

背景：Qwen-Image-2.1 的 VAE 解码输出是 4 通道（RGB + alpha，已由
decoder.head.2.weight 形状 [4,144,1,3,3] 证实），所以"透明图"在权重层面可行。
但工作台用的是 LoadImage + SaveImage 这条最普通的链路，必须确认 alpha 不会
在中途被静默丢掉（ComfyUI 的 LoadImage 长期只输出 RGB）。

做法：生成一张 4 通道 PNG（中心不透明、四周全透明）→ 上传 → LoadImage → SaveImage
      → 读回输出文件的通道数与角落像素的 alpha。

用法：python tools/diag/diag_alpha_roundtrip.py
"""
import json
import os
import struct
import sys
import urllib.request
import uuid
import zlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

COMFY = "http://127.0.0.1:8188"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


# ---------- 最小 PNG 读写（只用标准库，避免依赖 Pillow）----------
def write_rgba_png(path, w, h, pixel_fn):
    raw = bytearray()
    for y in range(h):
        raw.append(0)                       # filter: none
        for x in range(w):
            raw.extend(pixel_fn(x, y))

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))   # 6 = RGBA
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def read_png_info(path):
    """返回 (w, h, color_type, bit_depth, 角落像素的 RGBA)。"""
    with open(path, "rb") as f:
        data = f.read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "不是 PNG"
    pos, w, h, depth, ctype, idat = 8, None, None, None, None, b""
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        if tag == b"IHDR":
            w, h, depth, ctype = struct.unpack(">IIBB", body[:10])
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break
        pos += 12 + ln
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    raw = zlib.decompress(idat)
    stride = w * channels
    # 只解第一行（filter 应为 0，因为我们自己写的时候用的是 none；
    # 若是 SaveImage 的输出，PNG 自己会选 filter，所以这里做通用反滤波）
    px = _decode_first_row(raw, w, channels, depth)
    corner = tuple(px[:channels]) + (None,) * (4 - channels)
    return w, h, ctype, depth, corner


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    return a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)


def _decode_first_row(raw, w, channels, depth):
    if depth != 8:
        return []
    stride = w * channels
    ftype = raw[0]
    line = list(raw[1:1 + stride])
    if ftype == 0:
        return line
    # 第一行没有上一行，left/up 全 0
    out = []
    for i, v in enumerate(line):
        left = out[i - channels] if i >= channels else 0
        up = 0
        upleft = 0
        if ftype == 1:
            pred = left
        elif ftype == 2:
            pred = up
        elif ftype == 3:
            pred = (left + up) // 2
        elif ftype == 4:
            pred = _paeth(left, up, upleft)
        else:
            pred = 0
        out.append((v + pred) & 0xFF)
    return out


# ---------- ComfyUI 调用 ----------
def upload(path, name):
    boundary = "----dsh" + uuid.uuid4().hex
    with open(path, "rb") as f:
        content = f.read()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{name}"\r\n'
        "Content-Type: image/png\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}\r\n".encode()
    body += (
        f'Content-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n--{boundary}--\r\n'
    ).encode()
    req = urllib.request.Request(
        COMFY + "/upload/image", data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with OPENER.open(req, timeout=60) as r:
        return json.loads(r.read().decode())


def run_prompt(wf):
    req = urllib.request.Request(
        COMFY + "/prompt",
        data=json.dumps({"prompt": wf, "client_id": str(uuid.uuid4())}).encode(),
        headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=120) as r:
        return json.loads(r.read().decode())


def history(pid):
    with OPENER.open(f"{COMFY}/history/{pid}", timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(here, "_alpha_probe_in.png")
    # 中心不透明(255,0,0,255)，四周全透明(0,0,0,0)
    write_rgba_png(src, 64, 64, lambda x, y: (255, 0, 0, 255) if (16 <= x < 48 and 16 <= y < 48) else (0, 0, 0, 0))
    print("输入图:", os.path.basename(src))
    print("  写入属性:", read_png_info(src)[2], "(6=RGBA)  角落像素 RGBA =", read_png_info(src)[4])

    up = upload(src, "dsh_alpha_probe.png")
    name = up.get("name")
    print("  上传到 ComfyUI:", up)

    wf = {
        "1": {"class_type": "LoadImage", "inputs": {"image": name}},
        # 用 SaveImage 保存（工作台当前就是这条链路）
        "2": {"class_type": "SaveImage", "inputs": {"images": ["1", 0], "filename_prefix": "dsh_alpha_probe"}},
        # 同时把 alpha 单独提出来，看 LoadImage 有没有把它变成 MASK
        "3": {"class_type": "ImageToMask", "inputs": {"image": ["1", 0], "channel": "alpha"}},
        "4": {"class_type": "MaskToImage", "inputs": {"mask": ["3", 0]}},
        "5": {"class_type": "SaveImage", "inputs": {"images": ["4", 0], "filename_prefix": "dsh_alpha_mask"}},
    }
    res = run_prompt(wf)
    if "prompt_id" not in res:
        print("  提交失败:", json.dumps(res, ensure_ascii=False)[:800])
        return 1
    pid = res["prompt_id"]
    print("  已提交 prompt_id =", pid)

    import time
    for _ in range(90):
        time.sleep(1)
        h = history(pid)
        if pid in h:
            break
    h = history(pid)
    entry = h.get(pid, {})
    outs = entry.get("outputs", {})
    print("\n=== 输出文件 ===")
    outdir = os.path.join(os.path.dirname(os.path.dirname(here)), "..")
    comfy_out = os.path.join(os.environ.get("QWEN21_COMFY_ROOT",
                             r"D:\applications\comfy-ui\ComfyUI_windows_portable"),
                             "ComfyUI", "output")
    verdict = {}
    for node, o in outs.items():
        for im in o.get("images", []):
            p = os.path.join(comfy_out, im.get("subfolder", ""), im["filename"])
            if not os.path.exists(p):
                print(f"  node{node}  {im['filename']}  (文件没找到: {p})")
                continue
            w, hh, ctype, depth, corner = read_png_info(p)
            kind = {0: "灰度", 2: "RGB", 3: "调色板", 4: "灰度+A", 6: "RGBA"}[ctype]
            print(f"  node{node}  {im['filename']}")
            print(f"      {w}x{hh}  color_type={ctype} ({kind})  bit_depth={depth}")
            print(f"      左上角像素 = {corner}")
            verdict[node] = (ctype, corner)

    print("\n=== 判定 ===")
    if "2" in verdict:
        ctype, corner = verdict["2"]
        if ctype == 6:
            print("  ✅ SaveImage 保留了 alpha（color_type=6 = RGBA）")
        else:
            print(f"  ❌ SaveImage 输出是 {ctype}（{ {0:'灰度',2:'RGB',6:'RGBA'}.get(ctype,ctype) }）"
                  " → **alpha 在这条链路上被丢弃**")
    if "5" in verdict:
        ctype, corner = verdict["5"]
        print(f"  参考：单独把 alpha 当 MASK 保存 → color_type={ctype}，角落像素={corner}")
        if ctype == 0 and corner[0] == 255:
            print("     （角落是白 = LoadImage 的 alpha 通道被当成全不透明，alpha 信息已丢失）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
