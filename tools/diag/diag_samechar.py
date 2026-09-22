#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第七组诊断：用"同类型、同角色"的图对，排除"跨风格图对"这个变量。

之前所有多图测试用的都是异质图对（动漫表情包 + 蓝发动漫角色），
而官方 multi-ref 示例用的是同质图对（人像实拍 + 服装实拍）。
本组用两张**同一角色**的图，做最基础的身份保持测试。

参考图：
  A = ref_ab7e28826c.png  蓝发猫耳角色（绿底，站姿无遮挡）
  B = ref_bf7d6d03a0.png  同一角色（此前单图测试用的原图）

测试：
  N1 同角色两图 + <imageN> 标记："<image1> and <image2> are the same character..."
  N2 同角色两图 + 组合："<image1> and <image2> standing side by side..."
  N3 单图基线（只用 A）："the character in <image1> standing in a park"
  N4 换装任务（用官方示例同类思路）：把 A 的衣服换到 B 上

注意：N3 用 <image1> 单图，可验证 <imageN> 标记在单图下是否正常。
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

A = "ref_ab7e28826c.png"   # 蓝发猫耳角色（绿底）
B = "ref_bf7d6d03a0.png"   # 霓虹牌写实街景（工作台里的那张）

N1 = ("<image1> and <image2> show the same blue-haired cat-ear girl. "
      "Generate her standing in a sunny park, full body, keeping her exact "
      "hairstyle, hair color, cat ears and choker from <image1>.")
N2 = ("<image1> shows a blue-haired cat-ear girl on a green background. "
      "<image2> shows a girl in a rainy neon street. "
      "Generate both girls standing side by side in a sunny park, full body.")
N3 = ("The blue-haired cat-ear girl in <image1>, standing in a sunny park, full body, "
      "keeping her hairstyle, hair color, cat ears and choker exactly.")
N4 = ("Put the blue-haired cat-ear girl from <image2> into the rainy neon street scene of "
      "<image1>, full body, she should stand on the wet pavement in front of the neon sign.")


def post(path, payload):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=60) as r:
        return json.load(r)


def get(path, timeout=15):
    with OPENER.open(BASE + path, timeout=timeout) as r:
        return json.load(r)


def build(prompt, refs, steps=25, seed=555):
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


def run(label, prompt, refs, steps=25, seed=555):
    print(f"\n{'=' * 68}\n[{label}] refs={len(refs)}: {refs}")
    print(f"  {prompt[:140]}")
    wf = build(prompt, refs, steps, seed)
    wf["9"]["inputs"]["filename_prefix"] = "qwen21_diag/" + label
    try:
        resp = post("/prompt", {"prompt": wf, "client_id": "diag7"})
    except urllib.error.HTTPError as e:
        print("  提交失败:", e.code, e.read().decode("utf-8", "replace")[:400])
        return
    pid = resp.get("prompt_id")
    if not pid:
        print("  被拒绝:", json.dumps(resp, ensure_ascii=False)[:400])
        return
    t0 = time.time()
    while time.time() - t0 < 1500:
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
    run("N1_same_char_2img", N1, [A, B])
    run("N2_two_girls", N2, [A, B])
    run("N3_single_tag", N3, [A])
    run("N4_insert_char", N4, [B, A])
    print("\n完成。", os.path.abspath(OUT))
