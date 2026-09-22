# -*- coding: utf-8 -*-
"""
给所有跑图器追加【审美要求】通用段（依据 Pixiv 日榜/周榜高分作品的共通特征提炼）。

高分作品的共通点：
  · 单色主调 + 极小面积的对比色点缀（周榜#1 蓝白统摄只用一点红；日榜#2 近乎单色）
  · 明确的三层明暗结构，暗部有内容不死黑
  · painterly 柔和过渡比硬边平涂更高级（日榜#52）
  · 环境/氛围参与叙事，不是纯色背景（日榜#1 的暖金木质内景）
  · 留白与呼吸感（周榜#2）
  · 主体偏离正中、用动态与对角线（日榜#1 的前倾姿势）
"""
import io
import os
import re

ROOT = r'D:\developing\ai benchmark\QwenImage2.1\tools'
FILES = ['style_run.py', 'style_run3.py', 'style_run4.py', 'style_run5.py',
         'style_run6.py', 'style_run7.py', 'style_run8.py', 'style_run9.py']

MARK = '# ---- 审美要求（自动追加，勿删）----'
PARTS = [
    '① 单色主导——全画由一个主色调统摄（冷调或暖调只选一个），其余颜色只作极小面积的对比点缀，'
    '避免多种饱和色平均用力；',
    '② 明暗结构——明确分出亮部、中间调与暗部三层，暗部里要有内容而不是死黑'
    '（平涂类画法则用色块的冷暖与明度差建立同样的层次）；',
    '③ 刻画方式——形体之间的过渡要柔和、有虚实变化，不要处处硬边平涂（该清晰的地方清晰、'
    '该虚过去的地方要敢于虚）；',
    '④ 构图——主体偏离正中、放在三分线附近，留出有呼吸感的空白，不要填满画面；',
    '⑤ 主次——视觉中心（脸、眼睛、手）最精致，向外逐渐放松；',
    '⑥ 气质——追求美术馆藏品与画册印刷般的沉静克制，而不是商品海报式的鲜艳饱满。',
]
CLS = '"\\n\\n【审美要求】在符合上述媒介特性的前提下：' + ''.join(PARTS) + '"'
BLOCK = f'''    {MARK}
    prompt = prompt + (
        {CLS})
    # ---- 审美要求结束 ----
'''

done = []
for fn in FILES:
    p = os.path.join(ROOT, fn)
    if not os.path.exists(p):
        continue
    with io.open(p, 'r', encoding='utf-8') as f:
        src = f.read()
    if MARK in src:
        # 已存在 -> 替换整段（便于升级）
        src = re.sub(r'[ \t]*# ---- 审美要求（自动追加，勿删）----.*?# ---- 审美要求结束 ----\n',
                     BLOCK, src, flags=re.S)
        with io.open(p, 'w', encoding='utf-8', newline='') as f:
            f.write(src)
        done.append(f'  {fn}: 已更新')
        continue
    m = re.search(r'^(\s*)payload = \{"prompt": prompt', src, flags=re.M)
    if not m:
        done.append(f'  {fn}: 未找到 payload 处，跳过')
        continue
    src = src[:m.start()] + BLOCK + src[m.start():]
    with io.open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(src)
    done.append(f'  {fn}: 已插入')

print('结果：')
for d in done:
    print(d)

print('\n语法自检：')
import py_compile
ok = True
for fn in FILES:
    p = os.path.join(ROOT, fn)
    if not os.path.exists(p):
        continue
    try:
        py_compile.compile(p, doraise=True)
    except Exception as e:
        ok = False
        print(f'  {fn}: 语法错误 -> {e}')
print('  全部通过' if ok else '  有错误')
