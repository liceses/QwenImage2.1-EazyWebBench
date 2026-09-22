#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第四组诊断：接入官方 edit 工作流的 QwenImage21Cache 节点，看多参考图是否改善。

官方 edit subgraph 里 QwenImage21Cache 接在 UNETLoader → KSampler 之间。
本次对照（同一 prompt、同一组参考图、同一种子 555、20 步）：

  K0 无缓存节点（基线，等于之前失败的 B 组条件）
  K1 cache device=auto     dtype=default
  K2 cache device=cpu      dtype=default
  K3 cache device=off      dtype=default   ← 官方说这是"排除缓存问题"的唯一开关
  K4 cache device=auto     dtype=int8      ← 官方说 int8 在多图编辑显存紧张时能提速

注：ComfySwitchNode 是前端 subgraph 专属节点，API 里不存在；
它的作用（选"参考图尺寸 latent"还是"显式宽高 latent"）本脚本用 latent 接线等价实现。
"""
import json
import os
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8188"
COMFY_OUT = r"D:\applications\comfy-ui\ComfyUI_windows_portable\ComfyUI\output"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "diag_out")
os.makedirs(OUT, exist_ok=True)
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

MEME = "ref_61bc466eab.jpg"
CHAN = "ref_ab7e28826c.png"

# 用之前"逐张描述"那版（唯一能确认图片被读到的写法）
PROMPT = ("Picture 1 is a meme with a black-haired cat-ear girl and white Chinese text. "
          "Picture 2 is a blue-haired cat-ear girl on a green background. "
          "Task: keep Picture 1's meme composition and its white Chinese text unchanged, "
          "but replace the girl with the girl from Picture 2.")


def post(path, payload):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=60) as r:
        return json.load(r)


def get(path, timeout=15):
    with OPENER.open(BASE + path, timeout=timeout) as r:
        return json.load(r)


def build(prompt, refs, cache=None, steps=20, seed=555):
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
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "diag"}},
    }
    for i, n in enumerate(refs):
        wf[str(10 + i)] = {"class_type": "LoadImage", "inputs": {"image": n}}

    if cache is None:
        model_ref = ["1", 0]
    else:
        device, dtype = cache
        wf["20"] = {"class_type": "QwenImage21Cache",
                    "inputs": {"model": ["1", 0], "device": device, "dtype": dtype}}
        model_ref = ["20", 0]

    wf["6"] = {"class_type": "KSampler",
               "inputs": {"model": model_ref, "positive": ["5", 0], "negative": ["5", 1],
                          "latent_image": ["5", 2], "seed": seed, "steps": steps, "cfg": 1.0,
                          "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}}
    return wf


def run(label, prompt, refs, cache=None, steps=20, seed=555):
    tag = "无缓存节点" if cache is None else f"device={cache[0]} dtype={cache[1]}"
    print(f"\n{'=' * 68}\n[{label}] {tag}  refs={len(refs)}  seed={seed}")
    wf = build(prompt, refs, cache, steps, seed)
    wf["9"]["inputs"]["filename_prefix"] = "qwen21_diag/" + label
    try:
        resp = post("/prompt", {"prompt": wf, "client_id": "diag4"})
    except urllib.error.HTTPError as e:
        print("  提交失败:", e.code, e.read().decode("utf-8", "replace")[:500])
        return
    pid = resp.get("prompt_id")
    if not pid:
        print("  被拒绝:", json.dumps(resp, ensure_ascii=False)[:500])
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
                return time.time() - t0
            if st == "error":
                print("  ERROR")
                for m in e.get("status", {}).get("messages", []):
                    if isinstance(m, list) and len(m) >= 2 and m[0] == "execution_error":
                        d = m[1] or {}
                        print(f"     {d.get('node_type')}: {d.get('exception_type')} {d.get('exception_message')}")
                return
    print("  超时")


if __name__ == "__main__":
    run("K0_nocache", PROMPT, [MEME, CHAN], None)
    run("K1_cache_auto", PROMPT, [MEME, CHAN], ("auto", "default"))
    run("K2_cache_cpu", PROMPT, [MEME, CHAN], ("cpu", "default"))
    run("K3_cache_off", PROMPT, [MEME, CHAN], ("off", "default"))
    run("K4_cache_int8", PROMPT, [MEME, CHAN], ("auto", "int8"))
    print("\n完成。", os.path.abspath(OUT))
