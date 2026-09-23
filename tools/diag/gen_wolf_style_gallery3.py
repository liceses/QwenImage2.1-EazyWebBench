#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""狼娘 × 第三批画风（青花瓷 / 彩铅 / 水彩 / 铜版画）

Round 1-2 的结论落进本批：
  · 选**有笔触余量**的媒介 —— 剪纸/像素会把脸压成 1~2 个特征，微表情施展不开；
    青花瓷、彩铅、水彩、铜版画都能承载面部细节。
  · **不指定瞳色**（Round 1 玻璃彩绘里我写"琥珀黄的眼睛"直接把角色瞳色改了）。
  · 换一个**瞬间**：前两轮都是"仰头看花"，本批改为
    **刚用掌心接住一片花瓣、低头看着它** —— 测另一种自然神态（小发现/专注），视线朝下。
  · 微表情纪律：一侧眉比另一侧高一线、嘴只在左边弯一小弧（不对称）；
    双耳朝掌心前倾、尾尖上卷（联动）；克制不用夸张词。

用法：python tools/diag/gen_wolf_style_gallery3.py [seed]
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

SEED = 20260927
STEPS = 25
CFG = 1.0

LEAD = "以 <image1> 的狼耳少女为主角，外貌、发型、服装与配饰一律以该图为准。"
# 本批共用的"瞬间"：接住花瓣低头看 —— 保证四条只有画风是变量
MOMENT = "她坐在老屋檐下的石阶上，刚用掌心接住一片落下来的花瓣，正低头看着它。"

