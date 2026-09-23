#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第九批：**同 seed 严格 A/B** —— 验证"媒介均匀覆盖"的修正

Round 8 的结论有方法学瑕疵：糖画修正版换了 seed，不是受控对比。
本批把变量锁死：**全部用 seed 20261002**（与 Round 8 相同）、同画布、同参考图，
只改提示词结构。

2×2 受控设计：
  糖画-旧结构 = Round 7 的原文（媒介只在开头写一次）
  糖画-新结构 = Round 8 的原文（媒介重述 + 均匀性硬约束）
  剪纸-旧结构 = 同一套路子写（媒介只写一次）
  剪纸-新结构 = 加均匀性硬约束 + 逐角色重述媒介 + 枚举更多部件

若"新结构"在两张里都让媒介覆盖到 <image2> 的角色与背景，则修正成立；
若两张都无差别，则 Round 7→8 的改善只是 seed 运气。

用法：python tools/diag/gen_wolf_ab_medium.py [seed]
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

SEED = 20261002          # 与 Round 8 相同 —— 锁死变量
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
UNIFORM = ("**画面里的每一处——两个人的头发、皮肤、衣服、尾巴，以及背景与地面——"
           "都必须由同一种媒介做成，没有一处是常规的不透明上色。**")

# ---------------- 糖画：旧结构（Round 7 原文，逐字） ----------------
SUGAR_OLD = LEAD + (
    "这是一幅糖画：整幅由一缕缕熬成琥珀色的糖丝在石板上浇成，线条是半透明的焦糖色，"
    "粗的地方糖浆堆起、细的地方几乎透明，光从背后透过来时颜色像蜂蜜一样发亮。" + SCENE +
    "狼耳少女的头发用一束束平行的糖丝排出，发梢的糖丝拉得极细、几乎透光；"
    "一对狼耳用较粗的糖线勾出轮廓、耳内留空；身上那条短裙用最厚的糖浆浇成深琥珀色，衣褶靠留空的石板分出；"
    "身后的大尾巴用放射状的糖丝排出蓬松的毛感，尾尖拉出一个小勾。"
    "她的视线落在少年伸出的那只手上，一侧的嘴角比另一侧翘起极细的一线，"
    "双耳朝少年那一侧前倾，尾尖轻轻摆向少年。"
    "少年的头发用更细的糖丝排出，呆毛是一根单独拉起的细糖丝；"
    "水手领用两道并排的糖线勾出，肩上那件外套只用最淡的几笔糖丝带过。"
    "他的眼睛盯着那片花瓣、比平时睁得略大一点，嘴微微张开，伸出的那只手五指并拢、掌心朝上。"
    "檐口在上缘用一条粗糖线压住，几片花瓣是几小块薄薄的糖片，正飘在两人之间。"
    "背景是石板本身的青灰色，只在远处用极淡的几笔糖丝扫出雨丝；地面是几道横向的糖线排出的石阶。"
    "光从背后透进来，糖丝的半透明感让琥珀色发亮，形体靠糖线的粗细与糖浆的厚薄来分。"
    "整体构图疏朗，糖浆最厚的地方集中在两人的裙子与发根两处，四周留出大片石板本色。"
)

# ---------------- 糖画：新结构（Round 8 原文，逐字） ----------------
SUGAR_NEW = LEAD + (
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
)

# ---------------- 剪纸：旧结构（媒介只写一次） ----------------
PAPER_OLD = LEAD + (
    "这是一幅套色剪纸：画面由一层层剪好的彩色纸叠成，浅蓝的纸剪出头发、黑色的纸剪出裙子、"
    "粉色的纸剪出花瓣、米白的纸剪出皮肤与台阶，每一层都比下一层略小、露出后面的颜色；"
    "所有形状都是剪出来的，边缘是剪刀走出来的硬边，转折处带着小小的锯齿与毛口。" + SCENE +
    "狼耳少女的头发剪成一缕缕相连的镂空线条，发梢收成尖角；一对狼耳是两块分开剪出的尖形纸片，耳内留一条镂空的细缝；"
    "身上那条短裙用几道平行的镂空表现衣褶，裙摆下缘剪成一排整齐的尖齿；"
    "身后的大尾巴剪成一片放射状的锯齿形纸片，尾尖弯向一侧。"
    "她的视线落在少年伸出的那只手上，一侧的嘴角比另一侧翘起极细的一线，"
    "双耳朝少年那一侧前倾，尾尖轻轻摆向少年。"
    "少年的头发剪成一缕缕相连的线条，呆毛剪成一小段独立的弯钩；水手领剪成两道并排的镂空线，"
    "肩上那件外套是叠在最上面的一层浅蓝纸片。"
    "他的眼睛盯着那片花瓣、比平时睁得略大一点，嘴微微张开，伸出的那只手五指并拢、掌心朝上。"
    "檐口在上缘剪成一排层叠的瓦当，每一片瓦当都有一个月牙形的镂空；几片花瓣形的纸屑正飘在两人之间。"
    "背景是平贴的米色底纸，镂空的地方透出后面的衬纸；地面是一层层横向的镂空石阶。"
    "光是均匀的，纸面平贴在底纸上，没有任何投影与渐变。"
    "整体构图疏朗，纸的红与花瓣的粉是仅有的两处彩色，四周留出大片底纸。"
)

