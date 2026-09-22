#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验收：透明背景「生成」与「编辑」两条路。

用法：python tools/diag/accept_transparency.py
验收点：
  1) 文生图 + transparent_bg：不手写官方模板，也应由服务端补全并出真透明图
     （期望透明像素占比明显 > 5%，alpha 下探到 0）
  2) 参考图编辑 + transparent_bg：参考图自带 alpha 时，输出应沿用它的 alpha
     （期望透明像素占比与参考图接近）
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


def post_json(path, obj):
    req = urllib.request.Request(WB + path, data=json.dumps(obj).encode(),
                                 headers={"Content-Type": "application/json"})
    with OPENER.open(req, timeout=60) as r:
        return json.loads(r.read().decode())


def get_json(path):
    with OPENER.open(WB + path, timeout=30) as r:
        return json.loads(r.read().decode())


def upload(path, name):
    b = "----acc" + uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\n"
            "Content-Type: image/png\r\n\r\n").encode()
    body += open(path, "rb").read()
    body += f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(WB + "/api/upload", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    with OPENER.open(req, timeout=120) as r:
        return json.loads(r.read().decode())


def wait(jid, label, limit=1200):
    t0 = time.time()
    last = None
    while time.time() - t0 < limit:
        time.sleep(3)
        p = get_json(f"/api/progress/{jid}")
        cur = (p.get("status"), p.get("step"))
        if cur != last:
            print(f"    {label}: {p.get('status')} step={p.get('step')}/{p.get('total_steps')}")
            last = cur
        if p.get("status") in ("done", "error", "cancelled"):
            return p, time.time() - t0
    return {"status": "timeout"}, time.time() - t0


def report(jid, label):
    # 注意：服务端是在 status=done **之后**才扫描产物 alpha 的，所以立刻读有可能读到竞态快照。
    # 这里轮询等 alpha 出现（最多 20 秒），拿不到就用本地统计兜底。
    job = None
    for _ in range(20):
        job = get_json(f"/api/jobs/{jid}")["job"]
        if any(im.get("alpha") for im in (job.get("images") or [])):
            break
        if job.get("status") in ("done", "error") and any(im.get("alpha") for im in (job.get("images") or [])):
            break
        time.sleep(1)
    p = job.get("params") or {}
    print(f"\n  [{label}] status={job['status']} 耗时={job.get('elapsed')}s")
    print(f"    提示词: {p.get('prompt', '')[:110]}")
    print(f"    transparent_bg={p.get('transparent_bg')} ref_has_alpha={p.get('ref_has_alpha')}")
    if job.get("error"):
        print(f"    错误: {job['error'][:500]}")
    ok = False
    for im in job.get("images") or []:
        a = im.get("alpha")
        local = os.path.join(ROOT, "outputs", im["file"])
        if not a and os.path.exists(local):
            a = local_alpha_stats(local)
            if a:
                print("      （接口还没更新，这里用本地统计兜底）")
        print(f"    {im['file']}")
        if a:
            print(f"      mode={a.get('mode')} alpha={a.get('min')}~{a.get('max')} "
                  f"透明像素={a.get('transparent_ratio')} 不透明={a.get('opaque_ratio')}")
            if (a.get("transparent_ratio") or 0) > 0.05:
                ok = True
                im["alpha"] = a
        else:
            print("      （没有 alpha 统计）")
    return ok, job


def local_alpha_stats(path):
    """本地兜底：整图统计 alpha（与 server.png_alpha_stats 同口径）。"""
    d = open(path, "rb").read()
    if d[:8] != b"\x89PNG\r\n\x1a\n":
        return None
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
    if ct not in (4, 6):
        return {"mode": "no-alpha", "min": None, "max": None,
                "transparent_ratio": None, "opaque_ratio": None}
    ch = 4 if ct == 6 else 2
    raw = zlib.decompress(idat)
    stride = w * ch
    prev = bytearray(stride)
    lo, hi, ntr, nop, tot = 255, 0, 0, 0, 0
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
        for x in range(w):
            av = line[x * ch + (ch - 1)]
            lo, hi = min(lo, av), max(hi, av)
            tot += 1
            if av < 16:
                ntr += 1
            elif av > 240:
                nop += 1
        prev = line
    return {"mode": "RGBA" if ct == 6 else "gray+alpha", "min": lo, "max": hi,
            "transparent_ratio": round(ntr / tot, 4), "opaque_ratio": round(nop / tot, 4)}


def make_ref_transparent_png(path, size=1024):
    """造一张"角色不透明 + 背景透明"的参考图（模拟用户抠好图后再编辑）。

    形状固定（不用随机）：中间一个不透明圆 + 一条不透明横带，背景全透明。
    这样验收时可以核对"背景保持透明、角色保留"。
    """
    w = h = size
    cx, cy = w // 2, int(h * 0.42)
    r = int((0.30 * w * h / 3.14159265) ** 0.5)      # 圆面积约占 30%，避免角色过瘦
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            inside = (x - cx) ** 2 + (y - cy) ** 2 <= r * r
            band = abs(y - int(h * 0.85)) <= h // 16   # 横带约占 12%
            if inside or band:
                raw.extend((40, 120, 220, 255))     # 角色：完全不透明
            else:
                raw.extend((0, 0, 0, 0))            # 背景：全透明
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return path


def probe_alpha(path):
    """返回 (透明像素占比, 不透明像素占比)，只看前 256 行。"""
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
    ch = 4 if ct == 6 else 3
    raw = zlib.decompress(idat)
    stride = w * ch
    prev = bytearray(stride)
    ntr = nop = tot = 0
    for y in range(min(h, 256)):
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
        for x in range(w):
            av = line[x * ch + (ch - 1)]
            tot += 1
            if av < 16:
                ntr += 1
            elif av > 240:
                nop += 1
        prev = line
    return round(ntr / max(tot, 1), 3), round(nop / max(tot, 1), 3)


def composite_checkerboard(src, dst, cell=32):
    """把带 alpha 的 PNG 合成到"棋盘格（左半）+ 纯黑（右半）"上，用于肉眼验证透明度。

    棋盘格是最直观的判据：真透明的地方会露出格子，不透明的图则会盖住格子。
    """
    d = open(src, "rb").read()
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
    if ct != 6:
        return None
    raw = zlib.decompress(idat)
    ch = 4
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

    out = bytearray()
    half = w // 2
    for y in range(h):
        out.append(0)
        line = rows[y]
        for x in range(w):
            r, g, b, a = line[x * 4], line[x * 4 + 1], line[x * 4 + 2], line[x * 4 + 3]
            if x < half:
                base = 0x66 if ((x // cell + y // cell) % 2 == 0) else 0x99
            else:
                base = 0x00
            af = a / 255.0
            out.extend((int(r * af + base * (1 - af)),
                        int(g * af + base * (1 - af)),
                        int(b * af + base * (1 - af))))
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(out), 6))
    png += chunk(b"IEND", b"")
    open(dst, "wb").write(png)
    return dst


def main():
    results = {}

    # ---------- 验收 1：文生图 + 透明开关（提示词故意不写模板）----------
    print("=" * 70)
    print("验收 1：文生图 + 透明开关（提示词不写官方模板，看服务端是否自动补全）")
    print("=" * 70)
    r = post_json("/api/generate", {
        "prompt": "一只招手的蓝色鲸鱼娘吉祥物，正面站立",
        "negative_prompt": "", "width": 1024, "height": 1024,
        "steps": 25, "cfg": 1.0, "seed": 424242,
        "transparent_bg": True,
    })
    print(f"  已提交 job_id={r.get('job_id')}")
    p, secs = wait(r["job_id"], "t2i")
    ok1, job1 = report(r["job_id"], "文生图+透明")
    results["t2i_transparent"] = ok1
    results["t2i_prompt_autofilled"] = "This is an RGBA image with transparency" in \
        ((job1.get("params") or {}).get("prompt") or "")

    # ---------- 验收 2：编辑 + 透明（参考图自带 alpha）----------
    print("\n" + "=" * 70)
    print("验收 2：参考图编辑 + 透明开关（参考图 = 角色不透明 + 背景透明）")
    print("=" * 70)
    ref_src = os.path.join(HERE, "_accept_ref_transparent.png")
    make_ref_transparent_png(ref_src)
    tr, op = probe_alpha(ref_src)
    print(f"  已造参考图: {os.path.basename(ref_src)}，透明 {tr * 100:.1f}% / 不透明 {op * 100:.1f}%")
    up = upload(ref_src, "accept_ref_alpha.png")
    print(f"  上传: {json.dumps(up, ensure_ascii=False)[:160]}")

    r2 = post_json("/api/generate", {
        "prompt": "把 <image1> 里的蓝色圆形与横带原样保留，其余一切不变",
        "negative_prompt": "", "width": 1024, "height": 1024,
        "steps": 25, "cfg": 1.0, "seed": 515151,
        "reference_images": [up["name"]],
        "transparent_bg": True,
    })
    print(f"  已提交 job_id={r2.get('job_id')}")
    p2, secs2 = wait(r2["job_id"], "edit")
    ok2, job2 = report(r2["job_id"], "编辑+透明")
    results["edit_transparent"] = ok2
    print(f"    ref_has_alpha={((job2.get('params') or {}).get('ref_has_alpha'))}"
          "（应为 True：参考图有不透明主体，才会走『沿用参考图 alpha』的接线）")
    # 编辑路径必须"既保留角色、又保持背景透明"
    for im in (job2.get("images") or []):
        a = im.get("alpha") or {}
        if a.get("opaque_ratio") is not None:
            results["edit_keeps_opaque_subject"] = a["opaque_ratio"] > 0.05
            print(f"    不透明像素占比 = {a['opaque_ratio']}（参考图为 {op}，应接近且 > 0.05）")

    print("\n" + "=" * 70)
    print("验收结论")
    print("=" * 70)
    for k, v in results.items():
        print(f"  {k}: {'✅ 通过' if v else '❌ 未通过'}")

    # 造肉眼可验证的对照图：棋盘格(左半) + 纯黑(右半)
    print()
    for label, job in (("文生图", job1), ("编辑", job2)):
        for im in (job.get("images") or []):
            src = os.path.join(ROOT, "outputs", im["file"])
            if not os.path.exists(src):
                continue
            dst = os.path.join(ROOT, "示例效果", f"透明背景-{label}-对照.png")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if composite_checkerboard(src, dst):
                print(f"  已生成肉眼对照图（左半棋盘格 / 右半纯黑）：{os.path.relpath(dst, ROOT)}")
            break
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
