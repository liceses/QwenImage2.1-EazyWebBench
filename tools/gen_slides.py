#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Qwen-Image-2.1 直接生成「带排版的 PPT 幻灯片」的能力。

变量：单页文字量（封面 ~20 字 → 内容页 ~48 字 → 表格页 ~90 字）。
判据：文字是否逐字正确、版面是否成立（不是文字糊成一团）。
画布统一 1920x1088（16:9）。
"""
import json
import os
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8642"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ppt_zcode", "gen_slides")
os.makedirs(OUT, exist_ok=True)
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

T1 = """一张 16:9 的学术风格 PPT 封面幻灯片，杂志版面设计。
深藏青到墨黑的暗色背景，左侧留 8% 宽的空白页边距。
左上角一行小号琥珀色无衬线标签文字：「官方公告」。
下方一行非常大的白色衬线中文标题：「ZCode 开源」。
标题下方一条短的琥珀色横线。
再下方一行中等大小的浅灰色中文副标题：「一次安全事件的整改、审计与开源」。
左下角一行小号灰色文字：「2026 年 9 月 21 日 08:45」。
画面右侧是深色背景上的抽象几何光效（几个半透明的圆和一条斜光线），不放文字。
整张幻灯片除了上面列出的这几行文字以外没有任何其它文字，排版克制、专业、大量留白。"""

T2 = """一张 16:9 的学术风格 PPT 内容幻灯片，杂志版面设计。
暖白色（接近 #F7F5F1）背景，四周留 8% 宽的空白页边距。
左上角一行小号灰色无衬线标签文字：「01   事件」。
下方一行大号深藏青衬线中文标题：「社区反馈与官方回应」。
标题下方一条细的浅灰色横线。
横线下方是三行左对齐的正文，每行前面有一个小圆点：
「社区反馈的 ZCode 产品安全问题」
「官方公告称已完成整改」
「并向所有用户道歉」
正文是深灰色无衬线中文，字号中等，行距宽松。
页面右下角一行很小的浅灰色页码：「1 / 10」。
除上述文字外，整张页面没有任何其它文字或图形，大量留白、克制、专业。"""

T3 = """一张 16:9 的学术风格 PPT 表格幻灯片，杂志版面设计。
暖白色（接近 #F7F5F1）背景，四周留 8% 宽的空白页边距。
左上角一行小号灰色标签文字：「04   审计」。
下方一行大号深藏青衬线中文标题：「两份第三方安全审计」。
标题下方一条细的浅灰色横线。
横线下方是一个两列的数据表格，表头是两行深色加粗小字：「中国信息通信研究院」和「绿盟科技」。
表格第一行左侧灰色小字「存储桶结论」，右侧两列分别是：
「zcode-prod 阿里云 OSS 存储桶状态为云端零数据」
「全部数据对象及存储桶本身已删除」
表格第二行左侧灰色小字「客户端结论」，右侧两列分别是：
「v3.14.0 客户端已完成安全整改」
「未发现可触发本地仓库快照或文件外发的功能路径」
表格用细的浅灰色横线分隔，没有竖线，文字都是深灰色无衬线中文。
除上述文字外没有其它文字，版面对齐整齐、大量留白、专业。"""

CASES = [("Q1_封面_20字", T1, 8801), ("Q2_内容页_48字", T2, 8802), ("Q3_表格页_90字", T3, 8803)]


def post(path, payload):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=60) as r:
        return json.load(r)


def get(path, timeout=15):
    with OPENER.open(BASE + path, timeout=timeout) as r:
        return json.load(r)


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    todo = [c for c in CASES if not only or only in c[0]]
    for name, prompt, seed in todo:
        print(f"\n{'='*70}\n[{name}]")
        payload = {"prompt": prompt, "negative_prompt": " ",
                   "steps": 35, "cfg": 1.0, "width": 1920, "height": 1088,
                   "seed": seed, "reference_images": [], "ref_resolution": 0}
        try:
            r = post("/api/generate", payload)
        except urllib.error.HTTPError as e:
            print("  提交失败:", e.code, e.read().decode("utf-8", "replace")[:300])
            continue
        job = r.get("job_id")
        if not job:
            print("  被拒绝:", json.dumps(r, ensure_ascii=False)[:300]); continue
        t0 = time.time()
        while time.time() - t0 < 900:
            time.sleep(3)
            p = get(f"/api/progress/{job}")
            if p.get("status") != "running":
                break
        full = get(f"/api/jobs/{job}")
        imgs = (full.get("job") or {}).get("images") or []
        if not imgs:
            print("  无产物:", p.get("error")); continue
        rel = imgs[0]["file"]
        src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs",
                           rel.replace("/", os.sep))
        dst = os.path.join(OUT, name + ".png")
        with open(src, "rb") as fi, open(dst, "wb") as fo:
            fo.write(fi.read())
        print(f"  OK {p.get('elapsed')}s -> {dst}")
    print("\n产物:", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