# ---------------- 剪纸：新结构（媒介重述 + 均匀性硬约束） ----------------
PAPER_NEW = LEAD + (
    "**这是一幅套色剪纸：整幅画面里的每一处都由剪好的彩纸叠成**——浅蓝的纸剪出头发、黑色的纸剪出裙子、"
    "粉色的纸剪出花瓣、米白的纸剪出皮肤与台阶，每一层都比下一层略小、露出后面的颜色；"
    "所有形状都是剪出来的，边缘是剪刀走出来的硬边，转折处带着小小的锯齿与毛口；"
    "**画面里没有一处是画上去的，全部是纸剪出来的。**" + UNIFORM + SCENE +
    "狼耳少女的头发剪成一缕缕相连的镂空线条，发梢收成尖角；一对狼耳是两块分开剪出的尖形纸片，耳内留一条镂空的细缝；"
    "身上那条短裙用几道平行的镂空表现衣褶，裙摆下缘剪成一排整齐的尖齿；"
    "身后的大尾巴剪成一片放射状的锯齿形纸片，尾尖弯向一侧。"
    "她的视线落在少年伸出的那只手上，一侧的嘴角比另一侧翘起极细的一线，"
    "双耳朝少年那一侧前倾，尾尖轻轻摆向少年。"
    "少年的头发**同样剪成一缕缕相连的线条**，只是比少女的更细；那根呆毛剪成一小段独立的弯钩；"
    "鲸鱼发夹是一小块单独的深蓝纸片；水手领剪成两道并排的镂空线；"
    "肩上那件外套是叠在最上面的一层浅蓝纸片；短裤与堆堆袜也一律由剪出的纸片叠成。"
    "他的眼睛盯着那片花瓣、比平时睁得略大一点，嘴微微张开，伸出的那只手五指并拢、掌心朝上。"
    "檐口在上缘剪成一排层叠的瓦当，每一片瓦当都有一个月牙形的镂空；几片花瓣形的纸屑正飘在两人之间。"
    "背景是平贴的米色底纸，镂空的地方透出后面的衬纸；地面是一层层横向的镂空石阶。"
    "光是均匀的，纸面平贴在底纸上，没有任何投影与渐变，画面里也没有一处平涂的颜色。"
    "整体构图疏朗，四周留出大片底纸。"
)

CASES = [
    ("A1", "糖画-旧结构(媒介只写一次)", SUGAR_OLD),
    ("A2", "糖画-新结构(重述+硬约束)", SUGAR_NEW),
    ("B1", "剪纸-旧结构(媒介只写一次)", PAPER_OLD),
    ("B2", "剪纸-新结构(重述+硬约束)", PAPER_NEW),
]


def upload(path):
    b = "----ab9" + str(int(time.time() * 1000))
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
    print(f"参数：seed={seed}（锁死，与 Round 8 同）  {W}x{H}  steps={STEPS}  cfg={CFG}")
    print("2×2 受控设计：唯一变量 = 提示词结构\n")

    done = []
    for tag, label, prompt in CASES:
        print("=" * 74)
        print(f"[{tag}] {label}   正文 {len(prompt)} 字")
        print("=" * 74)
        r = post("/api/generate", {
            "prompt": prompt, "negative_prompt": "",
            "width": W, "height": H,
            "steps": STEPS, "cfg": CFG, "seed": seed,
            "reference_images": [r1, r2],
            "custom_canvas": True, "ref_resolution": 0,
        })
        jid = r.get("job_id")
        if not jid:
            print("  提交失败:", json.dumps(r, ensure_ascii=False)[:300])
            continue
        p = wait(jid, f"[{tag}]{label}")
        job = get(f"/api/jobs/{jid}")["job"]
        print(f"  status={job['status']} 耗时={job.get('elapsed')}s")
        if job.get("error"):
            print("  错误:", job["error"][:400])
        for im in job.get("images") or []:
            print(f"  产物: outputs/{im['file']}")
            done.append((tag, label, im["file"]))

    print("\n汇总：")
    for tag, label, f in done:
        print(f"  [{tag}] {label} -> outputs/{f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())