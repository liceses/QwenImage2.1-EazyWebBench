# -*- coding: utf-8 -*-
"""下载源测速：找出这台机器上最快的 Qwen-Image-2.1 权重来源。"""
import os
import time
import urllib.request

URLS = [
    ("HF直连(无代理)", "https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/vae/qwen_image_2.1_vae_bf16.safetensors", False),
    ("HF走代理", "https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/vae/qwen_image_2.1_vae_bf16.safetensors", True),
    ("hf-mirror直连", "https://hf-mirror.com/Comfy-Org/Qwen-Image-2.1/resolve/main/vae/qwen_image_2.1_vae_bf16.safetensors", False),
    ("hf-mirror走代理", "https://hf-mirror.com/Comfy-Org/Qwen-Image-2.1/resolve/main/vae/qwen_image_2.1_vae_bf16.safetensors", True),
    ("ModelScope直连", "https://modelscope.cn/models/Qwen/Qwen-Image-2.1/resolve/master/vae/diffusion_pytorch_model.safetensors", False),
    ("ModelScope走代理", "https://modelscope.cn/models/Qwen/Qwen-Image-2.1/resolve/master/vae/diffusion_pytorch_model.safetensors", True),
]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    os.environ.pop(k, None)


def build_opener(use_proxy):
    if use_proxy:
        h = urllib.request.ProxyHandler({
            "http": "http://127.0.0.1:10808",
            "https": "http://127.0.0.1:10808",
        })
        return urllib.request.build_opener(h)
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


WINDOW = 6.0
results = []
for name, url, use_proxy in URLS:
    op = build_opener(use_proxy)
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": UA, "Range": "bytes=0-10485759"}
        )
        t0 = time.time()
        got = 0
        with op.open(req, timeout=25) as r:
            while time.time() - t0 < WINDOW:
                c = r.read(262144)
                if not c:
                    break
                got += len(c)
        dt = max(time.time() - t0, 1e-6)
        mbps = got / 1048576.0 / dt
        eta = 16.1 * 1024 / (got / 1048576.0 / dt) / 60 if got else -1
        results.append((mbps, name))
        print(f"{name:16s} {got/1048576:7.2f} MB / {dt:5.1f}s = {mbps:8.3f} MB/s   ETA(16.1GB)={eta:7.1f} min")
    except Exception as e:
        print(f"{name:16s} 失败: {type(e).__name__} {str(e)[:100]}")

if results:
    results.sort(reverse=True)
    print("\n最快:", results[0][1], f"({results[0][0]:.3f} MB/s)")
