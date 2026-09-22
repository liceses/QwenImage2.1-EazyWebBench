#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第二组诊断：定位「两张参考图」失效的确切条件。

对照实验（只改一个变量）：
  E. 两张「同一角色」的图（我生成的霓虹牌图 + 蓝发角色图），prompt 明确要求合成
  F. 交换 A 组两张参考图的顺序（表情包↔角色）
  G. 同一张表情包图重复传两次当两个参考图（排除"图片内容冲突"这个变量）
  H. 一张表情包 + 明确英文 prompt，但宽高显式给成参考图尺寸（排除"latent 尺寸"这个变量）

全部 20 步、固定种子 555。
"""

# --- 可移植路径：环境变量优先，其次按本文件位置推导（详见 tools/_paths.py）---
import os as _os
_PROJECT_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))


def _comfy_dir(*_parts):
    """ComfyUI 下的目录；找不到 ComfyUI 时退回项目内同名目录。"""
    _r = _os.environ.get("QWEN21_COMFY_ROOT")
    _b = _os.path.join(_r, "ComfyUI") if _r else _PROJECT_ROOT
    return _os.path.join(_b, *_parts)

# ---------------------------------------------------------------------------
import json
import os
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8188"
COMFY_OUT = _comfy_dir(r"output")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "diag_out")
os.makedirs(OUT, exist_ok=True)
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

MEME = "ref_61bc466eab.jpg"     # 表情包：黑发猫耳娘 + 中文
CHAN = "ref_ab7e28826c.png"     # 蓝发猫耳娘
NEON = "ref_ad392cafdb.png"     # 霓虹牌（写实街景）

P_E = ("These two characters are standing together in a park, both facing the camera, "
       "full body, anime illustration.")
P_F = ("Replace the character in the first image with the character from the second image. "
       "Keep the meme composition and the white Chinese text unchanged.")
P_G = ("Replace the girl's hair color with blue and keep everything else exactly the same, "
       "keep the white Chinese text unchanged.")
P_H = ("Replace the girl in the first image with the girl from the second image, keep the meme "
       "layout and the white Chinese text overlays unchanged. The result should stay anime style.")


def post(path, payload):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=60) as r:
        return json.load(r)


def get(path, timeout=15):
    with OPENER.open(BASE + path, timeout=timeout) as r:
        return json.load(r)


def build(prompt, refs, size=None, steps=20, seed=555):
    wf = {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": "qwen_image_2.1_int8_convrot.safetensors",
                         "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": "qwen3vl_8b_int8_convrot.safetensors",
                         "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader",
              "inputs": {"vae_name": "qwen_image_2.1_vae_bf16.safetensors"}},
        "6": {"class_type": "KSampler",
              "inputs": {"model": ["1", 0], "positive": ["5", 0], "negative": ["5", 1],
                         "seed": seed, "steps": steps, "cfg": 1.0,
                         "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "diag"}},
    }
    if refs:
        wf["5"] = {"class_type": "TextEncodeQwenImage21",
                   "inputs": {"clip": ["2", 0], "prompt": prompt, "negative_prompt": " ",
                              "vae": ["3", 0], "resolution": 1024,
                              "images": {"image_%d" % (i + 1): [str(10 + i), 0]
                                         for i in range(len(refs))}}}
        for i, n in enumerate(refs):
            wf[str(10 + i)] = {"class_type": "LoadImage", "inputs": {"image": n}}
        wf["6"]["inputs"]["latent_image"] = ["5", 2]
    else:
        wf["5"] = {"class_type": "TextEncodeQwenImage21",
                   "inputs": {"clip": ["2", 0], "prompt": prompt, "negative_prompt": " ",
                              "vae": ["3", 0], "resolution": 1024}}
        wf["6"]["inputs"]["latent_image"] = ["7", 0]
    w, h = size or (1024, 1024)
    wf["7"] = {"class_type": "EmptyLatentImage",
               "inputs": {"width": w, "height": h, "batch_size": 1}}
    return wf


def run(label, prompt, refs, size=None, steps=20, seed=555):
    refs_desc = " + ".join(r.replace("ref_", "").replace(".png", "").replace(".jpg", "") for r in refs) or "无"
    print(f"\n{'=' * 66}\n[{label}] refs({len(refs)})={refs_desc}  size={size or 'auto'}  seed={seed}")
    print(f"  prompt: {prompt[:100]}")
    wf = build(prompt, refs, size, steps, seed)
    wf["9"]["inputs"]["filename_prefix"] = "qwen21_diag/" + label
    try:
        resp = post("/prompt", {"prompt": wf, "client_id": "diag2"})
    except urllib.error.HTTPError as e:
        print("  提交失败:", e.code, e.read().decode("utf-8", "replace")[:400])
        return
    pid = resp.get("prompt_id")
    if not pid:
        print("  被拒绝:", json.dumps(resp, ensure_ascii=False)[:400])
        return
    t0 = time.time()
    while time.time() - t0 < 900:
        time.sleep(2)
        e = get(f"/history/{pid}").get(pid)
        if e:
            st = e.get("status", {}).get("status_str")
            if st == "success":
                for o in (e.get("outputs") or {}).values():
                    for im in (o.get("images") or []):
                        rel = os.path.join(im.get("subfolder", ""), im["filename"])
                        src = os.path.join(COMFY_OUT, rel)
                        dst = os.path.join(OUT, os.path.basename(rel))
                        if os.path.isfile(src):
                            with open(src, "rb") as fi, open(dst, "wb") as fo:
                                fo.write(fi.read())
                        print(f"  OK {time.time() - t0:.1f}s -> {os.path.basename(rel)}")
                return
            if st == "error":
                print("  ERROR")
                for m in e.get("status", {}).get("messages", []):
                    if isinstance(m, list) and len(m) >= 2 and m[0] == "execution_error":
                        d = m[1] or {}
                        print(f"     {d.get('node_type')}: {d.get('exception_type')} {d.get('exception_message')}")
                return
    print("  超时")


if __name__ == "__main__":
    run("E_two_chars", P_E, [NEON, CHAN])
    run("F_swap_order", P_F, [CHAN, MEME])
    run("G_same_twice", P_G, [MEME, MEME])
    run("H_two_ref_explicit_size", P_H, [MEME, CHAN], size=(1024, 928))
    print("\n完成。", os.path.abspath(OUT))
