#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""双角色梗图：狼娘（手柄在手的挑衅方）× ds娘（鲸鱼娘，被欺负方）。

设计说明：
  · 交互用「捏脸」而不是任何窒息/暴力动作 —— 梗感来自表情与距离，不来自伤害。
  · 场景选书桌前的游戏现场：狼娘本来手里就有手柄（人设图自带道具），
    天然形成"打游戏打输了/赢了在嘲讽"的因果关系。
  · 两张参考图的角色特征逐项写进 prompt，避免模型把两套衣服/发色串味。
"""
import json
import os
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WB = "http://127.0.0.1:8642"
O = urllib.request.build_opener(urllib.request.ProxyHandler({}))
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))

WOLF = "ref_125815edb4.png"   # 狼娘
WHALE = "ref_98e47ec878.png"  # ds娘（鲸鱼娘）

PROMPT_V2 = f"""一张双人同框的搞笑梗图：两个角色紧挨着站在一起，像一局游戏刚结束时那样。

【角色一 · 画面左侧，欺负人的那个】<image1> 里的狼耳少女：浅蓝色长发、刘海遮住一只眼、狼耳、灰色蝴蝶结与三角发夹、黑色颈圈、黑色抹胸连衣短裙带蓝色描边、大腿蝴蝶结腿环、蓝紫色蓬松大尾巴；她身旁跟着一只小黑猫。

【角色二 · 画面右侧，被欺负的那个】<image2> 里的鲸鱼娘：深宝蓝色长卷发、发尾渐变成浅蓝、头顶一根弯钩呆毛、蓝色眼睛；耳部一对宽扁的鲸鱼鳍耳（深藏青外缘配白色内侧）；白色荷叶边女仆头饰、右侧浅蓝色蝴蝶结；白色衬衫式上衣外罩深藏青紧身马甲（两排金色纽扣与金色滚边）、领口深色蝴蝶结；身前白色荷叶边围裙（右下角一个小鲸鱼图案）；深藏青大裙摆压金色藤蔓纹样、正中央浅蓝竖条纹面板、裙摆下一圈白色荷叶边衬裙；身后一条深藏青鲸鱼尾鳍。

【动作 —— 梗就在这里，务必画准】狼娘和鲸鱼娘**侧身面对面、贴得很近**，肩膀几乎挨在一起，体格差明显（狼娘略高一点）。狼娘左手得意地把游戏手柄举在胸前当战利品；右手伸出两根手指，**捏住鲸鱼娘的脸颊往旁边轻轻一拧**，把那张脸捏得嘟起来变形。狼娘一脸"赢麻了"的坏笑、眉毛上挑、眼睛半眯着看她。

【被捏的鲸鱼娘的表情 —— 这是全图最好笑的地方】脸颊被捏得鼓起来、嘴巴被挤成一小坨，眉头紧皱、眼睛瞪得圆圆的，一副**气鼓鼓又拿她没办法**的幽怨表情；一只手抬起来想去拍掉狼娘的手。脸微微泛红。

【氛围】朋友之间闹着玩的喜剧感、夸张的动画表演感，绝无任何伤害、疼痛或威胁的意味。

【画面一体性】两人站在同一个室内场景、脚下同一片地面；同一套柔和暖光从左上方照下来，两人身上是同一套光照方向与阴影；两人的颜色饱和度、线条粗细与眼睛画法完全一致，看起来像同一部动画里的两个角色，而不是两张图拼在一起。

【背景】温馨的室内游戏角落：浅色墙面、桌上散落着零食袋与饮料罐、背景里一台显示器虚化发光，整体柔和虚化不抢主体。

【约束】画面里没有文字、没有字幕、没有水印；只有这两个角色，没有第三个人物。"""

PROMPT = PROMPT_V2


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
    seeds = [int(s) for s in (sys.argv[1:] or ["20260922", "771102"])]
    for seed in seeds:
        print(f"\n=== seed {seed} ===")
        r = post("/api/generate", {
            "prompt": PROMPT,
            "negative_prompt": "",
            "width": 1152, "height": 768,
            "steps": 30, "cfg": 1.0,
            "seed": seed,
            "reference_images": [WOLF, WHALE],
            "custom_canvas": True,
            "ref_resolution": 0,
        })
        jid = r.get("job_id")
        if not jid:
            print("  提交失败:", json.dumps(r, ensure_ascii=False)[:300])
            continue
        p = wait(jid, f"seed{seed}")
        job = get(f"/api/jobs/{jid}")["job"]
        print(f"  status={job['status']} 耗时={job.get('elapsed')}s")
        if job.get("error"):
            print("  错误:", job["error"][:400])
        for im in job.get("images") or []:
            print(f"  产物: outputs/{im['file']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
