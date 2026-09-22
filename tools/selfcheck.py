#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交付自检：核验 Qwen-Image-2.1 工作台是否处于可出图状态。

检查项：
  1. 三件套权重是否齐全、字节数是否与官方一致
  2. 权重是否已硬链接进 ComfyUI 模型目录
  3. ComfyUI 是否在 127.0.0.1:8188 运行
  4. 工作台是否在 127.0.0.1:8642 运行
  5. ComfyUI 是否已提供 2.1 专属节点

用法：python tools/selfcheck.py
"""
import json
import os
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MODELS = os.path.join(ROOT, "models")
COMFY_MODELS = r"D:\applications\comfy-ui\ComfyUI_windows_portable\ComfyUI\models"

EXPECT = {
    "diffusion_models/qwen_image_2.1_int8_convrot.safetensors": 7256783064,
    "text_encoders/qwen3vl_8b_int8_convrot.safetensors": 9350798360,
    "vae/qwen_image_2.1_vae_bf16.safetensors": 675509688,
}

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
fails = []


def ok(cond, msg):
    print(("  [OK ] " if cond else "  [FAIL] ") + msg)
    if not cond:
        fails.append(msg)
    return cond


def http_json(url, timeout=8):
    with OPENER.open(url, timeout=timeout) as r:
        return json.load(r)


print("=" * 64)
print("Qwen-Image-2.1 工作台 · 交付自检")
print("=" * 64)

print("\n① 权重文件")
total = 0
for rel, exp in EXPECT.items():
    p = os.path.join(MODELS, rel.replace("/", os.sep))
    if not os.path.exists(p):
        ok(False, f"缺失 {rel}")
        continue
    size = os.path.getsize(p)
    total += size
    ok(size == exp,
       f"{os.path.basename(rel):44s} {size / 1e9:5.2f} GB / 期望 {exp / 1e9:5.2f} GB")
print(f"  合计 {total / 1e9:.2f} GB = {total / 1024 ** 3:.2f} GiB")

print("\n② 硬链接到 ComfyUI")
for rel, exp in EXPECT.items():
    d = os.path.join(COMFY_MODELS, rel.replace("/", os.sep))
    ok(os.path.exists(d) and os.path.getsize(d) == exp,
       f"{os.path.basename(rel):44s} {'已挂载' if os.path.exists(d) else '未挂载'}")

print("\n③ ComfyUI 服务 (127.0.0.1:8188)")
try:
    st = http_json("http://127.0.0.1:8188/system_stats")
    dev = (st.get("devices") or [{}])[0]
    ok(True, f"运行中 · v{st.get('system', {}).get('comfyui_version')} · "
             f"{dev.get('name')} · 显存 {dev.get('vram_free', 0) / 1e9:.2f}"
             f"/{dev.get('vram_total', 0) / 1e9:.2f} GB 可用")
except Exception as e:
    ok(False, f"未运行: {type(e).__name__} {e}")

print("\n④ 工作台服务 (127.0.0.1:8642)")
try:
    s = http_json("http://127.0.0.1:8642/api/status")
    ok(bool(s.get("models_ready")), f"权重就绪 = {s.get('models_ready')}")
    ok(bool(s.get("comfyui", {}).get("ready")),
       f"后端就绪 = {s.get('comfyui', {}).get('ready')} ({s.get('comfyui', {}).get('detail')})")
except Exception as e:
    ok(False, f"未运行: {type(e).__name__} {e}")

print("\n⑤ 2.1 专属节点")
try:
    oi = http_json("http://127.0.0.1:8188/object_info/TextEncodeQwenImage21", timeout=20)
    node = oi.get("TextEncodeQwenImage21") or {}
    ok(bool(node), f"TextEncodeQwenImage21 · 输出 {node.get('output')}")
    oi2 = http_json("http://127.0.0.1:8188/object_info/QwenImage21Cache", timeout=20)
    ok(bool(oi2.get("QwenImage21Cache")), "QwenImage21Cache 可用")
except Exception as e:
    ok(False, f"节点查询失败: {type(e).__name__} {e}")

print("\n" + "=" * 64)
if fails:
    print(f"结果：{len(fails)} 项未通过")
    for f in fails:
        print("  - " + f)
else:
    print("结果：全部通过，工作台处于可出图状态")
print("=" * 64)
sys.exit(1 if fails else 0)
