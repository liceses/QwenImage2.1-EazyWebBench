#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""狼娘 × 第二批画风（剪纸 / 像素 / 油画厚涂 / 蓝晒）

Round 1 暴露的两个问题，本批修正：
  1. ❌ 上批玻璃彩绘里我把眼睛写成"琥珀黄的玻璃" -> 角色瞳色被改成琥珀金。
     ✅ 本批一律**不指定瞳色**（交给 <image1>），只在需要时用"深色/留白"描述结构。
  2. ❌ 上批玻璃彩绘丢掉了"仰头看花"的瞬间，变成正面摆拍微笑。
     ✅ 本批每一条都把**视线落点锁在右上方那片花瓣**上，并保留"瞬间"感。

沿用两套规则：八步观察者法（比例不进正文/无质量词/位置短语/材质/一句光照/一句收尾）
+ 微表情纪律（不对称、联动、克制、抓中间态）。

用法：python tools/diag/gen_wolf_style_gallery2.py [seed]
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

SEED = 20260926
STEPS = 25
CFG = 1.0

LEAD = "以 <image1> 的狼耳少女为主角，外貌、发型、服装与配饰一律以该图为准。"

STYLES = [
    {
        "key": "papercut",
        "label": "5-套色剪纸",
        "cn": LEAD + (
            "这是一幅套色剪纸：画面由一层层剪好的彩色纸叠成，浅蓝的纸剪出头发、"
            "黑色的纸剪出裙子、粉色的纸剪出樱花、米白的纸剪出皮肤与台阶，每一层都比下一层略小、露出后面的颜色；"
            "所有形状都是剪出来的，边缘是剪刀走出来的硬边，转折处带着小小的锯齿与毛口。"
            "她侧身坐在老屋檐下的石阶上，仰着头看一枝从左上方斜伸进来的樱花。"
            "头发剪成一缕缕相连的镂空线条，发梢收成尖角；头顶一对狼耳是两块分开剪出的尖形纸片，内侧留出一条镂空的细缝。"
            "她的脸是整幅里唯一没有镂空的地方：侧脸只剪出一条鼻梁与一小段下颌线，"
            "眼睛剪成两弯细长的月牙形缺口，视线的落点在左上方那枝花上；嘴是一小段微微上翘的弧线，左边比右边长了极细的一线。"
            "颈间一条细细的镂空颈圈，身上的短裙用几道平行的镂空表现衣褶，裙摆下缘剪成一排整齐的尖齿。"
            "身后那条蓬松的大尾巴剪成一片放射状的锯齿形纸片，尾尖弯向一侧。"
            "樱花枝是深褐色的纸剪出的硬朗枝干，花朵是五瓣一朵的粉色镂空小花，花瓣之间留出透光的缝；"
            "几片花瓣形的纸屑正飘在半空，其中一片落在她的膝头。"
            "瓦檐在上缘剪成一排层叠的瓦当，每一片瓦当都有一个月牙形的镂空。地面是一层层横向的镂空石阶。"
            "光是均匀的，纸面平贴在底纸上，镂空的地方透出后面淡米色的衬纸，没有任何投影与渐变。"
            "整体构图左右留白，边缘一圈细窄的镂空花边收住画面。"
        ),
    },
    {
        "key": "pixel",
        "label": "6-像素画",
        "cn": LEAD + (
            "这是一幅像素画：整个画面由一个个方形的像素块拼成，每一块都有清楚的直角边缘，斜线呈阶梯状。"
            "她坐在老屋檐下的石阶上，仰头看一枝从右上角伸进来的樱花。"
            "头发用三到四档深浅不同的蓝色像素排出发丝的走向，发梢以最浅的一档收尾；"
            "头顶一对狼耳用米白与淡粉两档像素拼出，耳廓边缘是锯齿状的。"
            "她的脸只占十几个像素宽：眼睛是两个深色的像素块，视线的落点在右上方那朵花上；"
            "嘴是一个像素宽的浅色点，左边的嘴角比右边高了一个像素。"
            "颈间一条深色的颈圈像素线，身上的短裙用黑色与深灰两档排出一排排平行的衣褶像素，裙摆下缘有一道浅蓝的像素边。"
            "身后那条大尾巴用蓝紫两色的像素排成放射状的毛丛，尾尖弯向一侧。"
            "樱花枝用深褐像素勾出，花朵是五瓣的粉色像素团，花心点一个深红的像素。"
            "几片花瓣是单独的粉色像素块，正飘在半空。"
            "瓦檐在上缘排成一排深浅相间的瓦当像素，每一片都有一个小小的方形高光。"
            "天空是平涂的暖黄色，没有渐变；地面是一层层横向的灰色像素石阶。"
            "光是平的，颜色之间只有硬边，没有过渡与抗锯齿。"
            "整体构图把人物放在画面正中偏下，四周留出大片平涂的天空色，整幅使用的颜色不超过十六种。"
        ),
    },
    {
        "key": "impasto",
        "label": "7-油画厚涂",
        "cn": LEAD + (
            "这是一幅油画，颜料堆得很厚：每一笔都留着画刀的刮痕与颜料的凸起，笔触的边缘在侧光下有细小的阴影。"
            "她坐在老屋檐下的石阶上，微微仰头看一枝从右上角斜伸进来的樱花，一只手撑在身后的台阶上。"
            "她的头发用几笔宽大的浅蓝与白色颜料扫出，发梢的笔触拖得很长、末梢翘起来；"
            "头顶一对狼耳是两笔厚实的米白，内侧刮出一小片淡粉，耳廓的边缘用刀尖挑出毛边。"
            "她的脸只用了很少的几笔：眼睛是两点深色的短笔触，视线的落点在右上方那朵花上；"
            "一侧的眼尾比另一笔略微收紧；嘴是一小道偏斜的朱红笔触，左边比右边长了极细的一线。"
            "颈间一条深色的短笔触，身上的黑色短裙用一大片厚涂的黑，衣褶是几道用刀背刮出来的亮线；"
            "裙摆下缘有一道浅蓝的细笔触。身后那条大尾巴用蓝紫两色的厚涂颜料一簇簇地挑起来，尾尖弯向一侧。"
            "樱花枝是深褐色的一笔，花朵用粉色颜料一小坨一小坨地堆上去，花心点一滴朱红。"
            "几片花瓣是单独的一小笔粉色，正飘在半空。瓦檐在上缘用几笔厚重的深蓝与墨黑堆出瓦当的层叠。"
            "天空是一片薄薄的暖黄底色，只留下刮刀扫过的痕迹。"
            "光是从左上方来的侧光，把颜料的凸起照出一层浅浅的立体阴影。"
            "整体构图饱满，颜料最厚的地方集中在头发、尾巴与花朵三处，四周的天空与台阶则画得很薄、露出画布的纹理。"
        ),
    },
    {
        "key": "cyanotype",
        "label": "8-蓝晒印相",
        "cn": LEAD + (
            "这是一幅蓝晒印相：整幅只有深浅不同的普鲁士蓝与纸本身的白色，像是把物体直接压在感光纸上晒出来的影子。"
            "她坐在老屋檐下的石阶上，微微仰头看一枝从右上角斜伸进来的樱花。"
            "她的头发是一整片深蓝的实影，发丝的分界靠留白的细线勾出；"
            "头顶一对狼耳是两块深蓝的影子，内侧留出一条白色的缝。"
            "她的脸是一小块浅蓝的受光面：眼睛是两处白色的留白，视线的落点在右上方那朵花上；"
            "嘴是一小段极淡的弧线，左边比右边长了极细的一线。"
            "颈间一条白色的细颈圈，身上的短裙是一大片最深的蓝，衣褶靠留白的线条排出；裙摆下缘有一道浅蓝的边。"
            "身后那条大尾巴是一片边缘发虚的深蓝影子，尾尖弯向一侧。"
            "樱花枝是深蓝的一笔，花朵是白色的五瓣留白，花心是一小点深蓝。"
            "几片花瓣是单独的白点，正飘在半空。瓦檐在上缘是几片交叠的深蓝瓦当。"
            "天空是一大片均匀的淡蓝，纸的纤维与刷痕隐约可见；地面是一层层横向的深蓝石阶。"
            "光是均匀的漫射光，没有方向，形体全靠蓝的深浅与留白的边界来分。"
            "整体构图安静克制，最深的地方集中在裙与头发两处，白色的花朵与花瓣是画面里最亮的几处，四周留出大片淡蓝的空白。"
        ),
    },
]


def upload(path):
    b = "----wolf2" + str(int(time.time() * 1000))
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
    print(f"参数：seed={seed}  steps={STEPS}  cfg={CFG}  画布跟随参考图\n")

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