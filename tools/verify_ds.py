#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用新参考图出一次全身验证图，检查：鳍状鲸耳 / 鲸鱼尾鳍 / 服装细节是否都回来。"""
import json
import os
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = "http://127.0.0.1:8642"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "style_run7")
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

DS = ('深宝蓝色长卷发、发尾渐渐变成浅蓝色，头顶一根弯钩状的呆毛，一双蓝色的眼睛、开朗的笑容。'
      '耳部是一对宽扁的鳍状鲸耳——深藏青色的外缘配上白色的内侧，向两侧下方伸出。'
      '头上戴着白色荷叶边女仆头饰，右侧系一只浅蓝色蝴蝶结。'
      '身上是白色衬衫式上衣（前襟有竖褶）外罩一件深藏青色的紧身马甲，马甲正面有两排金色纽扣与金色滚边；'
      '深藏青色的长袖配白色荷叶边袖口，领口系一只深色蝴蝶结、正中一颗蓝宝石扣。'
      '身前系一条白色荷叶边围裙，围裙的右下角有一个小小的鲸鱼图案。'
      '下身是深藏青色的大裙摆：裙面压着金色的藤蔓纹样，正中央是一片浅蓝色的竖条纹面板、面板两侧各系一只小蝴蝶结，'
      '裙摆下方露出一圈白色荷叶边衬裙。白色短袜配深藏青色的玛丽珍鞋。'
      '身后伸出一条深藏青色的鲸鱼尾鳍（尾鳍宽大、内侧偏浅蓝）。')

PROMPT = f"""一张干净的全身角色立绘。

主题：一位{DS}

她正面站立、双脚自然并拢、一只手臂自然垂在身侧、另一只微微抬起，开朗地笑着看镜头。**必须是完整的全身**（从头顶到鞋底都在画面内），姿态自然、身体不扭转。

背景：纯白色的干净背景，只有脚下有一小片柔和的淡灰色投影，不放任何其它元素。

风格：动漫插画，干净利落的线稿，明亮均匀的棚拍光，鲜明的高饱和上色，官方角色立绘的完成度。

约束：画面里只有她一个人物、只有一个形象，不是角色设定表、不是三视图、不要分栏分屏；双手空着、手中不要拿任何物品；画面中没有文字。"""

payload = {"prompt": PROMPT, "negative_prompt": " ",
           "steps": 35, "cfg": 1.0, "width": 1024, "height": 1536,
           "seed": 9901, "reference_images": ["ref_ec15289879.png"],
           "ref_resolution": 0, "custom_canvas": True}

req = urllib.request.Request(BASE + "/api/generate",
                             data=json.dumps(payload).encode(),
                             headers={"Content-Type": "application/json"})
with OPENER.open(req, timeout=60) as r:
    resp = json.load(r)
job = resp.get("job_id")
print("job =", job)
t0 = time.time()
while time.time() - t0 < 900:
    time.sleep(3)
    with OPENER.open(f"{BASE}/api/progress/{job}", timeout=15) as r:
        p = json.load(r)
    if p.get("status") != "running":
        break
with OPENER.open(f"{BASE}/api/jobs/{job}", timeout=15) as r:
    full = json.load(r)
imgs = (full.get("job") or {}).get("images") or []
if imgs:
    src = os.path.join(HERE, "..", "outputs", imgs[0]["file"].replace("/", os.sep))
    dst = os.path.join(OUT, "99_DS娘全身验证.png")
    with open(src, "rb") as fi, open(dst, "wb") as fo:
        fo.write(fi.read())
    print(f"  OK {p.get('elapsed')}s -> {dst}")
else:
    print("  无产物:", p.get("error"))
