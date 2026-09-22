#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 Qwen-Image-2.1 的 VAE 是否支持透明通道（RGBA）。

判据：VAE 解码端最后一层卷积的输出通道数 —— 3 = 只有 RGB，4 = RGB + alpha。
直接读 safetensors 头 + 张量形状，不需要加载权重到显存。

用法：python tools/diag/diag_vae_alpha.py
"""
import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
VAE = os.path.join(HERE, "..", "..", "models", "vae", "qwen_image_2.1_vae_bf16.safetensors")


def read_safetensors_header(path):
    """读 safetensors 头：返回 {tensor_name: {dtype, shape}}。"""
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        raw = f.read(n)
    meta = json.loads(raw.decode("utf-8"))
    meta.pop("__metadata__", None)
    return meta


def main():
    print(f"VAE 文件：{os.path.basename(VAE)}")
    print(f"大小：{os.path.getsize(VAE) / 1024**3:.2f} GB\n")
    t = read_safetensors_header(VAE)

    print("=== 解码输出层（决定输出是 RGB 还是 RGBA）===")
    # 常见命名：decoder.conv_out.weight / decoder.conv_out.bias
    cands = [k for k in t if "conv_out" in k or ("decoder" in k and k.endswith("weight") and len(t[k]["shape"]) == 4)]
    for k in sorted(cands):
        print(f"  {k:60s} {t[k]['dtype']:8s} {t[k]['shape']}")

    print("\n=== 编码输入层（决定能否吃 alpha）===")
    cands2 = [k for k in t if "encoder" in k and "conv_in" in k]
    for k in sorted(cands2):
        print(f"  {k:60s} {t[k]['dtype']:8s} {t[k]['shape']}")

    print("\n=== 判定 ===")
    out_ch = None
    for k in t:
        if "conv_out" in k and k.endswith("weight") and len(t[k]["shape"]) == 4:
            out_ch = t[k]["shape"][0]
            print(f"  解码输出通道数 = {out_ch}  ({k})")
            break
    in_ch = None
    for k in t:
        if "encoder" in k and "conv_in" in k and k.endswith("weight") and len(t[k]["shape"]) == 4:
            in_ch = t[k]["shape"][1]
            print(f"  编码输入通道数 = {in_ch}  ({k})")
            break

    if out_ch == 4:
        print("\n  => VAE **能解码出 4 通道（RGB + alpha）**：透明图是可行的。")
    elif out_ch == 3:
        print("\n  => VAE 解码输出是 3 通道（只有 RGB）：**拿不到 alpha**。")
    else:
        print("\n  => 没找到 conv_out，无法判定。")
    if in_ch == 4:
        print("  => VAE 编码端接受 4 通道：参考图的 alpha 也能参与编码。")
    elif in_ch == 3:
        print("  => VAE 编码端只接受 3 通道：参考图的 alpha 会被丢弃。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
