#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第六组诊断（按官方文档修正）：prompt 里使用 <imageN> 字面标记。

官方 workflow_templates/image_qwen_image_2_1_image_edit.json 的 Note: Usage 明确写：
  - Mention them in the prompt as `<image1>`, `<image2>`, ...
  - image_1 is the edit target. The rest are references.
  - prompt: edit instruction. Use `<image1>` ... `<image10>`.

本次对照（参考图 = 官方示例同类任务：人像 + 服装/角色）：
  M1 官方标记 + 组合任务：  "<image1> and <image2> are standing together in a park..."
  M2 官方标记 + 换装任务：  "Dress the girl in <image1> with the outfit from <image2>..."
  M3 官方标记 + 角色替换：  "Replace the girl in <image1> with the character from <image2>..."
  M4 官方标记 + 中文：      "<image1> 和 <image2> 并排站在公园里..."

参考图顺序：image1=表情包(黑发猫耳少女+白字)，image2=蓝发猫耳角色
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

MEME = "ref_61bc466eab.jpg"   # image_1（编辑目标）
CHAN = "ref_ab7e28826c.png"   # image_2（参考）

M1 = ("<image1> and <image2> are standing together in a sunny park, full body, "
      "each keeping her own hairstyle, hair color and outfit.")
M2 = ("Dress the girl in <image1> with the blue hair and the outfit of the girl in <image2>, "
      "keep her pose and the white Chinese text in <image1> unchanged.")
M3 = ("Replace the girl in <image1> with the girl from <image2>, "
      "keep the composition and the white Chinese text from <image1> unchanged.")
M4 = ("<image1> 和 <image2> 并排站在阳光明媚的公园里，全身，"
      "各自保持自己那张图里的发型、发色和服装。")


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
    print(f"\n{'=' * 68}\n[{label}] refs={len(refs)}  steps={steps}  seed={seed}")
    print(f"  {prompt[:140]}")
    wf = build(prompt, refs, steps, seed)
    wf["9"]["inputs"]["filename_prefix"] = "qwen21_diag/" + label
    try:
        resp = post("/prompt", {"prompt": wf, "client_id": "diag6"})
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
    run("M1_tagname_compose", M1, [MEME, CHAN])
    run("M2_tagname_outfit", M2, [MEME, CHAN])
    run("M3_tagname_replace", M3, [MEME, CHAN])
    run("M4_tagname_zh", M4, [MEME, CHAN])
    print("\n完成。", os.path.abspath(OUT))
