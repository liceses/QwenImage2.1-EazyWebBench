#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""狼娘抱着卡通炸弹惊恐的夸张风格插画。

设计说明（沿用 2026-09-23 A/B 实测结论）：
  · 本图**不换装**：角色保留人设原服装，因此"文字角色描述"与"参考图槽位"不冲突，
    不会重演上一轮"保角色 vs 换装"的零和（见 能力清单.md 第 16 节）。
  · 炸弹用**橡胶管卡通风**（黑色圆球 + 点燃的引线）：这是喜剧道具，不是写实军械，
    配合"抱着点燃的炸弹"这个卡通片老梗，落点是搞笑而非恐怖。
  · 夸张感靠三样：广角低机位近距离（炸弹显大）、人物缩成一团紧抱、尾巴炸开 + 速度线背景。

用法：python tools/diag/gen_wolf_bomb_comedy.py [seed ...]
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

WIDTH = HEIGHT = 1024
STEPS = 28
CFG = 1.0

PROMPT = """一张**夸张喜剧风格**的卡通插画：画面主体是一个动漫狼耳少女，
她正**吃力地斜抱着一枚核导弹**，脸上是极度惊恐的夸张表情。

【角色 —— 以 <image1> 为准，服装发型配饰完全沿用参考图，不做任何改动】
浅蓝色长发、刘海遮住一只眼睛、头顶一对狼耳（外缘白、内侧粉）；发侧系着灰色小蝴蝶结与一枚三角发夹；
脖子上一条黑色颈圈；黑色抹胸连衣短裙（领口与裙摆带一道蓝色细描边）；双腿各系一只蝴蝶结腿环；
黑色高跟鞋。**保留参考图的头身比例（少年体型的少女，不要压缩成幼儿）**，皮肤白皙。
身后那条**蓝紫色蓬松大尾巴**在本图中**因惊吓而整个炸开、竖直翘起、毛发根根竖立**。
（她肩头那只小小的黑色猫灵也一起吓到炸毛。）

【道具 —— 喜剧化的核导弹（关键：是导弹，不是圆球炸弹）】
她怀里抱着的是一枚**核导弹**，用复古卡通动画里的经典造型来表现：
**细长的圆柱形弹体**（哑光浅灰白色，表面有几道简洁的铆接缝线），
**前端一枚锥形的红色弹头**，**尾部四片醒目的三角形尾翼**；
弹体侧面印着一枚**黄黑相间的辐射三叶标志**，表明它是核弹头导弹；
弹体表面有一道**长条形高光**，让它整体是光滑圆润的卡通道具质感。
**绝对不要圆球形的老式炸弹、不要写实的军事细节、不要发射架、不要军事文字与编号。**
这枚导弹**又大又长**，被她斜抱在怀里、几乎贯穿整个画面。

【姿势与构图 —— 夸张的来源】
**广角低机位近距离**视角：导弹被**斜抱**在她胸前、**横跨整个画面**，
弹头翘在她的左肩上方、尾翼垂到右胯旁边，看起来**比她的身高还长**。
她**吃力地环抱着这枚导弹**：两条手臂箍住弹体中段、十指交扣、手臂因使劲而绷紧；
身体被压得**向后仰、腰部后折**、重心不稳；一条腿撑地、另一条腿膝盖弯曲往前蹬；
肩膀因用力而耸起；一侧脸颊贴在弹体上被挤得变形。

【表情 —— 极度惊恐且夸张】
眼睛瞪到极大、瞳孔缩成小点，眉毛高高挑起；嘴巴大张成"哦"形、牙齿打颤；
脸侧挂着**一大滴冷汗**，脸色发青发白；头顶上方一个表示"被吓到"的爆炸形符号。

【背景 —— 强烈虚化（本次重点）】
背景**整体重度虚化、不出现任何清晰可辨的景物轮廓**：只用**柔和的大块色斑与圆形散景光点**
铺出氛围，像是用大光圈浅景深拍出来的照片背景（暖调与冷调柔和交织）。
**不要速度线、不要爆炸状色块、不要放射状线条、不要清晰的建筑或天空细节。**
散景光点在弹体与她的发梢边缘勾出**柔和的轮廓光**。
**人物与导弹必须保持完全锐利清晰**，与虚化背景形成强烈的前后景分离。

【画面风格 —— 强夸张动画感】
高饱和度的卡通动画插画风：**粗黑描边**、形变明显、动态张力强。
用**夸张的动感表达慌张、但不吓人**：整体基调是**搞笑、可爱、动画片式的紧张感**，不是真实威胁。

【约束】画面里没有文字、没有字幕、没有水印；除了狼耳少女与那只小黑猫灵，没有其他人物。"""

