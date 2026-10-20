# -*- coding: utf-8 -*-
r"""从妈妈画的「成品-透明底」三帧生成桌宠素材。

输入：..\..\小D\拆分图\成品-透明底\成品-{睁眼, 单眼眨, 笑眼闭眼}-透明.png
输出：assets\{idle, wink, blink}.png （对齐裁切 + 底部柔化渐隐）

用法：python 生成素材.py
"""
import os

import numpy as np
from PIL import Image

APP = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(APP, "..", "..", "小D", "拆分图", "成品-透明底")
OUT = os.path.join(APP, "assets")

PAIRS = [
    ("成品-睁眼-透明.png", "idle.png"),
    ("成品-单眼眨-透明.png", "wink.png"),
    ("成品-笑眼闭眼-透明.png", "blink.png"),
]

ALPHA_MIN = 30       # 判断"人物"用的 alpha 阈值（调低才吃得到淡色星光装饰）
SOLID = 2            # 一行/一列至少这么多像素才算数（滤掉杂点）
PAD = 12             # 裁切留白
FADE = 0.045         # 底部渐隐比例（画稿在画布底边被切掉了）
X_MAX = 1125         # 右边缘有几点孤立杂色（尾巴旁的碎点），忽略到这儿


def content_box(imgs):
    x0 = y0 = 10 ** 9
    x1 = y1 = -1
    for im in imgs:
        a = np.array(im)[:, :, 3] > ALPHA_MIN
        a[:, X_MAX:] = False
        cols = np.where(a.sum(axis=0) > SOLID)[0]
        rows = np.where(a.sum(axis=1) > SOLID)[0]
        x0, x1 = min(x0, cols.min()), max(x1, cols.max())
        y0, y1 = min(y0, rows.min()), max(y1, rows.max())
    return max(0, x0 - PAD), max(0, y0 - PAD), min(1280, x1 + PAD), min(1280, y1 + PAD)


def fade_bottom(im):
    """底部 alpha 线性渐隐到 0，避免出现一条硬切的断腿线"""
    im = im.convert("RGBA")
    a = np.array(im)
    h = a.shape[0]
    n = max(1, int(h * FADE))
    ramp = np.ones(h, dtype=float)
    ramp[h - n:] = np.linspace(1.0, 0.0, n)
    a[:, :, 3] = (a[:, :, 3] * ramp[:, None]).astype(np.uint8)
    return Image.fromarray(a, "RGBA")


def main():
    imgs = {src: Image.open(os.path.join(SRC, src)).convert("RGBA") for src, _ in PAIRS}
    box = content_box(list(imgs.values()))
    print("content box:", box, "size:", box[2] - box[0], box[3] - box[1])
    os.makedirs(OUT, exist_ok=True)
    for src, dst in PAIRS:
        out = fade_bottom(imgs[src].crop(box))
        out.save(os.path.join(OUT, dst))
        print("wrote", dst, out.size)


if __name__ == "__main__":
    main()
