#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A/B 对照：提示词里「完整角色描述段」vs「方案B精简标志物清单」

目的：上一轮两版成品除提示词外还有两处混杂变量（画布 768x1344 vs 1024x1024、
参考图 jpg/png 不同）。本脚本把变量锁死，只改那一段，用同一 seed 各出一张，
从而把「是提示词还是画布造成的差异」钉死。

设计（结论来自 2026-09-23 的分析）：
  · 身份交给 <imageN> 槽位；文字只写「表演 + 场景 + 优先级」。
  · 方案B 保留 5 个高辨识标志物作为补充锚点，服装细节一律不写。
  · 两版除「身份标记」段落外逐字相同。

用法：
  python tools/diag/gen_ab_identity_markers.py            # 两版都跑
  python tools/diag/gen_ab_identity_markers.py A          # 只跑详细版
  python tools/diag/gen_ab_identity_markers.py B          # 只跑精简版
"""
import json
import os
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WB = "http://127.0.0.1:8642"
O = urllib.request.build_opener(urllib.request.ProxyHandler({}))

CAMERA_ROLL = r"D:\Pictures\Camera Roll"
REF_IMG1 = os.path.join(CAMERA_ROLL, "玫瑰香槟粉CCD复古直闪，两位年轻成年东亚女性.jpg")
REF_IMG2 = os.path.join(CAMERA_ROLL, "小名人设.png")
REF_IMG3 = os.path.join(CAMERA_ROLL, "截图", "狼狼.png")

# 统一参数：两版必须完全一致，否则又引入混杂变量
SEED = 20260923
WIDTH = HEIGHT = 1024
STEPS = 25
CFG = 1.0

# ---------------- 两版共用的提示词骨架 ----------------
# {IDENTITY} 处插入两版不同的段落
PROMPT = """一张竖版（9:16）的动画插画：两个动漫角色重现一张复古 CCD 直闪照片的构图与表演。
只借用参考图的**构图、姿势、神态、场景与色调**；画面里的人**换成指定的两位原创角色**，
身份以对应的参考图为准。

【参考图的职责分工】
· <image1>：**只提供画面结构与表演**，不提供人物外貌。它决定：画幅与取景、歌剧院包厢场景、
  光线方向与色温、整体色调，以及两人的**姿势、相对站位、距离、神态、表情、视线、手上道具**。
· <image2>：**只提供画面左侧角色的身份**（外貌与服装一律以这张图为准）。
· <image3>：**只提供画面右侧角色的身份**（同上）。

{IDENTITY}

【表演层 —— 完全照 <image1>，两人都在复现图中动作】
· 两人并肩站在**歌剧院包厢的栏杆前**，面朝镜头。
· 左侧角色身体微侧向右、上半身**倚靠在金色雕花栏杆上**，一条腿微屈、交叉站立；
  **右手举着一只香槟杯**，杯口齐胸；头微微侧转、眼睛看向镜头，嘴角一丝**含蓄的浅笑**。
· 右侧角色站在左侧角色右后方半步，**一只手抬起、用小团扇半遮住下半张脸**，只露出眼睛；
  另一只手在腰前握一只金色手拿包；眼神侧看向左侧同伴，**眉眼弯弯、似笑非笑**。
  ⚠️ 团扇只遮**嘴部以下**，务必露出完整眼睛与额头，让辨识特征可见。
· 相对位置、身高差、前后关系、身体朝向，严格按 <image1>。

【服装剪影 —— 照 <image1> 的轮廓，配色随各自角色】
两人都穿**高领无袖长旗袍、裙身高开叉**：左侧**暗酒红丝绒**（金色缠枝花刺绣），
右侧**香槟玫瑰色缎面**（细花卉暗纹）；都穿细带高跟凉鞋。
除剪影之外的服装细节，一律以 <image2> / <image3> 为准。

{ARBITRATION}

【场景与色调 · 照搬 <image1>】
金碧辉煌的**古典歌剧院**：多层金色雕花包厢、红色帷幔、头顶水晶吊灯；背景包厢里**虚化的观众**。
右侧前景：带流苏灯罩的台灯、小圆桌、桌上一只金色酒杯；右下角一角**红色丝绒沙发**。
光线：**正面直打的硬闪光**（复古 CCD 直闪），皮肤与缎面强高光、阴影浓重偏暖；
整体**玫瑰香槟粉调**；轻微噪点颗粒、轻微暗角、老式数码相机柔焦与轻微畸变。

【氛围一致】
两人处在同一套闪光与阴影里，颜色饱和度、线条粗细、眼睛画法、上色质感完全一致，
看起来像同一部动画里的两个角色、同一次拍摄。

