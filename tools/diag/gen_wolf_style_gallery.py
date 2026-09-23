#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""狼娘 × 四画风（八步观察者法 + 微表情自然度纪律）

沿用上一批（白猫版）的构图骨架：老屋瓦檐 + 樱花 + 仰头看花的瞬间，
只把主角换成 <image1> 的狼耳少女，画风结构不变，便于横向对照。

两套规则同时生效：

【A】t2i.md 八步观察者法
  · 观察者口吻、单段连续文字；比例不进正文（画布跟随参考图）；无质量词
  · 位置短语导航；材质与修饰色；枚举不概括；一句光照；一句"整体构图"收尾

【B】微表情知识库（反 AI 假脸）
  · 不对称：嘴角左侧先翘、右侧还平着；一只眼眼尾比另一只略收紧
  · 联动：视线落点 → 狼耳朝同一方向偏转 → 尾尖轻摆 → 胸口随呼吸微起伏
  · 克制（默认 L2）：不用"极度/突然/表情丰富"，不写对称呆滞的摆拍脸
  · 瞬间：抓住"花瓣正在下坠、她刚注意到"的中间态，而不是静止定格

用法：python tools/diag/gen_wolf_style_gallery.py [seed]
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

SEED = 20260925
STEPS = 25
CFG = 1.0

# 身份指向：按 edit.md「身份来自参考图时指向那张图」，不逐条复述外观
LEAD = "以 <image1> 的狼耳少女为主角，外貌、发型、服装与配饰一律以该图为准。"

