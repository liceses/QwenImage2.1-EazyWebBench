#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""狼娘 × 小名 —— 第七批：**双角色同框**（新维度测试）

前六轮都是单角色。本批测多角色一致性 —— 这是最容易出问题的地方（特征串味）。
  角色：<image1> 狼娘（左） + <image2> 小名（右）
  瞬间：两人并坐檐下石阶，狼娘把掌心的花瓣**递过去**，小名**伸手接** —— 交互瞬间
  画布：改用 3:2 横版（1152×768，两人并坐更适合横构图）

沿用已固化的写法：
  · 身份指向参考图，文字只补 3~5 个高辨识标志物（避免文字覆盖参考图特征）
  · 不写瞳色
  · 每个角色各有自己的视线落点（狼娘→少年伸出的手；小名→那片花瓣）
  · 不对称细节 + 耳/尾/呆毛的联动
  · 防串味：明确写"两人特征不得互换"

用法：python tools/diag/gen_wolf_style_gallery7.py [seed]
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
XIAOMING = r"D:\Pictures\Camera Roll\小名人设.png"

SEED = 20261001
W, H = 1152, 768      # 3:2 横版（两人并坐）
STEPS = 25
CFG = 1.0

LEAD = ("画面里有两个角色：左侧是 <image1> 的狼耳少女，右侧是 <image2> 的银发少年；"
        "两人的外貌、发型、服装与配饰一律以各自对应的参考图为准，"
        "只补记几个高辨识标志物——狼耳少女：浅蓝长发与狼耳、黑色短裙、蓝紫大尾巴；"
        "银发少年：银白短发带蓝色挑染、一根呆毛、一只蓝色小鲸鱼发夹、水手领露脐上衣与浅蓝短裤、"
        "一件披在肩上的浅蓝外套。**两人的特征不得互换，也不得把一人的衣物画到另一人身上。**")

MOMENT = "两人并排坐在檐下的石阶上，狼耳少女把掌心里的一片花瓣递向身旁的银发少年，少年正伸出手去接。"

FACE = ("狼耳少女的视线落在少年伸出的那只手上，一侧的嘴角比另一侧翘起极细的一线，"
        "双耳朝少年那一侧前倾，尾尖轻轻摆向少年；"
        "少年的眼睛盯着那片花瓣、比平时睁得略大一点，嘴微微张开，"
        "伸出的那只手五指并拢、掌心朝上，额前那根呆毛随着动作轻轻一晃。")

