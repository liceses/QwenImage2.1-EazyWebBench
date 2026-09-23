#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第十一批：**槽位对调** —— 验证"槽位决定媒介强度"

Round 10 的发现：同一条糖画提示词跑 4 个 seed，**4/4 都是 image1 的角色吃满媒介、
image2 的角色只吃到一部分**，背景只吃到边缘（檐口糖条+石阶滴落），墙面仍是石质。
→ 系统性现象，与 seed 无关。

本轮的可证伪假设：
  H：媒介强度由**槽位**决定（谁在 <image1> 谁吃满）
  做法：把两个角色整体对调 —— 小名放 <image1> 且描述在左，狼娘放 <image2> 且描述在右；
        提示词其余部分（媒介、均匀性硬约束、瞬间、表情）逐字不变；沿用 Round 10 的 seed。
  预期：若 H 成立，糖化强度应**反过来偏向小名**，狼娘变成"只吃到一部分"的那个。

用法：python tools/diag/gen_wolf_slot_swap.py [seed ...]
"""
import json
import os
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WB = "http://127.0.0.1:8642"
O = urllib.request.build_opener(urllib.request.ProxyHandler({}))

XIAOMING = r"D:\Pictures\Camera Roll\小名人设.png"   # 本轮放 <image1>
WOLF = r"D:\Pictures\Camera Roll\截图\狼狼.png"      # 本轮放 <image2>

SEEDS = [20261003, 20261005, 20261007]
W, H = 1152, 768
STEPS = 25
CFG = 1.0

# 角色整体对调：小名在左（image1），狼娘在右（image2）；其余逐字沿用
LEAD = ("以 <image1> 的银发少年与 <image2> 的狼耳少女为主角，"
        "两人的外貌、发型、服装与配饰一律以各自对应的参考图为准，只补记几个高辨识标志物——"
        "银发少年：银白短发带蓝色挑染、一根呆毛、一只蓝色小鲸鱼发夹、"
        "水手领露脐上衣与浅蓝短裤、一件披在肩上的浅蓝外套；"
        "狼耳少女：浅蓝长发与狼耳、黑色短裙、蓝紫大尾巴。"
        "**两人的特征不得互换，也不得把一人的衣物画到另一人身上。**")
SCENE = "两人并排坐在檐下的石阶上，银发少年把手心里的花瓣递向身旁的狼耳少女，少女正伸出手去接。"
UNIFORM = ("**画面里的每一处——两个人的头发、皮肤、衣服、尾巴，以及背景与地面——"
           "都必须由同一种媒介做成，没有一处是常规的不透明上色。**")

PROMPT = LEAD + (
    "**这是一幅糖画：整幅画面里的每一处都由一缕缕熬成琥珀色的糖丝在青灰石板上浇成**，"
    "线条是半透明的焦糖色，粗的地方糖浆堆起、细的地方几乎透明，光从背后透过来时颜色像蜂蜜一样发亮；"
    + UNIFORM + SCENE +
    "银发少年的头发用一束束平行的糖丝排出，发梢的糖丝拉得极细、几乎透光；"
    "那根呆毛是一根单独拉起的细糖丝；鲸鱼发夹是一小块较厚的糖片；"
    "水手领用两道并排的糖线勾出；肩上那件外套用最淡的几笔糖丝带过；"
    "短裤与堆堆袜也一律由糖丝排成。"
    "他的视线落在少女伸出的那只手上，一侧的嘴角比另一侧翘起极细的一线，"
    "额前那根呆毛随着动作轻轻一晃。"
    "狼耳少女的头发**同样用一束束平行的糖丝排出**、只是比少年的更长；"
    "一对狼耳用较粗的糖线勾出轮廓、耳内留空；身上那条短裙用最厚的糖浆浇成深琥珀色；"
    "身后的大尾巴用放射状的糖丝排出蓬松的毛感。"
    "她的眼睛盯着那片花瓣、比平时睁得略大一点，嘴微微张开，伸出的那只手五指并拢、掌心朝上，"
    "双耳朝少年那一侧前倾，尾尖轻轻摆向少年。"
    "檐口在上缘用一条粗糖线压住，几片花瓣是几小块薄薄的糖片，正飘在两人之间；"
    "背景的青灰石板上看得见糖丝拉过留下的细痕，地面是几道横向的糖线排出的石阶。"
    "光从背后透进来，糖丝的半透明感让琥珀色发亮，形体靠糖线的粗细与糖浆的厚薄来分。"
    "整体构图疏朗，糖浆最厚的地方集中在两人的裙子与发根两处，四周留出大片石板本色。"
)


def upload(path):
    b = "----swap" + str(int(time.time() * 1000))
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
    seeds = [int(a) for a in sys.argv[1:]] or SEEDS
    for p in (XIAOMING, WOLF):
        if not os.path.exists(p):
            print("缺少参考图:", p)
            return 1
    print("上传两张人设图（**槽位对调**）…")
    r1 = upload(XIAOMING)["name"]   # image1 = 小名
    r2 = upload(WOLF)["name"]       # image2 = 狼娘
    print(f"  image1(小名)={r1}\n  image2(狼娘)={r2}")
    print(f"参数：{W}x{H}  steps={STEPS}  cfg={CFG}   提示词固定（糖画），仅槽位与左右对调")
    print(f"采样 seed：{seeds}（其中 20261003/20261005 与 Round 10 同 seed，可直接对照）\n")

    done = []
    for seed in seeds:
        print("=" * 74)
        print(f"seed {seed}   [槽位对调版]")
        print("=" * 74)
        r = post("/api/generate", {
            "prompt": PROMPT, "negative_prompt": "",
            "width": W, "height": H,
            "steps": STEPS, "cfg": CFG, "seed": seed,
            "reference_images": [r1, r2],
            "custom_canvas": True, "ref_resolution": 0,
        })
        jid = r.get("job_id")
        if not jid:
            print("  提交失败:", json.dumps(r, ensure_ascii=False)[:300])
            continue
        p = wait(jid, f"swap-seed{seed}")
        job = get(f"/api/jobs/{jid}")["job"]
        print(f"  status={job['status']} 耗时={job.get('elapsed')}s")
        if job.get("error"):
            print("  错误:", job["error"][:400])
        for im in job.get("images") or []:
            print(f"  产物: outputs/{im['file']}   (seed={seed})")
            done.append((seed, im["file"]))

    print("\n汇总（待人工判定：媒介是否反过来偏向小名）：")
    for seed, f in done:
        print(f"  seed {seed} -> outputs/{f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())