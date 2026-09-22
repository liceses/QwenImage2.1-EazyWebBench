# -*- coding: utf-8 -*-
"""
修正角色描述错误：DS娘的耳朵是「鳍状鲸耳」，不是「猫耳」。

参考图（ds_front_only.png）实际形状：深藏青、宽扁、向外下方伸出、带浅色内缘的鳍状耳，
不是尖三角朝上的猫耳。此前所有脚本写成「猫耳」，导致模型画成通用猫耳、鲸耳丢失。

本脚本把 style_run*.py 里的「猫耳」统一替换成带限定说明的「鳍状鲸耳」。
"""
import io
import os
import re

ROOT = r'D:\developing\ai benchmark\QwenImage2.1\tools'
FILES = ['style_run.py', 'style_run3.py', 'style_run4.py',
         'style_run5.py', 'style_run6.py', 'style_run7.py']

# 替换规则：先处理"深藏青色的猫耳"这类带修饰的，再处理裸"猫耳"
RULES = [
    # 带修饰语的
    ('深藏青色的猫耳', '向外下方伸出的深藏青色鳍状鲸耳（宽扁、带浅色内缘，不是尖三角的猫耳）'),
    ('向两侧伸出的深藏青猫耳', '向两侧伸出的深藏青色鳍状鲸耳'),
    ('深藏青猫耳', '深藏青色鳍状鲸耳'),
    # 裸"猫耳"（含"猫耳的尖角"等）
    ('猫耳', '鳍状鲸耳'),
]

report = []
for fn in FILES:
    p = os.path.join(ROOT, fn)
    if not os.path.exists(p):
        report.append(f'  跳过（不存在）: {fn}')
        continue
    with io.open(p, 'r', encoding='utf-8') as f:
        src = f.read()
    before = src.count('猫耳')
    for a, b in RULES:
        src = src.replace(a, b)
    with io.open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(src)
    after = src.count('猫耳')
    left = len(re.findall(r'(?<!不是尖三角的)猫耳', src))
    report.append(f'  {fn}: 原有 {before} 处"猫耳" -> 替换后剩余 {after} 处（其中作为反例保留 {after - left + 0} 处）')

print('替换完成：')
for r in report:
    print(r)

print('\n校验：所有文件的 DS 描述行')
for fn in FILES:
    p = os.path.join(ROOT, fn)
    if not os.path.exists(p):
        continue
    with io.open(p, 'r', encoding='utf-8') as f:
        for i, ln in enumerate(f, 1):
            if '鳍状鲸耳' in ln and ('DS = ' in ln or 'DS_FACE' in ln):
                print(f'  {fn}:{i}')
                print('    ' + ln.strip()[:160])
