# -*- coding: utf-8 -*-
"""分析妈妈画的 PSD：图层结构、顺序、透明度、用色 —— 小D 学画画用

用法：
    python 分析PSD.py <psd路径> <输出目录>

输出：
    结构.txt            图层树（名字/位置/可见/不透明度/混合模式）
    总览.png            整张合成图（白底）
    图层一览.png        所有图层的缩略图拼版（带编号）
    用色.txt            整体 + 每个图层的主要颜色
"""
import os
import sys

from psd_tools import PSDImage
from psd_tools.api.layers import Group
from PIL import Image, ImageDraw, ImageFont

FONT = r"C:\Windows\Fonts\msyh.ttc"


def walk(layer, depth, out, index, thumbs, palette):
    for ch in layer:
        if isinstance(ch, Group):
            out.write("%s[组] %s\n" % ("  " * depth, ch.name))
            walk(ch, depth + 1, out, index, thumbs, palette)
            continue
        index[0] += 1
        i = index[0]
        info = ("%s%02d. %s | bbox=%s | 可见=%s | 不透明度=%d | 混合=%s"
                % ("  " * depth, i, ch.name, tuple(ch.bbox) if ch.bbox else None,
                   ch.visible, ch.opacity, ch.blend_mode))
        out.write(info + "\n")
        try:
            img = ch.composite()
            if img is None:
                return
            img = img.convert("RGBA")
            thumbs.append((i, ch.name, img))
            a = img.split()[3]
            if a.getbbox():
                small = img.resize((48, 48), Image.LANCZOS)
                colors = []
                for r, g, b, al in small.getdata():
                    if al > 120:
                        colors.append((r // 24 * 24, g // 24 * 24, b // 24 * 24))
                from collections import Counter
                palette.append((i, ch.name, Counter(colors).most_common(3)))
        except Exception as e:
            out.write("   （取图层失败：%r）\n" % (e,))


def contact_sheet(thumbs, path, cols=6, cell=190):
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * (cell + 22)), (250, 248, 252))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype(FONT, 13)
    except Exception:
        font = ImageFont.load_default()
    for k, (i, name, img) in enumerate(thumbs):
        c, r = k % cols, k // cols
        x, y = c * cell, r * (cell + 22)
        box = cell - 16
        im = img.copy()
        im.thumbnail((box, box), Image.LANCZOS)
        # 透明底铺一层浅色棋盘
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        bg.alpha_composite(im)
        sheet.paste(bg.convert("RGB"), (x + (cell - im.width) // 2, y + (box - im.height) // 2 + 4))
        d.text((x + 6, y + cell + 2), "%02d %s" % (i, name[:12]), fill=(90, 80, 120), font=font)
    sheet.save(path)


def main():
    psd_path = sys.argv[1]
    outdir = sys.argv[2]
    os.makedirs(outdir, exist_ok=True)

    psd = PSDImage.open(psd_path)
    with open(os.path.join(outdir, "结构.txt"), "w", encoding="utf-8") as out:
        out.write("PSD: %s\n尺寸: %s  图层数: %d\n\n" % (os.path.basename(psd_path), psd.size,
                                                         len(list(psd.descendants()))))
        index = [0]
        thumbs, palette = [], []
        walk(psd, 0, out, index, thumbs, palette)

    psd.composite().convert("RGBA").save(os.path.join(outdir, "总览.png"))
    contact_sheet(thumbs, os.path.join(outdir, "图层一览.png"))

    with open(os.path.join(outdir, "用色.txt"), "w", encoding="utf-8") as f:
        f.write("# 每个图层最常见的颜色（量化到 24 级）\n")
        for i, name, top in palette:
            f.write("%02d %-16s %s\n" % (i, name, top))
    print("done", outdir, "layers:", len(thumbs))


if __name__ == "__main__":
    main()
