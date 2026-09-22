#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为 ZCode 开源公告 PPT 生成 4 张抽象概念配图（纯文生图，不带参考图）。

风格统一：深藏青/炭黑底 + 暖琥珀光 + 冷青点缀，几何抽象、克制、无文字。
学术期刊封面质感，不要插画人物、不要文字。
"""
import json
import os
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8642"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ppt_zcode", "figs")
os.makedirs(OUT, exist_ok=True)
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

STYLE = ("抽象概念图，深藏青到墨黑的暗色空间，暖琥珀色为主光、冷青色为点缀光，"
         "极简几何构成，克制的学术期刊封面质感，材质细腻有体积感，"
         "画面中没有任何文字、字母、数字，没有任何人物。")

FIGS = [
    ("01-cover", 20260921,
     "一个半透明的玻璃立方体悬浮在黑暗空间的正中央，立方体内部有细密的青蓝色光点像数据流一样缓慢流动；"
     "立方体的一侧被一束从右上角射来的暖琥珀色光强烈照亮，另一侧落在深蓝的阴影里，"
     "下方地面上有一个柔和的倒影。画面极简、对称、空旷。" + STYLE),

    ("02-opensource", 20260922,
     "一个明亮的青白色发光核心位于画面左侧，从中向外辐射出成千上万条极细的光线，"
     "这些光线向右扩散、在画面右侧织成一张逐渐稀疏的立体网络；"
     "网络的一些节点上悬浮着小小的透明立方体。整体像一张正在展开的数据网络。" + STYLE),

    ("03-audit", 20260923,
     "两个巨大的半透明圆环像两枚放大镜一样、以不同角度悬叠在画面中央，"
     "圆环内部是极其细密的网格与数据点阵；一束暖琥珀色的扫描光从左侧穿过两个圆环，"
     "在背景上投下两道清晰的环形阴影。几何、精确、克制。" + STYLE),

    ("04-mechanism", 20260924,
     "三条粗细不同的弧形箭头首尾相接、在深色空间里构成一个闭环的循环结构，"
     "环上的三个节点各是一个发光的琥珀色小球，"
     "闭环中心的暗处有一个微小的青色发光点，"
     "整体像一套精密机制的示意图，线条干净、结构清晰。" + STYLE),
]


def post(path, payload):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=60) as r:
        return json.load(r)


def get(path, timeout=15):
    with OPENER.open(BASE + path, timeout=timeout) as r:
        return json.load(r)


def main():
    for name, seed, prompt in FIGS:
        payload = {
            "prompt": prompt, "negative_prompt": " ",
            "steps": 35, "cfg": 1.0, "width": 1920, "height": 1088,
            "seed": seed, "reference_images": [], "ref_resolution": 0,
        }
        print(f"\n[{name}] 提交…")
        try:
            r = post("/api/generate", payload)
        except urllib.error.HTTPError as e:
            print("  提交失败:", e.code, e.read().decode("utf-8", "replace")[:300])
            continue
        job = r.get("job_id")
        if not job:
            print("  被拒绝:", json.dumps(r, ensure_ascii=False)[:300])
            continue
        t0 = time.time()
        while time.time() - t0 < 900:
            time.sleep(3)
            p = get(f"/api/progress/{job}")
            if p.get("status") != "running":
                break
        full = get(f"/api/jobs/{job}")
        imgs = (full.get("job") or {}).get("images") or []
        if not imgs:
            print("  无产物:", p.get("error"))
            continue
        rel = imgs[0]["file"]
        src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs",
                           rel.replace("/", os.sep))
        dst = os.path.join(OUT, name + ".png")
        with open(src, "rb") as fi, open(dst, "wb") as fo:
            fo.write(fi.read())
        print(f"  OK {p.get('elapsed')}s -> {dst}")
    print("\n配图目录:", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
