#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""狼娘 × 第五批画风（刺绣 / 泥金手抄本 / 皮影 / 蜡染）

前四轮结论落进本批：
  · 媒介要有**笔触/工艺余量**（剪纸、像素会把脸压成 1~2 个特征）；
    本批四种都能承载面部细节（刺绣丝线、矿物颜料细笔、皮料刻线、蜡刀描线）。
  · **不写瞳色**（Round 1 教训：写了就覆盖参考图）。
  · 第四个瞬间：R1-2「仰头看花」→ R3「掌心接花低头看」→ R4「别花到耳侧、侧头看画外」，
    本批改为**低头把花瓣从掌心吹起来** —— 加入**呼吸**这个联动层（微表情库强调"情绪必须配呼吸"）。
  · 微表情：一侧眉高一线、嘴偏斜（不对称）；双耳朝掌心前倾、尾尖轻翘（联动）；克制不夸张。

用法：python tools/diag/gen_wolf_style_gallery5.py [seed]
"""
import json
import os
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WB = "http://127.0.0.1:8642"
O = urllib.request.build_opener(urllib.request.ProxyHandler({}))

WOLF = r"D:\Pictures\Camera Roll\截图\狼狼.png"

SEED = 20260929
STEPS = 25
CFG = 1.0

LEAD = "以 <image1> 的狼耳少女为主角，外貌、发型、服装与配饰一律以该图为准。"
# 本批共用瞬间：低头把花瓣从掌心吹起来（带呼吸）
MOMENT = "她坐在老屋檐下的石阶上，低头把一片花瓣从掌心吹起来，嘴唇微微张开。"

STYLES = [
    {
        "key": "embroidery",
        "label": "17-刺绣",
        "cn": LEAD + (
            "这是一幅刺绣：画面绣在粗纹的米色麻布上，所有形体都由一针一针的丝线排出来，"
            "线的走向顺着形体的结构，绣得密的地方微微凸起、在侧光下投出细小的影子。" + MOMENT +
            "她的头发用一束束顺着发丝方向的蓝丝线平绣排出来，发梢的线渐渐变稀、露出底下的麻布；"
            "头顶一对狼耳用米白与淡粉的丝线绣出，耳廓的边缘是一圈锁边的短针，两只耳朵朝掌心那一侧前倾。"
            "她的脸是整幅针脚最细的地方：眼睛用两道深色的细线绣出上眼睑与瞳孔，眼皮压得低低的、半眯着，"
            "视线的落点就在掌心那片正被吹起的花瓣上；一侧的眉毛比另一侧高了极细的一线，"
            "嘴用一小段偏斜的朱红线绣出，左边比右边长了极细的一线。"
            "颈间一道深色的线，身上的短裙用密实的黑丝线平绣压成深色，衣褶靠丝线的走向分出；裙摆下缘有一道浅蓝的绣线边。"
            "她伸出的那只手绣得最细，五指并拢、掌心向上，一片花瓣正从掌窝里被吹起来。"
            "身后那条大尾巴用蓝紫两色的丝线一簇簇地绣出蓬松的毛感，尾尖轻轻翘起。"
            "樱花枝从右上方斜进来，枝干用深褐的粗线绣出，花朵用粉色丝线一圈圈盘成五瓣，花心绣一小点朱红；几片花瓣正飘在半空。"
            "瓦檐在上缘用深浅相间的线绣出瓦当的层叠。天空只留麻布本身的米色，绣得最疏的地方几乎看得见经纬；"
            "地面是几道横向的灰线绣出的石阶。"
            "光是从左上方来的侧光，绣线凸起的地方投出细小的阴影，形体全靠针脚的疏密与丝线的走向来分。"
            "整体构图疏朗，针脚最密的地方集中在裙子、发根与花朵三处，四周留出大片没绣过的麻布。"
        ),
    },
    {
        "key": "manuscript",
        "label": "18-泥金手抄本",
        "cn": LEAD + (
            "这是一幅中世纪泥金装饰手抄本插图：画在米黄的羊皮纸上，颜料是磨细的矿物色，"
            "金色部分贴着金箔、在光里发亮；画面四周围着一圈缠枝纹与几何格组成的装饰边框。" + MOMENT +
            "她的头发用平涂的浅蓝矿物色铺出，发梢以更淡的一层收住，发丝的分界用细笔勾出；"
            "头顶一对狼耳用米白与淡粉平涂，耳廓的边缘勾一道深色的细线，两只耳朵朝掌心那一侧前倾。"
            "她的脸是整幅笔法最细的地方：眼睛用两道深色的细线勾出上眼睑与瞳孔，眼皮压得低低的、半眯着，"
            "视线的落点就在掌心那片正被吹起的花瓣上；一侧的眉毛比另一侧高了极细的一线，"
            "嘴用一小段偏斜的朱红勾出，左边比右边长了极细的一线。"
            "颈间一道深色的细线，身上的短裙用平涂的深色压住，衣褶用几道细笔勾出；裙摆下缘有一道浅蓝的边。"
            "她伸出的那只手勾得最细，五指并拢、掌心向上，一片花瓣正从掌窝里被吹起来。"
            "身后那条大尾巴用蓝紫两色平涂，边缘勾出蓬松的毛尖，尾尖轻轻翘起。"
            "樱花枝从右上方斜进来，枝干用深褐平涂，花朵用粉色平涂、花心点一小块朱红；几片花瓣正飘在半空。"
            "瓦檐在上缘用平涂的深色勾出瓦当的层叠。背景是羊皮纸本身的米黄，远处用极淡的蓝灰扫一两笔。"
            "边框里每隔一段嵌一枚小小的金箔方块，四角各有一朵缠枝花。"
            "光是从左上方来的柔和光，金箔在画面右侧亮起一道细长的反光，形体靠平涂的色块与细线的边界来分。"
            "整体构图端整，金色与朱红是画面里最亮的两处，四周留出大片没上色的羊皮纸。"
        ),
    },
    {
        "key": "shadowpuppet",
        "label": "19-皮影",
        "cn": LEAD + (
            "这是一幅皮影：所有形体都用半透明的彩绘皮料刻成，边缘是刀刻的硬边，"
            "皮料上的颜色在背后透进来的光里发亮，各处用细小的铆钉关节连起来。" + MOMENT +
            "她的头发用一片片刻出的浅蓝皮料叠成，发梢收成尖角，发丝的分界是刻透的细缝；"
            "头顶一对狼耳是两块分开刻出的尖形皮料，耳内刻出一小片淡粉，两只耳朵朝掌心那一侧前倾。"
            "她的脸是整幅刻得最细的地方：眼睛刻成两道细长的镂空，视线的落点就在掌心那片正被吹起的花瓣上；"
            "一侧的眉毛比另一侧高了极细的一线，嘴刻成一小段偏斜的朱红皮料，左边比右边长了极细的一线。"
            "颈间一条深色的皮料，身上的短裙用深色的皮料刻出、衣褶是几道刻透的细缝；裙摆下缘有一道浅蓝的皮料边。"
            "她伸出的那只手刻得最细，五指并拢、掌心向上，手腕处有一枚小小的铆钉关节；一片花瓣正从掌窝里被吹起来。"
            "身后那条大尾巴用蓝紫两色的皮料刻出放射状的毛尖，尾尖轻轻翘起。"
            "樱花枝从右上方斜进来，枝干用深褐皮料刻出，花朵刻成五瓣的粉色镂空，花心留一小块朱红；几片花瓣正飘在半空。"
            "瓦檐在上缘用几片深色皮料刻出瓦当的层叠。背景是背后透光的米色幕布，幕布上看得见细密的布纹；"
            "地面是几道刻出的石阶线。"
            "光从幕布后面透进来，皮料的半透明感让颜色发亮，形体靠刻线的边界与皮料的深浅来分。"
            "整体构图疏朗，刻得最密的地方集中在脸与手上，四周留出大片透光的幕布。"
        ),
    },
    {
        "key": "batik",
        "label": "20-蜡染",
        "cn": LEAD + (
            "这是一幅蜡染：布面是靛蓝与白两色，所有线条都是蜡刀描出的防染线，"
            "蓝底上布满蜡层裂开渗进去的细密冰纹。" + MOMENT +
            "她的头发用一层层深浅不同的靛蓝染出，发丝的分界是蜡刀描出的白线；"
            "头顶一对狼耳用留白与淡蓝染出，耳廓的边缘是一圈蜡刀的短点，两只耳朵朝掌心那一侧前倾。"
            "她的脸是整幅留白最多的地方：眼睛用两道深色的蜡线描出上眼睑与瞳孔，"
            "视线的落点就在掌心那片正被吹起的花瓣上；一侧的眉毛比另一侧高了极细的一线，"
            "嘴用一小段偏斜的深线描出，左边比右边长了极细的一线。"
            "颈间一条深色的蜡线，身上的短裙用最浓的靛蓝染住，衣褶靠留白的线条分出；裙摆下缘有一道浅蓝的边。"
            "她伸出的那只手描得最细，五指并拢、掌心向上，一片花瓣正从掌窝里被吹起来。"
            "身后那条大尾巴用深浅两色靛蓝染出放射状的毛尖，尾尖轻轻翘起。"
            "樱花枝从右上方斜进来，枝干用深线描出，花朵用留白圈成五瓣、花心点一小块深蓝；几片花瓣正飘在半空。"
            "瓦檐在上缘用深浅相间的蜡线描出瓦当的层叠。天空是一大片浅靛蓝，蓝底上看得见细密的冰纹；"
            "地面是几道横向的深线描出的石阶。"
            "光是均匀的漫射光，没有方向，形体全靠靛蓝的深浅与留白的边界来分，画面各处都能看见蜡层裂开的细纹。"
            "整体构图疏朗，蓝最深的地方集中在裙子与发根两处，四周留出大片浅蓝与白。"
        ),
    },
]


def upload(path):
    b = "----wolf5" + str(int(time.time() * 1000))
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; "
            f"filename=\"{os.path.basename(path)}\"\r\nContent-Type: application/octet-stream\r\n\r\n").encode()
    body += open(path, "rb").read()
    body += f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(WB + "/api/upload", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    with O.open(req, timeout=300) as r:
        return json.loads(r.read().decode())


def post(path, obj):
    req = urllib.request.Request(WB + path, data=json.dumps(obj).encode(),
                                 headers={"Content-Type": "application/json"})
    with O.open(req, timeout=120) as r:
        return json.loads(r.read().decode())


def get(path):
    with O.open(WB + path, timeout=60) as r:
        return json.loads(r.read().decode())


def wait(jid, label, limit=1500):
    t0 = time.time()
    last = None
    while time.time() - t0 < limit:
        time.sleep(3)
        try:
            p = get(f"/api/progress/{jid}")
        except Exception:
            continue
        cur = (p.get("status"), p.get("step"))
        if cur != last:
            print(f"    {label}: {p.get('status')} step={p.get('step')}/{p.get('total_steps')}"
                  f"  已用 {time.time() - t0:.0f}s")
            last = cur
        if p.get("status") in ("done", "error", "cancelled"):
            return p
    return {"status": "timeout"}


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else SEED
    if not os.path.exists(WOLF):
        print("缺少参考图:", WOLF)
        return 1
    print("上传狼娘人设图…")
    ref = upload(WOLF)["name"]
    print(f"  {ref}")
    print(f"参数：seed={seed}  steps={STEPS}  cfg={CFG}  画布跟随参考图")
    print("本批瞬间：低头把花瓣从掌心吹起来（加入呼吸联动）\n")

    done = []
    for st in STYLES:
        print("=" * 74)
        print(f"{st['label']}   正文 {len(st['cn'])} 字")
        print("=" * 74)
        r = post("/api/generate", {
            "prompt": st["cn"], "negative_prompt": "",
            "steps": STEPS, "cfg": CFG, "seed": seed,
            "reference_images": [ref],
            "custom_canvas": False, "ref_resolution": 0,
        })
        jid = r.get("job_id")
        if not jid:
            print("  提交失败:", json.dumps(r, ensure_ascii=False)[:300])
            continue
        p = wait(jid, st["label"])
        job = get(f"/api/jobs/{jid}")["job"]
        print(f"  status={job['status']} 耗时={job.get('elapsed')}s")
        if job.get("error"):
            print("  错误:", job["error"][:400])
        for im in job.get("images") or []:
            print(f"  产物: outputs/{im['file']}")
            done.append((st["label"], im["file"]))

    print("\n汇总：")
    for label, f in done:
        print(f"  {label} -> outputs/{f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())