#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""端到端验证：Qwen-Image-2.1 到底能不能出**真透明**的图。

官方给的透明图提示词固定句式：
    "This is an RGBA image with transparency. <描述>.
     The image has alpha channel and the background is transparent."

背景：VAE 解码输出 4 通道（decoder.head.2.weight = [4,144,1,3,3]），
SaveImage 也确实把 4 通道写成 color_type=6 的 RGBA PNG。
历史产物 180 张全是 RGBA，但 alpha 都在 252~255（VAE 噪声，等于全不透明）。
所以真正要问的是：**模型会不会按提示词生成真正的透明区域**。

用法：python tools/diag/diag_transparent_gen.py [--ref]
      加 --ref 则同时带一张参考图（测"编辑"路径）
"""
import json
import os
import struct
import sys
import time
import urllib.request
import uuid
import zlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WORKBENCH = "http://127.0.0.1:8642"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))

PROMPT = ("This is an RGBA image with transparency. A cute chibi whale-girl mascot "
          "standing and waving, full body, simple flat illustration. "
          "The image has alpha channel and the background is transparent.")


def alpha_scan(path, rows=None):
    """返回 (w, h, ctype, alpha_min, alpha_max, 透明像素占比)。"""
    data = open(path, "rb").read()
    pos, w, h, ctype, idat = 8, None, None, None, b""
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        if tag == b"IHDR":
            w, h, _, ctype = struct.unpack(">IIBB", body[:10])
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break
        pos += 12 + ln
    if ctype != 6:
        return w, h, ctype, None, None, None
    ch = 4
    raw = zlib.decompress(idat)
    stride = w * ch
    prev = bytearray(stride)
    lo, hi, n_transparent, n_total = 255, 0, 0, 0
    limit = rows or h
    for y in range(min(h, limit)):
        off = y * (stride + 1)
        f = raw[off]
        line = bytearray(raw[off + 1: off + 1 + stride])
        for i in range(stride):
            a = line[i - ch] if i >= ch else 0
            b = prev[i]
            c = prev[i - ch] if i >= ch else 0
            if f == 1:
                p = a
            elif f == 2:
                p = b
            elif f == 3:
                p = (a + b) // 2
            elif f == 4:
                pp = a + b - c
                pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - c)
                p = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
            else:
                p = 0
            line[i] = (line[i] + p) & 0xFF
        for x in range(w):
            av = line[x * ch + 3]
            lo, hi = min(lo, av), max(hi, av)
            n_total += 1
            if av < 16:
                n_transparent += 1
        prev = line
    return w, h, ctype, lo, hi, (n_transparent / n_total if n_total else 0)


def main():
    t0 = time.time()
    if "--scan" in sys.argv:
        # 只扫已有产物，不重新出图：python diag_transparent_gen.py --scan outputs/a060749c9d62/xxx.png
        for rel in sys.argv[sys.argv.index("--scan") + 1:]:
            path = rel if os.path.isabs(rel) else os.path.join(ROOT, rel)
            if not os.path.exists(path):
                print("找不到:", path)
                continue
            w, h, ctype, lo, hi, frac = alpha_scan(path)
            print(f"{rel}\n  {w}x{h} color_type={ctype}")
            print(f"  alpha 范围 = {lo} ~ {hi}，alpha<16 的像素占 {(frac or 0) * 100:.1f}%")
            print("  ✅ 真的生成了透明区域" if frac and frac > 0.05
                  else "  ❌ alpha 接近全不透明（模型没生成透明背景）")
        return 0

    body = {
        "prompt": PROMPT,
        "negative_prompt": "",
        "width": 1024, "height": 1024,
        "steps": 25, "cfg": 1.0, "seed": 777001,
        "sampler_name": "euler", "scheduler": "simple",
    }
    if "--ref" in sys.argv:
        ref = "ref_ec15289879.png"
        body["reference_images"] = [ref]
        body["prompt"] = ("This is an RGBA image with transparency. Keep the character in "
                          "<image1> exactly as is, but remove the background so that only the "
                          "character remains. The image has alpha channel and the background "
                          "is transparent.")
        print(f"带参考图模式：{ref}")

    req = urllib.request.Request(WORKBENCH + "/api/generate",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=60) as r:
        res = json.loads(r.read().decode())
    print("提交:", json.dumps(res, ensure_ascii=False)[:300])
    jid = res.get("job_id")
    if not jid:
        return 1

    last = None
    p = {}
    while time.time() - t0 < 900:
        time.sleep(3)
        with OPENER.open(f"{WORKBENCH}/api/progress/{jid}", timeout=30) as r:
            p = json.loads(r.read().decode())
        cur = (p.get("status"), p.get("step"), p.get("total_steps"))
        if cur != last:
            print(f"  {cur}")
            last = cur
        if p.get("status") in ("done", "error", "cancelled"):
            break
    print("最终:", json.dumps(p, ensure_ascii=False)[:600])
    if p.get("status") != "done":
        return 1

    with OPENER.open(f"{WORKBENCH}/api/jobs/{jid}", timeout=30) as r:
        imgs = (json.loads(r.read().decode()).get("job") or {}).get("images") or []
    print(f"\n产出 {len(imgs)} 张，耗时 {time.time() - t0:.1f}s")
    for im in imgs:
        # 工作台的 images 元素形如 {"file": "<job_id>/<name>.png", "comfy_ref": "..."}
        rel = im.get("file") if isinstance(im, dict) else str(im)
        if not rel:
            print("  (无法解析 images 项)", im)
            continue
        path = os.path.join(ROOT, "outputs", rel.replace("/", os.sep))
        if not os.path.exists(path):
            print("  (找不到文件)", path)
            continue
        w, h, ctype, lo, hi, frac = alpha_scan(path)
        print(f"\n  {rel}")
        print(f"    {w}x{h}  color_type={ctype}")
        print(f"    alpha 范围 = {lo} ~ {hi}，alpha<16 的像素占 {(frac or 0) * 100:.1f}%")
        if frac and frac > 0.05:
            print("    ✅ **真的生成了透明区域**（背景透明）")
        else:
            print("    ❌ alpha 仍然接近全不透明 —— 模型没有按提示词生成透明背景")
    return 0


if __name__ == "__main__":
    sys.exit(main())
