#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构图/姿势大变体抽卡：每张都与参考图的「全身直立正面站姿」拉开距离。

三轴设计：机位（俯拍/仰角/背后/特写/框中框）+ 姿势（躺/腾空/背影/抱膝/侧身）+ 构图装置（放射/倒影/剪影/留白/纵深）。

固定条件：seed=777, steps=35, cfg=1.0, ref_resolution=1024（加速）
提示词一律中文（官方 edit 指南：说明文字跟随用户指令语言）。
"""
import json
import os
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8188"
COMFY_OUT = r"D:\applications\comfy-ui\ComfyUI_windows_portable\ComfyUI\output"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "pose_out")      # tools/ 只退一级
os.makedirs(OUT, exist_ok=True)
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

XIAOMING = "ref_ad9905933f.png"
LANG = "ref_19ed6c27f2.png"

SEED = 777
STEPS = 35
BUDGET = 1024

LANG_OK = ("浅蓝色长发、刘海遮住一只眼的狼耳少女，紫瞳，灰色蝴蝶结发饰和三角发夹，"
           "黑色颈圈，黑色抹胸连衣裙带蓝色描边，大腿蝴蝶结腿环，蓝紫色蓬松大尾巴，"
           "身旁跟着一只小黑猫灵体")
BOY_OK = ("银白色短发带蓝色挑染的小男孩，头顶呆毛和蓝色鲸鱼发夹，白蓝水手领短上衣配蓝色蝴蝶结，"
          "浅蓝牛仔外套，浅蓝短裤配大腿绑带，白色堆堆袜和白色运动鞋")

CASES = [
    # 1 正上方俯拍 + 仰面躺 + 放射散开
    ("P1_俯拍躺冰面", [("image_2", LANG)],
     "<image2> 中的" + LANG_OK + "。"
     "她仰面平躺在结冰的湖面上，长发和大尾巴在身体周围的水面散开成放射状，"
     "双手自然放在身侧，闭着眼睛。镜头从正上方垂直俯拍，画面是干净的几何对称构图，"
     "冰面透出深蓝色的水下裂纹，冷调，柔和均匀的顶光，头顶不出现天空。"),

    # 2 极低仰角 + 腾空跳 + 鲸鱼跃出
    ("P2_仰角腾空跳", [("image_1", XIAOMING)],
     BOY_OK + "，就是这个男孩。"
     "他正从海面腾空跳起，双臂张开，双腿在空中收拢，外套和头发被向上吹起，"
     "镜头放在贴近水面的极低仰角往上拍，他的身体在画面上方形成强烈的对角线动势，"
     "背后一头巨大的鲸鱼正好跃出水面，溅起的水花逆着阳光发亮，"
     "强逆光的海面，明亮高饱和，动感十足。"),

    # 3 背后跟随 + 背影走远 + 纵深
    ("P3_背后走远", [("image_1", XIAOMING), ("image_2", LANG)],
     BOY_OK + "，和 <image2> 中的" + LANG_OK + "。"
     "两人背对镜头并肩往前走在一条覆雪的窄街上，只能看到背影，"
     "他们走远了，在画面中只占很小的比例，街道的消失点落在画面正中央偏上，"
     "两侧是亮着暖黄灯光的橱窗，路灯一排排往远处收拢，飘着雪，"
     "冷蓝夜色，大面积留白，安静而深远。"),

    # 4 大特写 + 只到眼睛 + 极简
    ("P4_眼睛大特写", [("image_2", LANG)],
     "<image2> 中的" + LANG_OK + "。"
     "极特写，画面只切到她的一只紫色眼睛、一小截刘海和一只狼耳的根部，"
     "睫毛和虹膜纹理清晰可见，皮肤有细微的高光，"
     "背景完全虚化成一片干净的浅蓝色，大面积留白，"
     "柔和的侧光，画面极简、安静、有质感。"),

    # 5 框中框 + 侧身探出
    ("P5_框中框探头", [("image_1", XIAOMING), ("image_2", LANG)],
     BOY_OK + "，和 <image2> 中的" + LANG_OK + "。"
     "两人从一扇半开的旧木门后面探出来看向镜头，男孩在下面一点，少女在上面一点，"
     "门框在画面前景形成深色的框，前景的门框是虚化的，两人的脸是清晰的，"
     "门内是昏暗的暖色，门外是明亮的冷色雪光，形成明暗对比，"
     "构图上是框中框，人物偏画面右侧。"),

    # 6 倒影对称 + 站在浅水
    ("P6_水中倒影", [("image_2", LANG)],
     "<image2> 中的" + LANG_OK + "。"
     "她站在只没过脚踝的浅水里，低头看着自己的倒影，"
     "水面几乎静止，倒影和本体上下对称，把画面分成ratio相等的两半，"
     "尾巴垂到水面，尾尖轻触水面泛起一小圈涟漪，"
     "黄昏的橘粉色天空映在水里，冷暖交界，构图严格对称，宁静。"),

    # 7 全剪影逆光
    ("P7_剪影逆光", [("image_1", XIAOMING), ("image_2", LANG)],
     BOY_OK + "，和 <image2> 中的" + LANG_OK + "。"
     "两人并排站在一个巨大的落日正前方，完全逆光，"
     "他们的身体变成纯黑色的剪影，只能看清轮廓：男孩的呆毛、少女的狼耳和蓬松的大尾巴，"
     "太阳在两人中间偏上，光晕把画面染成橙金色，天空有层次分明的云，"
     "地面是暗色的剪影，强烈的高对比，史诗般的氛围。"),

    # 8 低角度 + 抱膝仰头坐
    ("P8_抱膝仰头坐", [("image_2", LANG)],
     "<image2> 中的" + LANG_OK + "。"
     "她蜷坐在地板上，双膝抱在胸前，双手环着膝盖，下巴几乎抵着膝盖，仰起头往上看着什么，"
     "长发自然垂落到地面，尾巴在身侧绕了半圈，"
     "镜头比她的头顶低一些，微微往上仰拍，她的身体在画面左下形成一条斜线，"
     "右上留出大片空旷的冷灰色墙面，单侧顶光把她的轮廓勾出一道亮边，孤独安静。"),
]


def post(path, payload):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=60) as r:
        return json.load(r)


def get(path, timeout=15):
    with OPENER.open(BASE + path, timeout=timeout) as r:
        return json.load(r)


def build(prompt, refs, seed=SEED, steps=STEPS, budget=BUDGET):
    inputs = {"clip": ["2", 0], "prompt": prompt, "negative_prompt": " ",
              "vae": ["3", 0], "resolution": budget}
    wf = {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": "qwen_image_2.1_int8_convrot.safetensors",
                         "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": "qwen3vl_8b_int8_convrot.safetensors",
                         "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader",
              "inputs": {"vae_name": "qwen_image_2.1_vae_bf16.safetensors"}},
        "6": {"class_type": "KSampler",
              "inputs": {"model": ["1", 0], "positive": ["5", 0], "negative": ["5", 1],
                         "latent_image": ["5", 2], "seed": seed, "steps": steps, "cfg": 1.0,
                         "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "pose"}},
    }
    for i, (slot, fn) in enumerate(refs):
        nid = str(10 + i)
        inputs["images.%s" % slot] = [nid, 0]
        wf[nid] = {"class_type": "LoadImage", "inputs": {"image": fn}}
    wf["5"] = {"class_type": "TextEncodeQwenImage21", "inputs": inputs}
    return wf


def run(label, refs, prompt):
    print(f"\n{'=' * 74}\n[{label}]  {len(refs)}张参考图  {len(prompt)}字符")
    wf = build(prompt, refs)
    wf["9"]["inputs"]["filename_prefix"] = "qwen21_pose/" + label
    rec = {"label": label, "prompt": prompt, "chars": len(prompt),
           "image": None, "canvas": None, "elapsed": None, "error": None}
    try:
        resp = post("/prompt", {"prompt": wf, "client_id": "pose"})
    except urllib.error.HTTPError as e:
        rec["error"] = f"HTTP {e.code}"
        print("  提交失败:", e.code, e.read().decode("utf-8", "replace")[:300])
        return rec
    pid = resp.get("prompt_id")
    if not pid:
        rec["error"] = json.dumps(resp, ensure_ascii=False)[:200]
        print("  被拒绝")
        return rec
    t0 = time.time()
    while time.time() - t0 < 1800:
        time.sleep(2)
        e = get(f"/history/{pid}").get(pid)
        if e:
            st = e.get("status", {}).get("status_str")
            if st == "success":
                for o in (e.get("outputs") or {}).values():
                    for im in (o.get("images") or []):
                        rel = os.path.join(im.get("subfolder", ""), im["filename"])
                        src = os.path.join(COMFY_OUT, rel)
                        dst = os.path.join(OUT, label + ".png")
                        if os.path.isfile(src):
                            with open(src, "rb") as fi, open(dst, "wb") as fo:
                                fo.write(fi.read())
                            rec["image"] = dst
                try:
                    from PIL import Image
                    rec["canvas"] = list(Image.open(rec["image"]).size)
                except Exception:
                    pass
                rec["elapsed"] = round(time.time() - t0, 1)
                print(f"  OK {rec['elapsed']}s  {rec['canvas']}")
                return rec
            if st == "error":
                for m in e.get("status", {}).get("messages", []):
                    if isinstance(m, list) and len(m) >= 2 and m[0] == "execution_error":
                        d = m[1] or {}
                        rec["error"] = f"{d.get('node_type')}: {d.get('exception_message')}"
                print("  ERROR:", rec["error"])
                return rec
    rec["error"] = "超时"
    return rec


if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else None
    todo = [c for c in CASES if not only or only in c[0]]
    print(f"共 {len(todo)} 张  seed={SEED} steps={STEPS} 预算={BUDGET}")
    results = []
    for label, refs, prompt in todo:
        results.append(run(label, refs, prompt))
        with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n" + "=" * 74)
    for r in results:
        print(f"  {'OK ' if r['image'] else 'FAIL'} {r['label']:18s} {r['elapsed']}s  {r['canvas']}")
    print("产物:", os.path.abspath(OUT))