# ---- 上一版（圆球炸弹 + 速度线背景）留档备查，改 --legacy 可复用 ----
PROMPT_BOMB_V1 = """一张**夸张喜剧风格**的卡通插画：画面主体是一个动漫狼耳少女，她正**死死抱住一枚核弹**，
脸上是极度惊恐的夸张表情。

【角色 —— 以 <image1> 为准，服装发型配饰完全沿用参考图，不做任何改动】
浅蓝色长发、刘海遮住一只眼睛、头顶一对狼耳（外缘白、内侧粉）；发侧系着灰色小蝴蝶结与一枚三角发夹；
脖子上一条黑色颈圈；黑色抹胸连衣短裙（领口与裙摆带一道蓝色细描边）；双腿各系一只蝴蝶结腿环；
黑色高跟鞋。在她 3D 身形之外，保留**少年感偏小的体格**与白皙皮肤。
身后那条**蓝紫色蓬松大尾巴**在本图中**因惊吓而整个炸开、竖直翘起、毛发根根竖立**。
（她肩头那只小小的黑色猫灵也一起吓到炸毛。）

【道具 —— 喜剧化的核弹】
她怀里抱着一枚**核弹**，用**复古卡通片里的经典造型**来表现：
一颗**浑圆的深色弹体**（哑光深灰近黑，成对圆润像玩具），顶端插着一根
**正在燃烧、滋滋冒火星的引线**，引线已经烧到只剩一小截；
弹体侧面印着一枚**黄黑相间的辐射三叶标志**，让它在视觉上明确是核弹；
表面有一块**圆形白色高光**，让它整体是圆润的卡通道具质感，
**不要写实的军械纹理、不要导弹外形、不要发射井与军事文字**。

【姿势与构图 —— 夸张的来源】
**广角低机位近距离**视角：核弹被她抱在胸前**占据画面中央很大一块**，
因为在镜头前所以显得**比她的头还大**，形成"道具被夸张放大"的喜剧效果。
她的动作是**缩成一团、整个人贴在弹体上**：两条手臂**紧紧环抱住核弹**、手指抠住弹面、
手臂因为用力绷紧；脸颊贴上去、被挤得变形；双腿**脚软发抖、膝盖内扣**，站姿僵硬；
身体微微后仰、整个人僵在原地不敢动。

【表情 —— 极度惊恐且夸张】
眼睛瞪到极大、瞳孔缩成小点，眉毛高高挑起；嘴巴大张成"哦"形、甚至牙齿打颤；
脸侧挂着**一大滴冷汗**，脸色发青发白；头顶上方一个表示"被吓到"的小爆炸形符号。

【画面风格 —— 强夸张动画感】
高饱和度的卡通动画插画风：**粗黑描边**、**Q 版夸张比例**、形变明显、动态张力强。
用**夸张的动感表达慌张、但不吓人**：背景放射出速度线、角落一个爆炸状色块，
引线在滋滋冒火星；整体基调是**搞笑、可爱、动画片式的紧张感**，不是真实威胁。

【约束】画面里没有文字、没有字幕、没有水印；除了狼耳少女与那只小黑猫灵，没有其他人物。"""


def upload(path):
    b = "----bomb" + str(int(time.time() * 1000))
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


def wait(jid, label, limit=1800):
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
    seeds = [int(s) for s in sys.argv[1:]] or [880417, 190233]
    if not os.path.exists(WOLF):
        print("缺少参考图:", WOLF)
        return 1
    print("上传狼娘人设图…")
    ref = upload(WOLF)["name"]
    print(f"  {ref}")
    print(f"\n参数：{WIDTH}x{HEIGHT}  步数 {STEPS}  cfg {CFG}  跟随参考图画布\n")

    done = []
    for seed in seeds:
        print("=" * 74)
        print(f"seed {seed}")
        print("=" * 74)
        r = post("/api/generate", {
            "prompt": PROMPT, "negative_prompt": "",
            "width": WIDTH, "height": HEIGHT,
            "steps": STEPS, "cfg": CFG, "seed": seed,
            "reference_images": [ref],
            "custom_canvas": False, "ref_resolution": 0,
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
            done.append((seed, im["file"]))
    print("\n汇总：")
    for seed, f in done:
        print(f"  seed {seed} -> outputs/{f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
