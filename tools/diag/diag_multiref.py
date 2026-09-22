#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断：多参考图编辑为何产出无关图。

对照实验设计（尽量只改一个变量）：
  A. 复现：原 prompt「把图一表情包的角色换成图二」+ 2 张参考图
  B. 只改 prompt 为明确英文描述 + 同样 2 张参考图
  C. 只用「表情包」那张作单参考图 + 明确英文描述
  D. 不传参考图，但 prompt 里描述整个场景（看模型本身能否画出）

每次跑 20 步、固定种子，输出到独立目录并记录耗时。
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

REF_MEME = "ref_61bc466eab.jpg"   # 表情包：黑发猫耳娘 + 中文字
REF_CHAN = "ref_ab7e28826c.png"   # 蓝发猫耳娘

PROMPT_A = "把图一表情包的角色换成图二"
PROMPT_B = ("Replace the character in the first image with the character from the second image. "
            "Keep the meme composition, the white Chinese text overlays, and the plain background unchanged.")
PROMPT_C = ("Replace the girl's black hair and outfit with the blue-haired cat-ear girl from the reference "
            "image. Keep the meme composition and the white Chinese text unchanged.")
PROMPT_D = ("An anime meme poster: a blue-haired cat-ear girl with a black choker in the center, "
            "plain light background, big white Chinese text at top-left and bottom.")


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
        "6": {"class_type": "KSampler",
              "inputs": {"model": ["1", 0], "positive": ["5", 0], "negative": ["5", 1],
                         "seed": seed, "steps": steps, "cfg": 1.0,
                         "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveImage",
              "inputs": {"images": ["8", 0], "filename_prefix": "qwen21_diag/%s" % prompt[:0] or "diag"}},
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
        wf["7"] = {"class_type": "EmptyLatentImage",
                   "inputs": {"width": 1024, "height": 1024, "batch_size": 1}}
        wf["6"]["inputs"]["latent_image"] = ["7", 0]
    return wf


def run(label, prompt, refs, steps=20, seed=555):
    print(f"\n{'=' * 66}\n[{label}] refs={len(refs)}  seed={seed}  steps={steps}")
    print(f"  prompt: {prompt[:110]}")
    wf = build(prompt, refs, steps, seed)
    for nid, n in wf.items():
        if n["class_type"] == "SaveImage":
            n["inputs"]["filename_prefix"] = "qwen21_diag/" + label
    try:
        resp = post("/prompt", {"prompt": wf, "client_id": "diag"})
    except urllib.error.HTTPError as e:
        print("  提交失败:", e.code, e.read().decode("utf-8", "replace")[:500])
        return None
    pid = resp.get("prompt_id")
    if not pid:
        print("  被拒绝:", json.dumps(resp, ensure_ascii=False)[:500])
        return None
    t0 = time.time()
    while time.time() - t0 < 900:
        time.sleep(2)
        h = get(f"/history/{pid}")
        e = h.get(pid)
        if e:
            st = e.get("status", {}).get("status_str")
            if st == "success":
                imgs = []
                for o in (e.get("outputs") or {}).values():
                    for im in (o.get("images") or []):
                        imgs.append(os.path.join(im.get("subfolder", ""), im["filename"]))
                el = time.time() - t0
                print(f"  ✅ {el:.1f}s  ->  {imgs}")
                for rel in imgs:
                    src = os.path.join(COMFY_OUT, rel)
                    if os.path.isfile(src):
                        dst = os.path.join(OUT, os.path.basename(rel))
                        with open(src, "rb") as fi, open(dst, "wb") as fo:
                            fo.write(fi.read())
                        print(f"     复制到 {dst}")
                return imgs
            if st == "error":
                print("  ❌ 执行错误:")
                for m in e.get("status", {}).get("messages", []):
                    if isinstance(m, list) and len(m) >= 2 and m[0] == "execution_error":
                        d = m[1] or {}
                        print(f"     {d.get('node_type')}: {d.get('exception_type')} {d.get('exception_message')}")
                return None
    print("  ❌ 超时")
    return None


if __name__ == "__main__":
    run("A_repro", PROMPT_A, [REF_MEME, REF_CHAN])
    run("B_clear2ref", PROMPT_B, [REF_MEME, REF_CHAN])
    run("C_single_meme", PROMPT_C, [REF_MEME])
    run("D_noref", PROMPT_D, [])
    print("\n完成。产物目录:", os.path.abspath(OUT))
