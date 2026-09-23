#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""狼娘 × 第四批画风（圆珠笔 / 马赛克 / 掐丝珐琅 / 粉笔黑板）

前三轮结论落进本批：
  · 媒介要有**笔触余量**（剪纸/像素会把脸压成 1~2 个特征）——本批四种都能承载面部细节；
    马赛克特意写成"小块的嵌片"，避免大颗粒把脸糊掉。
  · **不写瞳色**（Round 1 教训）。
  · 换第三个瞬间：Round 1-2 是"仰头看花"，Round 3 是"掌心接花低头看"，
    本批改为**刚把一朵花别到耳侧、手还停在耳边、侧头看向画面外** ——
    视线**离开镜头**（避开摆拍直视），并留一个"没做完的动作"。
  · 微表情：一侧眉高一线、嘴只在左边弯一小弧（不对称）；双耳朝视线方向偏、尾尖轻摆（联动）。

用法：python tools/diag/gen_wolf_style_gallery4.py [seed]
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

SEED = 20260928
STEPS = 25
CFG = 1.0

LEAD = "以 <image1> 的狼耳少女为主角，外貌、发型、服装与配饰一律以该图为准。"
# 本批共用瞬间：别花到耳侧、手停在耳边、侧头看画面外（动作未完成）
MOMENT = ("她坐在老屋檐下的石阶上，刚把一朵花别到耳侧的发间，手还停在耳边没有放下，"
          "微微侧着头，视线越过画面右侧的边缘看向画外。")

