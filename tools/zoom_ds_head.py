from PIL import Image
import os

src = r'D:\applications\comfy-ui\dsko短片\通用角色参考图\ds娘少女三视图.png'
out = r'D:\developing\ai benchmark\QwenImage2.1\fish_ref'
os.makedirs(out, exist_ok=True)

im = Image.open(src).convert('RGB')
W, H = im.size
print('原图', W, H)

# 最左侧视图的头部区域放大
third = W // 3
head = im.crop((int(third * 0.10), 0, int(third * 1.00), int(H * 0.34)))
head = head.resize((head.width * 3, head.height * 3), Image.LANCZOS)
dst = os.path.join(out, 'ds_head_zoom.png')
head.save(dst)
print('头部放大 ->', dst, head.size)
