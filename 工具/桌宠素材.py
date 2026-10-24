# -*- coding: utf-8 -*-
"""桌宠换装素材的公共处理：妈妈的画稿 → 干净的透明底帧（不留白边）

关键点：妈妈在画布上画的图，边缘半透明像素的颜色常常发白（白底混色），
直接缩放会在桌宠上显出「一圈白边」。这里先把透明区域的颜色从邻近的实心像素
"渗"过去，再分开缩放 RGB 和 alpha，就不会有白边了。
"""
import os
import numpy as np
from PIL import Image, ImageFilter

H = 340
TAIL_FRAMES = 4          # 桌宠按 4 个尾巴角度轮播，先都放同一张


def load_rgba(path):
    return Image.open(path).convert('RGBA')


def trim(im, margin=4):
    a = np.array(im.getchannel('A'))
    ys, xs = np.where(a > 8)
    if len(xs) == 0:
        return im
    return im.crop((max(0, xs.min() - margin), max(0, ys.min() - margin),
                    min(im.width, xs.max() + 1 + margin), min(im.height, ys.max() + 1 + margin)))


def _bleed_colors(rgb, alpha, rounds=40):
    """把透明区域的 RGB 用邻近实心像素的颜色填满（边缘渗色），缩放时不会混进白色"""
    rgb = rgb.copy()
    known = alpha > 0.5
    for _ in range(rounds):
        if known.all():
            break
        acc = np.zeros_like(rgb)
        cnt = np.zeros(known.shape, dtype=np.float32)
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            srgb = np.roll(rgb, (dy, dx), axis=(0, 1))
            sknown = np.roll(known, (dy, dx), axis=(0, 1))
            acc += srgb * sknown[..., None]
            cnt += sknown
        fill = (~known) & (cnt > 0)
        if not fill.any():
            break
        rgb[fill] = acc[fill] / cnt[fill][:, None]
        known = known | fill
    return rgb


def to_frame(path, h=H):
    """图片 → 高 h 的透明底帧

    桌宠是用「洋红键控」显示贴图的（半透明像素会被硬阈值化成不透明），
    所以边缘半透明像素必须取"里面的实色"，不然就会显出一圈发白的光边。
    """
    im = trim(load_rgba(path))
    arr = np.array(im).astype(np.float32) / 255.0
    rgb, alpha = arr[..., :3], arr[..., 3]

    # 只用「很实心」的像素当取色源：半透明像素的颜色是和白底混出来的，用它会染出白边
    core_src = alpha > 0.85
    filled_src = _bleed_colors(rgb, core_src.astype(np.float32), rounds=30)
    rgb = np.where(core_src[..., None], rgb, filled_src)
    rgb = np.clip(rgb, 0, 1)

    w = max(1, int(round(im.width * h / im.height)))
    rgb_img = Image.fromarray((rgb * 255).round().astype(np.uint8), 'RGB')
    a_img = Image.fromarray((alpha * 255).round().astype(np.uint8), 'L')
    rgb_small = np.array(rgb_img.resize((w, h), Image.LANCZOS)).astype(np.float32) / 255.0
    a_small = np.array(a_img.resize((w, h), Image.LANCZOS)).astype(np.float32) / 255.0

    # 缩放后又出现了一层半透明边，再用实心像素的颜色填一次
    core = a_small > 0.75
    filled = _bleed_colors(rgb_small, core.astype(np.float32), rounds=24)
    final_rgb = np.where(core[..., None], rgb_small, filled)

    out = Image.fromarray((final_rgb.clip(0, 1) * 255).round().astype(np.uint8), 'RGB').convert('RGBA')
    a_out = (a_small * 255).round().astype(np.uint8)
    a_out[a_out < 12] = 0

    # 最后再向外「长」1 像素，并把最外圈压成深色描边：
    # 桌宠是洋红键控的硬边显示，外圈不留浅色，才不会看到一圈白边
    a_img2 = Image.fromarray(a_out, 'L')
    a_dil = np.array(a_img2.filter(ImageFilter.MaxFilter(3)))
    ring = (a_dil > 0) & (a_out == 0)
    if ring.any():
        filled2 = _bleed_colors(final_rgb, (a_out > 60).astype(np.float32), rounds=4)
        final_rgb = np.where(ring[..., None], filled2, final_rgb)
        a_out = a_dil
        a_out[a_out < 12] = 0

    # 最外一圈半透明像素 → 压成深色（跟画里的描边一个颜色）
    band = (a_out > 20) & (a_out < 250)
    final_rgb = np.where(band[..., None], final_rgb * 0.45, final_rgb)
    # 向外「长」出来的一圈 → 直接用深色描边色，盖住键控边缘的浅色缝隙
    if ring.any():
        final_rgb = np.where(ring[..., None], np.array([0.22, 0.20, 0.22], dtype=np.float32), final_rgb)

    out = Image.fromarray((final_rgb.clip(0, 1) * 255).round().astype(np.uint8), 'RGB').convert('RGBA')
    out.putalpha(Image.fromarray(a_out, 'L'))
    return out


def write_outfit(name, face_paths, out_root):
    """把 3 张表情图写成一套衣服：outfits/<name>/{idle,blink,wink}_{0..3}_0.png"""
    dst = os.path.join(out_root, name)
    os.makedirs(dst, exist_ok=True)
    states = ['idle', 'blink', 'wink']
    for i, p in enumerate(face_paths):
        state = states[min(i, len(states) - 1)]
        im = to_frame(p)
        for ti in range(TAIL_FRAMES):
            im.save(os.path.join(dst, '%s_%d_0.png' % (state, ti)))
        print('ok', state, im.size, '->', os.path.join(dst, state + '_*.png'))
    return dst
