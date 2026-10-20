# -*- coding: utf-8 -*-
"""把妈妈手画的表情小件，拼到小D 的底图上，生成成品表情包。

输入：
  小D/表情包/原图/*.png                       妈妈画的透明底小件（1024×1024 画布）
  小D/拆分图/成品-透明底/成品-睁眼-透明.png     小D 的底图（1280×1280）
  小D/拆分图/成品-透明底/成品-笑眼闭眼-透明.png 闭眼帧（困困 用）
  小D/拆分图/分层/*.png                        妈妈的分层原件（补干净皮肤用）
输出：
  小D/表情包/成品/<表情>-1024.png   成品（透明底 1024×1024）
  小D/表情包/预览/预览-<表情>.png   白底预览，方便看效果
"""
import os
import numpy as np
from PIL import Image, ImageFilter

ROOT = r"D:\小鲸鱼的专属文件夹"
EMO = os.path.join(ROOT, "小D", "表情包")
RAW = os.path.join(EMO, "原图")
OUT = os.path.join(EMO, "成品")
PRE = os.path.join(EMO, "预览")
SPLIT = os.path.join(ROOT, "小D", "拆分图")
FRAMES = os.path.join(SPLIT, "成品-透明底")
LAYERS = os.path.join(SPLIT, "分层")

WS = 1280            # 底图尺寸
OUT_S = 1024         # 成品尺寸
EYES = (458, 424, 831, 580)   # 底图里眼睛的范围

os.makedirs(OUT, exist_ok=True)
os.makedirs(PRE, exist_ok=True)


def load(path):
    return Image.open(path).convert("RGBA")


def stack(names):
    canvas = Image.new("RGBA", (WS, WS), (0, 0, 0, 0))
    for n in names:
        p = os.path.join(LAYERS, n + ".png")
        if os.path.exists(p):
            canvas = Image.alpha_composite(canvas, load(p))
    return canvas


def skin_face():
    """只有皮肤和头发、没有眼睛和睫毛的脸（困困 用）。"""
    return stack(["01-后发", "02-辫子", "03-脸", "04-猫耳-右", "05-刘海"])


def erase_eyes(base):
    """把眼睛那块（含睫毛）换成干净的脸皮。"""
    x0, y0, x1, y1 = EYES
    pad = 34
    box = (max(0, x0 - pad), max(0, y0 - pad - 20), min(WS, x1 + pad), min(WS, y1 + pad))
    clean = base.copy()
    region = Image.new("RGBA", (box[2] - box[0], box[3] - box[1]), (0, 0, 0, 0))
    skin = skin_face().crop(box)
    region = Image.alpha_composite(region, skin)
    # 边缘柔化，避免出现硬边
    mask = Image.new("L", region.size, 255)
    mask = mask.filter(ImageFilter.GaussianBlur(0))
    clean.paste(region, (box[0], box[1]), mask)
    return clean


def mom(name):
    return load(os.path.join(RAW, name + ".png")).resize((WS, WS), Image.LANCZOS)


def split_ink(im):
    """把妈妈画的件拆成「蓝色闭眼线」和「灰色困困符号」两张。"""
    a = np.array(im)
    ink = a[:, :, 3] > 24
    rgb = a[:, :, :3].astype(int)
    blue = ink & (rgb[:, :, 2] - rgb[:, :, 0] > 80)   # 深蓝 = 妈妈画的闭眼线
    gray = ink & ~blue                                # 灰 = Zzz / 困困符号
    out = {}
    for k, m in (("blue", blue), ("gray", gray)):
        t = a.copy()
        t[~m] = 0
        out[k] = Image.fromarray(t)
    return out


def fit_into(im, box, keep_ratio=True, scale=1.0):
    """把图按内容裁出来，缩放后摆到 box 中间。"""
    a = np.array(im)
    ys, xs = np.where(a[:, :, 3] > 16)
    if not len(xs):
        return None, (0, 0)
    c = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    x0, y0, x1, y1 = box
    tw, th = (x1 - x0) * scale, (y1 - y0) * scale
    if keep_ratio:
        r = min(tw / c.width, th / c.height)
        c = c.resize((max(1, int(c.width * r)), max(1, int(c.height * r))), Image.LANCZOS)
    else:
        c = c.resize((int(tw), int(th)), Image.LANCZOS)
    return c, (int(x0 + ((x1 - x0) - c.width) / 2), int(y0 + ((y1 - y0) - c.height) / 2))


