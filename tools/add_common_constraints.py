# -*- coding: utf-8 -*-
"""
系统性修复：给所有跑图器的每个 prompt 自动追加"通用约束"。

背景：反复出现"参考图手持道具泄漏"（游戏光盘/手柄被画进新图），
以及"参考图原背景色（黄绿）泄漏"。根因是提示词里逐条手写约束，容易漏。

做法：在 main() 里组装 payload 前，统一给 prompt 追加一段通用约束；
单人参考图的用例再追加"不是角色设定表/三视图"。
"""
import io
import os
import re

ROOT = r'D:\developing\ai benchmark\QwenImage2.1\tools'
FILES = ['style_run.py', 'style_run3.py', 'style_run4.py',
         'style_run5.py', 'style_run6.py', 'style_run7.py', 'style_run8.py']

MARK = '# ---- 通用约束（自动追加，勿删）----'
BLOCK = f'''
    {MARK}
    prompt = prompt + (
        "\\n\\n【通用约束】画面中不要出现参考图里的任何手持道具——"
        "不要游戏光盘、不要手柄、不要任何被拿在手里的物件，双手是空的；"
        "不要沿用参考图的黄绿色底色。")
    if len(refs) == 1:
        prompt = prompt + (
            "\\n\\n【通用约束二】画面里只有这一个人物、只有一个正面形象，"
            "不是角色设定表、不是三视图、不要分栏分屏。")
    # ---- 通用约束结束 ----
'''

changed = []
for fn in FILES:
    p = os.path.join(ROOT, fn)
    if not os.path.exists(p):
        continue
    with io.open(p, 'r', encoding='utf-8') as f:
        src = f.read()
    if MARK in src:
        changed.append(f'  {fn}: 已有通用约束，跳过')
        continue

    # 在 payload = {...} 之前插入
    m = re.search(r'^(\s*)payload = \{"prompt": prompt', src, flags=re.M)
    if not m:
        changed.append(f'  {fn}: 未找到 payload 组装处（跳过）')
        continue
    src = src[:m.start()] + BLOCK.lstrip('\n') + src[m.start():]
    with io.open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(src)
    changed.append(f'  {fn}: 已插入通用约束')

print('结果：')
for c in changed:
    print(c)

print('\n语法自检：')
import py_compile
for fn in FILES:
    p = os.path.join(ROOT, fn)
    if not os.path.exists(p):
        continue
    try:
        py_compile.compile(p, doraise=True)
        print(f'  {fn}: OK')
    except Exception as e:
        print(f'  {fn}: 语法错误 -> {e}')
