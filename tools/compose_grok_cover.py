# -*- coding: utf-8 -*-
"""测量 Grok 封面底图的 4:3 安全区，并合成官方图标。"""
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os

ROOT = r'D:\developing\ai benchmark\QwenImage2.1\grok_logo'
BASE = os.path.join(ROOT, 'cover_base.png')
ICON = os.path.join(ROOT, 'grok_app_icon.png')
OUT = os.path.join(ROOT, 'cover_final_16x9.png')
OUT43 = os.path.join(ROOT, 'cover_final_4x3.png')

im = Image.open(BASE).convert('RGB')
W, H = im.size
L = int(H * 4 / 3)
left = (W - L) // 2
print(f'底图 {W}x{H}   4:3 裁切窗 x = {left} .. {left+L}（左右各切 {left}px）')

# --- 检黑色文字面板的横向范围 ---
a = np.asarray(im).astype(np.int16)
bk = (a[:, :, 0] < 45) & (a[:, :, 1] < 45) & (a[:, :, 2] < 45)
colcnt = bk.sum(axis=0)
rows = np.where(bk.sum(axis=1) > 300)[0]
cols = np.where(colcnt > 300)[0]
if len(cols):
    print(f'  黑面板横向 {cols.min()}..{cols.max()}  纵向 {rows.min() if len(rows) else "?"}..{rows.max() if len(rows) else "?"}')
    print(f'  距左裁切线 {cols.min()-left:+d}px ({ (cols.min()-left)/L*100:.1f}%)')
    print(f'  距右裁切线 {left+L-cols.max():+d}px')
else:
    print('  未检出黑面板')

# --- 人物（肤色/浅蓝发）范围 ---
skin = (a[:, :, 0] > 225) & (a[:, :, 1] > 195) & (a[:, :, 2] > 185) & (a[:, :, 0] - a[:, :, 2] > 15)
sc = skin.sum(axis=0)
scols = np.where(sc > 20)[0]
if len(scols):
    print(f'  肤色区域横向 {scols.min()}..{scols.max()}  （人脸/腿）')

# --- 合成官方图标：放在安全区左上角（先合成，最后统一裁切校验）---
SIZE = 150
PAD = 12
lx, ly = 310, 40
# 采样该处背景色做圆角垫底
crop = im.crop((lx - 40, ly - 20, lx + SIZE + 60, ly + SIZE + 40))
colors = crop.resize((1, 1), Image.LANCZOS).getpixel((0, 0))
print(f'  图标处背景均色 = {colors}')

logo = Image.open(ICON).convert('RGBA').resize((SIZE, SIZE), Image.LANCZOS)
draw = ImageDraw.Draw(im)
draw.rounded_rectangle((lx - PAD, ly - PAD, lx + SIZE + PAD, ly + SIZE + PAD), radius=18, fill=colors)
im.paste(logo, (lx, ly), logo)

# Grok 字标
font = None
for fp in (r'C:\Windows\Fonts\arialbd.ttf', r'C:\Windows\Fonts\segoeuib.ttf'):
    if os.path.exists(fp):
        font = ImageFont.truetype(fp, 54)
        print(f'  字标字体 {fp}')
        break
tx, ty = lx + SIZE + 24, ly + SIZE // 2 - 36
ImageDraw.Draw(im).text((tx, ty), 'Grok 4.7', font=font, fill=(20, 20, 24))

im.save(OUT)
print(f'  已存成品 {OUT}')

# --- 4:3 裁切校验（必须在合成之后，否则看不到图标）---
im.crop((left, 0, left + L, H)).save(OUT43)
print(f'  已存裁切校验图 {OUT43}')

# --- 关键元素安全区检查 ---
print('\n安全检查（4:3 窗 %d..%d）:' % (left, left + L))
checks = [('图标左缘', lx, True), ('垫底左缘', lx - PAD, True),
          ('字标右缘', tx + 240, False)]
for name, x, is_left in checks:
    if is_left:
        ok = x >= left + 12
        print(f'  {name:10s} x={x:5d}  距左裁切线 {x-left:+5d}px  {"OK" if ok else "会被切!"}')
    else:
        ok = x <= left + L - 12
        print(f'  {name:10s} x={x:5d}  距右裁切线 {left+L-x:+5d}px  {"OK" if ok else "会被切!"}')
