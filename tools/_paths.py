#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""共享路径解析：让所有工具脚本都能在别人的机器上直接用。

为什么要这个模块：
    脚本原先写死了作者本机的绝对路径（`D:\\applications\\comfy-ui\\...`、
    `D:\\developing\\ai benchmark\\QwenImage2.1\\...`），别人 clone 下来必然跑不通。
    统一改成"环境变量优先 → 基于 __file__ 相对推导 → 常见位置探测"。

用法：
    from _paths import PROJECT_ROOT, comfy_root, comfy_dir, comfy_input, comfy_output

    comfy_root()    -> ComfyUI 根目录（含 ComfyUI/main.py 的那一层），找不到返回 None
    comfy_dir(...)  -> 根目录下的子目录，例如 comfy_dir("output")
"""
import os
import sys

# 本文件在 tools/ 下，项目根就是它的上一级
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 常见 ComfyUI 安装位置（先通用位置，作者本机路径只是兜底）
_CANDIDATES = [
    os.path.join(PROJECT_ROOT, "ComfyUI"),
    os.path.expanduser(r"~\ComfyUI_windows_portable"),
    os.path.expanduser(r"~\Desktop\ComfyUI_windows_portable"),
    os.path.expanduser(r"~\Documents\ComfyUI_windows_portable"),
    r"C:\ComfyUI_windows_portable",
    r"D:\ComfyUI_windows_portable",
    r"E:\ComfyUI_windows_portable",
    r"C:\ComfyUI",
    r"D:\ComfyUI",
    r"C:\Program Files\ComfyUI",
    r"D:\applications\comfy-ui\ComfyUI_windows_portable",
]


def _looks_like_comfy_root(p):
    return bool(p) and os.path.isfile(os.path.join(p, "ComfyUI", "main.py"))


def comfy_root():
    """解析 ComfyUI 根目录：环境变量 → 项目内 config.json → 常见位置探测。

    找不到时返回 None（调用方应给出可读提示，而不是抛异常）。
    """
    # 1) 环境变量
    p = os.environ.get("QWEN21_COMFY_ROOT")
    if _looks_like_comfy_root(p):
        return p

    # 2) 项目内 config.json（与 server.py 同一约定）
    cfg = os.path.join(PROJECT_ROOT, "config.json")
    if os.path.isfile(cfg):
        try:
            import json
            with open(cfg, "r", encoding="utf-8") as f:
                v = (json.load(f) or {}).get("comfy_root")
            if _looks_like_comfy_root(v):
                return v
        except Exception:
            pass

    # 3) 常见位置
    for c in _CANDIDATES:
        if _looks_like_comfy_root(c):
            return c
    return None


def comfy_dir(*parts):
    """ComfyUI 根目录下的路径，例如 comfy_dir("output")、comfy_dir("ComfyUI","input")。

    解析不到根目录时**退回项目内同名目录**，避免调用方直接崩：
    调用方若需要严格判断，请先自行调用 comfy_root() 检查。
    """
    root = comfy_root()
    base = root if root else PROJECT_ROOT
    if root:
        return os.path.join(root, "ComfyUI", *parts)
    return os.path.join(base, *parts)


def require_comfy_root(tool_name="本脚本"):
    """拿不到 ComfyUI 路径时，打印一段可照做的提示并返回 None。"""
    root = comfy_root()
    if root:
        return root
    print(
        f"[{tool_name}] 未找到 ComfyUI 安装目录。请任选一种方式配置：\n"
        '  1) 在项目根目录建 config.json：{"comfy_root": "<你的ComfyUI根目录>"}\n'
        "  2) 设置环境变量 QWEN21_COMFY_ROOT=<你的ComfyUI根目录>\n"
        "  「ComfyUI 根目录」指包含 ComfyUI/main.py 的那一层\n"
        r"  （便携版形如 ...\ComfyUI_windows_portable）。" + "\n"
        "  3) 若 ComfyUI 已在 127.0.0.1:8188 运行，多数脚本可直接连它，无需此项。",
        file=sys.stderr)
    return None


def ensure_comfy_importable():
    """某些脚本要 import 项目根下的 server.py，这里保证 sys.path 正确。"""
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)


if __name__ == "__main__":
    # 直接运行本文件 = 环境自检
    print("PROJECT_ROOT :", PROJECT_ROOT)
    r = comfy_root()
    print("comfy_root   :", r if r else "（未找到，需要配置 config.json 或 QWEN21_COMFY_ROOT）")
    if r:
        print("  ComfyUI/input :", comfy_dir("input"))
        print("  ComfyUI/output:", comfy_dir("output"))
