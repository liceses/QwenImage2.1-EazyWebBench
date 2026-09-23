#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""狼娘 × 小名 —— 第八批：**攻"画风偏袒 image1"的缺陷**

Round 7 发现的失败模式：糖画那张里只有 <image1> 的狼娘被做成了糖，
<image2> 的小名仍是常规不透明上色 —— 媒介处理没有均匀覆盖两个角色。

本轮的可证伪假设：
  H1：媒介要求只在开头写一次时，会绑到 <image1> 槽位上（Round 7 的现象）
  H2：把媒介要求在**每个角色的段落里各写一遍**（共 4 处：开头/左/右/背景），
      并加一句"画面里没有一处是常规不透明上色"的硬约束，即可让媒介均匀覆盖

对照设计：
  · 27-糖画 是 Round 7 失败那张的**直接重跑**（同场景同交互，只改提示词结构）→ A/B 锚点
  · 另加 3 个"媒介必须覆盖全画面"的强媒介：琉璃铸造 / 彩绘瓷砖 / 拓片
    这四种只要媒介没盖全，一眼就能看出来，是检验 H2 的好探针。

用法：python tools/diag/gen_wolf_style_gallery8.py [seed]
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

SEED = 20261002
W, H = 1152, 768
STEPS = 25
CFG = 1.0

LEAD = ("以 <image1> 的狼耳少女与 <image2> 的银发少年为主角，"
        "两人的外貌、发型、服装与配饰一律以各自对应的参考图为准，只补记几个高辨识标志物——"
        "狼耳少女：浅蓝长发与狼耳、黑色短裙、蓝紫大尾巴；"
        "银发少年：银白短发带蓝色挑染、一根呆毛、一只蓝色小鲸鱼发夹、"
        "水手领露脐上衣与浅蓝短裤、一件披在肩上的浅蓝外套。"
        "**两人的特征不得互换，也不得把一人的衣物画到另一人身上。**")
SCENE = "两人并排坐在檐下的石阶上，狼耳少女把掌心里的一片花瓣递向身旁的银发少年，少年正伸出手去接。"
UNIFORM = "**画面里的每一处——两个人的头发、皮肤、衣服、尾巴，以及背景与地面——都必须由同一种媒介做成，没有一处是常规的不透明上色。**"

