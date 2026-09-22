# -*- coding: utf-8 -*-
"""
切换到鲸鱼娘的正确参考图，并重写角色描述。

新参考图：D:\applications\comfy-ui\dsko短片\通用角色参考图\ds娘.png
         -> 上传为 ref_ec15289879.png

依据新立绘重写（补齐此前漏掉的关键特征）：
  · 耳部＝一对宽扁鳍状鲸耳（深藏青外缘 + 白色内侧），向外下方伸出
  · 身后一条深藏青鲸鱼尾鳍（宽大、内侧浅蓝）—— 此前完全没写
  · 白色衬衫式上衣 + 深藏青马甲（两排金扣 + 金滚边）
  · 白色荷叶边围裙（右下角一个小鲸鱼图案）
  · 深藏青大裙摆：金色藤蔓纹 + 正中浅蓝竖条纹面板 + 两侧小蝴蝶结 + 下摆白荷叶边衬裙
  · 白色荷叶边袖口（星形装饰）、领口深色蝴蝶结配蓝宝石扣
  · 发色深宝蓝渐变到浅蓝
"""
import io
import os
import re

ROOT = r'D:\developing\ai benchmark\QwenImage2.1\tools'
FILES = ['style_run.py', 'style_run3.py', 'style_run4.py',
         'style_run5.py', 'style_run6.py', 'style_run7.py']

NEW_REF = 'ref_ec15289879.png'

NEW_DS = ('深宝蓝色长卷发、发尾渐渐变成浅蓝色，头顶一根弯钩状的呆毛，一双蓝色的眼睛、开朗的笑容。'
          '耳部是一对宽扁的鳍状鲸耳——深藏青色的外缘配上白色的内侧，向两侧下方伸出。'
          '头上戴着白色荷叶边女仆头饰，右侧系一只浅蓝色蝴蝶结。'
          '身上是白色衬衫式上衣（前襟有竖褶）外罩一件深藏青色的紧身马甲，马甲正面有两排金色纽扣与金色滚边；'
          '深藏青色的长袖配白色荷叶边袖口（袖口上有星形装饰），领口系一只深色蝴蝶结、正中一颗蓝宝石扣。'
          '身前系一条白色荷叶边围裙，围裙的右下角有一个小小的鲸鱼图案。'
          '下身是深藏青色的大裙摆：裙面压着金色的藤蔓纹样，正中央是一片浅蓝色的竖条纹面板、面板两侧各系一只小蝴蝶结，'
          '裙摆下方露出一圈白色荷叶边衬裙。白色短袜配深藏青色的玛丽珍鞋。'
          '身后伸出一条深藏青色的鲸鱼尾鳍（尾鳍宽大、内侧偏浅蓝）。')

report = []
for fn in FILES:
    p = os.path.join(ROOT, fn)
    if not os.path.exists(p):
        continue
    with io.open(p, 'r', encoding='utf-8') as f:
        src = f.read()

    orig = src

    # 1) 换参考图变量
    src = re.sub(r'DS_REF\s*=\s*"[^"]+"', f'DS_REF = "{NEW_REF}"', src)

    # 2) 替换 DS = ( ... ) 多行常量
    src = re.sub(r'^DS\s*=\s*\(.*?\)\s*$',
                 'DS = "' + NEW_DS + '"', src, flags=re.S | re.M)
    # 3) 替换 DS_FACE = ( ... ) 多行常量
    src = re.sub(r'^DS_FACE\s*=\s*\(.*?\)\s*$',
                 'DS_FACE = "' + NEW_DS + '"', src, flags=re.S | re.M)

    if src != orig:
        with io.open(p, 'w', encoding='utf-8', newline='') as f:
            f.write(src)
        report.append(f'  {fn}: 已更新')
    else:
        report.append(f'  {fn}: 未匹配到需要替换的常量（检查）')

print('切换结果：')
for r in report:
    print(r)

print('\n校验：')
for fn in FILES:
    p = os.path.join(ROOT, fn)
    with io.open(p, 'r', encoding='utf-8') as f:
        s = f.read()
    has_ref = NEW_REF in s
    has_whale = '鲸鱼尾鳍' in s
    old = s.count('鳍状鲸耳（两个')
    print(f'  {fn:16s} 新参考图={has_ref}  含鲸鱼尾鳍={has_whale}')
