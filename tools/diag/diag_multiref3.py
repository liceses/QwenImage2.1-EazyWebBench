#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第三组诊断：验证「2.1 节点不把图片编号写进 prompt」这一假设。

对照组：
  I. 两图 + prompt 里显式写出图片顺序说明（模仿老节点的 Picture N 写法）
  J. 两图 + 极简直白指令（排除"指令太绕"这个变量）

若 I 明显好于 A/B/H，则确认是「prompt 必须自己指明图片顺序」。
若 I 与 J 都崩，则多图参考在本机 ComfyUI 路径下不可用。
"""
import json
import os
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8188"
COMFY_OUT = r"D:\applications\comfy-ui\ComfyUI_windows_portable\ComfyUI\output"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "diag_out")
os.makedirs(OUT, exist_ok=True)
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

MEME = "ref_61bc466eab.jpg"
CHAN = "ref_ab7e28826c.png"

# I: 显式声明图片顺序（模仿老架构 llama_template 的 Picture N 提示）
P_I = ("Picture 1 is a meme with a black-haired cat-ear girl and white Chinese text. "
       "Picture 2 is a blue-haired cat-ear girl on a green background. "
       "Task: keep Picture 1's meme composition and its white Chinese text unchanged, "
       "but replace the girl with the girl from Picture 2.")

# J: 极简直白
P_J = ("Use the second image as the character reference and the first image as the layout "
       "reference. Put the blue-haired cat-ear girl from the second image into the first image.")


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
    print(f"\n{'=' * 66}\n[{label}] refs={len(refs)}  seed={seed}")
    print(f"  {prompt[:150]}")
    wf = build(prompt, refs, steps, seed)
    wf["9"]["inputs"]["filename_prefix"] = "qwen21_diag/" + label
    try:
        resp = post("/prompt", {"prompt": wf, "client_id": "diag3"})
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
                        dst = os.path.join(OUT, os.path.basename(rel))
                        src = os.path.join(COMFY_OUT, rel)
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
    run("I_picture_numbering", P_I, [MEME, CHAN])
    run("J_simple_direct", P_J, [MEME, CHAN])
    print("\n完成。", os.path.abspath(OUT))
