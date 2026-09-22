# -*- coding: utf-8 -*-
"""校验镜像源提供的 int8 权重与官方 HF 完全一致（大小 + sha256 前缀）。"""
import hashlib
import os
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    os.environ.pop(k, None)

EXPECT = {
    "diffusion_models/qwen_image_2.1_int8_convrot.safetensors": 7256783064,
    "text_encoders/qwen3vl_8b_int8_convrot.safetensors": 9350798360,
    "vae/qwen_image_2.1_vae_bf16.safetensors": 675509688,
}

MIRRORS = [
    ("hf-mirror直连", "https://hf-mirror.com/Comfy-Org/Qwen-Image-2.1/resolve/main/", False),
    ("ModelScope直连", "https://modelscope.cn/models/Comfy-Org/Qwen-Image-2.1/resolve/master/", False),
]

for name, base, use_proxy in MIRRORS:
    print(f"\n===== {name} =====")
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for path, size in EXPECT.items():
        url = base + path
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Range": "bytes=0-1023"})
            with op.open(req, timeout=30) as r:
                head = r.read(1024)
                total = r.headers.get("Content-Range", "")
                print(f"  {os.path.basename(path)}")
                print(f"    HTTP {r.status}  Content-Range={total or '(无)'}  读到 {len(head)}B")
        except Exception as e:
            print(f"  {os.path.basename(path)}  失败: {type(e).__name__} {str(e)[:80]}")
