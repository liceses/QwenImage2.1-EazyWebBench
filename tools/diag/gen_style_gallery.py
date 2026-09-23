#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 bozo-qwen21-prompt 的「八步观察者法」做画风实验。

同一题材（老屋瓦檐下看樱花的白猫）× 四种画风，提示词全部按
prompt_skills/bozo-qwen21-prompt/references/t2i.md 的纪律写：

  · 观察者口吻：只写画面里有什么，不写"请生成/确保"
  · 比例只进画布（wh_ratio = 1:1 -> 1024x1024），绝不写进提示词正文
  · 无质量词（masterpiece / 8K / highly detailed 一概不出现）
  · 约三分之一的句子以位置短语开头；颜色带修饰语；给材质；枚举不概括
  · 单张图无可读文字 -> 不编造标牌
  · 一句光照单独交代；一句 "整体构图…" 收尾

纯文生图：不带任何参考图（<imageN> 槽位为空）。

用法：python tools/diag/gen_style_gallery.py [seed]
"""
import json
import os
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WB = "http://127.0.0.1:8642"
O = urllib.request.build_opener(urllib.request.ProxyHandler({}))

SEED = 20260924
W = H = 1024          # wh_ratio = 1:1（方形题材：册页/版画/绘本/花窗）
STEPS = 25
CFG = 1.0

STYLES = [
    {
        "key": "shuimo",
        "label": "1-水墨-写意册页",
        "cn": (
            "这是一幅方形的写意水墨画，画的是一只白猫坐在老木屋的瓦檐下，"
            "一枝樱花从画面右上角探进来。吸水的宣纸留出大片未着墨的空白，"
            "远处一两笔淡墨扫出朦胧的山影，山与屋檐之间横着一带柔和的雾气。"
            "屋檐从画面上缘斜出，深墨色的瓦当一片叠着一片，檐口用干笔扫出几道枯涩的木纹。"
            "在画面下三分之一处，白猫端坐在一方生苔的青石台阶上，脊背微微弓起，"
            "尾巴整齐地收拢在前爪边，两只耳朵一高一低，正侧头望着飘落的花瓣。"
            "猫的白全靠纸底留白衬出来，只在脊背与后腿敷一层极淡的赭墨，"
            "眼睛是两滴稀释过的淡墨，半睁半闭。"
            "樱花枝以焦墨写出，顿挫分明，花朵用极淡的胭脂点染，两三片花瓣正落在猫的前爪旁。"
            "屋檐下方有一小段斑驳的院墙，只用一块宽宽的淡墨扫出，下缘故意留得毛糙，让纸底透出来。"
            "沿底边的石阶用几道干笔交代，石头的颗粒感是擦出来的，不是描出来的。"
            "右下角盖着一方小小的朱红方形印章，是整张纸上唯一饱和的颜色。"
            "左上角的空白里有两三片被风掀起的花瓣，用最淡的墨勾出轮廓。"
            "光是均匀而平和的宣纸漫射光，形体全靠墨色从湿黑到淡银的层次与留白来分，没有任何投影。"
            "整体构图疏朗安静，大约三分之二的纸面是空的，笔触在湿笔晕染与干笔擦痕之间交替，像一页刚收笔的册页。"
        ),
    },
    {
        "key": "ukiyoe",
        "label": "2-浮世绘-木版画",
        "cn": (
            "这是一幅方形的日本浮世绘木版画，画的是一只白猫端坐在老屋的石座上，"
            "背后是深色的瓦檐，一枝盛开的樱花从右上角横过画面。"
            "猫的身体用几道流畅的墨线勾出轮廓，平涂米白的底色，胸口的绒毛用一排排细密的短弧线排出；"
            "它的尾巴绕到身前，尾尖搭在前爪上，侧着一张窄长的脸，眼睛细长而安静。"
            "瓦檐在画面上缘排成一行，是一片片独立描边的平行四边形色块，靛蓝与深灰相间，"
            "每一片都有细细的深色底线。樱花枝从右上角伸进来，枝干用粗重的深墨色勾边、平涂褐色，"
            "花朵是一朵朵平涂的粉色圆盘，每个花心点一小点朱红。"
            "天空留着木版特有的米黄纸底，檐角上方浮着两朵样式化的扁云，云的轮廓在边角处收成方角。"
            "地面是一大块平涂的暖灰色，上缘用一条水平的深色线收住。"
            "较大块的色区里能看出淡淡的木纹压痕，一两个色块的边缘与邻色错开一丝，是手工拓印的痕迹。"
            "光是平坦而均匀的版画式光照，没有投影，形体全靠色块的边界与粗黑的轮廓线来区分。"
            "用色只有靛蓝、米白、墨黑、樱粉与少量朱红五种。"
            "整体构图安稳对称，猫的坐姿端正，垂下的花枝与端坐的猫形成一竖一斜的呼应。"
        ),
    },
    {
        "key": "picturebook",
        "label": "3-绘本-水粉",
        "cn": (
            "这是一幅方形的儿童绘本插画，用柔和的水粉画成：一只圆滚滚的白猫坐在老屋檐下的奶油色木台阶上，"
            "仰着头看头顶飘落的樱花瓣。"
            "猫的身体是一团温暖的奶白，绒毛的边缘画得毛毛的；两只眼睛是温柔的黑豆眼，鼻子是小小的粉色三角，"
            "耳朵里透出淡淡的粉；尾巴松松地绕在身前，尾巴尖翘起来。"
            "屋檐从画面上方横过，瓦片是柔和的青蓝色，一片边缘微微发歪；"
            "檐下挂着一盏小小的橘色纸灯笼，纸面透出暖黄的灯光。"
            "樱花枝从右上角弯进来，花是一团一团粉色的圆点簇，其中一瓣正落在猫的鼻尖上，还有两瓣飘在半空。"
            "台阶旁边摆着一只蓝白花纹的小茶杯，茶杯边是一小盆刚冒出两片新叶的绿植。"
            "天空是奶油般的暖黄色，飘着两朵软软的、一边高一边低的云。"
            "光是从画面右侧斜进来的午后阳光，柔和均匀，在台阶上留下一小片暖色的光斑，没有硬的影子。"
            "水粉的质感很明显：笔触看得见，纸纹粗粗的，颜色是一块一块并排摆在一起的，边缘微微不匀。"
            "整体构图温暖安静，猫在画面正中偏下，花枝从右上垂下来，四周留出大片暖色的空。"
        ),
    },
    {
        "key": "glass",
        "label": "4-玻璃彩绘-花窗",
        "cn": (
            "这是一幅方形哥特式彩色玻璃花窗风格的插画：一只白猫端坐在尖拱窗的正中央，"
            "它身后有一枝盛开的樱花横过画面的上部。"
            "猫的身体由奶白色与淡蓝色的玻璃片拼成，每一片都被黑色的铅条勾出边界；"
            "眼睛是两小块琥珀黄的玻璃；尾巴绕到身前，尾巴尖那一小片用的是最亮的月白玻璃。"
            "樱花枝是深琥珀色的玻璃，花朵由粉色与玫红的玻璃片拼成，每一片花瓣都被铅线勾边。"
            "背景由大块的宝石色玻璃铺成：深钴蓝、祖母绿与紫罗兰，色块之间嵌着几片淡黄的小玻璃。"
            "光从玻璃的背面透进来，整个窗面都在发亮；窗下的石台由几块灰蓝色玻璃拼出，"
            "台面上落着淡蓝与粉色两团透射下来的光。"
            "铅线在光里显出深色的剪影，猫圆背的弧线、瓦檐的折线、每一片花瓣的轮廓全部由铅线走形；"
            "大块形状之间的空隙里填着许多形状不规则的小玻璃片。"
            "猫身上那几片奶白玻璃是整扇窗最亮的部分，樱花是仅次于它的亮部。"
            "整体构图对称、庄重而明亮，尖拱的轮廓把猫与樱花一起框在窗心，"
            "窗的四周绕着一圈细窄的重复铅格边框。"
        ),
    },
]


def post(path, obj):
    req = urllib.request.Request(WB + path, data=json.dumps(obj).encode(),
                                 headers={"Content-Type": "application/json"})
    with O.open(req, timeout=120) as r:
        return json.loads(r.read().decode())


def get(path):
    with O.open(WB + path, timeout=60) as r:
        return json.loads(r.read().decode())


def wait(jid, label, limit=1200):
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
    print("八步观察者法 · 画风实验   题材：老屋瓦檐下看樱花的白猫")
    print(f"固定参数：seed={seed}  {W}x{H}（wh_ratio 1:1）  steps={STEPS}  cfg={CFG}  纯文生图\n")

    done = []
    for st in STYLES:
        print("=" * 74)
        print(f"{st['label']}   中文 {len(st['cn'])} 字")
        print("=" * 74)
        r = post("/api/generate", {
            "prompt": st["cn"], "negative_prompt": "",
            "width": W, "height": H,
            "steps": STEPS, "cfg": CFG, "seed": seed,
            "reference_images": [],
            "ref_resolution": 0,
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
