#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实测脚本：用官方 Qwen-Image-2.1 t2i 工作流跑通第一张图，
记录单张耗时与出图过程中的显存峰值。

直接与 ComfyUI 的 HTTP API 交互（不经过工作台），用于独立验证。
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
import threading
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8188"
COMFY_OUTPUT = _comfy_dir(r"output")
OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "test_output")
os.makedirs(OUTDIR, exist_ok=True)

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def post(path, payload):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=60) as r:
        return json.load(r)


def get(path, timeout=15):
    with OPENER.open(BASE + path, timeout=timeout) as r:
        return json.load(r)


def vram_sampler(stop_evt, samples):
    """后台采样显存占用。"""
    try:
        import ctypes
        nvml = ctypes.WinDLL("nvml.dll")
        nvml.nvmlInit_v2()
        dev = ctypes.c_void_p()
        nvml.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(dev))
        while not stop_evt.is_set():
            info = (ctypes.c_uint * 8)()
            # nvmlMemory_t: total, free, used (unsigned long long x3)
            class Mem(ctypes.Structure):
                _fields_ = [("total", ctypes.c_ulonglong),
                            ("free", ctypes.c_ulonglong),
                            ("used", ctypes.c_ulonglong)]
            m = Mem()
            if nvml.nvmlDeviceGetMemoryInfo(dev, ctypes.byref(m)) == 0:
                samples.append(m.used / (1024 * 1024))
            time.sleep(0.6)
    except Exception as e:
        samples.append(-1)
        print(f"  (NVML 采样不可用: {type(e).__name__} {e})")


def build_workflow(prompt, neg, width, height, steps, seed, cfg=1.0):
    return {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": "qwen_image_2.1_int8_convrot.safetensors",
                         "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": "qwen3vl_8b_int8_convrot.safetensors",
                         "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader",
              "inputs": {"vae_name": "qwen_image_2.1_vae_bf16.safetensors"}},
        "5": {"class_type": "TextEncodeQwenImage21",
              "inputs": {"clip": ["2", 0], "prompt": prompt, "negative_prompt": neg,
                         "vae": ["3", 0], "resolution": 1024}},
        "6": {"class_type": "KSampler",
              "inputs": {"model": ["1", 0], "positive": ["5", 0], "negative": ["5", 1],
                         "latent_image": ["7", 0], "seed": seed, "steps": steps, "cfg": cfg,
                         "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "7": {"class_type": "EmptyLatentImage",
              "inputs": {"width": width, "height": height, "batch_size": 1}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveImage",
              "inputs": {"images": ["8", 0], "filename_prefix": "qwen21_test/first"}},
    }


def main():
    prompt = ("雨夜霓虹招牌，牌子上写着「开摆」两个中文字，湿滑路面倒影，"
              "电影感打光，高细节")
    width = height = 1024
    steps = int(os.environ.get("TEST_STEPS", "25"))
    seed = 12345

    print("=" * 60)
    print("Qwen-Image-2.1 首次出图实测")
    print("=" * 60)
    print(f"提示词: {prompt}")
    print(f"尺寸: {width}x{height}   步数: {steps}   种子: {seed}")

    # 等 ComfyUI 就绪
    for _ in range(60):
        try:
            get("/system_stats", timeout=5)
            break
        except Exception:
            time.sleep(2)
    else:
        print("ComfyUI 未就绪")
        return 1

    wf = build_workflow(prompt, "模糊, 低质量, 错别字, 乱码, 水印", width, height, steps, seed)
    t0 = time.time()
    try:
        resp = post("/prompt", {"prompt": wf, "client_id": "first-test"})
    except urllib.error.HTTPError as e:
        print("提交失败:", e.code, e.read().decode("utf-8", "replace")[:1500])
        return 1

    pid = resp.get("prompt_id")
    if not pid:
        print("ComfyUI 拒绝工作流:", json.dumps(resp, ensure_ascii=False)[:1500])
        return 1
    print(f"\n已提交 prompt_id={pid}")

    stop = threading.Event()
    samples = []
    th = threading.Thread(target=vram_sampler, args=(stop, samples), daemon=True)
    th.start()

    last_step = -1
    while True:
        time.sleep(2)
        hist = get(f"/history/{pid}")
        e = hist.get(pid)
        if e:
            st = e.get("status", {})
            s = st.get("status_str")
            if s == "success":
                break
            if s == "error":
                stop.set()
                print("\n❌ 执行失败：")
                for m in st.get("messages", []):
                    if isinstance(m, list) and len(m) >= 2 and m[0] == "execution_error":
                        d = m[1] or {}
                        print(f"  节点 {d.get('node_type')} (id={d.get('node_id')})")
                        print(f"  异常 {d.get('exception_type')}: {d.get('exception_message')}")
                return 1
        try:
            q = get("/queue")
            running = q.get("queue_running") or []
            if running:
                extra = running[0][3] if len(running[0]) > 3 else {}
                pass
        except Exception:
            pass
        el = time.time() - t0
        if el > 2400:
            stop.set()
            print("\n❌ 超时")
            return 1

    stop.set()
    elapsed = time.time() - t0

    images = []
    for out in (e.get("outputs") or {}).values():
        for im in (out.get("images") or []):
            images.append(os.path.join(im.get("subfolder", ""), im["filename"]))

    print("\n" + "=" * 60)
    print("✅ 出图成功")
    print("=" * 60)
    print(f"总耗时        : {elapsed:.1f} 秒（{steps} 步）")
    print(f"每步约        : {elapsed / steps:.2f} 秒")
    if samples and samples[0] >= 0:
        print(f"显存占用峰值  : {max(samples):.0f} MB")
        print(f"显存占用起点  : {samples[0]:.0f} MB")
        print(f"采样点数      : {len(samples)}")
    print(f"输出图片      : {images}")

    # 复制到工作区
    for rel in images:
        src = os.path.join(COMFY_OUTPUT, rel)
        if os.path.isfile(src):
            dst = os.path.join(OUTDIR, os.path.basename(rel))
            with open(src, "rb") as fi, open(dst, "wb") as fo:
                fo.write(fi.read())
            print(f"已复制到      : {dst}")
            try:
                from PIL import Image
                im = Image.open(dst)
                print(f"图片尺寸/模式 : {im.size} {im.mode}")
            except Exception:
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
