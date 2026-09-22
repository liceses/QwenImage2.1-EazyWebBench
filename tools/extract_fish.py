from PIL import Image
import os

src = r'D:\Pictures\image_ACG\蓝色大肥鱼表情包'
out = r'D:\developing\ai benchmark\QwenImage2.1\fish_ref'
os.makedirs(out, exist_ok=True)

cands = [
    '蓝色大肥鱼_呆 1_2026-08-18-14-10-05.gif',
    '蓝色大肥鱼_打招呼 1_2026-08-18-14-14-29.gif',
    '蓝色大肥鱼_点头_2026-08-18-14-15-19.gif',
    '蓝色大肥鱼_点赞_2026-08-18-14-38-05.gif',
]
for i, c in enumerate(cands):
    p = os.path.join(src, c)
    if not os.path.exists(p):
        print('  missing', c)
        continue
    im = Image.open(p)
    n = getattr(im, 'n_frames', 1)
    print(f'  {c}: size={im.size} frames={n} mode={im.mode}')
    im.seek(0)
    fr = im.convert('RGBA')
    bg = Image.new('RGB', fr.size, (255, 255, 255))
    bg.paste(fr, (0, 0), fr)
    dst = os.path.join(out, f'cand{i}.png')
    bg.save(dst)
    print('    ->', dst)
