from PIL import Image
import os

src = r'D:\applications\comfy-ui\dsko短片\通用角色参考图\ds娘少女三视图.png'
out = r'D:\developing\ai benchmark\QwenImage2.1\fish_ref'
os.makedirs(out, exist_ok=True)

im = Image.open(src).convert('RGB')
W, H = im.size
print('原图', W, H)

# 三个视图横向排布：裁最左侧的正面视图（留少量边距）
third = W // 3
crop = im.crop((0, 0, third, H))
# 再稍微内缩，去掉相邻视图的边缘
w2, h2 = crop.size
crop = crop.crop((int(w2 * 0.06), 0, int(w2 * 0.96), h2))
dst = os.path.join(out, 'ds_front_only.png')
crop.save(dst)
print('裁出正面单视图 ->', dst, crop.size)
