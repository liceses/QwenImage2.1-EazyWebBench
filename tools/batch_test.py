#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量抽卡 + 提示词形式对照实验。

受控条件（全部固定，只变提示词）：seed=777, steps=35, cfg=1.0,
ref_resolution=1024（加速），euler/simple。
唯一变量 = 提示词的长度 / 形式 / 风格。

参考图：
  XIAOMING = ref_ad9905933f.png  小名（816x1216, ratio 0.671）
  LANG     = ref_19ed6c27f2.png  狼娘（945x1562, ratio 0.605）
画布比例跟随 <image1>。
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
OUT = os.path.join(HERE, "..", "..", "batch_out")
os.makedirs(OUT, exist_ok=True)
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

XIAOMING = "ref_ad9905933f.png"
LANG = "ref_19ed6c27f2.png"

SEED = 777
STEPS = 35
BUDGET = 1024

# ---------------------------------------------------------------- 提示词矩阵
# 变量轴：长度(短/中/长/超长) × 形式(标签/叙述/结构化/官方观察式) × 风格跨度

OFFICIAL_LONG = (
    "The image is a vertical anime illustration of a young woman with light blue hair, "
    "standing against a flat pale lime-green wall lit by soft even daylight. "
    "The wall fills the upper two thirds of the frame and holds almost no detail. "
    "In the upper-left of the frame, two blue wolf ears rise above her hair, each tied with a small grey bow, "
    "and a tiny triangle hair clip sits just right of centre above her brow. "
    "Her long light blue hair falls past her shoulders through the centre of the frame, "
    "one thick fringe hanging over her left eye. "
    "A slim black choker sits centred on her neck just below the jawline. "
    "On the right side of the frame a large fluffy tail with a purple gradient sweeps out horizontally, "
    "its tip reaching toward the right edge. "
    "She wears a black strapless mini dress that occupies the centre and lower middle of the frame, "
    "its upper edge marked by a thin blue trim line, the fabric reading as a soft matte synthetic "
    "with a faint sheen along the highlights. "
    "Both arms bend inward toward the centre of the frame, and her hands hold a small pale disc "
    "just in front of her waist. Below the hem, bow-shaped garter bands wrap both thighs across the lower third. "
    "Her legs continue to the bottom edge, ending in black high-heeled shoes planted at the base of the frame. "
    "In the upper right, just beside her shoulder, a small black cat-like spirit hovers in the air. "
    "Her expression appears calm and slightly distant, eyes fixed forward, cheeks faintly flushed. "
    "The lighting is soft and even, arriving from the front and slightly above, "
    "leaving gentle shadows beneath the chin, under the dress hem and along the inner edges of her legs. "
    "The overall composition is centred and near-symmetrical, built on a cool blue palette "
    "against a pale green ground, with clean linework, soft cel shading and a quiet, mildly aloof mood."
)

