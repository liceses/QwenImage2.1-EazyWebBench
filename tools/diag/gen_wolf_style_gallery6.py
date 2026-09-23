#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""狼娘 × 第六批画风（木刻版画 / 岩彩壁画 / 霓虹赛博 / 油画棒）—— 换题材

前五轮都在同一场景（瓦檐 + 樱花 + 白天）。本批**换题材维度**，验证这套写法换场景后是否同样稳：
  新场景：雨夜，一家店铺门前的屋檐下避雨（店里透出暖光、地面积水反光）
  新瞬间：伸手去接檐口滴下来的水、侧头看雨 —— 视线落在**指尖那颗水珠**上

沿用已固化的三条：
  · 不写瞳色（R1 教训，R4/R5 验证有效）
  · 锁视线落点（每次都给一个具体的落点物）
  · 微表情：一侧眉高一线、嘴偏斜（不对称）+ 耳/尾/肩的联动 + 克制不夸张
本批新增联动层：**肩因凉意微微内收**（体感联动，对应"雨夜"的冷）

用法：python tools/diag/gen_wolf_style_gallery6.py [seed]
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

SEED = 20260930
STEPS = 25
CFG = 1.0

LEAD = "以 <image1> 的狼耳少女为主角，外貌、发型、服装与配饰一律以该图为准。"
MOMENT = "她蹲坐在雨夜里一家店铺门前的台阶上，一只手伸出去接檐口滴下来的水，侧着头看雨。"
# 表情层：各风格共用（保证只有画风是变量）
FACE = ("她的脸是整幅{FOCUS}的地方：眼睛只用{EYE}勾出，眼皮压得低低的，"
        "视线的落点就在伸出那只手的指尖上；一侧的眉毛比另一侧高了极细的一线，"
        "嘴是一小道偏斜的{MOUTH}，左边比右边长了极细的一线。")