STYLES = [
    {
        "key": "ballpoint",
        "label": "13-圆珠笔素描",
        "cn": LEAD + (
            "这是一幅圆珠笔画，画在略泛黄的纸上：线条是细细的圆珠笔油墨，"
            "颜色只有蓝黑与它稀释后的一点点青灰，深浅靠排线的疏密叠出来。" + MOMENT +
            "她的头发用一排排顺着发丝方向的细线排出，发梢的线渐渐变疏、留下纸的底色；"
            "头顶一对狼耳用短促的细线勾出毛边，耳内留白，两只耳朵朝画面右侧微微偏转。"
            "她的脸是整幅排线最少的地方：眼睛用两条细线勾出上眼睑与瞳孔，视线的落点在画面右外侧；"
            "一侧的眉毛比另一侧高了极细的一线，嘴只在左边弯起一小弧、右边还平着。"
            "颈间一条压深的短线，身上的短裙用最密的交叉排线压成近黑，衣褶靠留白的空白线分出；"
            "裙摆下缘有一道浅色的边。她抬起的那只手停在耳边，指节只用几条短弧线交代，两指间还夹着那朵花的细梗。"
            "身后那条大尾巴用放射状的排线排出蓬松的毛感，尾尖轻轻摆向一侧。"
            "樱花枝从右上方斜进来，枝干用密排线画出，花朵只勾轮廓、花瓣内留白，花心点几道短线；几片花瓣正飘在半空。"
            "瓦檐在上缘用斜向的排线画出瓦当的层叠。背景只在远处用极疏的几道线扫出山影，其余留白。"
            "光是从左上方来的侧光，形体完全靠排线的疏密来分，纸上看得见笔尖反复描过的深色处。"
            "整体构图疏朗，排线最密的地方集中在裙子、发根与枝干三处，四周留着大片未被画过的纸。"
        ),
    },
    {
        "key": "mosaic",
        "label": "14-马赛克镶嵌",
        "cn": LEAD + (
            "这是一幅马赛克镶嵌画：整个画面由一块块**细小的方形与三角形嵌片**拼成，"
            "嵌片之间留着细细的灰浆缝，每一块嵌片的颜色都略有深浅差别，表面带着石材与玻璃的哑光。" + MOMENT +
            "她的头发用一排排顺着发丝方向的浅蓝嵌片排出，越到发梢嵌片越稀、露出底下的灰浆；"
            "头顶一对狼耳用米白与淡粉两色的嵌片拼出，耳廓的边缘是锯齿状的碎嵌片，两只耳朵朝画面右侧偏转。"
            "她的脸用最小的一批嵌片拼成：眼睛是几块深色的碎嵌片，视线的落点在画面右外侧；"
            "一侧的眉毛比另一侧高了极细的一线，嘴只在左边弯起一小弧、右边还平着。"
            "颈间一行深色的嵌片，身上的短裙用黑色与深灰两色的嵌片排出衣褶的走向，裙摆下缘有一道浅蓝的嵌片边。"
            "她抬起的那只手停在耳边，手指用几块细长的嵌片交代，两指间夹着一朵花的花梗。"
            "身后那条大尾巴用蓝紫两色的嵌片排出放射状的毛感，尾尖轻轻摆向一侧。"
            "樱花枝从右上方斜进来，枝干用深褐的嵌片排出，花朵用粉色嵌片围成五瓣，花心嵌一小块深红；几片花瓣正飘在半空。"
            "瓦檐在上缘用深浅相间的嵌片排出瓦当的层叠。天空是一大片浅米色的嵌片，越靠上嵌片越大；地面是一层层灰色的石阶嵌片。"
            "光是均匀的，形体完全靠嵌片的深浅与灰浆缝的走向来分，画面里没有一处平涂的色块。"
            "整体构图疏朗，最细的嵌片集中在脸与手上，四周的嵌片明显变大。"
        ),
    },
    {
        "key": "cloisonne",
        "label": "15-掐丝珐琅",
        "cn": LEAD + (
            "这是一幅掐丝珐琅画：画面由细金属丝围成的一个个小区块组成，"
            "丝线是鎏金的，区块里填着浓艳的珐琅釉，釉面有细小的气泡与磨痕，光在釉上留下一层硬亮的反光。" + MOMENT +
            "她的头发用一道道金色细丝分隔出浅蓝的釉块，越到发梢丝线越密、釉色越浅；"
            "头顶一对狼耳用米白与淡粉的釉块拼出，耳廓的边缘由金丝走形，两只耳朵朝画面右侧偏转。"
            "她的脸是整幅丝线最细的地方：眼睛用两道极细的金丝勾出上眼睑与瞳孔，视线的落点在画面右外侧；"
            "一侧的眉毛比另一侧高了极细的一线，嘴只在左边弯起一小弧、右边还平着。"
            "颈间一道深色的釉条，身上的短裙填着近黑的釉，衣褶靠金丝的走向分出；裙摆下缘有一道浅蓝的釉边。"
            "她抬起的那只手停在耳边，指节由几段细金丝勾出，两指间夹着一朵花的花梗。"
            "身后那条大尾巴填着蓝紫两色的釉块，金丝排出放射状的毛感，尾尖轻轻摆向一侧。"
            "樱花枝从右上方斜进来，枝干填深褐釉，花朵用粉色与玫红的釉块拼成五瓣，花心嵌一滴朱红；几片花瓣正飘在半空。"
            "瓦檐在上缘用深浅相间的釉块排出瓦当的层叠。天空是一大片淡青的釉，釉面看得见细小的开片；地面是灰蓝的釉块石阶。"
            "光是柔和的，釉面在画面右侧有一道硬亮的高光，形体靠金丝的分隔与釉色的深浅来分。"
            "整体构图疏朗，最细的金丝集中在脸与手上，四周的釉块明显变大。"
        ),
    },
    {
        "key": "chalk",
        "label": "16-粉笔画-黑板",
        "cn": LEAD + (
            "这是一幅黑板粉笔画：底色是深墨绿的黑板，画面完全由白色的粉笔线条与几笔淡彩的粉笔灰堆出来，"
            "粉笔走过的地方留着细碎的粉痕与断线，手指擦过的地方是一片模糊的白雾。" + MOMENT +
            "她的头发用一排排白色的粉笔短线排出，发梢的线渐渐变淡、散成粉雾；"
            "头顶一对狼耳用白粉笔勾出轮廓，耳内用一小片淡粉的粉笔灰抹开，两只耳朵朝画面右侧偏转。"
            "她的脸是整幅最亮的地方：眼睛用两道深色的短线压在粉笔白上，视线的落点在画面右外侧；"
            "一侧的眉毛比另一侧高了极细的一线，嘴只在左边弯起一小弧、右边还平着。"
            "颈间一条白色的短线，身上的短裙用一大片擦开的粉笔灰压成深色，衣褶靠留下的白色粉线分出；裙摆下缘有一道淡蓝的粉线。"
            "她抬起的那只手停在耳边，指节只用几道白粉笔的短弧线交代，两指间夹着一朵花的花梗。"
            "身后那条大尾巴用白色粉笔的放射状线条排出毛感，尾尖轻轻摆向一侧。"
            "樱花枝从右上方斜进来，枝干用白色粉笔勾出，花朵用淡粉的粉笔灰抹成五瓣，花心点一小块深色；几片花瓣正飘在半空。"
            "瓦檐在上缘用白色的粉笔线画出瓦当的层叠。天空是黑板本身的深绿，只在右下角留出一小块没被擦过的黑板原色；地面是几道白色的粉线勾出的石阶。"
            "光是从左上方来的侧光，把粉笔的颗粒照出细小的起伏，形体全靠粉笔的白与黑板的深来分。"
            "整体构图疏朗，白色的粉痕最密的地方集中在头发、尾巴与花朵三处，四周留着大片黑板底色。"
        ),
    },
]


def upload(path):
    b = "----wolf4" + str(int(time.time() * 1000))
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
    print("本批瞬间：别花到耳侧、手停在耳边、侧头看画外（动作未完成）\n")

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