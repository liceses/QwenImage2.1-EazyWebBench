#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验收：局部编辑（标注 → 模型重绘 → 按标注合成回原图）。

判据（硬指标）：
  1. 标注区内**确实变了**（模型重绘生效）
  2. 标注区外**逐点不变**（合成生效，这是"局部"的定义）
  3. 输出尺寸与基准图一致

用法：python tools/diag/accept_local_edit.py [--base <png>]
"""
import json
import os
import struct
import sys
import time
import urllib.request
import urllib.error
import uuid
import zlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WB = "http://127.0.0.1:8642"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))


def read_rgba(path):
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
    rows = []
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
        rows.append(line)
        prev = line
    return w, h, ch, rows


def draw_disc(rows, w, h, cx, cy, r, color=(255, 40, 40)):
    for y in range(max(0, cy - r), min(h, cy + r + 1)):
        for x in range(max(0, cx - r), min(w, cx + r + 1)):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                o = x * 4 if len(rows[y]) >= (x + 1) * 4 else x * 3
                rows[y][o] = color[0]
                rows[y][o + 1] = color[1]
                rows[y][o + 2] = color[2]


def write_rgb(path, w, h, rows):
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw.extend(rows[y][:w * 3])
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += chunk(b"IEND", b"")
    open(path, "wb").write(png)


def post(path, obj):
    req = urllib.request.Request(WB + path, data=json.dumps(obj).encode(),
                                 headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=120) as r:
        return json.loads(r.read().decode())


def get(path):
    with OPENER.open(WB + path, timeout=60) as r:
        return json.loads(r.read().decode())


def upload(path, name):
    b = "----local" + uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\n"
            "Content-Type: image/png\r\n\r\n").encode()
    body += open(path, "rb").read()
    body += f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(WB + "/api/upload", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    with OPENER.open(req, timeout=120) as r:
        return json.loads(r.read().decode())


def wait_job(jid, label, limit=900):
    t0 = time.time()
    last = None
    while time.time() - t0 < limit:
        time.sleep(3)
        p = get(f"/api/progress/{jid}")
        cur = (p.get("status"), p.get("step"))
        if cur != last:
            print(f"    {label}: {p.get('status')} step={p.get('step')}/{p.get('total_steps')}")
            last = cur
        if p.get("status") in ("done", "error", "cancelled"):
            return p
    return {"status": "timeout"}


def main():
    base_rel = None
    for a in sys.argv[1:]:
        if a.startswith("--base="):
            base_rel = a.split("=", 1)[1]
    base = base_rel or os.path.join(ROOT, "outputs", "a060749c9d62", "bd846348_00001_.png")
    if not os.path.exists(base):
        print("基准图不存在:", base)
        return 1
    print(f"基准图: {os.path.relpath(base, ROOT)}")

    w, h, ch, rows = read_rgba(base)
    print(f"  {w}x{h} channels={ch}")

    # 标注：在肚子区域涂一个圆斑（0~1 归一化坐标，与前端一致）
    cxr, cyr, rr = 0.50, 0.60, 0.12
    cx, cy, r = int(w * cxr), int(h * cyr), int(w * rr)
    marked_rows = [bytearray(row) for row in rows]
    if ch == 4:
        # 转成 RGB 再画（丢掉 alpha，模型看到的是不透明标记）
        marked_rows = []
        for row in rows:
            new = bytearray(w * 3)
            for x in range(w):
                new[x * 3] = row[x * 4]
                new[x * 3 + 1] = row[x * 4 + 1]
                new[x * 3 + 2] = row[x * 4 + 2]
            marked_rows.append(new)
    draw_disc(marked_rows, w, h, cx, cy, r)
    marked_png = os.path.join(HERE, "_local_marked.png")
    write_rgb(marked_png, w, h, marked_rows)
    print(f"  已标注: 圆心 ({cxr},{cyr}) 半径 {rr} → {os.path.basename(marked_png)}")

    up = upload(marked_png, "local_marked.png")
    print(f"  上传: {up['name']}")

    # 1) 让模型重绘（标记引导）
    edit_prompt = ("This is an image with a red marking on it. Change ONLY what is inside the red "
                   "marked area: replace it with a big red heart shape. Keep everything outside "
                   "the red marking exactly unchanged, and do not draw the red marking in the output.")
    r1 = post("/api/generate", {
        "prompt": edit_prompt, "negative_prompt": "",
        "width": w, "height": h, "steps": 25, "cfg": 1.0, "seed": 777888,
        "reference_images": [up["name"]],
    })
    print(f"  ① 模型重绘已提交 job_id={r1['job_id']}")
    p1 = wait_job(r1["job_id"], "重绘")
    if p1.get("status") != "done":
        print("  重绘失败:", p1.get("error"))
        return 1

    # 2) 按标注合成回基准图
    strokes = [{"points": [[cxr, cyr]]}]
    merged = post("/api/merge-local", {
        "base_ref": up["name"],
        "edit_job_id": r1["job_id"],
        "strokes": strokes,
        "brush": 0.10,
        "feather": 2,
    })
    print(f"  ② 合成完成 job_id={merged['job_id']} 标注覆盖={merged['masked_ratio'] * 100:.1f}%")
    out_path = os.path.join(ROOT, "outputs", merged["image"])
    if not os.path.exists(out_path):
        print("  合成产物不存在:", out_path)
        return 1

    # ---------- 判定 ----------
    mw, mh, mch, mrows = read_rgba(out_path)
    print(f"\n  合成图: {mw}x{mh} channels={mch}")
    results = {}

    results["size_match"] = (mw, mh) == (w, h)

    # 逐点比对：把 marked_png（RGB）当作基准，只在与标注区比较
    bw, bh, bch, brows = read_rgba(marked_png)
    inside_diff = inside_tot = outside_diff = outside_tot = 0
    for y in range(h):
        for x in range(w):
            in_mask = (x - cx) ** 2 + (y - cy) ** 2 <= r * r
            d = 0
            for k in range(3):
                va = brows[y][x * 3 + k]
                vb = mrows[y][x * mch + k]
                d = max(d, abs(va - vb))
            if in_mask:
                inside_tot += 1
                if d > 8:
                    inside_diff += 1
            else:
                outside_tot += 1
                if d > 8:
                    outside_diff += 1

    in_ratio = inside_diff / max(1, inside_tot)
    out_ratio = outside_diff / max(1, outside_tot)
    print(f"  标注区内变化: {inside_diff}/{inside_tot} = {in_ratio * 100:.1f}%")
    print(f"  标注区外变化: {outside_diff}/{outside_tot} = {out_ratio * 100:.3f}%")
    results["inside_changed"] = in_ratio > 0.30
    results["outside_unchanged"] = out_ratio < 0.002

    print("\n" + "=" * 60)
    print("验收结论")
    print("=" * 60)
    for k, v in results.items():
        print(f"  {k}: {'✅ 通过' if v else '❌ 未通过'}")
    print(f"\n  产物: outputs/{merged['image']}")
    print(f"  带标注的输入: {os.path.relpath(marked_png, ROOT)}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
