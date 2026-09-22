#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""实测「圈选 / 涂抹引导的局部编辑」：把标记画在参考图上，模型认不认。

为什么测这个：Qwen-Image-2.1 官方 README 写
  "specify local edits via circles, painted annotations, or separate masks"
且 Showcase 标题是 "Circle-guided multi-region editing"。
但 **diffusers 的 QwenImage21Pipeline.__call__ 没有任何 mask 参数**
（只有 prompt / image / height / width / steps / sigmas / generator / latents / ...）。
所以最可能的机制是**视觉提示**：标记画在条件图上，由 Qwen3-VL 视觉编码器读进去。
—— 那是"接得上"的路：工作台只要能在参考图上画圈即可，无需任何掩码 API。

做法：拿一张已有产物 → 在"要改的区域"画红圈 → 上传 → prompt 指明"红圈里的东西改成 X"
      → 看输出是否"只改了圈内"。

用法：python tools/diag/diag_circle_edit.py [底图路径]
"""
import json
import os
import struct
import sys
import time
import urllib.request
import uuid
import zlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WB = "http://127.0.0.1:8642"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))


# ---------- 最小 PNG 读写（只依赖标准库）----------
def read_png(path):
    d = open(path, "rb").read()
    pos, w, h, ct, idat = 8, None, None, None, b""
    while pos + 12 <= len(d):
        ln = struct.unpack(">I", d[pos:pos + 4])[0]
        tag = d[pos + 4:pos + 8]
        body = d[pos + 8:pos + 8 + ln]
        if tag == b"IHDR":
            w, h, _, ct = struct.unpack(">IIBB", body[:10])
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break
        pos += 12 + ln
    ch = {0: 1, 2: 3, 4: 2, 6: 4}[ct]
    raw = zlib.decompress(idat)
    stride = w * ch
    prev = bytearray(stride)
    px = []
    for y in range(h):
        off = y * (stride + 1)
        f = raw[off]
        line = bytearray(raw[off + 1: off + 1 + stride])
        for i in range(stride):
            a = line[i - ch] if i >= ch else 0
            b = prev[i]
            c = prev[i - ch] if i >= ch else 0
            if f == 1:
                pr = a
            elif f == 2:
                pr = b
            elif f == 3:
                pr = (a + b) // 2
            elif f == 4:
                pp = a + b - c
                pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
            else:
                pr = 0
            line[i] = (line[i] + pr) & 0xFF
        px.append(line)
        prev = line
    return w, h, ch, px


def write_rgb_png(path, w, h, px):
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw.extend(px[y])
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += chunk(b"IEND", b"")
    open(path, "wb").write(png)


def draw_circle(px, w, h, cx, cy, r, thickness=8, color=(255, 0, 0)):
    """在 RGB 像素缓冲上画一个圆环。"""
    for y in range(max(0, cy - r - thickness), min(h, cy + r + thickness + 1)):
        for x in range(max(0, cx - r - thickness), min(w, cx + r + thickness + 1)):
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if abs(d - r) <= thickness:
                px[y][x * 3] = color[0]
                px[y][x * 3 + 1] = color[1]
                px[y][x * 3 + 2] = color[2]


def draw_disc(px, w, h, cx, cy, r, color=(255, 40, 40)):
    """在 RGB 像素缓冲上涂一个实心圆斑（模拟"画笔涂抹"标注）。"""
    for y in range(max(0, cy - r), min(h, cy + r + 1)):
        for x in range(max(0, cx - r), min(w, cx + r + 1)):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                px[y][x * 3] = color[0]
                px[y][x * 3 + 1] = color[1]
                px[y][x * 3 + 2] = color[2]


def upload(path, name):
    b = "----circ" + uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\n"
            "Content-Type: image/png\r\n\r\n").encode()
    body += open(path, "rb").read()
    body += f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(WB + "/api/upload", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    with OPENER.open(req, timeout=120) as r:
        return json.loads(r.read().decode())


def wait(jid, limit=900):
    t0 = time.time()
    last = None
    while time.time() - t0 < limit:
        time.sleep(3)
        try:
            with OPENER.open(f"{WB}/api/progress/{jid}", timeout=30) as r:
                p = json.loads(r.read().decode())
        except Exception:
            continue
        cur = (p.get("status"), p.get("step"))
        if cur != last:
            print(f"    {p.get('status')} step={p.get('step')}/{p.get('total_steps')}")
            last = cur
        if p.get("status") in ("done", "error", "cancelled"):
            return p
    return {"status": "timeout"}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    base = args[0] if args else os.path.join(ROOT, "outputs", "a060749c9d62", "bd846348_00001_.png")
    # 圈的位置/半径（相对宽高的比例），可用 --circle cx,cy,r 覆盖
    cxr, cyr, rr = 0.42, 0.33, 0.13
    for a in sys.argv[1:]:
        if a.startswith("--circle="):
            parts = a.split("=", 1)[1].split(",")
            cxr, cyr, rr = (float(v) for v in parts)
    want = "golden yellow"
    for a in sys.argv[1:]:
        if a.startswith("--want="):
            want = a.split("=", 1)[1]
    inside = "the eye"
    for a in sys.argv[1:]:
        if a.startswith("--inside="):
            inside = a.split("=", 1)[1]

    if not os.path.exists(base):
        print("底图不存在:", base)
        return 1
    print(f"底图: {os.path.relpath(base, ROOT)}")

    w, h, ch, px = read_png(base)
    print(f"  {w}x{h} channels={ch}")
    if ch not in (3, 4):
        print(f"  只支持 3/4 通道 PNG，当前 {ch} 通道")
        return 1

    # 转成 RGB（丢掉 alpha），再画圈 —— 避免 alpha 干扰 Qwen3-VL 的视觉编码
    rgb = []
    for line in px:
        row = bytearray(w * 3)
        for x in range(w):
            row[x * 3] = line[x * ch]
            row[x * 3 + 1] = line[x * ch + 1]
            row[x * 3 + 2] = line[x * ch + 2]
        rgb.append(row)

    marked = os.path.join(HERE, "_circle_marked.png")
    mode = "ring"
    for a in sys.argv[1:]:
        if a.startswith("--mode="):
            mode = a.split("=", 1)[1]
    if mode == "disc":
        # 涂抹：用实心圆斑标注（模拟画笔），并把标记色写成"半透明红"观感（直接实心红更稳）
        draw_disc(rgb, w, h, cx=int(w * cxr), cy=int(h * cyr), r=int(w * rr))
        print(f"  已涂实心圆斑 -> {os.path.basename(marked)}（模拟画笔涂抹标注）")
    else:
        draw_circle(rgb, w, h, cx=int(w * cxr), cy=int(h * cyr), r=int(w * rr), thickness=10)
        print(f"  已画红圈 -> {os.path.basename(marked)}"
              f"（圆心 ({cxr:.2f}, {cyr:.2f}) 半径 {rr:.2f} × 宽）")
    write_rgb_png(marked, w, h, rgb)

    up = upload(marked, "circle_marked.png")
    print(f"  上传: {up.get('name')}")

    prompt = (f"Change only what is inside the red circle: make {inside} inside the red circle "
              f"{want}. Keep everything outside the red circle exactly unchanged, "
              f"and do not draw the red circle in the output.")
    body = {
        "prompt": prompt,
        "negative_prompt": "",
        "width": w, "height": h,
        "steps": 25, "cfg": 1.0, "seed": 313131,
        "reference_images": [up["name"]],
    }
    req = urllib.request.Request(WB + "/api/generate", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=60) as r:
        res = json.loads(r.read().decode())
    print(f"  已提交 job_id={res.get('job_id')}")
    p = wait(res["job_id"])
    print(f"  最终: status={p.get('status')} elapsed={p.get('elapsed')}s error={p.get('error')}")

    job = json.loads(OPENER.open(f"{WB}/api/jobs/{res['job_id']}", timeout=30).read().decode())["job"]
    out = None
    for im in job.get("images") or []:
        print(f"  产物: {im['file']}")
        out = im["file"]
    print(f"\n对照检查：\n  底图(已画圈): {os.path.relpath(marked, ROOT)}")
    print(f"  产物: outputs/{out}")
    print("人工看三点：圈内是否变了 / 圈外是否原样 / 红圈有没有被画进画面。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
