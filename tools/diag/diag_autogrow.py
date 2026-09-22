#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第十组诊断：验证 TextEncodeQwenImage21 的 images 入参到底是"嵌套 dict"还是"扁平键"。

判据：**输出画布尺寸**。
TextEncodeQwenImage21 的 latent 输出按第一张参考图的宽高比生成
（resolution=0 时 = 参考图对齐到 32 倍数）。所以：
  - 若图片真的收到了：945x1562 的参考图 -> 画布应变成长方形 960x1568
  - 若图片没收到：latent_w = latent_h = (resolution or 1024) -> 画布是正方形

对照：
  R1 嵌套形式  "images": {"image_1": ["10", 0]}        ← 本工作台此前的写法（怀疑失效）
  R2 扁平形式  "images.image_1": ["10", 0]             ← 展开后的真实输入名（怀疑正确）
  R3 扁平形式 + 两张图
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
OUT = os.path.join(HERE, "..", "..", "diag_out10")
os.makedirs(OUT, exist_ok=True)
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

REF = "ref_19ed6c27f2.png"   # 945x1562 竖版
CHAN = "ref_ab7e28826c.png"  # 1249x1252 近方

PROMPT = ("Change the girl's hair color in <image1> to pink. "
          "Keep the pose, the outfit, the tail, the face and the background exactly the same.")


def post(path, payload):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=60) as r:
        return json.load(r)


def get(path, timeout=15):
    with OPENER.open(path if path.startswith("http") else BASE + path, timeout=timeout) as r:
        return json.load(r)


def base_wf(prompt, refs_flat, resolution=0, steps=30, seed=555):
    """refs_flat: list of (node_id, filename) -> 用扁平键 images.image_N 传入"""
    inputs = {"clip": ["2", 0], "prompt": prompt, "negative_prompt": " ",
              "vae": ["3", 0], "resolution": resolution}
    for i, (nid, _fn) in enumerate(refs_flat):
        inputs["images.image_%d" % (i + 1)] = [nid, 0]
    wf = {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": "qwen_image_2.1_int8_convrot.safetensors",
                         "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": "qwen3vl_8b_int8_convrot.safetensors",
                         "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader",
              "inputs": {"vae_name": "qwen_image_2.1_vae_bf16.safetensors"}},
        "5": {"class_type": "TextEncodeQwenImage21", "inputs": inputs},
        "6": {"class_type": "KSampler",
              "inputs": {"model": ["1", 0], "positive": ["5", 0], "negative": ["5", 1],
                         "latent_image": ["5", 2], "seed": seed, "steps": steps, "cfg": 1.0,
                         "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "diag10"}},
    }
    for i, (nid, fn) in enumerate(refs_flat):
        wf[nid] = {"class_type": "LoadImage", "inputs": {"image": fn}}
    return wf


def submit(label, wf):
    wf["9"]["inputs"]["filename_prefix"] = "qwen21_diag10/" + label
    try:
        resp = post("/prompt", {"prompt": wf, "client_id": "diag10"})
    except urllib.error.HTTPError as e:
        print("  提交失败:", e.code, e.read().decode("utf-8", "replace")[:600])
        return None
    pid = resp.get("prompt_id")
    if not pid:
        print("  被拒绝:", json.dumps(resp, ensure_ascii=False)[:600])
        return None
    t0 = time.time()
    while time.time() - t0 < 1800:
        time.sleep(2)
        e = get(f"/history/{pid}").get(pid)
        if e:
            st = e.get("status", {}).get("status_str")
            if st == "success":
                outs = []
                for o in (e.get("outputs") or {}).values():
                    for im in (o.get("images") or []):
                        rel = os.path.join(im.get("subfolder", ""), im["filename"])
                        src = os.path.join(COMFY_OUT, rel)
                        dst = os.path.join(OUT, os.path.basename(rel))
                        if os.path.isfile(src):
                            with open(src, "rb") as fi, open(dst, "wb") as fo:
                                fo.write(fi.read())
                            outs.append(dst)
                print(f"  OK {time.time() - t0:.1f}s -> {[os.path.basename(x) for x in outs]}")
                return outs
            if st == "error":
                print("  ERROR")
                for m in e.get("status", {}).get("messages", []):
                    if isinstance(m, list) and len(m) >= 2 and m[0] == "execution_error":
                        d = m[1] or {}
                        print(f"     {d.get('node_type')}: {d.get('exception_type')} {d.get('exception_message')}")
                return None
    print("  超时")
    return None


def dims(paths):
    from PIL import Image
    return [Image.open(p).size for p in (paths or [])]


if __name__ == "__main__":
    from PIL import Image
    w, h = Image.open(os.path.join(HERE, "..", "..", "uploads", REF)).size
    print("=" * 70)
    print(f"参考图 {REF}: {w}x{h}  (竖版)")
    print("预期：图片真的收到 -> 画布 ≈ 960x1568（竖版长方形）")
    print("      图片没收到   -> 画布 1024x1024（正方形，因为 resolution=0 被当作 1024）")
    print("=" * 70)

    print("\n[R1] 嵌套形式 images = {'image_1': [...]}  （本工作台旧写法）")
    wf1 = base_wf(PROMPT, [("10", REF)], resolution=0, steps=20)
    wf1["5"]["inputs"].pop("images.image_1", None)
    wf1["5"]["inputs"]["images"] = {"image_1": ["10", 0]}
    p1 = submit("R1_nested", wf1)
    print("      画布:", dims(p1))

    print("\n[R2] 扁平形式 images.image_1 = [...]  （展开后的真实输入名）")
    wf2 = base_wf(PROMPT, [("10", REF)], resolution=0, steps=20)
    p2 = submit("R2_flat", wf2)
    print("      画布:", dims(p2))

    print("\n[R3] 扁平形式 + 两张图")
    wf3 = base_wf(PROMPT, [("10", REF), ("11", CHAN)], resolution=0, steps=20)
    p3 = submit("R3_flat_2img", wf3)
    print("      画布:", dims(p3))

    print("\n产物目录:", os.path.abspath(OUT))
