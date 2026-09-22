#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qwen-Image-2.1 本地工作台 —— 后端服务

职责：
  1. 启动时检查三件套权重是否就位（缺失/大小不符时给出明确的中文提示）
  2. 按需拉起本机 ComfyUI（127.0.0.1:8188），复用其已有的 PyTorch 环境，不重复下载
  3. 提供 HTTP API：配置查询 / 出图提交 / 进度查询 / 图片读取 / 参考图上传
  4. 通过 WebSocket 订阅 ComfyUI 的实时执行进度，转成前端可显示的百分比

只用标准库，不引入任何第三方依赖（复用 ComfyUI 便携版解释器即可运行）。
"""
import argparse
import json
import mimetypes
import os
import queue
import socket
import struct
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ---------------------------------------------------------------- 路径与常量

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(HERE, "models")
OUTPUT_DIR = os.path.join(HERE, "outputs")
UPLOAD_DIR = os.path.join(HERE, "uploads")
WEB_DIR = os.path.join(HERE, "web")

COMFY_HOST = "127.0.0.1"
COMFY_PORT = 8188
COMFY_BASE = f"http://{COMFY_HOST}:{COMFY_PORT}"


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------- ComfyUI 定位
# 为了让本项目可以分享给别人运行，ComfyUI 路径不做硬编码。
# 解析顺序：环境变量 QWEN21_COMFY_ROOT → 项目内 config.json 的 comfy_root →
#          常见安装位置自动探测 → 项目内的 ComfyUI/ 目录。
CONFIG_FILE = os.path.join(HERE, "config.json")

# 常见 ComfyUI 安装位置（按便携版优先，因为便携版自带匹配的 PyTorch）
COMFY_CANDIDATES = [
    r"D:\applications\comfy-ui\ComfyUI_windows_portable",
    r"C:\ComfyUI_windows_portable",
    r"D:\ComfyUI_windows_portable",
    r"C:\ComfyUI",
    r"D:\ComfyUI",
    os.path.join(HERE, "ComfyUI"),
    os.path.expanduser(r"~\ComfyUI_windows_portable"),
    os.path.expanduser(r"~\Desktop\ComfyUI_windows_portable"),
    os.path.expanduser(r"~\Documents\ComfyUI_windows_portable"),
    r"C:\Program Files\ComfyUI",
]


def _looks_like_comfy_root(p):
    """判断一个目录是不是 ComfyUI 根（含 ComfyUI/main.py）。"""
    return bool(p) and os.path.isfile(os.path.join(p, "ComfyUI", "main.py"))


def _read_config_comfy_root():
    try:
        if os.path.isfile(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            v = (cfg or {}).get("comfy_root")
            if v:
                return os.path.expanduser(str(v))
    except Exception as e:
        log(f"读取 config.json 失败（忽略）：{type(e).__name__} {e}")
    return None


def resolve_comfy_root():
    """按优先级找出可用的 ComfyUI 根目录；找不到返回 None。"""
    env = os.environ.get("QWEN21_COMFY_ROOT", "").strip()
    if env:
        p = os.path.expanduser(env)
        if _looks_like_comfy_root(p):
            return p, "环境变量 QWEN21_COMFY_ROOT"
        log(f"环境变量 QWEN21_COMFY_ROOT 指向的目录不像 ComfyUI 根：{p}")
    cfg = _read_config_comfy_root()
    if cfg:
        if _looks_like_comfy_root(cfg):
            return cfg, "config.json 的 comfy_root"
        log(f"config.json 的 comfy_root 不像 ComfyUI 根：{cfg}")
    for cand in COMFY_CANDIDATES:
        if _looks_like_comfy_root(cand):
            return cand, "自动探测"
    return None, "未找到"


COMFY_ROOT, COMFY_ROOT_SOURCE = resolve_comfy_root()
if COMFY_ROOT:
    COMFY_PY = os.path.join(COMFY_ROOT, "python_embeded", "python.exe")
    if not os.path.isfile(COMFY_PY):
        # 非便携版：用当前解释器去跑 ComfyUI
        COMFY_PY = sys.executable
    COMFY_MAIN = os.path.join(COMFY_ROOT, "ComfyUI", "main.py")
    COMFY_OUTPUT = os.path.join(COMFY_ROOT, "ComfyUI", "output")
    COMFY_INPUT = os.path.join(COMFY_ROOT, "ComfyUI", "input")
    COMFY_MODELS = os.path.join(COMFY_ROOT, "ComfyUI", "models")
else:
    COMFY_PY = COMFY_MAIN = COMFY_OUTPUT = COMFY_INPUT = COMFY_MODELS = None

# 三件套权重（文件名 -> (相对 models 的子目录, 官方字节数)）
REQUIRED_MODELS = {
    "transformer": (
        "diffusion_models/qwen_image_2.1_int8_convrot.safetensors", 7256783064,
        "去噪主干 (Transformer)", "models/diffusion_models/",
        "https://hf-mirror.com/Comfy-Org/Qwen-Image-2.1/resolve/main/diffusion_models/qwen_image_2.1_int8_convrot.safetensors",
    ),
    "text_encoder": (
        "text_encoders/qwen3vl_8b_int8_convrot.safetensors", 9350798360,
        "文本编码器 (Qwen3-VL-8B)", "models/text_encoders/",
        "https://hf-mirror.com/Comfy-Org/Qwen-Image-2.1/resolve/main/text_encoders/qwen3vl_8b_int8_convrot.safetensors",
    ),
    "vae": (
        "vae/qwen_image_2.1_vae_bf16.safetensors", 675509688,
        "VAE 解码器", "models/vae/",
        "https://hf-mirror.com/Comfy-Org/Qwen-Image-2.1/resolve/main/vae/qwen_image_2.1_vae_bf16.safetensors",
    ),
}

# 官方工作流默认值（来源: Comfy-Org/workflow_templates image_qwen_image_2_1_t2i.json 的 subgraph）
DEFAULTS = {
    "steps": 25,
    "cfg": 1.0,
    "width": 1024,
    "height": 1024,
    "sampler_name": "euler",
    "scheduler": "simple",
    "denoise": 1.0,
    # 官方 image-edit 模板的 resolution 默认是 0：参考图只对齐到 32 的倍数，
    # 不做像素预算缩放，保真度最高，画布比例跟随参考图。
    # 设为 1024/2048 则按"总像素预算"缩放参考图（省显存，但细节有损）。
    "ref_resolution": 0,
}

# 官方支持的比例（1:1 / 4:3 / 3:4 / 3:2 / 2:3 / 16:9 / 9:16），本机按 1024 档提供
ASPECT_PRESETS = [
    {"label": "1:1 方形 (1024×1024)", "width": 1024, "height": 1024},
    {"label": "4:3 横版 (1152×896)", "width": 1152, "height": 896},
    {"label": "3:4 竖版 (896×1152)", "width": 896, "height": 1152},
    {"label": "3:2 横版 (1248×832)", "width": 1248, "height": 832},
    {"label": "2:3 竖版 (832×1248)", "width": 832, "height": 1248},
    {"label": "16:9 宽屏 (1344×768)", "width": 1344, "height": 768},
    {"label": "9:16 竖屏 (768×1344)", "width": 768, "height": 1344},
    {"label": "官方原生 2K 1:1 (2048×2048)", "width": 2048, "height": 2048},
]

MAX_SIDE = 4096          # 与官方节点 resolution 上限一致
SIZE_STEP = 32           # 官方要求 32 的倍数
HTTP_TIMEOUT = 30
GENERATE_TIMEOUT = 1800  # 单张出图最长等待 30 分钟

# ---------------------------------------------------------------- 全局状态

STATE_LOCK = threading.Lock()
JOBS = {}                 # job_id -> dict
JOBS_ORDER = []           # 提交顺序，用于历史
ACTIVE_JOB = {"id": None} # 同时只允许一个推理任务
COMFY_PROC = {"proc": None, "started_by_us": False}
COMFY_READY = {"ok": False, "detail": ""}


# ---------------------------------------------------------------- ComfyUI 交互

def http_json(url, payload=None, timeout=HTTP_TIMEOUT):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    # 本机回环地址，必须绕过任何代理设置
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=timeout) as r:
        body = r.read()
        return json.loads(body) if body else {}


def comfy_alive(timeout=3):
    try:
        http_json(f"{COMFY_BASE}/system_stats", timeout=timeout)
        return True
    except Exception:
        return False


def ensure_comfy(timeout=240):
    """确保 ComfyUI 在 8188 上可用；必要时由本工作台拉起。"""
    if comfy_alive():
        with STATE_LOCK:
            COMFY_READY["ok"] = True
            COMFY_READY["detail"] = "复用已在运行的 ComfyUI"
        log("检测到已在运行的 ComfyUI，直接复用")
        return True

    if not COMFY_ROOT:
        msg = (
            "未找到 ComfyUI 安装目录。请任选一种方式配置：\n"
            f"  1) 在本项目目录新建 config.json，内容：{{\"comfy_root\": \"<你的ComfyUI根目录>\"}}\n"
            "  2) 设置环境变量 QWEN21_COMFY_ROOT=<你的ComfyUI根目录>\n"
            "「ComfyUI 根目录」指包含 ComfyUI/main.py 的那一层"
            "（便携版形如 ...\\ComfyUI_windows_portable）。\n"
            "若 ComfyUI 已在运行，本项可忽略（工作台会直接连 127.0.0.1:8188）。"
        )
        with STATE_LOCK:
            COMFY_READY["ok"] = False
            COMFY_READY["detail"] = msg
        return False

    if not os.path.isfile(COMFY_PY) or not os.path.isfile(COMFY_MAIN):
        with STATE_LOCK:
            COMFY_READY["ok"] = False
            COMFY_READY["detail"] = (
                f"找不到 ComfyUI 可执行文件：{COMFY_MAIN}\n"
                f"（当前 ComfyUI 根目录来自：{COMFY_ROOT_SOURCE} = {COMFY_ROOT}）"
            )
        return False

    log(f"未检测到 ComfyUI，正在拉起：{COMFY_MAIN}")
    env = dict(os.environ)
    env.pop("HTTP_PROXY", None)
    env.pop("HTTPS_PROXY", None)
    env.pop("http_proxy", None)
    env.pop("https_proxy", None)
    creationflags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
    try:
        p = subprocess.Popen(
            [COMFY_PY, "-s", COMFY_MAIN, "--port", str(COMFY_PORT)],
            cwd=COMFY_ROOT, env=env, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, creationflags=creationflags,
        )
    except Exception as e:
        with STATE_LOCK:
            COMFY_READY["ok"] = False
            COMFY_READY["detail"] = f"拉起 ComfyUI 失败：{type(e).__name__} {e}"
        return False

    with STATE_LOCK:
        COMFY_PROC["proc"] = p
        COMFY_PROC["started_by_us"] = True

    t0 = time.time()
    while time.time() - t0 < timeout:
        if p.poll() is not None:
            with STATE_LOCK:
                COMFY_READY["ok"] = False
                COMFY_READY["detail"] = f"ComfyUI 进程已退出（返回码 {p.returncode}）"
            return False
        if comfy_alive():
            with STATE_LOCK:
                COMFY_READY["ok"] = True
                COMFY_READY["detail"] = "已由工作台拉起 ComfyUI"
            log(f"ComfyUI 就绪，用时 {time.time() - t0:.1f}s")
            return True
        time.sleep(2)

    with STATE_LOCK:
        COMFY_READY["ok"] = False
        COMFY_READY["detail"] = f"ComfyUI 启动超时（>{timeout}s）"
    return False


def ensure_model_links():
    """
    把工作台 models/ 下的权重挂到 ComfyUI 的模型目录。

    优先用硬链接（同盘，零额外空间）；失败则退回复制。
    这样权重只需在项目里保存一份，ComfyUI 也能直接看到。
    """
    if not COMFY_MODELS:
        log("未配置 ComfyUI 目录，跳过权重挂载"
            "（若 ComfyUI 已单独运行，请自行把权重放进它的 models/ 下）")
        return False
    linked, copied, failed = [], [], []
    for key, (relpath, expect, label, _target_dir, _url) in REQUIRED_MODELS.items():
        src = os.path.join(MODELS_DIR, relpath)
        if not os.path.exists(src) or os.path.getsize(src) != expect:
            continue
        dst_dir = os.path.join(COMFY_MODELS, os.path.dirname(relpath))
        dst = os.path.join(COMFY_MODELS, relpath)
        os.makedirs(dst_dir, exist_ok=True)
        if os.path.exists(dst) and os.path.getsize(dst) == expect:
            continue
        if os.path.exists(dst):
            try:
                os.remove(dst)
            except Exception:
                pass
        try:
            os.link(src, dst)          # 硬链接：同盘零拷贝
            linked.append(os.path.basename(relpath))
        except Exception:
            try:
                import shutil
                shutil.copy2(src, dst)  # 跨盘时退化为复制
                copied.append(os.path.basename(relpath))
            except Exception as e:
                failed.append(f"{os.path.basename(relpath)}: {e}")

    if linked:
        log(f"已硬链接到 ComfyUI（零额外空间）: {', '.join(linked)}")
    if copied:
        log(f"已复制到 ComfyUI: {', '.join(copied)}")
    for f in failed:
        log(f"警告：挂载失败 {f}")
    return not failed


def check_models():
    """返回三件套权重的就位情况。"""
    out = {}
    all_ok = True
    for key, (relpath, expect, label, target_dir, url) in REQUIRED_MODELS.items():
        path = os.path.join(MODELS_DIR, relpath)
        info = {
            "label": label,
            "filename": os.path.basename(relpath),
            "expected_dir": target_dir,
            "path": path,
            "expected_bytes": expect,
            "url": url,
        }
        if not os.path.exists(path):
            info["status"] = "missing"
            info["message"] = f"缺少 {label}：未找到 {os.path.basename(relpath)}，应放在 {target_dir}"
            all_ok = False
        else:
            actual = os.path.getsize(path)
            info["actual_bytes"] = actual
            if actual != expect:
                info["status"] = "size_mismatch"
                info["message"] = (
                    f"{label} 文件大小不符：实际 {actual} 字节，应为 {expect} 字节"
                    f"（{actual / 1e9:.2f}GB / 期望 {expect / 1e9:.2f}GB），可能未下载完整，请重新下载"
                )
                all_ok = False
            else:
                info["status"] = "ok"
                info["message"] = f"{label} 就绪（{actual / 1e9:.2f}GB）"
        out[key] = info
    return all_ok, out


# ---------------------------------------------------------------- ComfyUI WebSocket 客户端

class ComfyWS(threading.Thread):
    """极简 WebSocket 客户端，用于接收 ComfyUI 的执行进度与预览图。"""

    def __init__(self, client_id, on_message):
        super().__init__(daemon=True)
        self.client_id = client_id
        self.on_message = on_message
        self.sock = None
        self.running = False

    def connect(self):
        s = socket.create_connection((COMFY_HOST, COMFY_PORT), timeout=15)
        key = uuid.uuid4().bytes
        import base64
        b64 = base64.b64encode(key).decode()
        req = (
            f"GET /ws?clientId={self.client_id} HTTP/1.1\r\n"
            f"Host: {COMFY_HOST}:{COMFY_PORT}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {b64}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        s.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = s.recv(4096)
            if not chunk:
                raise ConnectionError("WebSocket 握手期间连接被关闭")
            buf += chunk
        if b"101" not in buf.split(b"\r\n")[0]:
            raise ConnectionError(f"WebSocket 握手失败: {buf.split(chr(13).encode())[0]!r}")
        self.sock = s

    def run(self):
        self.running = True
        try:
            self.connect()
        except Exception as e:
            log(f"WebSocket 连接失败（不影响出图，仅无实时进度）: {e}")
            return
        try:
            while self.running:
                frame = self._read_frame()
                if frame is None:
                    break
                opcode, payload = frame
                if opcode == 0x1:
                    try:
                        self.on_message(json.loads(payload.decode("utf-8", "replace")))
                    except Exception:
                        pass
                elif opcode == 0x8:
                    break
        except Exception:
            pass

    def _read_frame(self):
        def recvn(n):
            buf = b""
            while len(buf) < n:
                c = self.sock.recv(n - len(buf))
                if not c:
                    return None
                buf += c
            return buf

        hdr = recvn(2)
        if not hdr:
            return None
        b1, b2 = hdr[0], hdr[1]
        opcode = b1 & 0x0F
        masked = b2 & 0x80
        length = b2 & 0x7F
        if length == 126:
            ext = recvn(2)
            if not ext:
                return None
            length = struct.unpack(">H", ext)[0]
        elif length == 127:
            ext = recvn(8)
            if not ext:
                return None
            length = struct.unpack(">Q", ext)[0]
        mask = recvn(4) if masked else None
        if mask is None and masked:
            return None
        payload = recvn(length) if length else b""
        if payload is None:
            return None
        if masked and mask:
            payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        return opcode, payload

    def stop(self):
        self.running = False
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass


# ---------------------------------------------------------------- 透明通道（RGBA）

# 官方透明图提示词固定句式（模型页 README「Native Transparency」）：
#   "This is an RGBA image with transparency. <描述>. The image has alpha channel
#    and the background is transparent."
# 实测：不写这句，模型出的是全不透明图（alpha 恒为 252~255 的 VAE 噪声）；
# 写了这句，alpha 会真的落到 0（本机实测 71.9% 像素透明）。
TRANSPARENT_PREFIX = "This is an RGBA image with transparency. "
TRANSPARENT_SUFFIX = (" The image has alpha channel and the background is transparent. "
                      "No background, no scenery, no solid backdrop.")
# 用于判断用户是否已经自己写了透明相关要求（避免重复追加）
_TRANSPARENT_HINTS = ("rgba", "alpha channel", "transparent background", "with transparency",
                      "透明背景", "背景透明", "透明底", "alpha 通道")


def transparent_applied(prompt):
    """提示词里是否已经表达了"要透明"（含中文说法）。"""
    low = (prompt or "").lower()
    return any(h in low for h in _TRANSPARENT_HINTS)


def apply_transparency_template(prompt):
    """按官方模板补全透明图提示词；已表达过就原样返回。"""
    if transparent_applied(prompt):
        return prompt
    p = (prompt or "").strip()
    if not p.endswith((".", "。", "!", "！", "?", "？")):
        p += "."
    return TRANSPARENT_PREFIX + p + TRANSPARENT_SUFFIX


def png_alpha_stats(path, sample_rows=None):
    """读 PNG 的 alpha 统计：返回 dict 或 None（非 PNG / 无 alpha / 读不了）。

    默认**整图统计**（sample_rows=None）。别只采样顶部若干行 ——
    实测一张"主体在中部、上下留白"的参考图，头 64 行全是透明背景，
    只采样那 64 行会把"有主体"误判成"全透明"，进而选错透明接线方案。

    {
      "mode": "RGBA" | "gray+alpha" | "no-alpha",
      "min": int, "max": int,          # alpha 的最小/最大（0~255，8 位）
      "transparent_ratio": float,      # alpha < 16 的像素占比
      "opaque_ratio": float,           # alpha > 240 的像素占比
      "sampled_rows": int, "height": int,
    }
    """
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return None
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None

    pos, w, h, depth, ctype, idat = 8, None, None, None, None, b""
    while pos + 12 <= len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        if tag == b"IHDR":
            w, h, depth, ctype = struct.unpack(">IIBB", body[:10])
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break
        pos += 12 + ln

    if ctype not in (4, 6) or depth != 8:
        return {"mode": "no-alpha" if ctype in (0, 2, 3) else f"color_type={ctype}",
                "min": None, "max": None, "transparent_ratio": None,
                "opaque_ratio": None, "sampled_rows": 0, "height": h}
    ch = 4 if ctype == 6 else 2
    try:
        raw = zlib.decompress(idat)
    except Exception:
        return None

    stride = w * ch
    prev = bytearray(stride)
    lo, hi = 255, 0
    n_trans = n_opaque = n_total = 0
    rows = h if sample_rows is None else min(h, sample_rows)
    for y in range(rows):
        off = y * (stride + 1)
        if off + 1 + stride > len(raw):
            break
        ftype = raw[off]
        line = bytearray(raw[off + 1: off + 1 + stride])
        for i in range(stride):
            a = line[i - ch] if i >= ch else 0
            b = prev[i]
            c = prev[i - ch] if i >= ch else 0
            if ftype == 1:
                pred = a
            elif ftype == 2:
                pred = b
            elif ftype == 3:
                pred = (a + b) // 2
            elif ftype == 4:
                pp = a + b - c
                pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - c)
                pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
            else:
                pred = 0
            line[i] = (line[i] + pred) & 0xFF
        for x in range(w):
            av = line[x * ch + (ch - 1)]
            lo, hi = min(lo, av), max(hi, av)
            n_total += 1
            if av < 16:
                n_trans += 1
            elif av > 240:
                n_opaque += 1
        prev = line
    return {
        "mode": "RGBA" if ctype == 6 else "gray+alpha",
        "min": lo, "max": hi,
        "transparent_ratio": round(n_trans / n_total, 4) if n_total else 0.0,
        "opaque_ratio": round(n_opaque / n_total, 4) if n_total else 0.0,
        "sampled_rows": rows, "height": h,
    }


# ---------------------------------------------------------------- 工作流构造

def build_workflow(p):
    """根据请求参数构造 ComfyUI API 格式工作流（对应官方 t2i / image-edit 图）。"""
    wf = {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": "qwen_image_2.1_int8_convrot.safetensors",
                         "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": "qwen3vl_8b_int8_convrot.safetensors",
                         "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader",
              "inputs": {"vae_name": "qwen_image_2.1_vae_bf16.safetensors"}},
        "7": {"class_type": "EmptyLatentImage",
              "inputs": {"width": p["width"], "height": p["height"], "batch_size": 1}},
        "6": {"class_type": "KSampler",
              "inputs": {"model": ["1", 0], "positive": ["5", 0], "negative": ["5", 1],
                         "latent_image": ["7", 0], "seed": p["seed"],
                         "steps": p["steps"], "cfg": p["cfg"],
                         "sampler_name": p["sampler_name"], "scheduler": p["scheduler"],
                         "denoise": p["denoise"]}},
        "8": {"class_type": "VAEDecode",
              "inputs": {"samples": ["6", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveImage",
              "inputs": {"images": ["8", 0], "filename_prefix": p["prefix"]}},
    }

    refs = p.get("reference_images") or []
    if refs:
        # 参考图编辑：TextEncodeQwenImage21 把参考图编码进 conditioning，
        # 并输出与首张参考图尺寸匹配的 latent（第 3 个输出，下标 2）。
        #
        # ⚠⚠ 关键坑（已实测定位）：ComfyUI 的 Autogrow 输入在 API 格式里
        #   **必须用扁平的带点名键** "images.image_1" / "images.image_2" …
        #   写成嵌套 dict（"images": {"image_1": [...]}）会被**静默忽略**：
        #   节点收到的 images 为空 → 参考图完全不进模型 → 退化成纯文生图，
        #   产出与参考图无关的图，且不报错。
        #   依据：comfy_api/latest/_io.py 的 Autogrow._expand_schema_for_dynamic
        #   用 finalize_prefix() 把子输入展开成 "images.image_N"；已用画布尺寸实测验证。
        te_inputs = {
            "clip": ["2", 0],
            "prompt": p["prompt"],
            "negative_prompt": p["negative_prompt"],
            "vae": ["3", 0],
            "resolution": p.get("ref_resolution", DEFAULTS["ref_resolution"]),
        }
        for i in range(len(refs)):
            te_inputs[f"images.image_{i + 1}"] = [str(10 + i), 0]
        wf["5"] = {"class_type": "TextEncodeQwenImage21", "inputs": te_inputs}
        for i, name in enumerate(refs):
            wf[str(10 + i)] = {"class_type": "LoadImage", "inputs": {"image": name}}

        if p.get("custom_canvas"):
            # 自定义画布：等价于官方 image-edit 工作流里的 ComfySwitchNode(custom_size=true)。
            # 用于「合影/合照/海报」这类**没有画布**的新构图任务 ——
            # 官方 prompt 指南规定这类任务不跟随输入图比例：
            # 合影 3:2、写真 2:3、海报 2:3、桌面壁纸 16:9、手机壁纸 9:16。
            wf["6"]["inputs"]["latent_image"] = ["7", 0]
        else:
            # 默认：画布跟随 <image1>（= 官方 ratio_follow "<image1>" 的行为）
            del wf["7"]                   # 改用 TextEncode 的 latent 输出
            wf["6"]["inputs"]["latent_image"] = ["5", 2]
    else:
        wf["5"] = {"class_type": "TextEncodeQwenImage21",
                   "inputs": {"clip": ["2", 0], "prompt": p["prompt"],
                              "negative_prompt": p["negative_prompt"],
                              "vae": ["3", 0],
                              "resolution": p.get("ref_resolution", DEFAULTS["ref_resolution"])}}

    # ---- 透明通道（RGBA）接线 ----
    # 实测结论（tools/diag/diag_mask_alpha_convention.py、cmp_alpha.py）：
    #   1) 这个 VAE 的解码输出本来就是 4 通道（decoder.head.2.weight = [4,144,1,3,3]），
    #      ComfyUI 的 SaveImage 会把 4 通道原样写成 RGBA PNG ——
    #      所以「文生图 + 官方透明模板」**不需要任何额外节点**就能拿到模型生成的 alpha。
    #   2) 想让**参考图的 alpha** 传递到输出（RGBA 进 → RGBA 出）才需要接线：
    #      LoadImage 的 MASK 输出就是参考图 alpha（约定正常：白=不透明），
    #      但 JoinImageWithAlpha 合成时会把 mask **取反**（逐像素实测和≈255），
    #      所以必须先 InvertMask 再合成。
    #   3) KJNodes 的 SaveImageWithAlpha 也取反（且 output 为空、不进 history），
    #      拆通道的 SplitImageChannels 对 4 通道图直接报错 —— 两个都不用。
    if p.get("transparent_bg"):
        refs = p.get("reference_images") or []
        if refs and p.get("ref_has_alpha"):
            # 编辑：把参考图的 alpha 传递到输出（RGBA 进 → RGBA 出）。
            # ⚠ 实测（tools/diag/diag_alpha_chain.py，四段探针 0/85/170/255）：
            #   LoadImage 的 MASK 输出在**数值上等于 1-alpha**（它内部把 alpha 存成了 mask 的语义），
            #   而 JoinImageWithAlpha 会把 mask 当"保留度"用 —— 两者正好抵消，
            #   所以**直接用 LoadImage 的 MASK 就是对的**，千万不要再 InvertMask（那样会反掉）。
            wf["62"] = {"class_type": "JoinImageWithAlpha",
                        "inputs": {"image": ["8", 0], "alpha": ["10", 1]}}
            wf["9"] = {"class_type": "SaveImage",
                       "inputs": {"images": ["62", 0], "filename_prefix": p["prefix"]}}
    return wf


def parse_params(raw):
    """校验并归一化前端参数，抛 ValueError 时由调用方转成 400。"""
    prompt = (raw.get("prompt") or "").strip()
    if not prompt:
        raise ValueError("提示词不能为空，请输入内容后再生成。")

    negative = raw.get("negative_prompt") or ""
    if isinstance(negative, str):
        negative = negative.strip() or " "

    def as_int(name, default, lo, hi):
        v = raw.get(name, default)
        if v is None or v == "":
            v = default
        try:
            v = int(float(v))
        except (TypeError, ValueError):
            raise ValueError(f"参数「{name}」必须是整数，当前值：{raw.get(name)!r}")
        if not (lo <= v <= hi):
            raise ValueError(f"参数「{name}」应在 {lo}~{hi} 之间，当前值：{v}")
        return v

    def as_float(name, default, lo, hi):
        v = raw.get(name, default)
        if v is None or v == "":
            v = default
        try:
            v = float(v)
        except (TypeError, ValueError):
            raise ValueError(f"参数「{name}」必须是数字，当前值：{raw.get(name)!r}")
        if not (lo <= v <= hi):
            raise ValueError(f"参数「{name}」应在 {lo}~{hi} 之间，当前值：{v}")
        return v

    steps = as_int("steps", DEFAULTS["steps"], 1, 200)
    cfg = as_float("cfg", DEFAULTS["cfg"], 0.0, 20.0)
    width = as_int("width", DEFAULTS["width"], 64, MAX_SIDE)
    height = as_int("height", DEFAULTS["height"], 64, MAX_SIDE)
    # 对齐到 32 的倍数（官方节点要求）
    width = max(SIZE_STEP, round(width / SIZE_STEP) * SIZE_STEP)
    height = max(SIZE_STEP, round(height / SIZE_STEP) * SIZE_STEP)

    # 种子：留空或给 0/-1 视为随机
    seed_raw = raw.get("seed", None)
    if seed_raw is None or seed_raw == "" or str(seed_raw).strip() in ("-1", "0"):
        seed = int(uuid.uuid4().int % (2 ** 31))
        seed_was_random = True
    else:
        try:
            seed = int(seed_raw)
        except (TypeError, ValueError):
            raise ValueError(f"随机种子必须是整数，当前值：{seed_raw!r}")
        if not (0 <= seed <= 2 ** 63 - 1):
            raise ValueError("随机种子必须是 0 ~ 2^63-1 之间的非负整数")
        seed_was_random = False

    sampler_name = str(raw.get("sampler_name") or DEFAULTS["sampler_name"])
    scheduler = str(raw.get("scheduler") or DEFAULTS["scheduler"])
    denoise = DEFAULTS["denoise"]

    refs = raw.get("reference_images") or []
    if not isinstance(refs, list):
        raise ValueError("参考图参数格式错误")
    if len(refs) > 10:
        raise ValueError(f"参考图最多 10 张，当前 {len(refs)} 张")
    refs = [os.path.basename(str(n)) for n in refs if n]

    # ---- 透明背景（RGBA）----
    # transparent_bg=True 时把提示词按官方模板补全（没写才补），并在工作流里
    # 接好 alpha 通路；出图后还会读产物 alpha 回报，免得"以为支持其实没生效"。
    transparent_bg = bool(raw.get("transparent_bg"))
    if transparent_bg:
        prompt = apply_transparency_template(prompt)

    # 参考图是否有**可用**的 alpha：
    # 判据不只是"存在透明像素"，还要"有足够多的不透明像素"——
    # 否则一张被抠成全透明的图也会被当成"带 alpha"，输出就只能是全透明（毫无意义）。
    # 全透明/几乎全透明的图应当改走 t2i 式的模型生成 alpha。
    ref_has_alpha = False
    ref_alpha_stats = None
    if refs:
        st = png_alpha_stats(os.path.join(UPLOAD_DIR, refs[0]))   # 整图统计，别截前若干行
        ref_alpha_stats = st
        if (st and st.get("min") is not None
                and st["min"] < 250 and (st.get("opaque_ratio") or 0) >= 0.05):
            ref_has_alpha = True

    if refs and cfg > 1.0:
        pass  # 允许，但前端会提示负向提示词才生效

    # 参考图像素预算：0 = 跟随参考图原生尺寸（官方 edit 模板默认，保真优先）
    # 也可传 1024 / 2048 等，按总像素预算缩放参考图以省显存。
    ref_res = raw.get("ref_resolution", DEFAULTS["ref_resolution"])
    if ref_res is None or ref_res == "":
        ref_res = DEFAULTS["ref_resolution"]
    try:
        ref_res = int(float(ref_res))
    except (TypeError, ValueError):
        raise ValueError(f"参考图像素预算必须是整数，当前值：{raw.get('ref_resolution')!r}")
    if ref_res != 0 and not (512 <= ref_res <= 4096):
        raise ValueError(f"参考图像素预算应为 0（跟随原图）或 512~4096，当前值：{ref_res}")

    return {
        "prompt": prompt,
        "negative_prompt": negative,
        "steps": steps, "cfg": cfg, "width": width, "height": height,
        "seed": seed, "seed_was_random": seed_was_random,
        "sampler_name": sampler_name, "scheduler": scheduler, "denoise": denoise,
        "reference_images": refs,
        "ref_resolution": ref_res,
        "transparent_bg": transparent_bg,
        "ref_has_alpha": ref_has_alpha,
        # 编辑模式下默认「画布跟随 <image1>」；打开 custom_canvas 则用 width/height
        # 自建画布，适用于合影/海报这类没有画布的新构图（官方指南：合影用 3:2）。
        "custom_canvas": bool(raw.get("custom_canvas")),
        "prefix": f"qwen21_workbench/{time.strftime('%Y%m%d')}/{uuid.uuid4().hex[:8]}",
        "mode": "edit" if refs else "t2i",
    }


# ---------------------------------------------------------------- 局部编辑（标注 + 合成）

def png_read_rgba(path):
    """读 PNG 为 (w, h, bytearray(RGBA))。支持 8 位灰度/RGB/调色板外的常见色型。"""
    with open(path, "rb") as f:
        d = f.read()
    if d[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("不是 PNG 文件")
    pos, w, h, depth, ctype, idat = 8, None, None, None, None, b""
    while pos + 12 <= len(d):
        ln = struct.unpack(">I", d[pos:pos + 4])[0]
        tag = d[pos + 4:pos + 8]
        body = d[pos + 8:pos + 8 + ln]
        if tag == b"IHDR":
            w, h, depth, ctype = struct.unpack(">IIBB", body[:10])
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break
        pos += 12 + ln
    if depth != 8:
        raise ValueError(f"只支持 8 位 PNG，当前位深 {depth}")
    ch = {0: 1, 2: 3, 4: 2, 6: 4}.get(ctype)
    if ch is None:
        raise ValueError(f"不支持的 PNG 色型 {ctype}（调色板请先转成 RGBA）")
    raw = zlib.decompress(idat)
    stride = w * ch
    prev = bytearray(stride)
    out = bytearray(w * h * 4)
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
        prev = line
        for x in range(w):
            o = (y * w + x) * 4
            if ch == 4:
                out[o] = line[x * 4]
                out[o + 1] = line[x * 4 + 1]
                out[o + 2] = line[x * 4 + 2]
                out[o + 3] = line[x * 4 + 3]
            elif ch == 3:
                out[o] = line[x * 3]
                out[o + 1] = line[x * 3 + 1]
                out[o + 2] = line[x * 3 + 2]
                out[o + 3] = 255
            elif ch == 2:
                out[o] = out[o + 1] = out[o + 2] = line[x * 2]
                out[o + 3] = line[x * 2 + 1]
            else:
                out[o] = out[o + 1] = out[o + 2] = line[x]
                out[o + 3] = 255
    return w, h, out


def png_write_rgba(path, w, h, rgba):
    """写 8 位 RGBA PNG（只用标准库）。"""
    stride = w * 4
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw.extend(rgba[y * stride:(y + 1) * stride])

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def rasterize_strokes(w, h, strokes, brush_norm):
    """把标注笔画栅格化成掩码（bytearray，255 = 标注区）。

    strokes: [{"points": [[x, y], ...]}, ...]，坐标是 0~1 的归一化值。
    brush_norm: 画笔半径，同样是相对**短边**的归一化值。
    用实心圆盘盖章，简单且形状明确（模型对"明确标记"的响应最稳）。
    """
    mask = bytearray(w * h)
    r = max(1, int(brush_norm * min(w, h)))
    r2 = r * r
    for st in strokes or []:
        pts = st.get("points") or []
        for k in range(len(pts)):
            x0 = int(pts[k][0] * w)
            y0 = int(pts[k][1] * h)
            # 相邻点之间插值补点，避免快速划动时斑点断续
            if k + 1 < len(pts):
                x1 = int(pts[k + 1][0] * w)
                y1 = int(pts[k + 1][1] * h)
            else:
                x1, y1 = x0, y0
            dist = max(abs(x1 - x0), abs(y1 - y0))
            steps = max(1, dist // max(1, r // 2))
            for s in range(steps + 1):
                t = s / steps
                cx = int(x0 + (x1 - x0) * t)
                cy = int(y0 + (y1 - y0) * t)
                for yy in range(max(0, cy - r), min(h, cy + r + 1)):
                    dy = yy - cy
                    row = yy * w
                    for xx in range(max(0, cx - r), min(w, cx + r + 1)):
                        dx = xx - cx
                        if dx * dx + dy * dy <= r2:
                            mask[row + xx] = 255
    return mask


def composite_by_mask(base_rgba, edited_rgba, mask, feather=0):
    """按掩码合成：掩码内取 edited，掩码外取 base。

    feather > 0 时对掩码做一次盒式模糊，让边界过渡自然（避免硬边）。
    """
    w = len(base_rgba) // 4
    if feather > 0:
        r = max(1, int(feather))
        blurred = bytearray(len(mask))
        for y in range(0, len(mask) // w):
            for x in range(w):
                s = n = 0
                for yy in range(max(0, y - r), min(len(mask) // w, y + r + 1)):
                    row = yy * w
                    for xx in range(max(0, x - r), min(w, x + r + 1)):
                        s += mask[row + xx]
                        n += 1
                blurred[y * w + x] = s // n
        mask = blurred

    out = bytearray(len(base_rgba))
    for i in range(0, len(base_rgba), 4):
        a = mask[i // 4]
        if a == 0:
            out[i:i + 4] = base_rgba[i:i + 4]
        elif a == 255:
            out[i:i + 4] = edited_rgba[i:i + 4]
        else:
            af = a / 255.0
            for k in range(4):
                out[i + k] = int(base_rgba[i + k] * (1 - af) + edited_rgba[i + k] * af)
    return out


# ---------------------------------------------------------------- 出图任务

def _scan_outputs_by_prefix(prefix):
    """在 ComfyUI 的 output 目录里按 filename_prefix 找刚写出的图。

    为什么需要：SaveImage 会把结果登记进 history.outputs，工作台据此找图；
    但 KJNodes 的 SaveImageWithAlpha 的 output 声明为空，不会出现在 history 里，
    文件却确实写到了 output/<prefix>_00001_.png。所以成功但没有登记时扫一遍目录。
    """
    found = []
    try:
        base = COMFY_OUTPUT
        if not os.path.isdir(base):
            return found
        for root_dir, _dirs, names in os.walk(base):
            for n in names:
                if not n.lower().endswith(".png"):
                    continue
                rel = os.path.relpath(os.path.join(root_dir, n), base).replace("\\", "/")
                if prefix.replace("\\", "/") in rel:
                    found.append({
                        "filename": n,
                        "subfolder": os.path.dirname(rel).replace("\\", "/"),
                        "type": "output",
                    })
    except Exception as e:
        log(f"扫描 output 目录失败: {e}")
    # 新的排前面（同一前缀一般只有一张）
    found.sort(key=lambda x: x["filename"], reverse=True)
    return found[:4]


def run_job(job_id, params):
    job = JOBS[job_id]
    client_id = job["client_id"]

    def on_message(msg):
        t = msg.get("type")
        if t == "progress":
            val, mx = msg.get("data", {}).get("value", 0), msg.get("data", {}).get("max", 1)
            job["step"] = val
            job["total_steps"] = mx
            if mx:
                job["progress"] = round(val * 100.0 / mx, 1)
        elif t == "executing":
            node = msg.get("data", {}).get("node")
            if node is None:
                job["progress"] = max(job.get("progress") or 0, 99.0)
        elif t == "execution_error":
            job["error"] = json.dumps(msg.get("data", {}), ensure_ascii=False)
        elif t == "execution_cached":
            pass

    ws = ComfyWS(client_id, on_message)
    ws.start()
    time.sleep(0.5)

    try:
        wf = build_workflow(params)
        resp = http_json(f"{COMFY_BASE}/prompt", {"prompt": wf, "client_id": client_id}, timeout=60)
        if "prompt_id" not in resp:
            err = resp.get("error") or resp
            job["status"] = "error"
            job["error"] = f"ComfyUI 拒绝该任务：{json.dumps(err, ensure_ascii=False)[:800]}"
            return
        prompt_id = resp["prompt_id"]
        job["prompt_id"] = prompt_id
        log(f"[{job_id}] 已提交 ComfyUI，prompt_id={prompt_id}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        job["status"] = "error"
        job["error"] = f"提交失败 HTTP {e.code}：{body[:600]}"
        return
    except Exception as e:
        job["status"] = "error"
        job["error"] = f"提交任务失败：{type(e).__name__} {e}"
        return
    finally:
        pass

    t0 = time.time()
    images = []
    while time.time() - t0 < GENERATE_TIMEOUT:
        if job.get("cancel"):
            job["status"] = "error"
            job["error"] = "任务已被用户取消"
            break
        try:
            hist = http_json(f"{COMFY_BASE}/history/{prompt_id}", timeout=15)
        except Exception:
            time.sleep(1)
            continue
        entry = hist.get(prompt_id)
        if entry:
            st = (entry.get("status") or {})
            status_str = st.get("status_str")
            for out in (entry.get("outputs") or {}).values():
                for im in (out.get("images") or []):
                    images.append({
                        "filename": im.get("filename"),
                        "subfolder": im.get("subfolder") or "",
                        "type": im.get("type") or "output",
                    })
            if status_str == "success":
                job["status"] = "done"
                job["progress"] = 100.0
                job["elapsed"] = round(time.time() - t0, 1)
                if not images:
                    # 兜底：有些保存节点（如 KJNodes 的 SaveImageWithAlpha，output 声明为空）
                    # 不会出现在 history.outputs 里，但文件确实写进了 output 目录。
                    # 按本次任务专属的 filename_prefix 去扫目录。
                    images = _scan_outputs_by_prefix(p["prefix"])
                break
            if status_str == "error":
                msgs = []
                for m in ((st.get("messages") or [])):
                    if isinstance(m, list) and len(m) >= 2 and m[0] == "execution_error":
                        d = m[1] or {}
                        msgs.append(
                            f"{d.get('node_type')} 节点出错：{d.get('exception_type')} "
                            f"{d.get('exception_message')}"
                        )
                job["status"] = "error"
                job["error"] = "；".join(msgs) or json.dumps(st, ensure_ascii=False)[:800]
                break
        time.sleep(0.8)
    else:
        job["status"] = "error"
        job["error"] = f"出图超时（超过 {GENERATE_TIMEOUT // 60} 分钟）"

    ws.stop()

    # 把结果复制到工作台自己的 outputs 目录
    local = []
    for im in images:
        try:
            src = os.path.join(COMFY_OUTPUT, im["subfolder"], im["filename"])
            if not os.path.isfile(src):
                continue
            job_dir = os.path.join(OUTPUT_DIR, job_id)
            os.makedirs(job_dir, exist_ok=True)
            dst = os.path.join(job_dir, im["filename"])
            with open(src, "rb") as fi, open(dst, "wb") as fo:
                while True:
                    b = fi.read(1024 * 1024)
                    if not b:
                        break
                    fo.write(b)
            local.append({
                "file": f"{job_id}/{im['filename']}",
                "comfy_ref": f"{im['subfolder']}/{im['filename']}" if im["subfolder"] else im["filename"],
            })
        except Exception as e:
            log(f"[{job_id}] 复制结果失败: {e}")

    job["images"] = local
    if job["status"] != "error":
        if local:
            job["status"] = "done"
        else:
            job["status"] = "error"
            job["error"] = "推理已完成，但未找到输出图片文件"

    # ---- 透明通道回报：直接读产物 PNG 的 alpha，给出可核对的数字 ----
    # 这一条是"看不见的能力"的保险：透明出图必须写官方模板句式，
    # 用户漏写时模型会安静地给出全不透明图，所以出图后主动量一次并报出来。
    if local and (params.get("transparent_bg") or _looks_transparent_request(params)):
        for item in local:
            p = os.path.join(OUTPUT_DIR, item["file"])
            stats = png_alpha_stats(p)
            if stats:
                item["alpha"] = stats
        first = next((i for i in local if i.get("alpha")), None)
        if first:
            a = first["alpha"]
            if a.get("transparent_ratio"):
                log(f"[{job_id}] 透明检查：alpha {a['min']}~{a['max']}，"
                    f"透明像素 {a['transparent_ratio'] * 100:.1f}%")
            else:
                log(f"[{job_id}] 透明检查：未检测到透明像素（alpha {a.get('min')}~{a.get('max')}）"
                    "—— 多半是提示词没写官方透明模板")

    job["finished_at"] = time.time()
    log(f"[{job_id}] 结束：{job['status']} 用时 {round(time.time() - t0, 1)}s "
        f"产图 {len(local)} 张")


def _looks_transparent_request(params):
    """用户虽没勾开关，但提示词里明显在要透明 —— 也报一次 alpha，免得他以为模型不行。"""
    return transparent_applied(params.get("prompt", ""))


# ---------------------------------------------------------------- HTTP 处理

class Handler(BaseHTTPRequestHandler):
    server_version = "QwenImage21Workbench/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        if "/api/progress" in (self.path or ""):
            return
        log(f"{self.address_string()} {fmt % args}")

    # ---------- 工具 ----------
    def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False))

    def _error(self, code, message, **extra):
        payload = {"ok": False, "error": message}
        payload.update(extra)
        self._json(code, payload)

    def _file(self, path, download_name=None):
        if not os.path.isfile(path):
            self._error(404, f"文件不存在：{os.path.basename(path)}")
            return
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        if ctype.startswith("image/") and ctype != "image/svg+xml":
            with open(path, "rb") as f:
                data = f.read()
            self._send(200, data, ctype)
            return
        size = os.path.getsize(path)
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(size))
        self.send_header("Cache-Control", "no-store")
        if download_name:
            self.send_header(
                "Content-Disposition",
                f'attachment; filename="{download_name}"; filename*=UTF-8\'\'{urllib.parse.quote(download_name)}',
            )
        self.end_headers()
        with open(path, "rb") as f:
            while True:
                b = f.read(256 * 1024)
                if not b:
                    break
                try:
                    self.wfile.write(b)
                except (BrokenPipeError, ConnectionAbortedError):
                    return

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            raise ValueError("请求体不是合法 JSON")

    # ---------- 路由 ----------
    def do_GET(self):
        # 顶层保护：任何请求级异常都不应影响服务继续运行
        # （客户端中途断开在 Windows 上会抛 ConnectionResetError/BrokenPipe，属正常现象）
        try:
            self._do_get()
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass
        except Exception as e:
            log(f"处理 GET {self.path} 时异常: {type(e).__name__} {e}")
            try:
                self._error(500, f"服务端异常：{type(e).__name__} {e}")
            except Exception:
                pass

    def _do_get(self):
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)
        qs = urllib.parse.parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            return self._file(os.path.join(WEB_DIR, "index.html"))
        if path == "/favicon.ico":
            return self._send(204, b"", "image/x-icon")
        if path.startswith("/static/"):
            rel = path[len("/static/"):]
            safe = os.path.normpath(rel).replace("\\", "/")
            if safe.startswith("..") or os.path.isabs(safe):
                return self._error(400, "非法路径")
            return self._file(os.path.join(WEB_DIR, safe))

        if path == "/api/config":
            return self._json(200, {
                "ok": True,
                "model_name": "Qwen-Image-2.1",
                "model_note": "统一文生图 + 图像编辑；视觉主干 7B（32 层 Single-Stream DiT）+ Qwen3-VL-8B 文本编码器",
                "defaults": DEFAULTS,
                "aspect_presets": ASPECT_PRESETS,
                "max_side": MAX_SIDE,
                "size_step": SIZE_STEP,
                "max_reference_images": 10,
                "samplers": ["euler", "euler_ancestral", "heun", "dpmpp_2m", "dpmpp_sde", "uni_pc"],
                "schedulers": ["simple", "normal", "beta", "sgm_uniform", "karras", "exponential"],
                "cfg_note": "官方推荐 true_cfg_scale=1.0（不开引导）。只有把引导强度调到 >1 时，负向提示词才会生效，且每步计算量翻倍。",
                "license_note": "本模型为 Qwen Research License，仅限非商用；商用需单独向官方申请授权。",
            })

        if path == "/api/status":
            return self._json(200, self._status_payload())

        if path == "/api/jobs":
            with STATE_LOCK:
                items = []
                for jid in reversed(JOBS_ORDER):
                    j = JOBS[jid]
                    items.append({
                        "id": jid, "status": j["status"], "progress": j.get("progress", 0),
                        "params": j["params"], "images": j.get("images", []),
                        "error": j.get("error"), "elapsed": j.get("elapsed"),
                    })
            return self._json(200, {"ok": True, "jobs": items})

        if path.startswith("/api/jobs/"):
            jid = path[len("/api/jobs/"):]
            j = JOBS.get(jid)
            if not j:
                return self._error(404, "找不到该任务")
            return self._json(200, {"ok": True, "job": {
                "id": jid, "status": j["status"], "progress": j.get("progress", 0),
                "step": j.get("step"), "total_steps": j.get("total_steps"),
                "params": j["params"], "images": j.get("images", []),
                "error": j.get("error"), "elapsed": j.get("elapsed"),
                "queued": j.get("queued", 0),
            }})

        if path.startswith("/api/progress/"):
            jid = path[len("/api/progress/"):]
            j = JOBS.get(jid)
            if not j:
                return self._error(404, "找不到该任务")
            return self._json(200, {
                "ok": True, "status": j["status"], "progress": j.get("progress", 0),
                "step": j.get("step"), "total_steps": j.get("total_steps"),
                "error": j.get("error"), "elapsed": j.get("elapsed"),
                "queue_position": j.get("queued", 0),
            })

        if path == "/api/image":
            rel = (qs.get("f") or [""])[0]
            safe = os.path.normpath(rel).replace("\\", "/")
            if safe.startswith("..") or os.path.isabs(safe):
                return self._error(400, "非法路径")
            return self._file(os.path.join(OUTPUT_DIR, safe))

        if path == "/api/upload-image":
            name = (qs.get("f") or [""])[0]
            safe = os.path.normpath(name).replace("\\", "/")
            if safe.startswith("..") or os.path.isabs(safe):
                return self._error(400, "非法路径")
            return self._file(os.path.join(UPLOAD_DIR, safe), download_name=os.path.basename(safe))

        return self._error(404, "接口不存在")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)

        try:
            if path == "/api/generate":
                return self._handle_generate()
            if path == "/api/upload":
                return self._handle_upload()
            if path == "/api/cancel":
                return self._handle_cancel()
            if path == "/api/merge-local":
                return self._handle_merge_local()
            if path == "/api/shutdown":
                return self._handle_shutdown()
        except ValueError as e:
            return self._error(400, str(e))
        except Exception as e:
            log(f"处理 {path} 时异常: {type(e).__name__} {e}")
            return self._error(500, f"服务端异常：{type(e).__name__} {e}")

        return self._error(404, "接口不存在")

    # ---------- 业务处理 ----------
    def _status_payload(self):
        ok, models = check_models()
        with STATE_LOCK:
            ready = dict(COMFY_READY)
            active = ACTIVE_JOB["id"]
        info = None
        if ready["ok"]:
            try:
                st = http_json(f"{COMFY_BASE}/system_stats", timeout=5)
                dev = (st.get("devices") or [{}])[0]
                info = {
                    "comfyui_version": (st.get("system") or {}).get("comfyui_version"),
                    "device": dev.get("name"),
                    "vram_total_gb": round(dev.get("vram_total", 0) / 1e9, 2),
                    "vram_free_gb": round(dev.get("vram_free", 0) / 1e9, 2),
                    "torch": dev.get("torch_version"),
                }
            except Exception:
                pass
        return {
            "ok": True,
            "models_ready": ok,
            "models": models,
            "comfyui": {"ready": ready["ok"], "detail": ready["detail"], "info": info},
            "active_job": active,
            "models_dir": MODELS_DIR,
            "download_hint": "在本项目目录执行：python tools/download.py  （约 17.3GB，自动多镜像续传）",
        }

    def _handle_generate(self):
        raw = self._read_json()

        ok, models = check_models()
        if not ok:
            missing = [v["message"] for v in models.values() if v["status"] != "ok"]
            return self._error(503, "模型权重未就绪，无法出图：\n" + "\n".join(missing),
                               models=models, models_dir=MODELS_DIR)

        with STATE_LOCK:
            ready = COMFY_READY["ok"]
        if not ready:
            return self._error(503, f"ComfyUI 后端不可用：{COMFY_READY['detail']}")

        params = parse_params(raw)   # 可能抛 ValueError -> 400

        with STATE_LOCK:
            if ACTIVE_JOB["id"]:
                return self._error(429, "已有出图任务正在进行中，请等待完成后再试。",
                                   active_job=ACTIVE_JOB["id"])
            job_id = uuid.uuid4().hex[:12]
            JOBS[job_id] = {
                "id": job_id, "status": "running", "progress": 0.0,
                "params": params, "images": [], "error": None,
                "created_at": time.time(), "client_id": uuid.uuid4().hex,
            }
            JOBS_ORDER.append(job_id)
            ACTIVE_JOB["id"] = job_id

        def runner():
            try:
                run_job(job_id, params)
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                JOBS[job_id]["status"] = "error"
                JOBS[job_id]["error"] = (
                    f"未预期的错误：{type(e).__name__} {e}\n{tb.splitlines()[-3]}"
                )
                log(f"[{job_id}] 崩溃:\n{tb}")
            finally:
                with STATE_LOCK:
                    if ACTIVE_JOB["id"] == job_id:
                        ACTIVE_JOB["id"] = None

        threading.Thread(target=runner, daemon=True).start()
        log(f"[{job_id}] 新任务 mode={params['mode']} size={params['width']}x{params['height']} "
            f"steps={params['steps']} cfg={params['cfg']} seed={params['seed']}")
        return self._json(200, {"ok": True, "job_id": job_id, "params": params})

    def _handle_upload(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            raise ValueError("上传内容为空")
        if length > 32 * 1024 * 1024:
            raise ValueError("参考图过大（上限 32MB）")
        raw = self.rfile.read(length)

        ctype = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in ctype:
            raise ValueError("上传格式必须是 multipart/form-data")
        boundary = ctype.split("boundary=")[-1].strip().strip('"')
        parts = raw.split(("--" + boundary).encode())
        filedata, filename = None, None
        for part in parts:
            if b"\r\n\r\n" not in part:
                continue
            head, body = part.split(b"\r\n\r\n", 1)
            if b"filename=" not in head:
                continue
            body = body.rstrip(b"\r\n")
            if body.endswith(b"--"):
                body = body[:-2].rstrip(b"\r\n")
            fn = head.decode("utf-8", "replace")
            i = fn.find('filename="')
            if i >= 0:
                filename = fn[i + 10:].split('"')[0]
            filedata = body
            break

        if not filedata:
            raise ValueError("没有解析到上传的图片数据")

        ext = os.path.splitext(filename or "")[1].lower() or ".png"
        if ext not in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
            raise ValueError(f"不支持的图片格式：{ext}")
        safe_name = f"ref_{uuid.uuid4().hex[:10]}{ext}"

        os.makedirs(UPLOAD_DIR, exist_ok=True)
        local_path = os.path.join(UPLOAD_DIR, safe_name)
        with open(local_path, "wb") as f:
            f.write(filedata)

        # 复制到 ComfyUI 的 input 目录，供 LoadImage 节点读取
        try:
            os.makedirs(COMFY_INPUT, exist_ok=True)
            with open(os.path.join(COMFY_INPUT, safe_name), "wb") as f:
                f.write(filedata)
        except Exception as e:
            log(f"复制参考图到 ComfyUI input 失败: {e}")

        return self._json(200, {
            "ok": True, "name": safe_name, "url": f"/api/upload-image?f={urllib.parse.quote(safe_name)}",
            "size": len(filedata),
        })

    def _handle_cancel(self):
        raw = self._read_json()
        jid = raw.get("job_id")
        j = JOBS.get(jid)
        if not j:
            return self._error(404, "找不到该任务")
        j["cancel"] = True
        return self._json(200, {"ok": True})

    def _handle_merge_local(self):
        """局部编辑收尾：把「模型重绘整图」按掩码合回原图，做到圈外逐点不变。

        body:
          base_job_id   基准图所在任务（未标注的原图）
          base_ref      基准图是参考图时的文件名（uploads 里那张未标注的原图）
          edit_job_id   模型输出的任务（整图重绘结果）
          strokes       [{"points": [[x,y],...]}]，0~1 归一化坐标
          brush         画笔半径（相对短边，归一化）
          feather       边界羽化像素（0 = 硬边）
        """
        raw = self._read_json()
        base_job = str(raw.get("base_job_id") or "")
        base_ref = os.path.basename(str(raw.get("base_ref") or ""))
        edit_job = str(raw.get("edit_job_id") or "")
        strokes = raw.get("strokes") or []
        brush = float(raw.get("brush") or 0.04)
        feather = int(raw.get("feather") or 0)
        if not (base_job or base_ref) or not edit_job:
            return self._error(400, "缺少 base_job_id / base_ref 或 edit_job_id")
        if not strokes:
            return self._error(400, "没有标注内容：请先在参考图上画要修改的区域。")

        def first_image(jid):
            j = JOBS.get(jid)
            if not j:
                return None
            for im in (j.get("images") or []):
                return os.path.join(OUTPUT_DIR, im["file"])
            return None

        # 基准图既可以是某个任务的产物，也可以是用户上传的参考图（未标注的原图）
        base_path = os.path.join(UPLOAD_DIR, base_ref) if base_ref else first_image(base_job)
        edited_path = first_image(edit_job)
        if not base_path or not os.path.exists(base_path):
            return self._error(404, f"找不到基准图（{base_ref or ('任务 ' + base_job)}）")
        if not edited_path or not os.path.exists(edited_path):
            return self._error(404, f"找不到模型输出（任务 {edit_job}）")

        try:
            bw, bh, base_rgba = png_read_rgba(base_path)
            ew, eh, edited_rgba = png_read_rgba(edited_path)
        except ValueError as e:
            return self._error(400, f"读取图片失败：{e}")

        if (ew, eh) != (bw, bh):
            # 尺寸不一致时把模型输出缩放到基准尺寸不可靠（没有图像库），直接拒绝并说明
            return self._error(
                400, f"尺寸不一致，无法合成：基准图 {bw}×{bh}，模型输出 {ew}×{eh}。"
                     "请保持画布跟随 <image1>（不要勾选自定义画布）。")

        mask = rasterize_strokes(bw, bh, strokes, brush)
        marked = sum(1 for v in mask if v)
        if marked == 0:
            return self._error(400, "标注区域是空的（笔画可能落在画面外），请重新标注。")

        out = composite_by_mask(base_rgba, edited_rgba, mask, feather=feather)

        job_id = uuid.uuid4().hex[:12]
        job_dir = os.path.join(OUTPUT_DIR, job_id)
        os.makedirs(job_dir, exist_ok=True)
        name = f"{uuid.uuid4().hex[:8]}_local_00001_.png"
        png_write_rgba(os.path.join(job_dir, name), bw, bh, out)

        with STATE_LOCK:
            JOBS[job_id] = {
                "id": job_id, "status": "done", "progress": 100.0,
                "params": {
                    "prompt": f"（局部编辑合成：仅替换标注区，取自任务 {edit_job}）",
                    "mode": "local", "width": bw, "height": bh,
                    "steps": 0, "cfg": 1.0, "seed": 0, "seed_was_random": False,
                    "sampler_name": "—", "scheduler": "—",
                    "reference_images": [], "ref_has_alpha": False,
                    "transparent_bg": False, "custom_canvas": False, "ref_resolution": 0,
                },
                "images": [{"file": f"{job_id}/{name}"}],
                "error": None, "elapsed": 0.0,
                "created_at": time.time(),
            }
            JOBS_ORDER.append(job_id)

        log(f"[{job_id}] 局部编辑合成：标注覆盖 {marked * 100.0 / (bw * bh):.1f}% 画面，"
            f"其余逐点沿用基准图")
        return self._json(200, {
            "ok": True, "job_id": job_id,
            "image": f"{job_id}/{name}",
            "masked_ratio": round(marked / (bw * bh), 4),
            "size": [bw, bh],
        })


    def _handle_shutdown(self):
        def bye():
            time.sleep(0.5)
            proc = COMFY_PROC.get("proc")
            if proc and COMFY_PROC.get("started_by_us") and proc.poll() is None:
                log("正在关闭由工作台拉起的 ComfyUI …")
                try:
                    proc.terminate()
                except Exception:
                    pass
            log("工作台已退出")
            os._exit(0)
        threading.Thread(target=bye, daemon=True).start()
        return self._json(200, {"ok": True, "message": "正在退出"})


# ---------------------------------------------------------------- 端口预检
# 为什么需要它：Windows 上 SO_REUSEADDR 的语义与 Linux 不同 —— 第一个监听者若开了
# SO_REUSEADDR（http.server.ThreadingHTTPServer 的 allow_reuse_address 默认就是 True），
# 第二个 socket 带着 SO_REUSEADDR 再绑同一个 host:port **不会报错，而是绑成功**，
# 之后内核把新连接随机分给其中一个监听者。于是"再双击一次启动脚本"会打印两次"启动成功"，
# 而一旦其中一个实例已经卡住（控制台被关掉等），浏览器就会随机拿到
# 「127.0.0.1 未发送任何数据 / ERR_EMPTY_RESPONSE」——连接建立成功，一个字节都没回来。
#
# 本机实测（3.13.14 / 3.14.2 行为一致）：
#   · 空闲 loopback 端口 connect 会**超时**而不是 connection refused
#     → 所以"连一下看响不响"无法区分"空闲"和"卡死"，不能用作判据。
#   · 第二个 socket **不带 SO_REUSEADDR** 去绑已被占用的端口 → 稳定报 WinError 10048。
#     → 所以"独占 bind"才是权威判据，也正是本文件采用的方案。

WORKBENCH_MARK = "QwenImage21Workbench"
PORT_PROBE_TIMEOUT = 1.5


def _probe_http(host, port, timeout=PORT_PROBE_TIMEOUT):
    """问一下端口上的服务是谁：返回 "workbench" / "other" / None（无应答或连不上）。"""
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.settimeout(timeout)
            s.sendall(
                f"GET /api/config HTTP/1.1\r\nHost: {host}:{port}\r\n"
                "Connection: close\r\n\r\n".encode("ascii")
            )
            buf = b""
            while len(buf) < 65536:
                try:
                    chunk = s.recv(8192)
                except (socket.timeout, OSError):
                    break
                if not chunk:
                    break
                buf += chunk
                if b"\r\n\r\n" in buf:      # 拿到完整响应头就够了
                    break
    except OSError:
        return None

    if not buf:
        return None
    head = buf.split(b"\r\n\r\n", 1)[0].decode("latin-1", "replace")
    return "workbench" if WORKBENCH_MARK in head else "other"


def _explain_busy(host, port, state):
    url = f"http://{host}:{port}"
    print()
    if state == "workbench":
        print(f"  [X] {host}:{port} 上已经有一个工作台在运行了。")
        print(f"      直接打开这个地址即可：{url}")
        print("      本进程不会重复启动 —— 两个实例监听同一端口会让页面随机打不开。")
    elif state == "other":
        print(f"  [X] {host}:{port} 已被其它程序占用（有应答，但不是本工作台）。")
        print("      换一个端口启动即可，例如：python server.py --port 8643")
    else:
        print(f"  [X] {host}:{port} 已被占用，但占用它的进程不应答任何请求"
              "（一个卡住的旧实例）。")
        print("      这正是浏览器显示「无法使用此页面 / 127.0.0.1 未发送任何数据」的原因。")
        print("      处置办法（在本项目目录执行）：")
        print(f"          netstat -ano | findstr :{port}      看最后一列的 PID")
        print("          taskkill /PID <那个PID> /F")
        print("      确认没有旧实例后重试；确实要强行接管端口时：")
        print(f"          python server.py --port {port} --force")
    print()


def _port_occupied(host, port, timeout=PORT_PROBE_TIMEOUT):
    """端口是否已被占用 —— 用**不带 SO_REUSEADDR** 的独占 socket 试绑来判定。

    这是唯一可靠的判据：本机实测空闲 loopback 端口 connect 会超时（不是 refused），
    所以"连一下看响不响"区分不了"空闲"和"卡死"；而独占 bind 在被占用时稳定报
    WinError 10048。探针 socket 立即关闭，不留任何痕迹。
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Windows 上必须显式关掉，否则默认可能允许共享
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        except (AttributeError, OSError):
            pass
        s.settimeout(timeout)
        s.bind((host, port))
        return False            # 绑上了 → 端口是空闲的
    except OSError:
        return True             # 10048 → 已被别人占着
    finally:
        s.close()


