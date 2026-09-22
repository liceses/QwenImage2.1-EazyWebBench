# -*- coding: utf-8 -*-
"""
把官方 ZCode 图标合成到封面预留区，并输出 16:9 成品与 4:3 裁切校验图。

为什么不在生成时让模型画图标：品牌标志不能让扩散模型重画（会变形、笔画错）。
正确做法 = 生成时预留干净区域 → 把官方 PNG 贴进去，像素级正确。
"""
from PIL import Image, ImageDraw, ImageFont
import os

ROOT = r'D:\developing\ai benchmark\QwenImage2.1'
BASE = os.path.join(ROOT, 'cover_base_s99.png')
LOGO = os.path.join(ROOT, 'zcode_logo', '1024x1024.png')
OUT = os.path.join(ROOT, 'cover_final_16x9.png')
OUT43 = os.path.join(ROOT, 'cover_final_4x3.png')

im = Image.open(BASE).convert('RGB')
W, H = im.size
print(f'底图 {W}x{H}')

# ---- 采样目标区域附近的背景色，用于垫底 ----
patch = im.crop((250, 10, 520, 190))
colors = patch.resize((1, 1), Image.LANCZOS).getpixel((0, 0))
print(f'预留区附近均色 = {colors}')

# ---- 布局：图标 + 字标，整体放在安全区左上（避开 235 裁切线与 y=196 的黑面板）----
SIZE = 150                      # 图标边长
PAD = 14                        # 垫底内边距
lx, ly = 286, 20                # 图标左上角
logo = Image.open(LOGO).convert('RGBA').resize((SIZE, SIZE), Image.LANCZOS)

# 垫底圆角块（保证图标与孟菲斯装饰干净分离）
pad_box = (lx - PAD, ly - PAD, lx + SIZE + PAD, ly + SIZE + PAD)
draw = ImageDraw.Draw(im)
draw.rounded_rectangle(pad_box, radius=18, fill=colors)

# 贴图标（保留 alpha）
im.paste(logo, (lx, ly), logo)

# ---- 字标 ZCode ----
font = None
for fp in (r'C:\Windows\Fonts\arialbd.ttf', r'C:\Windows\Fonts\msyhbd.ttc',
           r'C:\Windows\Fonts\segoeuib.ttf'):
    if os.path.exists(fp):
        try:
            font = ImageFont.truetype(fp, 52)
            print(f'字标字体: {fp}')
            break
        except Exception as e:
            print(f'  {fp} 加载失败: {e}')
if font is None:
    font = ImageFont.load_default()
    print('警告：未找到字体，字标使用默认字体')

draw = ImageDraw.Draw(im)
tx = lx + SIZE + 22
ty = ly + SIZE // 2 - 34
draw.text((tx, ty), 'ZCode', font=font, fill=(24, 24, 28))

im.save(OUT)
print(f'已保存 16:9 成品: {OUT}')

# ---- 4:3 裁切校验 ----
L = int(H * 4 / 3)
left = (W - L) // 2
im.crop((left, 0, left + L, H)).save(OUT43)
print(f'已保存 4:3 裁切: {OUT43}  (裁掉左右各 {left}px)')

# ---- 关键元素是否都在安全区内 ----
print()
print(f'4:3 安全区: x = {left} .. {left + L}')
checks = [
    ('ZCode 图标左缘', lx, 1),
    ('ZCode 图标右缘', lx + SIZE, 0),
    ('垫底块左缘', pad_box[0], 1),
    ('字标 ZCode 右缘', tx + 190, 0),
]
for name, x, is_left in checks:
    if is_left:
        ok = x >= left + 12
        print(f'  {name:16s} x={x:5d}  距左裁切线 {x-left:+5d}px  {"OK" if ok else "会被切!"}')
    else:
        ok = x <= left + L - 12
        print(f'  {name:16s} x={x:5d}  距右裁切线 {left+L-x:+5d}px  {"OK" if ok else "会被切!"}')
