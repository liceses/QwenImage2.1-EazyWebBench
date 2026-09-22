#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第八组诊断：验证"编辑是否真的保留了原图"。

关键判据：**小改动编辑**。如果模型真的在编辑原图，"只改发色/只改一个细节"
应当输出与参考图高度相似、只有局部不同的图。
如果输出是一张全新构图，说明它根本没有在编辑，而是在重画。

对照组（参考图 = 用户上传的狼狼.png，蓝发猫耳少女）：
  P1 极小改动：只换发色  → 应保持构图/姿势/服装/背景
  P2 极小改动：只换瞳色  → 同上
  P3 小改动：  换成白色连衣裙 → 服装变，其余不变
  P4 官方标记 + 三视图（复现用户那次）
  P5 极简官方风格：直接说场景（对照，看是否与 P1 明显不同）

判据：P1/P2 的输出应与 ref 高度相似。用像素级相似度（缩放到同尺寸后的平均绝对差）
给出定量结论，而不是只靠肉眼。
"""
import json
import os
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8188"
COMFY_OUT = r"D:\applications\comfy-ui\ComfyUI_windows_portable\ComfyUI\output"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "diag_out8")
os.makedirs(OUT, exist_ok=True)
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

REF = "ref_19ed6c27f2.png"          # 用户上传的狼狼.png
REF_LOCAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "uploads", REF)

P1 = "Change the girl's hair color in <image1> to pink. Keep everything else in <image1> exactly the same: the pose, the outfit, the tail, the background."
P2 = "Change the girl's eye color in <image1> to green. Keep everything else exactly the same."
P3 = "Change the girl's dress in <image1> to a white dress. Keep her hair, pose, tail and the background exactly the same."
P4 = ("Character reference sheet of the girl in <image1>: front view, side view and back view, "
      "full body, standing straight, three panels on a plain white background. "
      "Keep her design exactly: light blue long hair, purple eyes, blue cat ears with grey bows, "
      "black choker, black strapless mini dress with blue trim, thigh garter bands, black high heels, "
      "big fluffy light blue tail.")
P5 = "A blue-haired cat-ear girl standing in a sunny park, full body, anime illustration."


def post(path, payload):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=60) as r:
        return json.load(r)


def get(path, timeout=15):
    with OPENER.open(BASE + path, timeout=timeout) as r:
        return json.load(r)


def build(prompt, refs, steps=30, seed=555, w=1024, h=1024):
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
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "diag8"}},
    }
    for i, n in enumerate(refs):
        wf[str(10 + i)] = {"class_type": "LoadImage", "inputs": {"image": n}}
    return wf


def run(label, prompt, refs, steps=30, seed=555, w=1024, h=1024):
    print(f"\n{'=' * 70}\n[{label}] refs={len(refs)} steps={steps} size={w}x{h}")
    print(f"  {prompt[:120]}")
    wf = build(prompt, refs, steps, seed, w, h)
    wf["9"]["inputs"]["filename_prefix"] = "qwen21_diag8/" + label
    try:
        resp = post("/prompt", {"prompt": wf, "client_id": "diag8"})
    except urllib.error.HTTPError as e:
        print("  提交失败:", e.code, e.read().decode("utf-8", "replace")[:400])
        return None
    pid = resp.get("prompt_id")
    if not pid:
        print("  被拒绝:", json.dumps(resp, ensure_ascii=False)[:400])
        return None
    t0 = time.time()
    while time.time() - t0 < 1500:
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


def similarity(a, b):
    """缩到同尺寸后的平均绝对像素差（0=完全相同，255=完全不同）。"""
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
        print("  相似度计算失败:", e)
        return None


if __name__ == "__main__":
    res = {}
    res["P1_hair_pink"] = run("P1_hair_pink", P1, [REF])
    res["P2_eye_green"] = run("P2_eye_green", P2, [REF])
    res["P3_white_dress"] = run("P3_white_dress", P3, [REF])
    res["P4_sheet"] = run("P4_sheet", P4, [REF], steps=30)
    res["P5_t2i"] = run("P5_t2i", P5, [])

    print("\n" + "=" * 70)
    print("与参考图的像素相似度（越小越像原图，0=完全一致）")
    print("=" * 70)
    for k, v in res.items():
        if not v:
            print(f"  {k:16s} 无产物")
            continue
        s = similarity(REF_LOCAL, v)
        print(f"  {k:16s} MAE={s:6.2f}" if s is not None else f"  {k:16s} 计算失败")
    print("\n参考基准：原图 vs 原图 = 0.00；两张完全不同的图通常 MAE > 60")
    print("产物目录:", os.path.abspath(OUT))