STYLES = [
    {
        "key": "sugar2",
        "label": "29-糖画（修正版·A/B锚点）",
        "cn": LEAD + (
            "**这是一幅糖画：整幅画面里的每一处都由一缕缕熬成琥珀色的糖丝在青灰石板上浇成**，"
            "线条是半透明的焦糖色，粗的地方糖浆堆起、细的地方几乎透明，光从背后透过来时颜色像蜂蜜一样发亮；"
            + UNIFORM + SCENE +
            "狼耳少女的头发用一束束平行的糖丝排出，发梢的糖丝拉得极细、几乎透光；"
            "一对狼耳用较粗的糖线勾出轮廓、耳内留空；身上那条短裙用最厚的糖浆浇成深琥珀色；"
            "身后的大尾巴用放射状的糖丝排出蓬松的毛感。"
            "她的视线落在少年伸出的那只手上，一侧的嘴角比另一侧翘起极细的一线，"
            "双耳朝少年那一侧前倾，尾尖轻轻摆向少年。"
            "少年的头发**同样用一束束平行的糖丝排出**、只是比少女的更细；那根呆毛是一根单独拉起的细糖丝；"
            "鲸鱼发夹是一小块较厚的糖片；水手领用两道并排的糖线勾出；"
            "肩上的外套用最淡的几笔糖丝带过；短裤与堆堆袜也一律由糖丝排成。"
            "他的眼睛盯着那片花瓣、比平时睁得略大一点，嘴微微张开，伸出的那只手五指并拢、掌心朝上。"
            "檐口在上缘用一条粗糖线压住，几片花瓣是几小块薄薄的糖片，正飘在两人之间；"
            "背景的青灰石板上看得见糖丝拉过留下的细痕，地面是几道横向的糖线排出的石阶。"
            "光从背后透进来，糖丝的半透明感让琥珀色发亮，形体靠糖线的粗细与糖浆的厚薄来分。"
            "整体构图疏朗，糖浆最厚的地方集中在两人的裙子与发根两处，四周留出大片石板本色。"
        ),
    },
    {
        "key": "castglass",
        "label": "30-琉璃铸造",
        "cn": LEAD + (
            "**这是一幅琉璃铸造：整幅画面是一块浇铸出来的厚玻璃板**，"
            "所有形体都是玻璃内部的气泡、流痕与深浅不同的色料形成的，边缘是浇铸留下的圆钝口，"
            "光从背后穿过来，色料浓的地方发暗、薄的地方透亮。" + UNIFORM + SCENE +
            "狼耳少女的头发用一道道平行的流痕排出，发梢的流痕渐渐散成细小的气泡；"
            "一对狼耳用两块较厚的蓝色玻璃凸起、耳内是一小片几乎透明的薄处；"
            "身上那条短裙是整块玻璃里色料最浓的地方；身后的大尾巴用放射状的流痕排出蓬松的毛感。"
            "她的视线落在少年伸出的那只手上，一侧的嘴角比另一侧翘起极细的一线，"
            "双耳朝少年那一侧前倾，尾尖轻轻摆向少年。"
            "少年的头发**同样用一道道平行的流痕排出**、只是气泡更密；那根呆毛是一道单独拉起的细流痕；"
            "鲸鱼发夹是一小块较厚的深蓝玻璃；水手领用两道并排的浅色流痕勾出；"
            "肩上的外套是整块玻璃里最薄、最透的地方；短裤与堆堆袜也一律由流痕与色料形成。"
            "他的眼睛盯着那片花瓣、比平时睁得略大一点，嘴微微张开，伸出的那只手五指并拢、掌心朝上。"
            "檐口在上缘是一道较厚的玻璃边，几片花瓣是几小块薄薄的玻璃片，正飘在两人之间；"
            "背景的青灰底色由一层极薄的色料铺成，地面是几道横向的流痕排出的石阶。"
            "光从背后穿过来，玻璃的厚度决定深浅，形体靠流痕、气泡与色料的浓淡来分。"
            "整体构图疏朗，色料最浓的地方集中在两人的裙子与发根两处，四周留出大片几乎透明的薄玻璃。"
        ),
    },
    {
        "key": "azulejo",
        "label": "31-彩绘瓷砖",
        "cn": LEAD + (
            "**这是一幅彩绘瓷砖拼成的画：整幅画面由一块块上釉的方瓷砖拼成**，"
            "每块瓷砖的边缘都看得见一道细细的灰浆缝，釉面有细小的开片与硬亮的反光，"
            "颜色是一格一格画上去的、格与格之间略有深浅差别。" + UNIFORM + SCENE +
            "狼耳少女的头发由一排排竖着排列的瓷砖拼出，发梢那几格的蓝色更浅；"
            "一对狼耳的轮廓跨过好几块瓷砖、由深浅两色勾出；身上那条短裙由几块最深的瓷砖拼成；"
            "身后的大尾巴由放射状排列的瓷砖拼出蓬松的毛感。"
            "她的视线落在少年伸出的那只手上，一侧的嘴角比另一侧翘起极细的一线，"
            "双耳朝少年那一侧前倾，尾尖轻轻摆向少年。"
            "少年的头发**同样由一排排瓷砖拼出**、只是格子更小；那根呆毛由两格浅色瓷砖斜着拼出；"
            "鲸鱼发夹是一格单独的深蓝瓷砖；水手领由两排白色瓷砖勾出；"
            "肩上的外套是整幅里釉色最淡的几格；短裤与堆堆袜也一律由瓷砖拼成。"
            "他的眼睛盯着那片花瓣、比平时睁得略大一点，嘴微微张开，伸出的那只手五指并拢、掌心朝上。"
            "檐口在上缘由一排深色瓷砖压住，几片花瓣是几小块单独的粉色瓷砖，正飘在两人之间；"
            "背景是米白的瓷砖，灰浆缝在两人四周形成一道网格；地面是几排灰色瓷砖排出的石阶。"
            "光从上方来，釉面在画面右侧亮起一道硬反光，形体靠瓷砖的深浅与灰浆缝的走向来分。"
            "整体构图疏朗，釉色最深的地方集中在两人的裙子与发根两处，四周留出大片米白的瓷砖。"
        ),
    },
    {
        "key": "rubbing",
        "label": "32-拓片",
        "cn": LEAD + (
            "**这是一幅拓片：整幅画面是一张覆在刻石上拓下来的纸**，"
            "纸面被墨压成近黑，只有刻下去的地方留白，墨色在低处积得更深、在高处发灰，"
            "纸的纤维与几处扑墨不匀的斑块清晰可见。" + UNIFORM + SCENE +
            "狼耳少女的头发用一道道留白的细线排出，发梢的线渐渐断开；"
            "一对狼耳是两块留白的实心形状、耳内留出一点灰；身上那条短裙是整幅里墨最重的地方；"
            "身后的大尾巴用放射状的留白线条排出蓬松的毛感。"
            "她的视线落在少年伸出的那只手上，一侧的嘴角比另一侧翘起极细的一线，"
            "双耳朝少年那一侧前倾，尾尖轻轻摆向少年。"
            "少年的头发**同样用一道道留白的细线排出**、只是线更密；那根呆毛是一小段留白的弧线；"
            "鲸鱼发夹是一小块留白的实心形状；水手领用两道留白细线勾出；"
            "肩上的外套是整幅里墨最淡的地方、几乎只剩纸色；短裤与堆堆袜也一律由留白线排出。"
            "他的眼睛盯着那片花瓣、比平时睁得略大一点，嘴微微张开，伸出的那只手五指并拢、掌心朝上。"
            "檐口在上缘是一条留白的粗线，几片花瓣是几小块留白的薄片，正飘在两人之间；"
            "背景是纸本身的灰白，几处扑墨不匀的斑块落在四周；地面是几道横向的留白线排出的石阶。"
            "光是均匀的，形体完全靠留白与墨色的对比来分，画面里没有一处是彩色。"
            "整体构图疏朗，墨最重的地方集中在两人的裙子与发根两处，四周留出大片发灰的纸面。"
        ),
    },
]


def upload(path):
    b = "----wolf8" + str(int(time.time() * 1000))
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
    print("本批目标：验证『媒介要求在每个角色段落各写一遍』能否修掉画风偏袒 image1 的问题\n")

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