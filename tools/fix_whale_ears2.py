# -*- coding: utf-8 -*-
"""
第二次修正 DS娘耳部描述。

参考图放大确认（ds_head_zoom.png）：每侧是**两套耳结构叠在一起** ——
  ① 深藏青色的尖三角猫耳
  ② 叠在其外侧/下方的一对浅紫白色宽扁鲸鳍状耳（鲸鱼胸鳍形、宽而扁、边缘圆钝）
两者缺一不可。

上一轮我只写「鳍状鲸耳」并把猫耳当反例排除 —— 那是错的。现在改成「两者同时存在」。
"""
import io
import os

ROOT = r'D:\developing\ai benchmark\QwenImage2.1\tools'
FILES = ['style_run.py', 'style_run3.py', 'style_run4.py',
         'style_run5.py', 'style_run6.py', 'style_run7.py']

SHORT = '深藏青尖三角猫耳与叠在其外侧的浅紫白宽扁鲸鳍耳（两种耳必须同时存在）'

# 长的带括号变体先替换
RULES = [
    ('向外下方伸出的深藏青色鳍状鲸耳（宽扁、带浅色内缘，不是尖三角向上翘的猫耳）', SHORT),
    ('向外下方伸出的深藏青色鳍状鲸耳（宽扁、带浅色内缘，不是尖三角的猫耳）', SHORT),
    ('向外下方伸出的深藏青色鳍状鲸耳', SHORT),
    ('向两侧伸出的深藏青色鳍状鲸耳', SHORT),
    ('深藏青色鳍状鲸耳', SHORT),
    ('鳍状鲸耳少女', '耳部特征为' + SHORT + '的少女'),
    ('鳍状鲸耳', SHORT),
]

for fn in FILES:
    p = os.path.join(ROOT, fn)
    if not os.path.exists(p):
        continue
    with io.open(p, 'r', encoding='utf-8') as f:
        src = f.read()
    n0 = src.count('鳍状鲸耳')
    for a, b in RULES:
        src = src.replace(a, b)
    with io.open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(src)
    n1 = src.count('鳍状鲸耳')
    n2 = src.count('猫耳与鲸鳍耳') + src.count('猫耳与叠在其外侧')
    print(f'{fn}: 替换 {n0} 处，残留旧写法 {n1} 处')

print('\n校验各文件的角色描述行：')
for fn in ['style_run.py', 'style_run7.py']:
    p = os.path.join(ROOT, fn)
    with io.open(p, 'r', encoding='utf-8') as f:
        for i, ln in enumerate(f, 1):
            if ('DS = ' in ln or 'DS_FACE' in ln) and '鲸鳍耳' in ln:
                print(f'  {fn}:{i}  {ln.strip()[:170]}')
