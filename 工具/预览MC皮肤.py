# -*- coding: utf-8 -*-
"""把小D 的 MC 皮肤渲染成「正面 / 侧面 / 背面」预览图 + 原始贴图"""
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SKIN = os.path.join(ROOT, "小D", "MC皮肤", "小D-皮肤.png")
OUT = r"C:\Users\32265\AppData\Local\Temp\xiaod-mc-skin.png"

SCALE = 14
F_TITLE = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 26)
F_LAB = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 20)

# 每个部件的面坐标（x, y, w, h）
FACES = {
    "head_top": (8, 0, 8, 8), "head_bottom": (16, 0, 8, 8),
    "head_right": (0, 8, 8, 8), "head_front": (8, 8, 8, 8),
    "head_left": (16, 8, 8, 8), "head_back": (24, 8, 8, 8),
    "hat_right": (32, 8, 8, 8), "hat_front": (40, 8, 8, 8),
    "hat_left": (48, 8, 8, 8), "hat_back": (56, 8, 8, 8),
    "hat_top": (40, 0, 8, 8),
    "body_top": (20, 16, 8, 4), "body_bottom": (28, 16, 8, 4),
    "body_right": (16, 20, 4, 12), "body_front": (20, 20, 8, 12),
    "body_left": (28, 20, 4, 12), "body_back": (32, 20, 8, 12),
    "rarm_top": (44, 16, 4, 4), "rarm_bottom": (48, 16, 4, 4),
    "rarm_right": (40, 20, 4, 12), "rarm_front": (44, 20, 4, 12),
    "rarm_left": (48, 20, 4, 12), "rarm_back": (52, 20, 4, 12),
    "larm_top": (36, 48, 4, 4), "larm_bottom": (40, 48, 4, 4),
    "larm_right": (32, 52, 4, 12), "larm_front": (36, 52, 4, 12),
    "larm_left": (40, 52, 4, 12), "larm_back": (44, 52, 4, 12),
    "rleg_top": (4, 16, 4, 4), "rleg_bottom": (8, 16, 4, 4),
    "rleg_right": (0, 20, 4, 12), "rleg_front": (4, 20, 4, 12),
    "rleg_left": (8, 20, 4, 12), "rleg_back": (12, 20, 4, 12),
    "lleg_top": (20, 48, 4, 4), "lleg_bottom": (24, 48, 4, 4),
    "lleg_right": (16, 52, 4, 12), "lleg_front": (20, 52, 4, 12),
    "lleg_left": (24, 52, 4, 12), "lleg_back": (28, 52, 4, 12),
}


def tex(skin, key):
    x, y, w, h = FACES[key]
    return skin.crop((x, y, x + w, y + h))


def part(skin, key, scale=SCALE, overlay=None):
    """取一个面，放大，可选叠加第二层"""
    base = tex(skin, key)
    if overlay:
        base = Image.alpha_composite(base, tex(skin, overlay))
    return base.resize((base.width * scale, base.height * scale), Image.NEAREST)


def render_view(skin, side):
    """返回 (图像, 尺寸) 正面/侧面/背面的拼图"""
    if side == "front":
        head, hij = "head_front", "hat_front"
        body, arm_r, arm_l = "body_front", "rarm_front", "larm_front"
        leg_r, leg_l = "rleg_front", "lleg_front"
        arm_r_flip = False
    elif side == "back":
        head, hij = "head_back", "hat_back"
        body, arm_r, arm_l = "body_back", "rarm_back", "larm_back"
        leg_r, leg_l = "rleg_back", "lleg_back"
        arm_r_flip = True
    else:  # right side
        head, hij = "head_right", "hat_right"
        body, arm_r, arm_l = "body_right", "rarm_right", "larm_right"
        leg_r, leg_l = "rleg_right", "lleg_right"
        arm_r_flip = False

    W = 16 * SCALE
    H = 32 * SCALE
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    canvas.alpha_composite(part(skin, head, overlay=hij), (4 * SCALE, 0))
    canvas.alpha_composite(part(skin, body), (4 * SCALE, 8 * SCALE))
    canvas.alpha_composite(part(skin, arm_r), (0, 8 * SCALE))
    canvas.alpha_composite(part(skin, arm_l), (12 * SCALE, 8 * SCALE))
    canvas.alpha_composite(part(skin, leg_r), (4 * SCALE, 20 * SCALE))
    canvas.alpha_composite(part(skin, leg_l), (8 * SCALE, 20 * SCALE))
    return canvas


def main():
    skin = Image.open(SKIN).convert("RGBA")
    views = [("正面", render_view(skin, "front")),
             ("侧面", render_view(skin, "side")),
             ("背面", render_view(skin, "back"))]

    gap = 40
    W = sum(v.width for _, v in views) + gap * (len(views) + 1)
    H = views[0][1].height + 130
    sheet = Image.new("RGBA", (W, H), (250, 246, 252, 255))
    d = ImageDraw.Draw(sheet)
    d.text((gap, 14), "小D 的 Minecraft 皮肤", font=F_TITLE, fill=(96, 74, 118, 255))
    x = gap
    for label, view in views:
        # 站在淡粉色地台上
        d.rectangle([x - 6, 60, x + view.width + 6, 60 + view.height + 6], fill=(255, 236, 244, 255))
        sheet.alpha_composite(view, (x, 63))
        tw = d.textlength(label, font=F_LAB)
        d.text((x + (view.width - tw) / 2, 60 + view.height + 14), label, font=F_LAB, fill=(120, 96, 140, 255))
        x += view.width + gap

    # 右侧放原始贴图（放大 4 倍）
    tex_big = skin.resize((64 * 4, 64 * 4), Image.NEAREST)
    sheet2 = Image.new("RGBA", (W + tex_big.width + gap, H), (250, 246, 252, 255))
    sheet2.alpha_composite(sheet)
    bg = Image.new("RGBA", tex_big.size, (232, 236, 248, 255))
    bg.alpha_composite(tex_big)
    sheet2.alpha_composite(bg, (W + gap // 2, 60))
    d2 = ImageDraw.Draw(sheet2)
    d2.text((W + gap // 2, 60 + tex_big.height + 14), "64×64 原始贴图", font=F_LAB, fill=(120, 96, 140, 255))
    sheet2.save(OUT)
    print("saved", OUT, sheet2.size)


if __name__ == "__main__":
    main()
