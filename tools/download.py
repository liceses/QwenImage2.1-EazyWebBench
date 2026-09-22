#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
断点续传下载器（标准库实现，无第三方依赖）。

下载 ComfyUI 官方 Qwen-Image-2.1 int8 权重。
多镜像自动切换：hf-mirror 直连 / ModelScope 直连 / 官方 HF 走代理。
已校验三个镜像文件字节数与官方完全一致。

用法:
    python download.py [输出目录]
    python download.py --only <关键词> [输出目录]     # 只下某个文件(调试用)

已存在且大小一致的文件会跳过；下载中的 .part 支持断点续传，重跑即续传。
"""
import os
import sys
import time
import urllib.error
import urllib.request

# Windows 终端默认 GBK，强制 UTF-8 并对无法编码的字符降级，避免刷进度时崩溃
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

# 多源（按实测速度排序）。每个源给出 repo resolve 前缀。
SOURCES = [
    ("hf-mirror",   "https://hf-mirror.com/Comfy-Org/Qwen-Image-2.1/resolve/main/", None),
    ("ModelScope",  "https://modelscope.cn/models/Comfy-Org/Qwen-Image-2.1/resolve/master/", None),
    ("HF官方+代理", "https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/", "http://127.0.0.1:10808"),
]

# (仓库内路径, 本地子目录, 官方字节数)
TARGETS = [
    ("diffusion_models/qwen_image_2.1_int8_convrot.safetensors", "diffusion_models", 7256783064),
    ("text_encoders/qwen3vl_8b_int8_convrot.safetensors", "text_encoders", 9350798360),
    ("vae/qwen_image_2.1_vae_bf16.safetensors", "vae", 675509688),
]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def human(n):
    n = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def opener_for(proxy):
    if proxy:
        return urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        )
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def download_one(remote_path, dest_dir, expect, max_rounds=40):
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, os.path.basename(remote_path))
    part = dest + ".part"

    if os.path.exists(dest) and os.path.getsize(dest) == expect:
        print(f"[=] 已完成，跳过 {os.path.basename(dest)} ({human(expect)})")
        return True

    print(f"\n[>] {os.path.basename(dest)}  目标 {human(expect)}")
    src_i = 0
    for rnd in range(1, max_rounds + 1):
        have = os.path.getsize(part) if os.path.exists(part) else 0
        if have > expect:
            os.remove(part)
            have = 0
        if have == expect:
            os.replace(part, dest)
            print(f"[✓] 完成 {dest} ({human(expect)})")
            return True

        name, base, proxy = SOURCES[src_i % len(SOURCES)]
        op = opener_for(proxy)
        headers = {"User-Agent": UA}
        if have:
            headers["Range"] = f"bytes={have}-"
        req = urllib.request.Request(base + remote_path, headers=headers)
        try:
            with op.open(req, timeout=60) as r:
                if have and r.status != 206:
                    have = 0
                mode = "ab" if have else "wb"
                got = have
                t0 = time.time()
                last = 0.0
                stall = time.time()
                with open(part, mode) as fh:
                    while True:
                        chunk = r.read(2 * 1024 * 1024)
                        if not chunk:
                            break
                        fh.write(chunk)
                        got += len(chunk)
                        stall = time.time()
                        now = time.time()
                        if now - last >= 8:
                            last = now
                            sp = (got - have) / max(now - t0, 1e-6)
                            eta = (expect - got) / max(sp, 1)
                            print(
                                f"    [{name}] {human(got)}/{human(expect)} "
                                f"({got * 100.0 / expect:.1f}%) {human(sp)}/s "
                                f"ETA {eta / 60:.1f}min",
                                flush=True,
                            )
        except Exception as e:
            print(f"    [{name}] 中断: {type(e).__name__} {str(e)[:70]} —— 换源重试")
            src_i += 1
            time.sleep(2)
            continue

        if os.path.getsize(part) == expect:
            os.replace(part, dest)
            print(f"[✓] 完成 {dest} ({human(expect)})")
            return True

        print(f"    [{name}] 本次读到 {human(os.path.getsize(part))}，未达目标，继续/换源")
        # 若同一源反复无进展，就换源
        if rnd % 3 == 0:
            src_i += 1

    print(f"[X] {os.path.basename(dest)} 多轮重试仍未完成；.part 已保留，重跑本脚本可续传")
    return False


def main():
    argv = sys.argv[1:]
    only = None
    if "--only" in argv:
        i = argv.index("--only")
        only = argv[i + 1]
        del argv[i:i + 2]
    outdir = os.path.abspath(
        argv[0] if argv else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models")
    )
    print(f"输出目录: {outdir}")
    print("镜像: " + ", ".join(n for n, _, _ in SOURCES))

    todo = [t for t in TARGETS if not only or only in t[0]]
    print(f"计划下载 {len(todo)} 个文件，合计 {human(sum(t[2] for t in todo))}")

    ok = True
    for remote_path, subdir, expect in todo:
        ok = download_one(remote_path, os.path.join(outdir, subdir), expect) and ok

    print("\n" + ("全部完成。" if ok else "存在失败项，请重跑本脚本续传。"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