STYLES = [
    {
        "key": "woodcut",
        "label": "21-木刻版画",
        "cn": LEAD + (
            "这是一幅木刻版画：画面由刻刀在木板上凿出的块面与刀痕组成，黑白分明，"
            "中间调靠平行的排刀与留白挤出，印在略粗的纸上，边缘有几处墨色不均。" + MOMENT +
            "她的头发用一束束平行的刻刀排线排出，发梢的线渐渐断开；"
            "头顶一对狼耳用几块硬边的黑白块面刻出，耳内留白，两只耳朵朝雨声那一侧偏转。"
            "她的脸是整幅刀痕最少的地方：眼睛只用两道短促的刀口刻出，眼皮压得低低的，"
            "视线的落点就在伸出那只手的指尖上；一侧的眉毛比另一侧高了极细的一线，"
            "嘴是一小道偏斜的短刀口，左边比右边长了极细的一线。"
            "她的双肩微微内收，像是被雨夜的凉意收住。"
            "颈间一条深色的刻线，身上的短裙用一大块实黑压住，衣褶是几道留白的刀痕；裙摆下缘有一道浅色的边。"
            "她伸出的那只手刻得最细，指尖上正挂着一颗水滴，水滴用一小块留白刻出。"
            "身后那条大尾巴用放射状的排刀刻出蓬松的毛尖，尾尖轻轻摆向一侧。"
            "雨丝用一排排斜向的细刀痕铺满画面，檐口那一线用一块实黑刻出，几颗水滴正从檐口往下落。"
            "店铺的窗在画面右侧，是一块亮着的留白，窗格用几道黑线分出。"
            "地面积着一层水，水面用几道横向的刀痕刻出倒影的碎块。"
            "整体构图压在暗部，最亮的留白集中在店铺的窗、她伸出的手与那几颗水滴上。"
        ),
    },
    {
        "key": "mural",
        "label": "22-岩彩壁画",
        "cn": LEAD + (
            "这是一幅岩彩壁画：颜料是磨碎的矿物颗粒，粗的地方看得见沙粒，颜色厚重而不透明，"
            "墙面有几处剥落与烟熏的痕迹。" + MOMENT +
            "她的头发用一层层土青与石青的矿物色叠出，发梢的颜色渐渐变浅、露出墙底；"
            "头顶一对狼耳用蛤粉与淡赭叠出，耳廓的边缘有几粒颜料堆起，两只耳朵朝雨声那一侧偏转。"
            "她的脸是整幅颜料最薄的地方：眼睛用两道赭石细线勾出，眼皮压得低低的，"
            "视线的落点就在伸出那只手的指尖上；一侧的眉毛比另一侧高了极细的一线，"
            "嘴是一小道偏斜的朱砂，左边比右边长了极细的一线。"
            "她的双肩微微内收，像是被雨夜的凉意收住。"
            "颈间一道墨线，身上的短裙用一大块厚涂的墨压住，衣褶是几道刮出来的浅槽；裙摆下缘有一道石青的边。"
            "她伸出的那只手勾得最细，指尖上正挂着一颗水滴，水滴用一小块蛤粉提亮。"
            "身后那条大尾巴用石青与紫矿两色叠出蓬松的毛尖，尾尖轻轻摆向一侧。"
            "雨丝用一层薄薄的石绿罩染铺满画面，檐口那一线用墨压住，几颗水滴正从檐口往下落。"
            "店铺的窗在画面右侧，是一块暖赭的亮面，窗格用墨线分出。"
            "地面积着一层水，水面用几道横向的矿物色条扫出倒影。墙面在画面左上角有一处剥落，露出底下的白灰。"
            "整体构图厚重，最亮的地方集中在店铺的窗、她伸出的手与那几颗水滴上。"
        ),
    },
    {
        "key": "neon",
        "label": "23-霓虹赛博",
        "cn": LEAD + (
            "这是一幅霓虹赛博风格的画：画面压在很深的蓝紫暗部里，所有轮廓都由发光的霓虹线勾出，"
            "颜色在湿漉漉的地面上晕成一片一片的光斑。" + MOMENT +
            "她的头发用一道道发光的青蓝霓虹线排出，发梢的光渐渐散开；"
            "头顶一对狼耳用粉紫两色的光勾出轮廓，耳内是一小片淡光，两只耳朵朝雨声那一侧偏转。"
            "她的脸是整幅光最柔的地方：眼睛用两道细的发光勾出上眼睑与瞳孔，眼皮压得低低的，"
            "视线的落点就在伸出那只手的指尖上；一侧的眉毛比另一侧高了极细的一线，"
            "嘴是一小道偏斜的洋红光线，左边比右边长了极细的一线。"
            "她的双肩微微内收，像是被雨夜的凉意收住。"
            "颈间一条发光细线，身上的短裙是一块深色的实体，只在边缘勾出一道青蓝的轮廓光；裙摆下缘有一道洋红的细线。"
            "她伸出的那只手勾得最细，指尖上正挂着一颗水滴，水滴里折着一点洋红的光。"
            "身后那条大尾巴用青蓝与紫两色的光线一束束排出发光的毛感，尾尖轻轻摆向一侧。"
            "雨丝是一道道发光的细线斜穿画面，檐口那一线用一条亮青的霓虹管勾出，几颗水滴正从檐口往下落、每颗都折着一点光。"
            "店铺的招牌在画面右侧，是一块发着洋红光的方块，上面的光晕在雨里散开。"
            "地面积着一层水，水面把上方的青蓝与洋红拉成一道道竖直的光斑。"
            "整体构图压在暗部，最亮的地方集中在招牌、她伸出的手与那几颗水滴上。"
        ),
    },
    {
        "key": "oilpastel",
        "label": "24-油画棒",
        "cn": LEAD + (
            "这是一幅油画棒画，画在粗纹的深色纸上：笔触粗、油性重，颜色压上去留下一层厚厚的蜡质，"
            "浅色的地方要反复叠才能盖住纸底，边缘带着纸纹啃出来的毛口。" + MOMENT +
            "她的头发用几道宽大的浅蓝与白色笔触扫出，笔触之间留着没盖住的深色纸底，发梢的笔触拖得很长；"
            "头顶一对狼耳用米白与淡粉两笔厚涂，耳廓的边缘是纸纹啃出来的毛口，两只耳朵朝雨声那一侧偏转。"
            "她的脸是整幅笔触最少的地方：眼睛只用两道深色的短笔触压出，眼皮压得低低的，"
            "视线的落点就在伸出那只手的指尖上；一侧的眉毛比另一侧高了极细的一线，"
            "嘴是一小道偏斜的朱红笔触，左边比右边长了极细的一线。"
            "她的双肩微微内收，像是被雨夜的凉意收住。"
            "颈间一道深色的短笔触，身上的短裙用一大块厚涂的黑压住，衣褶是几道刮出来的亮线；裙摆下缘有一道浅蓝的笔触。"
            "她伸出的那只手画得最细，指尖上正挂着一颗水滴，水滴用一小点白色提亮。"
            "身后那条大尾巴用蓝紫两色的粗笔触一簇簇地挑起来，尾尖轻轻摆向一侧。"
            "雨丝用几道浅色的斜笔触扫过画面，檐口那一线用一块厚黑压住，几颗水滴正从檐口往下落。"
            "店铺的窗在画面右侧，是一块暖黄的厚涂，光在湿地上晕成一片暖色的斑。"
            "地面积着一层水，水面用几道横向的浅色笔触拉出倒影。"
            "整体构图厚重，最亮的地方集中在店铺的窗、她伸出的手与那几颗水滴上，四周留着大片没盖住的深色纸底。"
        ),
    },
]


def upload(path):
    b = "----wolf6" + str(int(time.time() * 1000))
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
    print("本批换题材：雨夜店铺檐下避雨 + 伸手接檐口水（新场景/新瞬间）\n")

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