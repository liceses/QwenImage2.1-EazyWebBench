from PIL import Image
import numpy as np

for tag in ['s11', 's99']:
    p = rf'D:\developing\ai benchmark\QwenImage2.1\cover_base_{tag}.png'
    im = Image.open(p).convert('RGB')
    a = np.asarray(im).astype(np.int16)
    W, H = im.size
    bk = (a[:, :, 0] < 40) & (a[:, :, 1] < 40) & (a[:, :, 2] < 40)
    colcnt = bk.sum(axis=0)
    rowcnt = bk.sum(axis=1)
    panel_cols = np.where(colcnt > 300)[0]
    panel_rows = np.where(rowcnt > 300)[0]
    L = int(H * 4 / 3)
    left = (W - L) // 2
    print(f'--- {tag}: {W}x{H}   4:3 crop window x={left}..{left+L}  (width {L})')
    if len(panel_cols):
        print(f'    black panel cols {panel_cols.min()}..{panel_cols.max()}'
              f'  ({panel_cols.min()/W*100:.1f}%..{panel_cols.max()/W*100:.1f}%)')
        print(f'    black panel rows {panel_rows.min()}..{panel_rows.max()}')
        lm = panel_cols.min() - left
        verdict = 'PASS' if lm >= 0.03 * L else ('TIGHT' if lm >= 0 else 'FAIL-clipped')
        print(f'    left margin {lm}px ({lm/L*100:.1f}%)  -> {verdict}')
    else:
        print('    no large black panel detected')
    print()
