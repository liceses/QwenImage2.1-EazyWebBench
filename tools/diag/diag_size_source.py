#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断：任务记录的宽高 vs 产物 PNG 的真实像素尺寸。

用来定位"界面显示的尺寸和实际图片不一致"的根因：
   · 记录值来自 server.py 的 params.width/height（用户在界面上选的，或编辑模式下的默认值）
   · 真实值来自产物 PNG 的 IHDR
两者在"参考图编辑"场景下**本来就会不一致** —— 编辑模式下画布跟随 <image1>，
params 里的 1024×1024 只是界面默认值，并非最终画布。

用法：python tools/diag/diag_size_source.py
"""
import json
import os
import struct
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

WB = "http://127.0.0.1:8642"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))


def png_size(path):
    """读 PNG 的 IHDR，返回 (w, h)；读不到返回 None。"""
    try:
        with open(path, "rb") as f:
            head = f.read(33)
    except OSError:
        return None
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    w, h = struct.unpack(">II", head[16:24])
    return w, h


def main():
    data = json.loads(OPENER.open(WB + "/api/jobs", timeout=30).read().decode())
    jobs = data.get("jobs") or []
    print(f"接口返回 {len(jobs)} 个任务\n")

    agree = mismatch = missing = 0
    rows = []
    for j in jobs:
        p = j.get("params") or {}
        rw, rh = p.get("width"), p.get("height")
        imgs = j.get("images") or []
        if not imgs:
            continue
        f = os.path.join(ROOT, "outputs", imgs[0]["file"])
        real = png_size(f)
        if real is None:
            missing += 1
            continue
        if real == (rw, rh):
            agree += 1
        else:
            mismatch += 1
            rows.append({
                "job": j["id"], "mode": p.get("mode"),
                "refs": len(p.get("reference_images") or []),
                "record": f"{rw}×{rh}", "real": f"{real[0]}×{real[1]}",
                "custom_canvas": p.get("custom_canvas"),
            })

    print(f"记录值 == 真实值 : {agree} 个")
    print(f"记录值 != 真实值 : {mismatch} 个")
    print(f"产物缺失/读不到   : {missing} 个\n")

    if rows:
        print("不一致明细（这就是「尺寸显示与实际不符」的来源）：")
        print(f"  {'job':<14}{'mode':<8}{'refs':<6}{'记录值':<12}{'真实值':<12}custom_canvas")
        for r in rows[:40]:
            print(f"  {r['job']:<14}{str(r['mode']):<8}{r['refs']:<6}"
                  f"{r['record']:<12}{r['real']:<12}{r['custom_canvas']}")
        if len(rows) > 40:
            print(f"  …还有 {len(rows) - 40} 条")
        # 归纳规律
        edit = [r for r in rows if r["refs"] > 0 and not r["custom_canvas"]]
        print(f"\n  其中「有参考图 + 未自定义画布」= {len(edit)} 个 —— "
              "这类任务画布跟随 <image1>，params 里的宽高只是界面默认值")
    return 0


if __name__ == "__main__":
    sys.exit(main())