【约束】两人特征不得互换或串味；注意手部细节；画面里没有文字、字幕、水印。"""

# 方案A：完整角色描述段（对照组的"旧写法"）
IDENTITY_A = """【左侧角色 · 身份取自 <image2>】
银白色短发、发梢渐变成浅蓝色，头顶一根弯钩状呆毛，耳侧有一缕蓝色挑染；
一双浅蓝色眼睛；鬓角别着一只**小小的蓝色鲸鱼发夹**；脖子上一条浅蓝色颈圈。
少年体型、皮肤白皙。
上身穿白色水手领露脐短上衣，胸前系一只**浅蓝色大蝴蝶结**，衣摆露出腰腹；
下身浅蓝色抽绳短裤；外面一件**浅蓝色宽肩外套随性地披在肩上、袖子垂落不穿**；
左大腿一个银色金属圆环腿环；白色堆堆袜配白色厚底系带球鞋。

【右侧角色 · 身份取自 <image3>】
浅蓝色长发、长发及腰、刘海遮住一只眼睛，头顶一对**狼耳**（外缘白、内侧粉）；
一双蓝紫色眼睛；发侧系着灰色小蝴蝶结与一枚三角发夹；脖子上一条黑色颈圈。
上身穿黑色抹胸连衣短裙（领口与裙摆带一道蓝色细描边）、裙身紧绷；
双腿各系一只**蝴蝶结腿环**；身后一条**蓝紫色蓬松大尾巴**；脚穿黑色高跟鞋。
她身旁飘着一只**小小的黑色猫灵**。"""

# 方案B：只列 5 个高辨识标志物 + 明确要求服装交给槽位
IDENTITY_B = """【关键标志物 —— 仅列高辨识特征作为补充锚点】
⚠️ 本段**只列头部与贴身配饰层面的标志物**，用于在生成中守住辨识度。
**服装款式、配色、剪裁细节一律不要由文字指定，全部交给 <image2> / <image3>。**
· 左侧角色（<image2>）：头顶一根**弯钩状呆毛**；鬓角一只**蓝色小鲸鱼发夹**；
  脖子上一条**浅蓝色颈圈**。
· 右侧角色（<image3>）：头顶一对**狼耳**（外缘白、内侧粉）；发侧一枚**三角发夹**；
  脖子上一条**黑色颈圈**。"""

# 仲裁段只有 B 版有（A 版此位为空）
ARBITRATION_B = """【冲突仲裁 —— 出现矛盾时按此优先级处理】
1. 优先保住**本段列出的关键标志物**（呆毛、鲸鱼发夹、颈圈、狼耳、三角发夹）；
2. 其次是 <image1> 的**旗袍剪影与整体构图**；
3. 若"右侧角色的蓝紫大尾巴"与长旗袍剪影冲突：**只允许从裙摆开叉或裙摆下缘自然露出一段，
   不得从裙摆中间穿出；若仍显突兀就放弃尾巴，以剪影干净为准**；
4. 若某件原服装与旗袍冲突，**宁可丢弃该件服装，也不要把画面处理成拼贴**。"""

VARIANTS = {
    "A": ("完整角色描述段(旧写法)", IDENTITY_A, ""),
    "B": ("方案B 关键标志物清单", IDENTITY_B, ARBITRATION_B),
}


def upload(path):
    b = "----ab" + str(int(time.time() * 1000))
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
    only = [a.upper() for a in sys.argv[1:] if a.upper() in VARIANTS] or ["A", "B"]

    for p in (REF_IMG1, REF_IMG2, REF_IMG3):
        if not os.path.exists(p):
            print("缺少参考图:", p)
            return 1

    print("上传三张参考图…")
    n1 = upload(REF_IMG1)["name"]
    n2 = upload(REF_IMG2)["name"]
    n3 = upload(REF_IMG3)["name"]
    print(f"  image1={n1}\n  image2={n2}\n  image3={n3}")
    print(f"\n固定参数：seed={SEED}  {WIDTH}x{HEIGHT}  steps={STEPS}  cfg={CFG}"
          f"  custom_canvas=False(跟随参考图)\n")

    results = {}
    for key in only:
        title, identity, arbitration = VARIANTS[key]
        prompt = PROMPT.format(IDENTITY=identity, ARBITRATION=arbitration)
        print("=" * 78)
        print(f"变体 {key}：{title}   提示词 {len(prompt)} 字符")
        print("=" * 78)
        r = post("/api/generate", {
            "prompt": prompt,
            "negative_prompt": "",
            "width": WIDTH, "height": HEIGHT,
            "steps": STEPS, "cfg": CFG,
            "seed": SEED,
            "reference_images": [n1, n2, n3],
            "custom_canvas": False,
            "ref_resolution": 0,
        })
        jid = r.get("job_id")
        if not jid:
            print("  提交失败:", json.dumps(r, ensure_ascii=False)[:300])
            continue
        p = wait(jid, f"变体{key}")
        job = get(f"/api/jobs/{jid}")["job"]
        print(f"  status={job['status']} 耗时={job.get('elapsed')}s")
        if job.get("error"):
            print("  错误:", job["error"][:400])
        for im in job.get("images") or []:
            print(f"  产物: outputs/{im['file']}")
            results[key] = im["file"]

    print("\n" + "=" * 78)
    print("产出汇总（可直接并排比对）")
    print("=" * 78)
    for k, v in results.items():
        print(f"  {k} ({VARIANTS[k][0]}): outputs/{v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
