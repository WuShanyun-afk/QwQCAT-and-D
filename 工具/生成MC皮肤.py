# -*- coding: utf-8 -*-
"""小D 的 Minecraft 皮肤生成器（64×64 现代格式，含第二层）

设计（来自妈妈画的人设）：
- 双色短发：左半蓝、右半藏青（中间分界）
- 猫耳（左蓝 / 右藏青，内耳白），画在第二层
- 右侧蓝色小鲸鱼发夹
- 白色冲锋衣 + 蓝色拉链，黑短裤
- 背后印蓝色小鲸鱼（DEEPSEEK 围裙的感觉）
- 大蓝眼睛、腮红、小张嘴

输出：小D/MC皮肤/小D-皮肤.png
"""
import os

from PIL import Image

SIZE = 64
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "小D", "MC皮肤")

# ---------- 调色板 ----------
SKIN = (255, 223, 205, 255)
SKIN_SH = (240, 198, 178, 255)
HAIR_B = (104, 146, 230, 255)      # 蓝发
HAIR_B_D = (74, 110, 196, 255)
HAIR_N = (40, 50, 78, 255)         # 藏青
HAIR_N_D = (28, 35, 56, 255)
WHITE = (248, 250, 254, 255)
WHITE_SH = (222, 228, 240, 255)
WHITE_D = (200, 208, 226, 255)
BLUE = (110, 198, 226, 255)
BLUE_D = (74, 162, 198, 255)
SHORTS = (46, 50, 64, 255)
SHORTS_SH = (34, 37, 49, 255)
EYE_W = (255, 255, 255, 255)
EYE = (78, 132, 222, 255)
EYE_D = (34, 46, 84, 255)
MOUTH = (219, 112, 128, 255)
BLUSH = (248, 186, 198, 255)
WHALE = (64, 118, 226, 255)
CLEAR = (0, 0, 0, 0)