STYLES = [
    {
        "key": "shuimo",
        "label": "1-水墨-写意册页",
        "cn": LEAD + (
            "这是一幅写意水墨画：她盘腿坐在老木屋的瓦檐下，仰头看一枝探进画面的樱花。"
            "吸水的宣纸留出大片未着墨的空白，远处一两笔淡墨扫出朦胧的山影，山与屋檐之间横着一带柔和的雾气。"
            "屋檐从画面上缘斜出，深墨色的瓦当一片叠着一片，檐口用干笔扫出几道枯涩的木纹。"
            "在画面下三分之一处，她坐在一方生苔的青石台阶上，上身微微前倾，一只手撑在膝头，"
            "另一只手抬起、虚虚地护在额前，像要接住落下来的花瓣。"
            "头发用几笔湿墨铺出，发梢以更淡的墨色化开；一对狼耳从发间竖起，"
            "两只耳朵朝左上方花瓣飘来的方向偏转，耳廓内侧留白。"
            "她的脸只占很小一块：眼睛是两滴稀释过的淡墨，视线的落点在左上方那片正在下坠的花瓣上；"
            "一只眼的眼尾比另一只略微收紧，嘴角是偏的，左侧先翘起一点、右侧还平着。"
            "颈间一条细墨线勾出的颈圈，身前是深墨色的抹胸短裙，只在衣褶处留出几道白。"
            "身后那条蓬松的大尾巴铺在台阶上，尾尖轻轻翘起、微微弯向左边。"
            "樱花枝以焦墨写出，顿挫分明，花朵用极淡的胭脂点染，两三片花瓣正落在她的膝头。"
            "屋檐下方有一小段斑驳的院墙，只用一块宽宽的淡墨扫出，下缘故意留得毛糙。"
            "右下角盖着一方小小的朱红方形印章，是整张纸上唯一饱和的颜色。"
            "光是均匀而平和的宣纸漫射光，形体全靠墨色从湿黑到淡银的层次与留白来分，没有任何投影。"
            "整体构图疏朗安静，大约三分之二的纸面是空的，笔触在湿笔晕染与干笔擦痕之间交替。"
        ),
    },
    {
        "key": "ukiyoe",
        "label": "2-浮世绘-木版画",
        "cn": LEAD + (
            "这是一幅日本浮世绘木版画：她侧身坐在老屋的石阶上，脸朝左上方，看着一枝横过画面的樱花。"
            "头发用流畅的墨线勾出轮廓、平涂几层深浅不同的蓝，发梢以浅色收尾；"
            "头顶一对狼耳用粗黑线勾边、平涂米白，内侧点一点淡粉，两只耳朵朝左上方同一方向偏着。"
            "她的脸是一张窄长的侧脸：眼睛细长，眼尾轻轻上扬，视线的落点在左上方那枝樱花上；"
            "嘴唇是一小片平涂的淡朱色，左侧嘴角比右侧高了极细的一线。颈间一条黑色颈圈。"
            "她穿着一件黑色的抹胸短裙，裙摆与领口各有一道蓝色的细边，裙身的褶皱用几条平行的深色线排出；"
            "大腿上各系着一只蝴蝶结腿环。一条蓬松的蓝紫色长尾从身后垂下来，尾尖轻轻弯向一侧。"
            "瓦檐在画面上缘排成一行，是一片片独立描边的平行四边形色块，靛蓝与深灰相间，每一片都有细细的深色底线。"
            "樱花枝从右上角伸进来，枝干用粗重的深墨色勾边、平涂褐色，花朵是一朵朵平涂的粉色圆盘，每个花心点一小点朱红。"
            "天空留着木版特有的米黄纸底，檐角上方浮着两朵样式化的扁云，云的轮廓在边角处收成方角。"
            "地面是一大块平涂的暖灰色，上缘用一条水平的深色线收住。"
            "光是平坦而均匀的版画式光照，没有投影，形体全靠色块的边界与粗黑的轮廓线来区分。"
            "用色只有靛蓝、米白、墨黑、樱粉与少量朱红五种。"
            "整体构图安稳，她端坐的姿态与垂下的花枝形成一竖一斜的呼应。"
        ),
    },
    {
        "key": "picturebook",
        "label": "3-绘本-水粉",
        "cn": LEAD + (
            "这是一幅儿童绘本插画，用柔和的水粉画成：她坐在老屋檐下的奶油色木台阶上，仰着脸看樱花瓣一片片飘下来。"
            "头发是软软的浅蓝色，画成一团一团圆润的色块，发梢颜色更浅；"
            "头顶一对圆圆的狼耳，内侧是淡淡的粉色，两只耳朵朝花瓣落下的方向偏着。"
            "她的脸圆圆的，两只眼睛是温柔的黑豆眼，视线的落点跟着一片正在飘下来的花瓣；"
            "嘴是一小笔粉色，左边嘴角微微翘起、右边还平着；脸颊上一小团淡粉。"
            "她穿着一件黑色的小裙子，裙边有一道浅蓝的线；身后一条蓬松的蓝紫色大尾巴搭在台阶上，尾巴尖轻轻摆着。"
            "屋檐从画面上方横过，瓦片是柔和的青蓝色，一片边缘微微发歪；"
            "檐下挂着一盏小小的橘色纸灯笼，纸面透出暖黄的灯光。"
            "樱花枝从右上角弯进来，花是一团一团粉色的圆点簇，其中一瓣正落在她的肩头，还有两瓣飘在半空。"
            "台阶旁边摆着一只蓝白花纹的小茶杯。天空是奶油般的暖黄色，飘着两朵软软的、一边高一边低的云。"
            "光是从画面右侧斜进来的午后阳光，柔和均匀，在台阶上留下一小片暖色的光斑，没有硬的影子。"
            "水粉的质感很明显：笔触看得见，纸纹粗粗的，颜色是一块一块并排摆在一起的。"
            "整体构图温暖安静，她在画面正中偏下，花枝从右上垂下来，四周留出大片暖色的空。"
        ),
    },
    {
        "key": "glass",
        "label": "4-玻璃彩绘-花窗",
        "cn": LEAD + (
            "这是一幅哥特式彩色玻璃花窗：她端坐在尖拱窗的正中央，仰头看着一枝横过画面上部的樱花。"
            "头发由深浅不同的蓝色玻璃片拼成，每一片都被黑色的铅条勾出边界；"
            "头顶一对狼耳用奶白与淡粉的玻璃片拼出，耳廓的边缘由铅线走形。"
            "她的脸用几片极浅的肉色玻璃拼成，眼睛是两小块琥珀黄的玻璃，视线的落点在左上方那枝樱花上；"
            "嘴唇是一小片淡红的玻璃，左侧比右侧略高一线。"
            "她穿一件由黑色玻璃拼成的短裙，领口与裙摆各有一道细窄的蓝色玻璃边。"
            "身后一条蓬松的大尾巴由蓝紫色玻璃片拼成，尾巴尖那一小片用的是最亮的月白玻璃。"
            "樱花枝是深琥珀色的玻璃，花朵由粉色与玫红的玻璃片拼成，每一片花瓣都被铅线勾边。"
            "背景由大块的宝石色玻璃铺成：深钴蓝、祖母绿与紫罗兰，色块之间嵌着几片淡黄的小玻璃。"
            "光从玻璃的背面透进来，整个窗面都在发亮；窗下的石台由几块灰蓝色玻璃拼出，"
            "台面上落着淡蓝与粉色两团透射下来的光。铅线在光里显出深色的剪影。"
            "大块形状之间的空隙里填着许多形状不规则的小玻璃片。"
            "整体构图对称、庄重而明亮，尖拱的轮廓把她与樱花一起框在窗心，"
            "窗的四周绕着一圈细窄的重复铅格边框。"
        ),
    },
]


def upload(path):
    b = "----wolf" + str(int(time.time() * 1000))
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
    print(f"参数：seed={seed}  steps={STEPS}  cfg={CFG}  画布跟随参考图（比例不进正文）\n")

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