def save(im, name, tag=""):
    im.resize((OUT_S, OUT_S), Image.LANCZOS).save(
        os.path.join(OUT, name + tag + f"-{OUT_S}.png"), optimize=True)
    bg = Image.new("RGBA", im.size, (250, 248, 252, 255))
    Image.alpha_composite(bg, im).convert("RGB").save(
        os.path.join(PRE, "预览-" + name + tag + ".png"), optimize=True)


def build_shy():
    """害羞：睁眼底图 + 妈妈画的心心 / 脸红。"""
    base = load(os.path.join(FRAMES, "成品-睁眼-透明.png"))
    return Image.alpha_composite(base, mom("害羞"))


def build_kun():
    """困困：闭眼底图 + 妈妈的 Zzz 和困困符号（她那两条线就是闭眼线，现成的闭眼帧里有了）。"""
    base = load(os.path.join(FRAMES, "成品-笑眼闭眼-透明.png"))
    parts = split_ink(mom("困困"))
    return Image.alpha_composite(base, parts["gray"])


def bbox_of(mask):
    ys, xs = np.where(mask)
    return (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1) if len(xs) else None


def build_kun_b():
    """困困：把眼睛擦干净，妈妈画的两条闭眼线各摆到一只眼睛上。"""
    base = erase_eyes(load(os.path.join(FRAMES, "成品-睁眼-透明.png")))
    parts = split_ink(mom("困困"))
    layer = Image.new("RGBA", (WS, WS), (0, 0, 0, 0))

    # 把眉毛（粉色那两条）补回来，只补眉、不补睫毛
    brow = np.array(load(os.path.join(LAYERS, "09-眉毛.png")))
    rgb = brow[:, :, :3].astype(int)
    pink = (brow[:, :, 3] > 40) & (rgb[:, :, 0] > 150) & (rgb[:, :, 0] - rgb[:, :, 2] > 25)
    brow_img = brow.copy()
    brow_img[~pink] = 0
    layer = Image.alpha_composite(layer, Image.fromarray(brow_img))
    layer = Image.alpha_composite(layer, parts["gray"])

    # 底图两只眼睛的位置（按中线拆开）
    eyes = np.array(load(os.path.join(LAYERS, "06-眼睛-睁.png")))[:, :, 3] > 16
    ex0, ey0, ex1, ey1 = EYES
    xmid = int((ex0 + ex1) / 2)
    eye_boxes = []
    for hx0, hx1 in ((ex0, xmid), (xmid, ex1)):
        b = bbox_of(eyes[ey0:ey1, hx0:hx1])
        if b:
            eye_boxes.append((b[0] + hx0, b[1] + ey0, b[2] + hx0, b[3] + ey0))

    # 妈妈画的闭眼线（蓝色），按中线拆成左右两条
    ba = np.array(parts["blue"])
    bmask = ba[:, :, 3] > 24
    bb = bbox_of(bmask)
    bxmid = int((bb[0] + bb[2]) / 2)
    dash_boxes = []
    for hx0, hx1 in ((bb[0], bxmid), (bxmid, bb[2])):
        b = bbox_of(bmask[:, hx0:hx1])
        if b:
            dash_boxes.append((b[0] + hx0, b[1], b[2] + hx0, b[3]))

    S = 1.35
    for db, eb in zip(dash_boxes, eye_boxes):
        dash = parts["blue"].crop(db)
        dash = dash.resize((max(1, int(dash.width * S)), max(1, int(dash.height * S))), Image.LANCZOS)
        cx = (eb[0] + eb[2]) / 2
        cy = (eb[1] + eb[3]) / 2 + 6
        layer.paste(dash, (int(cx - dash.width / 2), int(cy - dash.height / 2)), dash)
    return Image.alpha_composite(base, layer)


def main():
    shy = build_shy()
    save(shy, "害羞")
    kun_b = build_kun_b()
    save(kun_b, "困困")
    kun_a = build_kun()
    save(kun_a, "困困", tag="-另一种")
    print("ok")


if __name__ == "__main__":
    main()
