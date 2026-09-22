#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用 Qwen-Image-2.1 直接生成整套「带版面设计」的 PPT 幻灯片（一页一张图）。

统一设计系统（与 Q1/Q2/Q3 一致）：
  暖白纸底 #F7F5F1 · 深藏青标题 · 深灰正文 · 琥珀强调 · 衬线标题 / 无衬线正文
  浅色内容页 + 深色封面/结语，8% 页边距，大量留白
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

LIGHT = "暖白色（接近 #F7F5F1）背景，四周留 8% 宽的空白页边距。"
DARK = "深藏青到墨黑的暗色背景，四周留 8% 宽的空白页边距。"

HEAD = ("左上角一行小号灰色无衬线标签文字：「{num}   {kick}」。\n"
        "下方一行大号深藏青衬线中文标题：「{title}」。\n"
        "标题下方一条细的浅灰色横线。\n")
TAIL = "除上述文字外，整张页面没有任何其它文字，大量留白、排版克制专业、对齐整齐。"

SLIDES = [
    # 01 封面（重跑，换种子避开形近字）
    ("S01_封面", 9101, DARK, """一张 16:9 的学术风格 PPT 封面幻灯片，杂志版面设计。
深藏青到墨黑的暗色背景，左侧留 8% 宽的空白页边距。
左上角一行小号琥珀色无衬线标签文字：「官方公告」。
下方一行非常大的白色衬线中文标题：「ZCode 开源」。
标题下方一条短的琥珀色横线。
再下方一行中等大小的浅灰色中文副标题：「一次安全事件的整改、审计与开源」。
左下角一行小号灰色文字：「2026 年 9 月 21 日 08:45」。
画面右侧是深色背景上的抽象几何光效（几个半透明的圆和一条斜光线），不放文字。
整张幻灯片除了上面列出的这几行文字以外没有任何其它文字，排版克制、专业、大量留白。"""),

    # 02 摘要
    ("S02_摘要", 9102, LIGHT, f"""一张 16:9 的学术风格 PPT 内容幻灯片，杂志版面设计。
{LIGHT}
{HEAD.format(num="00", kick="摘要", title="一页看懂")}
横线下方是三组内容，每组由一行加粗小标题和一行浅色说明组成，从上到下竖直排列，组之间用细横线分隔：
第一组，小标题「整改完成并致歉」，说明「针对社区反馈的 ZCode 产品安全问题，已完成整改并向所有用户道歉」。
第二组，小标题「代码已开源」，说明「已开源至 github.com/zai-org/ZCode，把代码交给社区监督」。
第三组，小标题「两份第三方审计」，说明「中国信息通信研究院与绿盟科技分别开展安全审计」。
{TAIL}"""),

    # 03 事件与回应（「官方公告称」会稳定被渲染成「官方公全称」，改写绕开）
    ("S03_事件与回应", 9103, LIGHT, f"""一张 16:9 的学术风格 PPT 内容幻灯片，杂志版面设计。
{LIGHT}
{HEAD.format(num="01", kick="事件", title="社区反馈与官方回应")}
横线下方是三行左对齐的正文，每行前面有一个小圆点：
「社区反馈的 ZCode 产品安全问题」
「官方表示已完成整改」
「并向所有用户道歉」
正文是深灰色无衬线中文，字号中等，行距宽松。
页面右下角一行很小的浅灰色页码：「2 / 9」。
{TAIL}"""),

    # 04 整改清单
    ("S04_整改清单", 9104, LIGHT, f"""一张 16:9 的学术风格 PPT 内容幻灯片，杂志版面设计。
{LIGHT}
{HEAD.format(num="02", kick="整改", title="已完成的三项整改")}
横线下方是三条横向的浅灰色带状卡片，从上到下竖直排列、等距分布；每张卡片左侧有一条竖向的琥珀色短线作为标记。
第一张卡片：加粗小标题「移除 Repo Wiki 功能」，下面一行浅色说明「Repo Wiki 入口及相应生成链路已移除」。
第二张卡片：加粗小标题「切断本地仓库快照链路」，下面一行浅色说明「已切断本地仓库快照生成与上传链路」。
第三张卡片：加粗小标题「客户端安全整改」，下面一行浅色说明「ZCode v3.14.0 客户端已完成安全整改」。
{TAIL}"""),

    # 05 开源
    ("S05_开源", 9105, LIGHT, f"""一张 16:9 的学术风格 PPT 内容幻灯片，左右分栏的杂志版面。
{LIGHT}
{HEAD.format(num="03", kick="开源", title="把代码交给社区监督")}
横线下方分为左右两栏。
左栏是文字：先一行中等大小的深藏青中文「我们已将 ZCode 开源」，
下面一行青色的等宽字体网址「github.com/zai-org/ZCode」，
再下面一行深灰色中文「把代码交给社区监督，让 ZCode 变得开放、透明」，
最后一行更小的浅灰色中文「公告同时表示，欢迎开发者伙伴持续检查和反馈问题」。
右栏是一张抽象配图：深色背景下从一个发光核心向右侧扩散出细密的立体线网，若干节点上有小立方体；
配图下方一行很小的灰色斜体图注：「图 1 · 代码向社区展开」。
{TAIL}"""),

    # 06 两份审计（表格）
    ("S06_两份审计", 9106, LIGHT, f"""一张 16:9 的学术风格 PPT 表格幻灯片，杂志版面设计。
{LIGHT}
{HEAD.format(num="04", kick="审计", title="两份第三方安全审计")}
横线下方是一个三列两行的数据表格，表头两列是加粗深色小字：「中国信息通信研究院」和「绿盟科技」，第一列表头留空。
表格第一行左侧灰色小字「存储桶结论」，右侧两列分别是：
「zcode-prod 阿里云 OSS 存储桶状态为云端零数据」
「全部数据对象及存储桶本身已删除」
表格第二行左侧灰色小字「客户端结论」，右侧两列分别是：
「ZCode v3.14.0 客户端已完成安全整改」
「未发现可触发本地仓库快照或文件外发的功能路径」
表格只用细的浅灰色横线分隔，没有竖线，文字都是深灰色无衬线中文。
{TAIL}"""),

    # 07 审计边界（解读页）
    ("S07_审计边界", 9107, LIGHT, f"""一张 16:9 的学术风格 PPT 内容幻灯片，左右两个并列的圆角方框。
{LIGHT}
{HEAD.format(num="05", kick="解读", title="审计证实了什么，公告承诺了什么")}
横线下方左右并排两个圆角矩形方框。
左边的方框是淡青色底、青色边框，方框内第一行是青色加粗小标题「有第三方审计背书」，
下面三行带圆点的深灰色中文：「zcode-prod 阿里云 OSS 存储桶为云端零数据」、「存储桶内全部数据对象及存储桶本身已删除」、「ZCode v3.14.0 客户端已完成安全整改」。
右边的方框是淡琥珀色底、琥珀色边框，方框内第一行是琥珀色加粗小标题「出自公告的官方承诺」，
下面三行带圆点的深灰色中文：「承诺代码数据无留存」、「从未将其用于模型训练」、「将建立常态化产品安全漏洞机制」。
两个方框下方一行深藏青中文：「两份审计的结论只覆盖 OSS 存储桶与 v3.14.0 客户端两项；无留存与未用于训练出自公告的官方表述，审计结论未涉及。」
{TAIL}"""),

    # 08 流程线
    ("S08_脉络", 9108, LIGHT, f"""一张 16:9 的学术风格 PPT 流程图幻灯片，杂志版面设计。
{LIGHT}
{HEAD.format(num="06", kick="脉络", title="从社区反馈到持续监督")}
横线下方是一条横向的流程线：五个琥珀色的小圆点等距横向排开，圆点之间用细的浅灰色横线连接；
每个圆点下方一行居中的深藏青加粗中文，从左到右依次是：
「社区反馈问题」「完成整改并致歉」「开源代码」「第三方审计」「持续监督」。
流程线下方一行灰色小字标题「公告中的对应表述」，再下面四行左对齐的深灰色中文引文：
「针对社区反馈的 ZCode 产品安全问题，我们已经完成整改，并向所有用户道歉。」
「我们已将 ZCode 开源，把代码交给社区监督，让 ZCode 变得开放、透明。」
「经中国信息通信研究院技术评测，确认 OSS 存储桶状态为云端零数据。」
「再次向大家致歉，请大家持续监督。」
{TAIL}"""),

    # 09 结语
    ("S09_结语", 9109, DARK, """一张 16:9 的学术风格 PPT 结尾幻灯片，杂志版面设计。
深藏青到墨黑的暗色背景，左侧留 8% 宽的空白页边距。
画面中偏左是两行非常大的中文衬线标题：第一行白色「再次向大家致歉」，第二行琥珀色「请大家持续监督」。
标题下方一条短的琥珀色横线。
横线下方一行浅灰色中文「审计背书的是存储桶与客户端两项；无留存、未用于训练是公告的承诺」。
左下角一行小号深灰色文字：「来源：ZCode 官方公告（2026-09-21 08:45） · github.com/zai-org/ZCode」。
画面右侧是深色背景上的抽象几何配图（两个半透明圆环叠加，一束光穿过），不放文字。
整张幻灯片除了上述文字外没有任何其它文字，排版克制、专业。"""),
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
    only = sys.argv[1] if len(sys.argv) > 1 else None
    todo = [s for s in SLIDES if not only or only in s[0]]
    print(f"共 {len(todo)} 页")
    for name, seed, _bg, prompt in todo:
        print(f"\n{'='*70}\n[{name}]  seed={seed}")
        payload = {"prompt": prompt, "negative_prompt": " ",
                   "steps": 35, "cfg": 1.0, "width": 1920, "height": 1088,
                   "seed": seed, "reference_images": [], "ref_resolution": 0}
        try:
            r = post("/api/generate", payload)
        except urllib.error.HTTPError as e:
            print("  提交失败:", e.code, e.read().decode("utf-8", "replace")[:200])
            continue
        job = r.get("job_id")
        if not job:
            print("  被拒绝:", json.dumps(r, ensure_ascii=False)[:200]); continue
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
        print(f"  OK {p.get('elapsed')}s -> {os.path.basename(dst)}")
    print("\n目录:", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