# ---------------------------------------------------------------- 入口

def main():
    ap = argparse.ArgumentParser(description="Qwen-Image-2.1 本地工作台")
    ap.add_argument("--port", type=int, default=8642, help="工作台端口（默认 8642）")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--no-comfy", action="store_true", help="不自动拉起 ComfyUI")
    ap.add_argument("--comfy-timeout", type=int, default=240)
    ap.add_argument("--force", action="store_true",
                    help="跳过端口预检，强行绑定（用于接管卡死的旧实例）")
    args = ap.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    print("=" * 68)
    print("  Qwen-Image-2.1 本地能力展示台")
    print("=" * 68)

    # ---- 端口预检：Windows 上两个实例能同时绑同一个 host:port（SO_REUSEADDR），
    # 一旦其中一个卡住，页面就随机打不开（ERR_EMPTY_RESPONSE）。
    # 这里先用独占探针确认端口空闲，再照常绑定（保持 http.server 原生行为，
    # 这样 --force 才能真的接管一个卡死的旧实例）。
    if not args.force and _port_occupied(args.host, args.port):
        _explain_busy(args.host, args.port, _probe_http(args.host, args.port) or "stuck")
        return 2
    if args.force:
        print(f"  [警告] --force：跳过端口预检。若 {args.host}:{args.port} 上已有实例，"
              "内核会把新连接随机分给其中一个。\n")

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)

    ok, models = check_models()
    print("\n【权重检查】")
    for v in models.values():
        mark = "OK  " if v["status"] == "ok" else "缺失"
        print(f"  [{mark}] {v['message']}")
    if not ok:
        print("\n  提示：权重缺失不阻止工作台启动，但无法出图。")
        print("  下载命令（在本项目目录执行，支持断点续传、自动多镜像）：")
        print("      python tools/download.py")
        print(f"  权重根目录：{MODELS_DIR}")
        for v in models.values():
            if v["status"] != "ok":
                print(f"    {v['filename']}  ->  {v['expected_dir']}")
    else:
        print("\n【挂载到 ComfyUI】")
        ensure_model_links()

    if not args.no_comfy:
        print("\n【ComfyUI 后端】")
        print(f"  ComfyUI 根目录：{COMFY_ROOT or '（未找到）'}"
              + (f"   [来源：{COMFY_ROOT_SOURCE}]" if COMFY_ROOT else ""))
        okc = ensure_comfy(timeout=args.comfy_timeout)
        with STATE_LOCK:
            print(f"  {COMFY_READY['detail']}")
        if not okc:
            print("  提示：ComfyUI 未就绪，仍可打开界面，但出图会报错。")
    else:
        print("\n【ComfyUI 后端】已跳过自动拉起（--no-comfy）")

    url = f"http://{args.host}:{args.port}"
    print("\n" + "=" * 68)
    print(f"  工作台已启动，请在浏览器打开:  {url}")
    print(f"  (按住 Ctrl 并点击上面的地址，或复制到浏览器地址栏)")
    print("  按 Ctrl+C 退出")
    print("=" * 68 + "\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n收到退出信号 …")
    finally:
        httpd.server_close()
        proc = COMFY_PROC.get("proc")
        if proc and COMFY_PROC.get("started_by_us") and proc.poll() is None:
            print("关闭由工作台拉起的 ComfyUI …")
            try:
                proc.terminate()
            except Exception:
                pass


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main() or 0)
