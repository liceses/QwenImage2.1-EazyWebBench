#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第九组诊断：定位"编辑不保留原图"的可调因素。

官方 edit 模板 Note 原文：
  - "resolution is a total pixel budget (not width or height). Aspect ratio is preserved."
  - "Official default is 1024. The model supports up to 2048."
  - "**This template starts at 0: no resize beyond a multiple of 32.**"

即官方 edit 模板的 resolution 默认是 **0**（参考图只对齐到 32 倍数，不缩放到 1024 预算）。
本工作台此前硬编码 resolution=1024，会把参考图重缩放到 ~800x1312。

本组对照（参考图 = 狼狼.png 945x1562，prompt 固定为"只改发色"）：
  Q1 resolution=0   steps=30   ← 官方模板默认
  Q2 resolution=1024 steps=30  ← 本工作台原行为（基线）
  Q3 resolution=0   steps=50   ← 官方推荐步数
  Q4 resolution=2048 steps=40  ← 更大像素预算
并输出与参考图的 MAE（越小越像原图）。
"""
import json
import os
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8188"
COMFY_OUT = r"D:\applications\comfy-ui\ComfyUI_windows_portable\ComfyUI\output"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "diag_out9")
os.makedirs(OUT, exist_ok=True)
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

REF = "ref_19ed6c27f2.png"
REF_LOCAL = os.path.join(HERE, "..", "..", "uploads", REF)

PROMPT = ("Change the girl's hair color in <image1> to pink. "
          "Keep the pose, the outfit, the tail, the face and the background exactly the same.")


def post(path, payload):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=60) as r:
        return json.load(r)


def get(path, timeout=15):
    with OPENER.open(BASE + path, timeout=timeout) as r:
        return json.load(r)


def build(prompt, ref, resolution, steps, seed=555):
    return {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": "qwen_image_2.1_int8_convrot.safetensors",
                         "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": "qwen3vl_8b_int8_convrot.safetensors",
                         "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader",
              "inputs": {"vae_name": "qwen_image_2.1_vae_bf16.safetensors"}},
        "5": {"class_type": "TextEncodeQwenImage21",
              "inputs": {"clip": ["2", 0], "prompt": prompt, "negative_prompt": " ",
                         "vae": ["3", 0], "resolution": resolution,
                         "images": {"image_1": ["10", 0]}}},
        "6": {"class_type": "KSampler",
              "inputs": {"model": ["1", 0], "positive": ["5", 0], "negative": ["5", 1],
                         "latent_image": ["5", 2], "seed": seed, "steps": steps, "cfg": 1.0,
                         "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "diag9"}},
        "10": {"class_type": "LoadImage", "inputs": {"image": ref}},
    }


def run(label, resolution, steps):
    print(f"\n{'=' * 70}\n[{label}] resolution={resolution} steps={steps}")
    # 先查出 latent 尺寸（TextEncode 的第 3 个输出决定了画布）
    wf = build(PROMPT, REF, resolution, steps)
    wf["9"]["inputs"]["filename_prefix"] = "qwen21_diag9/" + label
    try:
        resp = post("/prompt", {"prompt": wf, "client_id": "diag9"})
    except urllib.error.HTTPError as e:
        print("  提交失败:", e.code, e.read().decode("utf-8", "replace")[:500])
        return None
    pid = resp.get("prompt_id")
    if not pid:
        print("  被拒绝:", json.dumps(resp, ensure_ascii=False)[:500])
        return None
    t0 = time.time()
    while time.time() - t0 < 1800:
        time.sleep(2)
        e = get(f"/history/{pid}").get(pid)
        if e:
            st = e.get("status", {}).get("status_str")
            if st == "success":
                out = None
                for o in (e.get("outputs") or {}).values():
                    for im in (o.get("images") or []):
                        rel = os.path.join(im.get("subfolder", ""), im["filename"])
                        src = os.path.join(COMFY_OUT, rel)
                        dst = os.path.join(OUT, os.path.basename(rel))
                        if os.path.isfile(src):
                            with open(src, "rb") as fi, open(dst, "wb") as fo:
                                fo.write(fi.read())
                            out = dst
                        print(f"  OK {time.time() - t0:.1f}s -> {os.path.basename(rel)}")
                return out
            if st == "error":
                print("  ERROR")
                for m in e.get("status", {}).get("messages", []):
                    if isinstance(m, list) and len(m) >= 2 and m[0] == "execution_error":
                        d = m[1] or {}
                        print(f"     {d.get('node_type')}: {d.get('exception_type')} {d.get('exception_message')}")
                return None
    print("  超时")
    return None


def packed_size(w, h, res):
    """复现 TextEncodeQwenImage21 的缩放逻辑，打印实际 latent 尺寸。"""
    import math
    if res > 0:
        ratio = w / h
        rw = round(math.sqrt(res * res * ratio) / 32) * 32
        rh = round(math.sqrt(res * res / ratio) / 32) * 32
    else:
        rw, rh = round(w / 32) * 32, round(h / 32) * 32
    return max(32, rw), max(32, rh)


def similarity(a, b):
    try:
        from PIL import Image
        ia = Image.open(a).convert("RGB").resize((256, 256))
        ib = Image.open(b).convert("RGB").resize((256, 256))
        pa, pb = ia.load(), ib.load()
        tot = 0
        for y in range(256):
            for x in range(256):
                ra, ga, ba = pa[x, y]
                rb, gb, bb = pb[x, y]
                tot += abs(ra - rb) + abs(ga - gb) + abs(ba - bb)
        return tot / (256 * 256 * 3)
    except Exception as e:
        print("  MAE 失败:", e)
        return None


if __name__ == "__main__":
    from PIL import Image
    w, h = Image.open(REF_LOCAL).size
    print(f"参考图: {REF}  {w}x{h}")
    print("\n各 resolution 下的实际参考尺寸（官方模板默认 resolution=0）：")
    for r in (0, 1024, 2048):
        rw, rh = packed_size(w, h, r)
        print(f"  resolution={r:5d} -> 参考图缩放为 {rw}x{rh}  (latent {rw//16}x{rh//16})")

    res = {}
    res["Q1_res0_s30"] = run("Q1_res0_s30", 0, 30)
    res["Q2_res1024_s30"] = run("Q2_res1024_s30", 1024, 30)
    res["Q3_res0_s50"] = run("Q3_res0_s50", 0, 50)
    res["Q4_res2048_s40"] = run("Q4_res2048_s40", 2048, 40)

    print("\n" + "=" * 70)
    print("与参考图狼狼.png 的像素差异（MAE，越小越像原图）")
    print("=" * 70)
    for k, v in res.items():
        if not v:
            print(f"  {k:16s} 无产物")
            continue
        s = similarity(REF_LOCAL, v)
        print(f"  {k:16s} MAE={s:6.2f}")
    print("\n产物目录:", os.path.abspath(OUT))
