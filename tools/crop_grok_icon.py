from PIL import Image
import os

src = r'D:\developing\ai benchmark\QwenImage2.1\grok_logo\Grok-2025-logo.png'
out = r'D:\developing\ai benchmark\QwenImage2.1\grok_logo'
im = Image.open(src).convert('RGBA')
W, H = im.size
print('logo 尺寸', W, H)

# 左侧的黑色圆角方块图标：取左边一个正方形区域
side = H
icon = im.crop((0, 0, side, H))
# 自动去掉四周多余的空白（找非透明/非白边界）
bbox = icon.getbbox()
print('icon bbox', bbox)
if bbox:
    icon = icon.crop(bbox)
icon = icon.resize((512, 512), Image.LANCZOS)
dst = os.path.join(out, 'grok_app_icon.png')
icon.save(dst)
print('已存', dst, icon.size)

# 同时把白底版本也存一份（方便看）
bg = Image.new('RGB', icon.size, (255, 255, 255))
bg.paste(icon, (0, 0), icon)
bg.save(os.path.join(out, 'grok_app_icon_white.png'))
print('已存白底版')
