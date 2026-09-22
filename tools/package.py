#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打包分享包（只装本项目文件，自动排除权重、生成物与其它任务的文件）。

用法：
    python tools/package.py                 # 输出到 ./dist/QwenImage2.1-本地工作台-分享包.zip
    python tools/package.py --with-samples  # 同时带上 示例效果/（默认就带）
    python tools/package.py --no-samples    # 不带示例图（包更小）

打包内容（白名单，只装这些）：
    server.py / web/ / tools/ / 启动工作台.bat / config.example.json
    能力清单.md / 使用说明.md / 分享说明.md / 示例效果/

绝不打包：
    models/（权重，17GB+）、outputs/、uploads/（你的生成物与上传图）、
    diag_out*/（调查中间产物）、.dsh/、__pycache__/、
    以及工作目录里其它任务的文件（cover_*.png、ppt_zcode/、style_run*/ 等）
"""
import argparse
import os
import sys
import time
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DIST = os.path.join(ROOT, "dist")

# 要打包的文件（白名单）
FILES = [
    "server.py",
    "启动工作台.bat",
    "config.example.json",
    "能力清单.md",
    "使用说明.md",
    "分享说明.md",
    "开发注意.md",
]
# 要打包的目录 → 该目录下的**文件白名单**（None 表示整目录递归，用 exclude 过滤）
DIRS = [
    ("web", None, ()),
    ("tools", [
        "download.py",
        "selfcheck.py",
        "first_run.py",
        "speedtest.py",
        "verify_mirror.py",
        "package.py",
    ], ()),
    ("示例效果", None, ()),
]

ZIP_NAME = "QwenImage2.1-本地工作台-分享包.zip"

# 明确不打包的东西（仅用于自检提示，避免误打包）
NEVER = ["models", "outputs", "uploads", "dist", "__pycache__", ".dsh",
         "diag_out", "diag_out8", "diag_out9", "diag_out10", "修复验证"]


def iter_dir(rel, whitelist, excludes):
    base = os.path.join(ROOT, rel)
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in excludes]
        for fn in filenames:
            if fn.endswith((".pyc", ".pyo")):
                continue
            if whitelist is not None:
                if fn not in whitelist:
                    continue
                if os.path.relpath(dirpath, base) != ".":
                    continue          # 白名单只在该目录第一层生效
            full = os.path.join(dirpath, fn)
            arc = os.path.relpath(full, ROOT)
            yield full, arc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-samples", action="store_true", help="不打包 示例效果/")
    ap.add_argument("--out", default=None, help="输出 zip 路径")
    args = ap.parse_args()

    dirs = list(DIRS)
    if args.no_samples:
        dirs = [d for d in dirs if d[0] != "示例效果"]

    os.makedirs(DIST, exist_ok=True)
    out = args.out or os.path.join(DIST, ZIP_NAME)
    if not out.lower().endswith(".zip"):
        out += ".zip"

    entries = []
    missing = []
    for f in FILES:
        p = os.path.join(ROOT, f)
        if os.path.isfile(p):
            entries.append((p, f))
        else:
            missing.append(f)
    for rel, whitelist, exc in dirs:
        if not os.path.isdir(os.path.join(ROOT, rel)):
            missing.append(rel + "/")
            continue
        entries.extend(iter_dir(rel, whitelist, exc))

    # 安全自检：绝不把大目录或他人文件打进去
    bad = []
    for _full, arc in entries:
        top = arc.replace("\\", "/").split("/")[0]
        if top in NEVER:
            bad.append(arc)
    if bad:
        print("!! 自检失败，以下文件不该被打包：")
        for b in bad:
            print("   ", b)
        return 1

    total = sum(os.path.getsize(f) for f, _ in entries)

    print(f"输出: {out}")
    print(f"文件数: {len(entries)}   原始大小: {total / 1024:.1f} KB")
    if missing:
        print("跳过（不存在）: " + ", ".join(missing))

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for full, arc in sorted(entries, key=lambda x: x[1]):
            z.write(full, arc)

        # 空的权重目录 + 说明，方便收件人知道放哪
        z.writestr("models/把权重放这里.txt",
                   "把三个权重文件按下列目录放置（或用 python tools/download.py 自动下载）：\r\n"
                   "  diffusion_models/qwen_image_2.1_int8_convrot.safetensors   (7.26 GB)\r\n"
                   "  text_encoders/qwen3vl_8b_int8_convrot.safetensors          (9.35 GB)\r\n"
                   "  vae/qwen_image_2.1_vae_bf16.safetensors                    (0.68 GB)\r\n"
                   "下载源: https://huggingface.co/Comfy-Org/Qwen-Image-2.1\r\n")

        # 生成说明文件放进包里
        z.writestr("打包说明.txt",
                   f"Qwen-Image-2.1 本地工作台 · 分享包\r\n"
                   f"打包时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\r\n"
                   f"文件数: {len(entries)}\r\n\r\n"
                   "本包不含模型权重（约 17.3 GB）与 ComfyUI 本体，\r\n"
                   "请先阅读 分享说明.md 的「一、包里有什么」到「四、下载权重」。\r\n")

    size = os.path.getsize(out)
    print(f"✅ 完成: {out}  ({size / 1024 / 1024:.2f} MB)")
    print("\n包内清单：")
    with zipfile.ZipFile(out) as z:
        for n in sorted(z.namelist()):
            print(f"   {z.getinfo(n).file_size:>10,} B  {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
