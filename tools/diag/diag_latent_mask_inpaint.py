#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""可行性实验：Qwen-Image-2.1 能否用"潜空间掩码重绘"做像素级局部编辑。

动机：圈选/涂抹引导（视觉提示）已验证可用，但它本质是**整图重绘 + 提示词约束**，
圈外像素不保证逐点不变。若要"圈外绝对不动"，标准做法是潜空间掩码：
    VAEEncode(原图) → SetLatentNoiseMask(掩码) → KSampler(denoise≈1)
ComfyUI 的 SetLatentNoiseMask 里 **白色区域 = 重新生成，黑色 = 保留**。

但 2.1 的 latent 走的是 TextEncodeQwenImage21 的输出（64 通道、16× 压缩、未 patch），
且 Transformer 用 block-causal 注意力区分画面块，**标准 inpaint 掩码能否被正确消费需要实测**。

做法：拿一张图 → 造一个"只在某处变白"的掩码 → 用带掩码的 latent 重绘该处 → 看圈外是否逐点不变。

用法：python tools/diag/diag_latent_mask_inpaint.py
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
COMFY_OUT = os.path.join(os.environ.get("QWEN21_COMFY_ROOT",
                                        r"D:\applications\comfy-ui\ComfyUI_windows_portable"),
                         "ComfyUI", "output")
COMFY_IN = os.path.join(os.environ.get("QWEN21_COMFY_ROOT",
                                       r"D:\applications\comfy-ui\ComfyUI_windows_portable"),
                        "ComfyUI", "input")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))


def write_mask_png(path, w, h, white_box):
    """写一张灰度 PNG：白 = 重绘区（一个矩形），黑 = 保留区。"""
    x0, y0, x1, y1 = white_box
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            raw.append(255 if (x0 <= x < x1 and y0 <= y < y1) else 0)
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += chunk(b"IEND", b"")
    open(path, "wb").write(png)


def post(wf):
    req = urllib.request.Request(COMFY + "/prompt",
                                 data=json.dumps({"prompt": wf, "client_id": str(uuid.uuid4())}).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        return json.loads(OPENER.open(req, timeout=60).read().decode())
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode("utf-8", "replace")[:900]}


def wait(pid, limit=900):
    for _ in range(limit):
        time.sleep(1)
        h = json.loads(OPENER.open(f"{COMFY}/history/{pid}", timeout=30).read().decode())
        if pid in h:
            return h[pid]
    return {}


def main():
    # 底图：用工作台里已有的产物，复制到 ComfyUI 的 input
    src = os.path.join(ROOT, "outputs", "a060749c9d62", "bd846348_00001_.png")
    if not os.path.exists(src):
        print("底图不存在:", src)
        return 1
    base_name = "dsh_inpaint_base.png"
    open(os.path.join(COMFY_IN, base_name), "wb").write(open(src, "rb").read())
    print(f"底图已放入 ComfyUI input: {base_name}")

    mask_name = "dsh_inpaint_mask.png"
    # 掩码白色区域：脸部偏左（约 x 350~560, y 250~430），目标改成金色眼睛区域
    write_mask_png(os.path.join(COMFY_IN, mask_name), 1024, 1024, (330, 230, 580, 460))
    print(f"掩码已写入: {mask_name}（白区 x330-580 / y230-460）")

    prompt = ("Change the eyes to bright golden yellow, keep the character, the pose, "
              "the clothing and the background exactly the same.")
    wf = {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": "qwen_image_2.1_int8_convrot.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": "qwen3vl_8b_int8_convrot.safetensors",
                         "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader",
              "inputs": {"vae_name": "qwen_image_2.1_vae_bf16.safetensors"}},
        "10": {"class_type": "LoadImage", "inputs": {"image": base_name}},
        "11": {"class_type": "LoadImage", "inputs": {"image": mask_name}},
        # 把参考图的 alpha 当作参考：这里只取 IMAGE 通道
        "5": {"class_type": "TextEncodeQwenImage21",
              "inputs": {"clip": ["2", 0], "prompt": prompt, "negative_prompt": " ",
                         "vae": ["3", 0], "resolution": 0, "images.image_1": ["10", 0]}},
        "31": {"class_type": "VAEEncode", "inputs": {"pixels": ["10", 0], "vae": ["3", 0]}},
        "32": {"class_type": "SetLatentNoiseMask",
               "inputs": {"samples": ["5", 2], "mask": ["11", 1]}},
        "6": {"class_type": "KSampler",
              "inputs": {"model": ["1", 0], "positive": ["5", 0], "negative": ["5", 1],
                         "latent_image": ["32", 0], "seed": 24680, "steps": 25, "cfg": 1.0,
                         "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveImage",
              "inputs": {"images": ["8", 0], "filename_prefix": "inpaint_probe"}},
    }
    res = post(wf)
    print("提交:", json.dumps(res, ensure_ascii=False)[:400])
    pid = res.get("prompt_id")
    if not pid:
        return 1
    e = wait(pid)
    st = (e.get("status") or {})
    print("status:", st.get("status_str"))
    for m in st.get("messages") or []:
        if isinstance(m, list) and m[0] == "execution_error":
            d = m[1] or {}
            print(f"ERR node{d.get('node_id')} {d.get('node_type')}: "
                  f"{d.get('exception_type')} {d.get('exception_message')}")
    for node, o in sorted((e.get("outputs") or {}).items()):
        for im in o.get("images") or []:
            p = os.path.join(COMFY_OUT, im["filename"])
            print(f"  node{node} -> {im['filename']}  存在={os.path.exists(p)}")
    print("\n下一步：把产物与底图逐像素比对 —— 白区外是否完全没变。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