CASES = [
    # ---- 长度 / 形式对照（同角色、同场景意图）----
    ("L1_极简中文", [("image_2", LANG)],
     "<image2> 特写，微笑，柔光"),

    ("L2_英文标签加质量词", [("image_2", LANG)],
     "<image2>, 1girl, wolf ears, light blue hair, black strapless dress, smile, looking at viewer, "
     "masterpiece, best quality, ultra detailed, 8k, sharp focus, studio lighting"),

    ("L3_中文中长叙述", [("image_2", LANG)],
     "<image2> 站在一面浅黄绿色的墙前，正对着镜头，露出安静而略带距离感的浅笑。"
     "窗外来的柔光从正前方偏上打下来，在下巴和裙摆下方留出淡淡的阴影。"
     "她的蓝紫色大尾巴向画面右侧水平铺开，尾尖几乎碰到画框右缘。"),

    ("L4_官方观察式长英文", [("image_2", LANG)], OFFICIAL_LONG),

    ("L5_中文结构化分块", [("image_2", LANG)],
     "【主体】<image2>\n"
     "【构图】半身特写，人物位于画面中央略偏右，头顶留一点空间\n"
     "【姿态】微微侧头，一只手抬起靠近脸侧，尾巴在身后向左侧铺开\n"
     "【服装】黑色抹胸连衣裙，蓝色描边，黑色颈圈，大腿蝴蝶结腿环\n"
     "【背景】浅灰蓝到淡青的柔和渐变，干净无杂物\n"
     "【光线】左前方柔光为主，右后方补一道冷色轮廓光，头发边缘有细亮边\n"
     "【色调】低饱和冷蓝为主，肤色一点点暖，形成冷暖对比\n"
     "【风格】日系动画，干净线稿，赛璐璐上色，浅景深"),

    # ---- 风格跨度 ----
    ("S1_厚涂油画", [("image_2", LANG)],
     "<image2> 的古典风格油画肖像，厚涂笔触，可见画布纹理，伦勃朗式单侧光，"
     "深褐色的暗背景，光只照亮半张脸、一侧肩头和尾巴的一小段，"
     "颜料堆积厚重，边缘有刮刀痕迹，像美术馆里的旧藏品"),

    ("S2_极简留白封面", [("image_2", LANG)],
     "<image2> 立于画面下方的三分之一处，头顶是大面积干净的留白，"
     "极简构图，大量负空间，低饱和冷调，时尚杂志封面感，安静克制"),

    ("S3_水墨", [("image_2", LANG)],
     "<image2> 用中国水墨画法绘制，大写意笔触，墨色浓淡分明，"
     "宣纸纤维和晕染痕迹清晰，只保留极少量的淡蓝色，大面积留白，"
     "尾巴用一笔拖出的飞白表现，落款印章在左下角"),

    # ---- 双人 / 官方多图句式 ----
    ("M1_双人官方句式", [("image_1", XIAOMING), ("image_2", LANG)],
     "将<image1>中的人物和<image2>中的人物置入一个夏日傍晚的海边浅滩场景中，"
     "生成一张两人并排站在浅水里的合影。保持两位人物的面部特征、发型和服装外观完全不变。"),

    ("M2_双人长叙述", [("image_1", XIAOMING), ("image_2", LANG)],
     "傍晚退潮的海边，海水只到脚踝，天空是橘粉和蓝紫交界的暮色。"
     "<image1> 的男孩卷起裤脚站在浅水里，回头看向身边的少女，脸颊有点红；"
     "<image2> 的狼耳少女站在他侧后方，尾巴垂在湿沙上，正低头看着他，神情温柔。"
     "两人的倒影落在被水浸亮的海滩上，远处是低平的礁石剪影。"
     "动漫插画，暖色暮光与冷色海面对比，宁静的傍晚氛围。"),
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
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "batch"}},
    }
    for i, (slot, fn) in enumerate(refs):
        nid = str(10 + i)
        inputs["images.%s" % slot] = [nid, 0]
        wf[nid] = {"class_type": "LoadImage", "inputs": {"image": fn}}
    wf["5"] = {"class_type": "TextEncodeQwenImage21", "inputs": inputs}
    return wf


def run(label, refs, prompt):
    print(f"\n{'=' * 74}\n[{label}]  参考图 {len(refs)} 张  提示词 {len(prompt)} 字符")
    print(f"  {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    wf = build(prompt, refs)
    wf["9"]["inputs"]["filename_prefix"] = "qwen21_batch/" + label
    rec = {"label": label, "prompt": prompt, "refs": [r[1] for r in refs],
           "chars": len(prompt), "image": None, "canvas": None, "elapsed": None, "error": None}
    try:
        resp = post("/prompt", {"prompt": wf, "client_id": "batch"})
    except urllib.error.HTTPError as e:
        rec["error"] = f"HTTP {e.code}: {e.read().decode('utf-8','replace')[:300]}"
        print("  提交失败:", rec["error"])
        return rec
    pid = resp.get("prompt_id")
    if not pid:
        rec["error"] = json.dumps(resp, ensure_ascii=False)[:300]
        print("  被拒绝:", rec["error"])
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
                print(f"  OK {rec['elapsed']}s  画布 {rec['canvas']}")
                return rec
            if st == "error":
                for m in e.get("status", {}).get("messages", []):
                    if isinstance(m, list) and len(m) >= 2 and m[0] == "execution_error":
                        d = m[1] or {}
                        rec["error"] = f"{d.get('node_type')}: {d.get('exception_type')} {d.get('exception_message')}"
                print("  ERROR:", rec["error"])
                return rec
    rec["error"] = "超时"
    print("  超时")
    return rec


if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else None
    todo = [c for c in CASES if not only or only in c[0]]
    print(f"共 {len(todo)} 张  固定 seed={SEED} steps={STEPS} 预算={BUDGET}  cfg=1.0")
    results = []
    for label, refs, prompt in todo:
        results.append(run(label, refs, prompt))
        with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n" + "=" * 74)
    print("汇总")
    print("=" * 74)
    for r in results:
        st = "OK " if r["image"] else "FAIL"
        print(f"  {st} {r['label']:22s} {r['chars']:5d}字符  {r['elapsed']}s  {r['canvas']}")
    print("\n产物目录:", os.path.abspath(OUT))