STYLES = [
    {
        "key": "porcelain",
        "label": "9-青花瓷",
        "cn": LEAD + (
            "这是一幅青花瓷画：整幅只用一种钴蓝，浓处近墨、淡处如烟，画在白釉的瓷面上；"
            "釉面有细细的冰裂纹，光在釉上留下一层柔和的反光。" + MOMENT +
            "她的头发用几笔浓淡不同的钴蓝扫出，发梢以最淡的一档收住；"
            "头顶一对狼耳用中锋勾出轮廓、耳内留白，两只耳朵朝掌心那一侧微微前倾。"
            "她的脸是整幅留白最多的地方：眼睛只画上眼睑与一小段瞳线，视线的落点就在掌心里那片花瓣上；"
            "一侧的眉毛比另一侧高了极细的一线，嘴只在左边弯起一小弧、右边还平着。"
            "颈间一条细线勾出的颈圈，身上的短裙用大块的浓蓝平涂，衣褶靠留白的细线分出；"
            "裙摆下缘有一道淡蓝的边。她伸出的那只手是整幅最细的几笔：五指并拢、掌心向上，一片花瓣正好落在掌窝里。"
            "身后那条大尾巴用淡蓝的飞白扫出蓬松的毛感，尾尖向上卷起一小勾。"
            "樱花枝从右上方斜进来，枝干用浓蓝写出，花朵只勾轮廓、花瓣内留白；几片花瓣正飘在半空。"
            "瓦檐在上缘用浓蓝的几笔勾出瓦当的层叠。背景是瓷面本身的白色，只在远处扫一两笔极淡的蓝表示山影。"
            "光是柔和的，釉面在画面右侧有一道浅浅的高光，所有的形体都靠蓝的浓淡与留白来分。"
            "整体构图疏朗，白色釉面占去大半，钴蓝最浓的地方集中在裙子、发根与枝干三处。"
        ),
    },
    {
        "key": "pencil",
        "label": "10-彩色铅笔",
        "cn": LEAD + (
            "这是一幅彩色铅笔画，画在带纹理的素描纸上：每一笔都能看见铅笔的走向，"
            "浅色的地方是一层一层叠出来的，纸的颗粒从颜色里透出来。" + MOMENT +
            "她的头发用一排排顺着发丝方向的蓝色短笔触排出来，发梢的地方笔触更轻、留下纸的白；"
            "头顶一对狼耳用米白与淡粉两色叠出，耳廓的边缘是铅笔一笔一笔点出来的毛边，两只耳朵朝掌心那一侧微微前倾。"
            "她的脸用极浅的肤色轻轻铺过：眼睛只画上眼睑与瞳孔的深色，视线的落点就在掌心里那片花瓣上；"
            "一侧的眉毛比另一侧高了极细的一线，嘴只在左边弯起一小弧、右边还平着。"
            "颈间一条深色的短笔触，身上的短裙用黑色与深灰两色一层层叠出，衣褶靠留白的纸面分出；"
            "裙摆下缘有一道浅蓝的边。她伸出的那只手画得最细：指节用浅浅的线勾出，一片花瓣正落在掌窝里。"
            "身后那条大尾巴用蓝紫两色的斜向笔触排出蓬松的毛感，尾尖向上卷起一小勾。"
            "樱花枝从右上方斜进来，枝干用深褐色的硬笔触画出，花朵用粉色一层层叠出来，花心点一点朱红；几片花瓣正飘在半空。"
            "瓦檐在上缘用深灰与靛蓝的排线画出瓦当的层叠。背景只留纸的白，远处用极轻的蓝灰扫几道。"
            "光是从左上方来的柔和光，形体靠颜色的深浅与笔触的方向来分，纸的纹理从所有颜色里透出来。"
            "整体构图疏朗，铅笔笔触最密的地方集中在头发、尾巴与花朵三处，四周留出大片纸白。"
        ),
    },
    {
        "key": "watercolor",
        "label": "11-水彩",
        "cn": LEAD + (
            "这是一幅水彩画：颜料在湿纸上化开，边缘留着水痕，白色的纸从最亮的地方透出来。" + MOMENT +
            "她的头发是一整片浅蓝的湿染，发梢的颜色自然淡下去、留出纸白；"
            "头顶一对狼耳用两笔淡彩点出，耳内是一小团淡淡的粉，两只耳朵朝掌心那一侧微微前倾。"
            "她的脸只用了极少的水分：眼睛是两点深色的短笔触，视线的落点就在掌心里那片花瓣上；"
            "一侧的眉毛比另一侧高了极细的一线，嘴只在左边弯起一小弧、右边还平着。"
            "颈间一条深色的细线，身上的短裙用一大片浓黑压下去，衣褶靠留白的纸面分出；裙摆下缘有一道浅蓝的水痕。"
            "她伸出的那只手画得最轻：指节只用浅浅的几笔带过，一片花瓣正落在掌窝里。"
            "身后那条大尾巴用蓝紫两色晕开，边缘毛茸茸的，尾尖向上卷起一小勾。"
            "樱花枝从右上方斜进来，枝干用一笔浓褐画出，花朵是几团粉色的湿染，花心点一滴朱红；颜料在花瓣边缘微微洇开。"
            "几片花瓣正飘在半空，其中一片正落向她的掌心。"
            "瓦檐在上缘用湿墨一笔带过，瓦当的层叠靠深浅的水痕分出。背景是纸的白，只在远处扫一两笔极淡的蓝灰。"
            "光是从左上方来的柔和散射光，形体靠水痕的边界与纸的留白来分，画面里看得见颜料干后留下的水渍边。"
            "整体构图通透，纸白占去大半，颜色最浓的地方集中在裙子与发根两处。"
        ),
    },
    {
        "key": "etching",
        "label": "12-铜版画",
        "cn": LEAD + (
            "这是一幅铜版画：整幅由细密的刻线与交叉排线组成，线条的疏密决定深浅，没有一块平涂。" + MOMENT +
            "她的头发用一排排顺着发丝方向的平行刻线排出，发梢的线渐渐变细、断开；"
            "头顶一对狼耳用短促的刻线勾出毛边，耳内留白，两只耳朵朝掌心那一侧微微前倾。"
            "她的脸是整幅刻线最少的地方：眼睛只用两条短线勾出上眼睑与瞳孔，视线的落点就在掌心里那片花瓣上；"
            "一侧的眉毛比另一侧高了极细的一线，嘴只在左边弯起一小弧、右边还平着。"
            "颈间一条深色的短线，身上的短裙用最密的交叉排线压成近黑，衣褶靠留白的空白线分出；裙摆下缘有一道浅色的边。"
            "她伸出的那只手刻得最细：指节的轮廓由几条短弧线组成，一片花瓣正落在掌窝里。"
            "身后那条大尾巴用放射状的排线排出蓬松的毛感，尾尖向上卷起一小勾。"
            "樱花枝从右上方斜进来，枝干用密排线刻出，花朵只勾轮廓、花瓣内留白，花心点几道短刻线；几片花瓣正飘在半空。"
            "瓦檐在上缘用交叉排线刻出瓦当的层叠。背景只在远处用极疏的几道线扫出山影，其余留白。"
            "光是从左上方来的侧光，形体完全靠刻线的疏密来分。"
            "整体构图疏朗，排线最密的地方集中在裙子、发根与枝干三处，画面四周留着大片未被刻过的纸白。"
        ),
    },
]


def upload(path):
    b = "----wolf3" + str(int(time.time() * 1000))
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
    print(f"本批瞬间：接住花瓣低头看（与前两轮的'仰头看花'不同）\n")

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