#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 Qwen-Image-2.1 的 VAE 能否吃进并吐出 4 通道（RGB + alpha）。

背景：decoder.head.2.weight 形状 [4,144,1,3,3] → 解码输出 4 通道；
encoder 的输入层是 conv1.weight [128,128,1,1,1]（patch 化），
颜色通道数在 patch 之后，所以从权重名看不出"吃 3 还是 4 通道"，只能实测。

做法（纯 ComfyUI 图，不跑扩散，几秒钟）：
  上传 RGBA 图 → LoadImage
    ├─ 分支 A：IMAGE 直接 VAEEncode → VAEDecode → SaveImage
    │            （若该 VAE 接受 4 通道，VAEDecode 输出应带 alpha）
    └─ 分支 B：LoadImage 的 MASK（= alpha）→ JoinImageWithAlpha → SaveImageWithAlpha
                 （验证"把 alpha 接回去"这条路可行，即输出侧有现成节点）

用法：python tools/diag/diag_vae_rgba.py
"""
import json
import os
import struct
import sys
import time
import urllib.request
import uuid
import zlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

COMFY = "http://127.0.0.1:8188"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
COMFY_ROOT = os.environ.get("QWEN21_COMFY_ROOT", r"D:\applications\comfy-ui\ComfyUI_windows_portable")
COMFY_OUT = os.path.join(COMFY_ROOT, "ComfyUI", "output")
HERE = os.path.dirname(os.path.abspath(__file__))


def write_rgba_png(path, w, h, fn):
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            raw.extend(fn(x, y))

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    open(path, "wb").write(png)


def png_info(path):
    data = open(path, "rb").read()
    pos, w, h, ctype, idat = 8, None, None, None, b""
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        if tag == b"IHDR":
            w, h, _, ctype = struct.unpack(">IIBB", body[:10])
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break
        pos += 12 + ln
    ch = {0: 1, 2: 3, 4: 2, 6: 4}[ctype]
    raw = zlib.decompress(idat)
    # 解第一行
    line = list(raw[1:1 + w * ch])
    f = raw[0]
    out = []
    for i, v in enumerate(line):
        left = out[i - ch] if i >= ch else 0
        pred = left if f == 1 else (0 if f == 0 else left)
        out.append((v + pred) & 0xFF)
    return w, h, ctype, tuple(out[:ch])


def upload(path, name):
    b = "----dsh" + uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{name}\"\r\n"
            "Content-Type: image/png\r\n\r\n").encode()
    body += open(path, "rb").read()
    body += f"\r\n--{b}\r\n".encode()
    body += (f"Content-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n"
             f"--{b}--\r\n").encode()
    req = urllib.request.Request(COMFY + "/upload/image", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    with OPENER.open(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    src = os.path.join(HERE, "_rgba_probe_in.png")
    write_rgba_png(src, 64, 64,
                   lambda x, y: (255, 0, 0, 255) if (16 <= x < 48 and 16 <= y < 48) else (0, 0, 0, 0))
    print("输入 RGBA 图:", png_info(src))
    up = upload(src, "dsh_rgba_probe.png")
    name = up["name"]
    print("上传:", name)

    wf = {
        "1": {"class_type": "LoadImage", "inputs": {"image": name}},
        "2": {"class_type": "VAELoader",
              "inputs": {"vae_name": "qwen_image_2.1_vae_bf16.safetensors"}},
        # A: image -> encode -> decode -> SaveImage
        "3": {"class_type": "VAEEncode", "inputs": {"pixels": ["1", 0], "vae": ["2", 0]}},
        "4": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["2", 0]}},
        "5": {"class_type": "SaveImage", "inputs": {"images": ["4", 0], "filename_prefix": "dsh_rgba_a"}},
        # 顺便看解码结果的通道数
        "6": {"class_type": "SplitImageChannels", "inputs": {"image": ["4", 0]}},
        # B: 把 LoadImage 的 alpha(MASK) 接回去 -> SaveImageWithAlpha
        "7": {"class_type": "JoinImageWithAlpha", "inputs": {"image": ["4", 0], "alpha": ["1", 1]}},
        "8": {"class_type": "SaveImageWithAlpha",
              "inputs": {"images": ["7", 0], "mask": ["1", 1], "filename_prefix": "dsh_rgba_b"}},
    }
    req = urllib.request.Request(COMFY + "/prompt",
                                 data=json.dumps({"prompt": wf, "client_id": str(uuid.uuid4())}).encode(),
                                 headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=120) as r:
        res = json.loads(r.read().decode())
    if "prompt_id" not in res:
        print("\n提交失败 / 图被拒绝：")
        print(json.dumps(res, ensure_ascii=False, indent=2)[:2500])
        return 1
    pid = res["prompt_id"]
    print("prompt_id =", pid)
    for _ in range(120):
        time.sleep(1)
        with OPENER.open(f"{COMFY}/history/{pid}", timeout=30) as r:
            h = json.loads(r.read().decode())
        if pid in h:
            break
    entry = h.get(pid, {})
    if entry.get("status", {}).get("status_str") == "error":
        print("\n执行报错：")
        print(json.dumps(entry["status"], ensure_ascii=False, indent=2)[:2500])
        return 1

    print("\n=== 输出文件 ===")
    for node, o in sorted((entry.get("outputs") or {}).items()):
        for im in o.get("images", []):
            p = os.path.join(COMFY_OUT, im.get("subfolder", ""), im["filename"])
            if os.path.exists(p):
                w, h, ctype, corner = png_info(p)
                kind = {0: "灰度", 2: "RGB", 4: "灰度+A", 6: "RGBA"}.get(ctype, ctype)
                print(f"  node{node}  {im['filename']}")
                print(f"      {w}x{h} color_type={ctype} ({kind}) 左上角={corner}")
            else:
                print(f"  node{node}  {im['filename']} (没找到文件)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