FACES = {
    "head_top": (8, 0, 8, 8), "head_bottom": (16, 0, 8, 8),
    "head_right": (0, 8, 8, 8), "head_front": (8, 8, 8, 8),
    "head_left": (16, 8, 8, 8), "head_back": (24, 8, 8, 8),
    "hat_top": (40, 0, 8, 8), "hat_bottom": (48, 0, 8, 8),
    "hat_right": (32, 8, 8, 8), "hat_front": (40, 8, 8, 8),
    "hat_left": (48, 8, 8, 8), "hat_back": (56, 8, 8, 8),
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


class Skin:
    def __init__(self):
        self.im = Image.new("RGBA", (SIZE, SIZE), CLEAR)
        self.px = self.im.load()

    def save(self, path):
        self.im.save(path)

    def p(self, x, y, c):
        if 0 <= x < SIZE and 0 <= y < SIZE:
            self.px[x, y] = c

    def rect(self, x, y, w, h, c):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.p(xx, yy, c)

    def face(self, key, rows, palette, mirror=False):
        """按字符画刷一个面；palette: char -> color"""
        x0, y0, w, h = FACES[key]
        for yy, row in enumerate(rows[:h]):
            for xx, ch in enumerate(row[:w]):
                c = palette.get(ch)
                if c is not None:
                    self.p(x0 + (w - 1 - xx if mirror else xx), y0 + yy, c)


def hair_of(x):
    """前脸按列分色：左半蓝、右半藏青"""
    return HAIR_B if x < 4 else HAIR_N


def hair_of_dark(x):
    return HAIR_B_D if x < 4 else HAIR_N_D


# ---------- 头 ----------
HEAD_FRONT = [
    "HHHHHHHH",
    "HHHHHHHH",
    "HHSSSSHH",
    "SWWSSWWS",
    "SEESSDDS",
    "SSSSSSSS",
    "SSSMSSSS",
    "SSSSSSSS",
]
HEAD_SIDE = [
    "HHHHHHHH",
    "HHHHHHHH",
    "HHHHHHHH",
    "HHHHHHHH",
    "HHHHHHHH",
    "SSSSSSSS",
    "SSSSSSSS",
    "SSSSSSSS",
]
HEAD_TOP = ["HHHHHHHH"] * 8
HEAD_BACK = [
    "HHHHHHHH",
    "HHHHHHHH",
    "HHHHHHHH",
    "HHHHHHHH",
    "HHHHHHHH",
    "HHHHHHHH",
    "HHHHHHHH",
    "HHHHHHHH",
]


def draw_head(s: Skin):
    x0, y0, _, _ = FACES["head_front"]
    # 先铺肤色，再按字符画（H/B 用列色，其余固定色）
    s.rect(x0, y0, 8, 8, SKIN)
    for yy, row in enumerate(HEAD_FRONT):
        for xx, ch in enumerate(row):
            if ch == "H":
                s.p(x0 + xx, y0 + yy, hair_of(xx))
            elif ch == "S":
                s.p(x0 + xx, y0 + yy, SKIN)
            elif ch == "W":
                s.p(x0 + xx, y0 + yy, EYE_W)
            elif ch == "E":
                s.p(x0 + xx, y0 + yy, EYE)
            elif ch == "D":
                s.p(x0 + xx, y0 + yy, EYE_D)
            elif ch == "M":
                s.p(x0 + xx, y0 + yy, MOUTH)
    # 腮红
    s.p(x0 + 1, y0 + 5, BLUSH)
    s.p(x0 + 6, y0 + 5, BLUSH)
    # 嘴（两像素的小张嘴）
    s.p(x0 + 3, y0 + 6, MOUTH)
    s.p(x0 + 4, y0 + 6, MOUTH)

    # 左右侧面：上 5 行头发（左蓝右藏青），下 3 行肤色
    for key, col in (("head_right", HAIR_N), ("head_left", HAIR_B)):
        x, y, _, _ = FACES[key]
        for yy in range(8):
            for xx in range(8):
                s.p(x + xx, y + yy, col if yy < 5 else SKIN)
        s.rect(x, y + 5, 8, 1, SKIN_SH)
        s.p(x + 7, y + 5, SKIN_SH)

    # 后脑：头发（左蓝右藏青）
    x, y, _, _ = FACES["head_back"]
    for yy in range(8):
        for xx in range(8):
            s.p(x + xx, y + yy, hair_of(xx) if yy < 6 else hair_of_dark(xx))

    # 头顶
    x, y, _, _ = FACES["head_top"]
    for yy in range(8):
        for xx in range(8):
            s.p(x + xx, y + yy, hair_of(xx) if yy < 6 else hair_of_dark(xx))

    # 头底 = 脖子
    x, y, _, _ = FACES["head_bottom"]
    s.rect(x, y, 8, 8, SKIN_SH)


# ---------- 第二层：猫耳 + 发夹 ----------
def draw_hat(s: Skin):
    # 前面板：耳尖（头顶两角）+ 鲸鱼发夹
    x, y, _, _ = FACES["hat_front"]
    ear_blue = [(0, 0), (1, 0), (0, 1)]
    ear_navy = [(7, 0), (6, 0), (7, 1)]
    for xx, yy in ear_blue:
        s.p(x + xx, y + yy, HAIR_B)
    for xx, yy in ear_navy:
        s.p(x + xx, y + yy, HAIR_N)
    # 耳朵内侧白毛
    s.p(x + 1, y + 1, WHITE)
    s.p(x + 6, y + 1, WHITE)
    # 鲸鱼发夹（在右侧头发上，2×2）
    s.p(x + 5, y + 2, WHALE)
    s.p(x + 5, y + 3, WHALE)
    s.p(x + 6, y + 3, WHALE)

    # 头顶面板：两个立起来的耳朵
    x, y, _, _ = FACES["hat_top"]
    for yy in range(0, 4):
        for xx in range(0, 4):
            if xx + yy <= 3:
                s.p(x + xx, y + yy, HAIR_B)
        for xx in range(4, 8):
            if (7 - xx) + yy <= 3:
                s.p(x + xx, y + yy, HAIR_N)

    # 侧面板：耳朵侧面三角
    x, y, _, _ = FACES["hat_right"]
    for yy in range(0, 3):
        for xx in range(5, 8):
            if (7 - xx) + yy <= 2:
                s.p(x + xx, y + yy, HAIR_N)
    x, y, _, _ = FACES["hat_left"]
    for yy in range(0, 3):
        for xx in range(0, 3):
            if xx + yy <= 2:
                s.p(x + xx, y + yy, HAIR_B)

    # 后脑板：头发厚度
    x, y, _, _ = FACES["hat_back"]
    for yy in range(2):
        for xx in range(8):
            s.p(x + xx, y + yy, hair_of(xx))
    x, y, _, _ = FACES["hat_bottom"]
    s.rect(x, y, 8, 8, CLEAR)


# ---------- 身体 ----------
BODY_FRONT = [
    "DDDDDDDD",
    "DDDDDDDD",
    "WWWWWWWW",
    "WWWZZWWW",
    "WWWZZWWW",
    "WWWZZWWW",
    "WWWZZWWW",
    "WWWZZWWW",
    "WWWZZWWW",
    "WBBBBBBW",
    "KKKKKKKK",
    "KKKKKKKK",
]
BODY_BACK = [
    "DDDDDDDD",
    "DDDDDDDD",
    "WWWWWWWW",
    "WWWWWWWW",
    "WWWWWWWW",
    "WWWWWWWW",
    "WWWWWWWW",
    "WWWWWWWW",
    "WWWWWWWW",
    "WBBBBBBW",
    "KKKKKKKK",
    "KKKKKKKK",
]
BODY_SIDE = [
    "DDDD", "DDDD",
    "WWWW", "WWWW", "WWWW", "WWWW", "WWWW", "WWWW", "WWWW", "WWWW",
    "KKKK", "KKKK",
]


def body_palette():
    return {"D": HAIR_N_D, "W": WHITE, "B": BLUE, "Z": WHITE_D, "K": SHORTS}


def draw_body(s: Skin):
    s.face("body_front", BODY_FRONT, body_palette())
    s.face("body_back", BODY_BACK, body_palette())
    s.face("body_right", BODY_SIDE, body_palette())
    s.face("body_left", BODY_SIDE, body_palette(), mirror=True)

    # 左胸口的小光球徽章（AI 光球）
    x, y, _, _ = FACES["body_front"]
    orb = [
        ".B.",
        "BWB",
        ".B.",
    ]
    for yy, row in enumerate(orb):
        for xx, ch in enumerate(row):
            if ch == "B":
                s.p(x + xx, y + 5 + yy, BLUE)
            elif ch == "W":
                s.p(x + xx, y + 5 + yy, (205, 250, 255, 255))

    # 背后的小鲸鱼 logo
    x, y, _, _ = FACES["body_back"]
    whale = [
        "..###.",
        ".#####",
        "######",
        "##.###",
        "#..#..",
    ]
    for yy, row in enumerate(whale):
        for xx, ch in enumerate(row):
            if ch == "#":
                s.p(x + 1 + xx, y + 3 + yy, WHALE)
    s.p(x + 4, y + 4, WHITE)      # 鲸鱼眼睛

    # 侧面加一条蓝边（更立体）
    for key in ("body_right", "body_left"):
        x, y, _, _ = FACES[key]
        for yy in range(2, 10):
            s.p(x + (3 if key == "body_left" else 0), y + yy, BLUE_D)

    # 顶面（肩膀）、底面（腰）
    x, y, _, _ = FACES["body_top"]
    s.rect(x, y, 8, 2, HAIR_N_D)
    s.rect(x, y + 2, 8, 2, WHITE_SH)
    x, y, _, _ = FACES["body_bottom"]
    s.rect(x, y, 8, 4, SHORTS_SH)


# ---------- 手臂 / 腿 ----------
ARM = [
    "WWWW", "WWWW", "WWWW", "WWWW", "WWWW", "WWWW", "WWWW", "BBBB",
    "SSSS", "SSSS", "SSSS", "SSSS",
]
LEG = [
    "KKKK", "KKKK", "KKKK", "SSSS", "SSSS", "SSSS",
    "SSSS", "SSSS", "SSSS", "SSSS", "SSSS", "SSSS",
]


def draw_limb(s: Skin, prefix, rows, mirror_shadow=False):
    pal = {"W": WHITE, "B": BLUE, "S": SKIN, "K": SHORTS, "Z": WHITE_D}
    s.face(prefix + "_front", rows, pal)
    s.face(prefix + "_back", rows, {"W": WHITE_SH, "B": BLUE_D, "S": SKIN_SH, "K": SHORTS_SH, "Z": WHITE_SH})
    s.face(prefix + "_right", rows, {"W": WHITE_D, "B": BLUE_D, "S": SKIN_SH, "K": SHORTS, "Z": WHITE_D})
    s.face(prefix + "_left", rows, {"W": WHITE_D, "B": BLUE_D, "S": SKIN_SH, "K": SHORTS, "Z": WHITE_D},
           mirror=mirror_shadow)
    x, y, _, _ = FACES[prefix + "_top"]
    s.rect(x, y, 4, 4, WHITE_SH if prefix.startswith("rarm") or prefix.startswith("larm") else SHORTS)
    x, y, _, _ = FACES[prefix + "_bottom"]
    s.rect(x, y, 4, 4, SKIN_SH if prefix.endswith("arm") else SKIN_SH)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    s = Skin()
    draw_head(s)
    draw_hat(s)
    draw_body(s)
    for p in ("rarm", "larm"):
        draw_limb(s, p, ARM)
    for p in ("rleg", "lleg"):
        draw_limb(s, p, LEG)
    out = os.path.join(OUT_DIR, "小D-皮肤.png")
    s.save(out)
    print("saved", out)


if __name__ == "__main__":
    main()
