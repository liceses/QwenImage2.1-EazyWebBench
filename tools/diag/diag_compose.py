#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第五组诊断（收口）：区分「组合任务」与「特征迁移任务」，并对比中英文。

之前所有多图失败都是「把 A 的特征搬到 B」这类**属性迁移**任务。
E 组是「两个角色站一起」的**组合**任务，也失败，但当时 prompt 很短。

本次：
  L1 组合任务 + 明确英文（两个角色并排站，各自保持特征）
  L2 组合任务 + 明确中文
  L3 特征迁移 + 逐张描述（English）
  L4 单图基线：只给蓝发角色，要求放到公园里（确认单图仍稳）

参考图固定：内存表情包(黑发) + 蓝发角色
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
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "diag_out")
os.makedirs(OUT, exist_ok=True)
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

MEME = "ref_61bc466eab.jpg"   # 黑发猫耳少女 + 白字
CHAN = "ref_ab7e28826c.png"   # 蓝发猫耳少女

P_L1 = ("Picture 1: a black-haired cat-ear girl, close-up portrait. "
        "Picture 2: a blue-haired cat-ear girl with a black choker. "
        "Generate a new image with BOTH girls standing side by side in a sunny park, "
        "full body, each keeping her own hairstyle, hair color, and outfit from her picture.")
P_L2 = ("图1：黑发猫耳少女的近距离肖像。图2：戴黑色颈圈的蓝发猫耳少女。"
        "生成一张新图：两个少女并排站在阳光明媚的公园里，全身，"
        "各自保持自己那张图里的发型、发色和服装。")
P_L3 = ("Picture 1 shows a black-haired cat-ear girl. Picture 2 shows a blue-haired cat-ear girl. "
        "Take the blue-haired girl from Picture 2 and place her into Picture 1's composition, "
        "keeping the white Chinese text from Picture 1 unchanged.")
P_L4 = ("Picture 1 is a blue-haired cat-ear girl with a black choker. "
        "Place her standing in a sunny park, full body, keeping her hairstyle and outfit.")


def post(path, payload):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=60) as r:
        return json.load(r)


def get(path, timeout=15):
    with OPENER.open(BASE + path, timeout=timeout) as r:
        return json.load(r)


def build(prompt, refs, steps=20, seed=555):
    wf = {
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
                         "vae": ["3", 0], "resolution": 1024,
                         "images": {"image_%d" % (i + 1): [str(10 + i), 0]
                                    for i in range(len(refs))}}},
        "6": {"class_type": "KSampler",
              "inputs": {"model": ["1", 0], "positive": ["5", 0], "negative": ["5", 1],
                         "latent_image": ["5", 2], "seed": seed, "steps": steps, "cfg": 1.0,
                         "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "diag"}},
    }
    for i, n in enumerate(refs):
        wf[str(10 + i)] = {"class_type": "LoadImage", "inputs": {"image": n}}
    return wf


def run(label, prompt, refs, steps=20, seed=555):
    print(f"\n{'=' * 68}\n[{label}] refs={len(refs)}")
    print(f"  {prompt[:130]}")
    wf = build(prompt, refs, steps, seed)
    wf["9"]["inputs"]["filename_prefix"] = "qwen21_diag/" + label
    try:
        resp = post("/prompt", {"prompt": wf, "client_id": "diag5"})
    except urllib.error.HTTPError as e:
        print("  提交失败:", e.code, e.read().decode("utf-8", "replace")[:400])
        return
    pid = resp.get("prompt_id")
    if not pid:
        print("  被拒绝:", json.dumps(resp, ensure_ascii=False)[:400])
        return
    t0 = time.time()
    while time.time() - t0 < 1200:
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
    run("L1_compose_en", P_L1, [MEME, CHAN])
    run("L2_compose_zh", P_L2, [MEME, CHAN])
    run("L3_transfer_en", P_L3, [MEME, CHAN])
    run("L4_single_base", P_L4, [CHAN])
    print("\n完成。", os.path.abspath(OUT))