STYLES = [
    {
        "key": "newsprint",
        "label": "25-报纸网点",
        "cn": LEAD + (
            "这是一幅老报纸上的网点印刷插图：画面由大小不一的黑色网点组成，深浅全靠网点的疏密，"
            "油墨略有不匀，纸是发黄的新闻纸，边缘有几处折痕。" + MOMENT +
            "狼耳少女的头发用一层层细网点排出，发梢的网点变疏；一对狼耳用密网点压出深色，耳内留白；"
            "身上那条黑色短裙用最密的网点压成近黑，衣褶靠留白的纸面分出；身后的大尾巴用疏密相间的网点排出毛感。" +
            FACE +
            "少年的头发用疏网点排出浅灰，发梢的蓝色挑染用一层更密的网点压出；呆毛是一小段留白勾出的弧线；"
            "水手领与短裤用中等的网点，肩上那件外套用最疏的网点、几乎只剩纸色。" +
            "檐口在上缘用一条实黑压住，几片花瓣正飘在两人之间。"
            "背景是新闻纸本身的米黄，只在远处用极疏的网点扫出雨丝的斜纹；地面是几道横向的网点排出的石阶。"
            "光是均匀的，形体完全靠网点的疏密来分，画面里没有一处平涂的灰。"
            "整体构图把两人放在画面中央偏下，四周留出大片没印上油墨的纸色。"
        ),
    },
    {
        "key": "relief",
        "label": "26-石膏浮雕",
        "cn": LEAD + (
            "这是一幅石膏浮雕：整幅是一块白色的石膏板，所有形体都是从板面上浅浅凿出来的，"
            "没有一处上色，深浅完全靠侧光在凿痕上投下的阴影。" + MOMENT +
            "狼耳少女的头发用一道道并排的浅凿槽排出，发梢的槽渐渐变浅；"
            "一对狼耳从板面上凸起一块，耳内凿出一小片凹陷；身上那条短裙凿得最深，衣褶是几道刮出来的浅槽；"
            "身后的大尾巴用放射状的凿痕排出毛感，尾尖微微翘起。" +
            FACE +
            "少年的头发用更浅的凿槽排出，呆毛是一小段凸起的细条；"
            "水手领用两道并排的浅槽勾出，肩上那件外套凿得最浅、只在侧光下勉强显形。" +
            "檐口在上缘凿成一条凸起的边，几片花瓣是几块薄薄的凸片，正飘在两人之间。"
            "背景是石膏板本身的哑光白，只在远处用极浅的凿痕扫出雨丝的斜纹；地面是几道横向的浅槽排出的石阶。"
            "光是从左上方来的硬侧光，把每一道凿痕都照出一条细影，形体完全靠凿痕的深浅与阴影来分。"
            "整体构图疏朗，凿得最深的地方集中在两人的裙子、发根与檐口三处，四周留出大片没被凿过的石膏面。"
        ),
    },
    {
        "key": "sugarpainting",
        "label": "27-糖画",
        "cn": LEAD + (
            "这是一幅糖画：整幅由一缕缕熬成琥珀色的糖丝在石板上浇成，线条是半透明的焦糖色，"
            "粗的地方糖浆堆起、细的地方几乎透明，光从背后透过来时颜色像蜂蜜一样发亮。" + MOMENT +
            "狼耳少女的头发用一束束平行的糖丝排出，发梢的糖丝拉得极细、几乎透光；"
            "一对狼耳用较粗的糖线勾出轮廓、耳内留空；身上那条短裙用最厚的糖浆浇成深琥珀色，衣褶靠留空的石板分出；"
            "身后的大尾巴用放射状的糖丝排出蓬松的毛感，尾尖拉出一个小勾。" +
            FACE +
            "少年的头发用更细的糖丝排出，呆毛是一根单独拉起的细糖丝；"
            "水手领用两道并排的糖线勾出，肩上那件外套只用最淡的几笔糖丝带过。" +
            "檐口在上缘用一条粗糖线压住，几片花瓣是几小块薄薄的糖片，正飘在两人之间。"
            "背景是石板本身的青灰色，只在远处用极淡的几笔糖丝扫出雨丝；地面是几道横向的糖线排出的石阶。"
            "光从背后透进来，糖丝的半透明感让琥珀色发亮，形体靠糖线的粗细与糖浆的厚薄来分。"
            "整体构图疏朗，糖浆最厚的地方集中在两人的裙子与发根两处，四周留出大片石板本色。"
        ),
    },
    {
        "key": "cavepainting",
        "label": "28-岩画",
        "cn": LEAD + (
            "这是一幅岩画：画在粗糙的岩壁上，颜料只有赭红、土黄与炭黑三种，"
            "是用手指与草茎直接抹上去的，颜色渗进石头的颗粒里，边缘发毛，岩壁本身的裂纹与凹坑从颜料里透出来。" + MOMENT +
            "狼耳少女的头发用几道粗赭红的抹痕排出，发梢的痕迹渐渐断开；"
            "一对狼耳用两块实心的赭红抹出、耳内留出岩壁本色；身上那条短裙用一大块炭黑压住；"
            "身后的大尾巴用放射状的赭红抹痕排出毛感，尾尖轻轻翘起。" +
            FACE +
            "少年的头发用更浅的土黄抹出，呆毛是一小笔勾起的赭红；"
            "水手领用两道并排的炭黑勾出，肩上那件外套只用最淡的几笔土黄带过。" +
            "檐口在上缘用一条粗炭黑压住，几片花瓣是几小块薄薄的赭红，正飘在两人之间。"
            "背景是岩壁本身的黄褐色，裂纹与凹坑清晰可见，只在远处用极淡的几笔炭黑扫出雨丝；"
            "地面是几道横向的炭黑排出的石阶。"
            "光是均匀的，没有方向，形体全靠三种颜料的浓淡与岩壁本身的凹凸来分。"
            "整体构图疏朗，颜料最厚的地方集中在两人的裙子与发根两处，四周留出大片没被抹过的岩壁。"
        ),
    },
]


def upload(path):
    b = "----wolf7" + str(int(time.time() * 1000))
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
    for p in (WOLF, XIAOMING):
        if not os.path.exists(p):
            print("缺少参考图:", p)
            return 1
    print("上传两张人设图…")
    r1 = upload(WOLF)["name"]
    r2 = upload(XIAOMING)["name"]
    print(f"  image1(狼娘)={r1}\n  image2(小名)={r2}")
    print(f"参数：seed={seed}  {W}x{H}（3:2 横版，自定义画布）  steps={STEPS}  cfg={CFG}")
    print("本批新维度：双角色同框 + 交互瞬间（递花瓣/伸手接）\n")

    done = []
    for st in STYLES:
        print("=" * 74)
        print(f"{st['label']}   正文 {len(st['cn'])} 字")
        print("=" * 74)
        r = post("/api/generate", {
            "prompt": st["cn"], "negative_prompt": "",
            "width": W, "height": H,
            "steps": STEPS, "cfg": CFG, "seed": seed,
            "reference_images": [r1, r2],
            "custom_canvas": True, "ref_resolution": 0,
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