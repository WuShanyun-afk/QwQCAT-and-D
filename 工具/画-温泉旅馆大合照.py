# -*- coding: utf-8 -*-
r"""『小D 的温泉旅馆 · 大合照』—— 五位客人挤在一个池子里

同一家温泉旅馆的同一个晚上：橘猫、水豚、水獭、企鹅、黑熊排排坐，
月亮、石灯笼、红枫、雪、热可可都在。1500×860，3 倍超采样 + 线稿。
"""
import math
import os

from PIL import Image, ImageDraw, ImageFilter

S = 3
W, H = 1500, 860
img = Image.new("RGB", (W * S, H * S), "#2f3563")
d = ImageDraw.Draw(img)

OL = "#3b2b28"
LW = 5
SKY_T = (44, 50, 98)
SKY_M = (104, 88, 132)
SKY_B = (206, 150, 146)

WATER = "#a9d8d2"
WATER_HL = "#eafaf7"
ROCK = "#8b7d74"
ROCK_D = "#6b5f58"
ROCK_L = "#a8998e"
SNOW = "#f6f1ea"
YUZU = "#f2b53c"
LEAF = "#7fb069"
LANTERN = "#9a8f86"
LIGHT = "#ffd98a"

CAT = "#f0a868"
CAT_D = "#d98d4f"
CAT_DD = "#c1793f"
CREAM = "#fdf1e2"
PINK = "#e88fa0"

CAPY = "#c9976a"
CAPY_D = "#ae7f57"
CAPY_DD = "#96694a"
CAPY_L = "#e0b58c"

OTTER = "#a97c56"
OTTER_D = "#8b6543"
OTTER_DD = "#745234"
OTTER_W = "#f0d9bd"

PENG = "#333b4d"
PENG_D = "#252b39"
PENG_W = "#f7f4ee"
BEAK = "#f2a03c"
BEAK_D = "#d8862a"
TOWEL = "#fdf8f0"
TOWEL_S = "#e6d6c4"

BEAR = "#8a6a52"
BEAR_D = "#6d513d"
BEAR_L = "#a5836a"
PEEL = "#f2b53c"
PEEL_D = "#d9962c"

WOOD = "#d8b48c"
WOOD_D = "#b8905f"


def E(x0, y0, x1, y1, fill, ol=LW):
    d.ellipse([x0 * S, y0 * S, x1 * S, y1 * S], fill=fill,
              outline=OL if ol else None, width=ol * S)


def NOE(x0, y0, x1, y1, fill):
    d.ellipse([x0 * S, y0 * S, x1 * S, y1 * S], fill=fill)


def R(x0, y0, x1, y1, r, fill, ol=LW):
    d.rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], radius=r * S, fill=fill,
                        outline=OL if ol else None, width=ol * S)


def P(pts, fill, ol=LW):
    d.polygon([(x * S, y * S) for x, y in pts], fill=fill,
              outline=OL if ol else None, width=ol * S)


def NO_P(pts, fill):
    d.polygon([(x * S, y * S) for x, y in pts], fill=fill)


def L(pts, col, width=3):
    d.line([(x * S, y * S) for x, y in pts], fill=col, width=width * S, joint="curve")


def A(x0, y0, x1, y1, a0, a1, col, width=LW):
    d.arc([x0 * S, y0 * S, x1 * S, y1 * S], start=a0, end=a1, fill=col, width=width * S)


def maple(x, y, col, s=1.0, rot=0.0):
    pts = []
    for (dx, dy) in [(0, -14), (7, -6), (4, -1), (12, 4), (2, 8), (0, 14),
                     (-2, 8), (-12, 4), (-4, -1), (-7, -6)]:
        c, si = math.cos(rot), math.sin(rot)
        pts.append((x + (dx * c - dy * si) * s, y + (dx * si + dy * c) * s))
    d.polygon([(px * S, py * S) for px, py in pts], fill=col, outline=OL, width=2 * S)
    L([(x, y + 10 * s), (x + 3 * s, y + 20 * s)], OL, 2)


SHORE_Y = 600

# ================= 夜空 =================
for i in range(0, SHORE_Y * S):
    t = i / (SHORE_Y * S)
    if t < 0.55:
        u = t / 0.55
        c = tuple(int(SKY_T[k] + (SKY_M[k] - SKY_T[k]) * u) for k in range(3))
    else:
        u = (t - 0.55) / 0.45
        c = tuple(int(SKY_M[k] + (SKY_B[k] - SKY_M[k]) * u) for k in range(3))
    d.line([(0, i), (W * S, i)], fill=c)

# 月亮
NOE(1232, 108, 1344, 220, "#fff4d4")
NOE(1282, 96, 1388, 200, (66, 64, 108))
for x, y, r in [(140, 110, 2.8), (300, 170, 2.4), (420, 80, 3), (620, 130, 2.6),
                (840, 90, 2.2), (1080, 160, 2.6), (1180, 250, 2.2), (720, 250, 2.4),
                (980, 60, 2.2), (1460, 150, 2.6), (60, 250, 2.2)]:
    NOE(x - r, y - r, x + r, y + r, "#fff6dd")

# 远山
NO_P([(0, 540), (150, 462), (320, 508), (500, 440), (700, 500), (880, 430),
      (1060, 496), (1240, 440), (1400, 496), (1500, 470), (1500, 600), (0, 600)], "#3b3457")
NO_P([(0, 566), (220, 512), (440, 556), (680, 500), (920, 556), (1160, 506),
      (1400, 550), (1500, 528), (1500, 620), (0, 620)], "#4a4066")

# 枫枝（左上角伸进来）
L([(0, 70), (110, 112), (210, 120), (300, 110)], "#5a3f39", 7)
L([(210, 120), (240, 170), (252, 220)], "#5a3f39", 4)
L([(110, 112), (92, 164)], "#5a3f39", 4)
for (x, y, c, s, r) in [(70, 140, "#d9553f", 1.2, -0.3), (146, 112, "#e87a4a", 1.0, 0.4),
                        (232, 166, "#c8452f", 1.05, 0.1), (290, 100, "#e87a4a", 0.95, -0.4),
                        (252, 220, "#d9553f", 0.9, 0.5), (36, 88, "#c8452f", 0.85, -0.2)]:
    maple(x, y, c, s, r)

# ================= 左右石头 =================
P([(0, 520), (70, 492), (150, 510), (206, 496), (270, 528), (300, 580),
   (290, 640), (200, 668), (80, 664), (0, 640)], ROCK)
NO_P([(0, 520), (70, 492), (150, 510), (206, 496), (270, 528), (262, 552),
      (150, 566), (60, 556), (0, 548)], ROCK_L)
NO_P([(40, 596), (130, 588), (196, 616), (170, 660), (70, 662), (24, 630)], ROCK_D)
NOE(96, 502, 176, 552, SNOW)
NO_P([(0, 520), (70, 492), (150, 510), (206, 496), (270, 528), (250, 534),
      (140, 528), (60, 526), (0, 530)], SNOW)

P([(1500, 500), (1400, 486), (1330, 506), (1258, 492), (1190, 526), (1160, 590),
   (1170, 654), (1250, 690), (1370, 700), (1450, 682), (1500, 654)], ROCK)
NO_P([(1500, 500), (1400, 486), (1330, 506), (1258, 492), (1190, 526), (1174, 556),
      (1290, 574), (1410, 562), (1500, 550)], ROCK_L)
NO_P([(1250, 600), (1350, 592), (1430, 626), (1400, 686), (1290, 684), (1236, 640)], ROCK_D)
NOE(1330, 500, 1428, 548, SNOW)
NO_P([(1500, 500), (1400, 486), (1330, 506), (1258, 492), (1290, 512), (1400, 520), (1500, 516)], SNOW)

# ================= 石灯笼 =================
R(1382, 560, 1450, 612, 8, LANTERN)
R(1398, 612, 1434, 646, 4, ROCK_D)
P([(1398, 560), (1434, 560), (1426, 530), (1406, 530)], LANTERN)
R(1402, 532, 1430, 560, 3, LIGHT)
P([(1394, 530), (1438, 530), (1430, 510), (1402, 510)], ROCK_D)
L([(1416, 510), (1416, 496)], ROCK_D, 4)
NOE(1374, 516, 1460, 590, "#ffe9b8")

# ================= 温泉水面 =================
shore = [(0, SHORE_Y), (90, 588), (180, SHORE_Y), (270, 588), (360, SHORE_Y),
         (450, 588), (540, SHORE_Y), (630, 588), (720, SHORE_Y), (810, 588),
         (900, SHORE_Y), (990, 588), (1080, SHORE_Y), (1170, 588), (1260, SHORE_Y),
         (1350, 588), (1440, SHORE_Y), (1500, SHORE_Y)]
P(shore + [(1500, 860), (0, 860)], WATER)
water_grad = Image.new("RGB", (W * S, H * S), WATER)
wg = ImageDraw.Draw(water_grad)
for i in range(SHORE_Y * S, H * S):
    t = (i - SHORE_Y * S) / max(1, (H - SHORE_Y) * S)
    wg.line([(0, i), (W * S, i)],
            fill=(int(169 - 20 * t), int(216 - 24 * t), int(210 - 22 * t)))
mask = Image.new("L", (W * S, H * S), 0)
ImageDraw.Draw(mask).polygon([(x * S, y * S) for x, y in shore + [(1500, 860), (0, 860)]],
                             fill=255)
img.paste(water_grad, (0, 0), mask)
d = ImageDraw.Draw(img)
L(shore, OL, 5)

# ================= 五位客人 =================
# ---------- 1. 橘猫（最左） ----------
CX = 232
E(CX - 100, 424, CX + 100, 636, CAT)
NO_P([(CX + 72, 440), (CX + 100, 500), (CX + 100, 580), (CX + 60, 636),
      (CX + 20, 630), (CX + 50, 550)], CAT_D)
NOE(CX - 82, 466, CX - 18, 538, "#f8c48f")
# 塌下来的耳朵
P([(CX - 84, 448), (CX - 128, 430), (CX - 108, 486)], CAT)
P([(CX + 84, 448), (CX + 128, 430), (CX + 108, 486)], CAT)
P([(CX - 106, 446), (CX - 120, 438), (CX - 112, 470)], PINK)
P([(CX + 106, 446), (CX + 120, 438), (CX + 112, 470)], PINK)
# 头顶毛巾
P([(CX - 78, 420), (CX + 40, 406), (CX + 48, 446), (CX - 70, 460)], TOWEL)
L([(CX - 72, 434), (CX + 44, 420)], TOWEL_S, 3)
P([(CX + 40, 406), (CX + 74, 418), (CX + 56, 460), (CX + 48, 446)], TOWEL)
# 嘴套 + 五官
E(CX - 62, 534, CX + 62, 648, CREAM, ol=0)
P([(CX - 18, 554), (CX + 18, 554), (CX, 578)], PINK)
L([(CX, 578), (CX, 590)], OL, 3)
A(CX - 26, 584, CX + 2, 612, 20, 160, OL, 4)
A(CX + 2, 584, CX + 30, 612, 20, 160, OL, 4)
A(CX - 68, 496, CX - 18, 542, 190, 350, OL, 6)
A(CX + 18, 496, CX + 68, 542, 190, 350, OL, 6)
L([(CX - 68, 504), (CX - 82, 496)], OL, 3)
L([(CX + 68, 504), (CX + 82, 496)], OL, 3)
NOE(CX - 96, 548, CX - 58, 582, "#f2a0a0")
NOE(CX + 58, 540, CX + 96, 574, "#f2a0a0")
for k in range(3):
    L([(CX - 56, 586 + k * 10), (CX - 116, 596 + k * 14)], OL, 3)
    L([(CX + 56, 582 + k * 10), (CX + 116, 592 + k * 14)], OL, 3)

# ---------- 2. 水豚 ----------
CX = 500
# 柚子（顶在头上）
NOE(CX - 36, 372, CX + 26, 434, YUZU)
L([(CX - 6, 372), (CX - 6, 354)], "#8a6b3a", 4)
NO_P([(CX - 4, 362), (CX + 28, 342), (CX + 20, 370)], LEAF)
# 耳朵
E(CX - 106, 396, CX - 44, 456, CAPY)
E(CX - 96, 410, CX - 54, 448, CAPY_D, ol=3)
E(CX + 44, 394, CX + 106, 454, CAPY)
E(CX + 54, 408, CX + 96, 446, CAPY_D, ol=3)
# 头
E(CX - 132, 422, CX + 132, 660, CAPY)
NO_P([(CX + 60, 440), (CX + 132, 500), (CX + 132, 590), (CX + 90, 660),
      (CX + 20, 660), (CX + 50, 560)], CAPY_D)
NOE(CX - 118, 462, CX - 50, 530, CAPY_L)
# 五官
E(CX - 92, 530, CX + 92, 660, CAPY_L, ol=0)
R(CX - 32, 552, CX + 32, 586, 12, "#5b3f31")
NOE(CX - 22, 558, CX - 10, 570, "#7a5a48")
NOE(CX + 10, 558, CX + 22, 570, "#7a5a48")
L([(CX, 564), (CX, 582)], "#3f2b21", 3)
A(CX - 46, 590, CX - 4, 626, 20, 160, OL, 4)
A(CX + 4, 590, CX + 46, 626, 20, 160, OL, 4)
A(CX - 86, 474, CX - 30, 520, 190, 350, OL, 6)
A(CX + 30, 472, CX + 86, 518, 190, 350, OL, 6)
NOE(CX - 118, 540, CX - 76, 568, "#e8a08e")
NOE(CX + 76, 538, CX + 118, 566, "#e8a08e")

# ---------- 3. 小水獭 ----------
CX = 748
E(CX - 106, 494, CX - 58, 534, OTTER)
E(CX + 58, 490, CX + 106, 530, OTTER)
E(CX - 104, 490, CX + 104, 662, OTTER)
NO_P([(CX + 74, 506), (CX + 104, 552), (CX + 104, 610), (CX + 60, 662),
      (CX + 20, 650), (CX + 44, 578)], OTTER_D)
E(CX - 70, 560, CX - 6, 666, OTTER_W, ol=0)
A(CX - 76, 516, CX - 22, 560, 190, 350, OL, 6)
A(CX + 22, 514, CX + 76, 558, 190, 350, OL, 6)
NOE(CX - 18, 594, CX + 18, 620, "#4a382f")
NOE(CX - 6, 600, CX + 6, 610, "#7a5f52")
A(CX - 28, 624, CX + 2, 648, 20, 160, OL, 4)
A(CX + 2, 624, CX + 32, 648, 20, 160, OL, 4)
NOE(CX - 96, 570, CX - 60, 598, "#f2a0a0")
NOE(CX + 60, 566, CX + 96, 594, "#f2a0a0")
for k in range(2):
    L([(CX - 62, 590 + k * 12), (CX - 118, 584 + k * 16)], OL, 3)
    L([(CX + 62, 586 + k * 12), (CX + 118, 580 + k * 16)], OL, 3)
# 两只小爪子搭在水面上
E(CX - 96, 596, CX - 46, 636, OTTER_W)
E(CX + 46, 592, CX + 96, 632, OTTER_W)
A(CX - 104, 610, CX - 38, 644, 195, 350, WATER_HL, 3)
A(CX + 38, 606, CX + 104, 640, 195, 350, WATER_HL, 3)

# ---------- 4. 企鹅（头顶毛巾） ----------
CX = 1000
E(CX - 100, 480, CX + 100, 720, PENG)
NOE(CX - 64, 512, CX + 64, 700, PENG_W)
P([(CX - 96, 512), (CX - 132, 580), (CX - 110, 604), (CX - 76, 552)], PENG)
P([(CX + 96, 512), (CX + 132, 580), (CX + 110, 604), (CX + 76, 552)], PENG)
E(CX - 100, 352, CX + 100, 546, PENG)
NOE(CX - 88, 366, CX + 88, 452, PENG)
E(CX - 72, 396, CX + 72, 530, PENG_W)
# 头顶毛巾
P([(CX - 62, 356), (CX + 54, 342), (CX + 62, 382), (CX - 54, 396)], TOWEL)
L([(CX - 56, 370), (CX + 58, 356)], TOWEL_S, 3)
P([(CX + 54, 342), (CX + 88, 354), (CX + 70, 396), (CX + 62, 382)], TOWEL)
# 眼睛 + 嘴
E(CX - 46, 424, CX - 4, 470, "#2b2f39", ol=4)
E(CX + 4, 424, CX + 46, 470, "#2b2f39", ol=4)
NOE(CX - 38, 432, CX - 20, 452, "#ffffff")
NOE(CX + 12, 432, CX + 30, 452, "#ffffff")
P([(CX - 22, 476), (CX + 22, 476), (CX, 508)], BEAK)
L([(CX, 480), (CX, 502)], BEAK_D, 3)
NOE(CX - 66, 468, CX - 34, 490, "#f0a39a")
NOE(CX + 34, 468, CX + 66, 490, "#f0a39a")

# ---------- 5. 黑熊（背对着，柚子皮帽子） ----------
CX = 1258
E(CX - 108, 386, CX - 34, 462, BEAR)
E(CX - 92, 402, CX - 50, 446, BEAR_D, ol=3)
E(CX + 34, 382, CX + 108, 458, BEAR)
E(CX + 50, 398, CX + 92, 442, BEAR_D, ol=3)
E(CX - 116, 410, CX + 116, 680, BEAR)
NOE(CX - 100, 428, CX + 100, 508, BEAR)
NOE(CX - 96, 470, CX - 30, 560, BEAR_L)
# 柚子皮帽子
d.pieslice([(CX - 92) * S, 402 * S, (CX + 92) * S, 486 * S], 180, 360, fill=PEEL)
d.arc([(CX - 92) * S, 402 * S, (CX + 92) * S, 486 * S], 180, 360, fill=OL, width=LW * S)
for (x0, x1) in [(CX - 86, CX - 58), (CX + 30, CX + 58)]:
    P([(x0, 444), (x1, 444), (x1 - 8, 478), (x0 + 8, 472)], PEEL)
    L([(x0 + 6, 450), (x0 + 8, 468)], PEEL_D, 2)
L([(CX - 60, 420), (CX - 58, 442)], PEEL_D, 2)
L([(CX, 408), (CX, 442)], PEEL_D, 2)
L([(CX + 56, 418), (CX + 52, 442)], PEEL_D, 2)
# 背上毛感 + 水珠
for (x, y) in [(CX - 84, 600), (CX - 50, 640), (CX - 10, 610), (CX + 30, 650),
               (CX + 70, 606), (CX + 96, 648), (CX - 70, 680), (CX + 20, 690)]:
    L([(x, y), (x + 4, y - 16)], BEAR_D, 4)
NOE(CX - 96, 540, CX - 82, 554, "#d8eef0")
NOE(CX + 86, 566, CX + 100, 580, "#d8eef0")

# ================= 水下的身体压一层水色 =================
tint = Image.new("RGBA", (W * S, H * S), (150, 205, 200, 0))
td = ImageDraw.Draw(tint)
td.polygon([(x * S, y * S) for x, y in shore + [(1500, 860), (0, 860)]],
           fill=(150, 205, 200, 96))
img.paste(Image.alpha_composite(img.convert("RGBA"), tint).convert("RGB"), (0, 0))
d = ImageDraw.Draw(img)

# ================= 水面波纹 / 反光 / 漂着的叶子 =================
for (x, y, w2) in [(150, 690, 80), (330, 730, 100), (560, 700, 86), (760, 750, 110),
                   (980, 700, 90), (1160, 740, 100), (1330, 690, 84), (1440, 760, 70)]:
    A(x - w2 // 2, y - 9, x + w2 // 2, y + 9, 200, 340, WATER_HL, 3)
for k in range(4):
    A(1402 - k * 5, 664 + k * 18, 1440 + k * 5, 674 + k * 18, 195, 345, "#ffe0a8", 4)
NOE(1252, 672, 1338, 710, "#e7f4ef")
for (x, y, c, s, r) in [(300, 626, "#d9553f", 1.0, 0.4), (430, 682, "#e87a4a", 0.9, -0.3),
                        (900, 640, "#c8452f", 0.95, 0.2), (1180, 700, "#e87a4a", 1.0, -0.5),
                        (68, 700, "#d9553f", 0.9, 0.3)]:
    maple(x, y, c, s, r)

# ================= 石头上的热可可 + 木桶 =================
P([(8, 556), (66, 538), (124, 556), (118, 582), (14, 582)], ROCK_L)
R(34, 482, 96, 552, 12, "#fffaf3")
E(88, 496, 122, 532, "#fffaf3")
E(94, 502, 114, 524, "#f2e4dc")
NOE(38, 484, 90, 508, "#8b5a4a")
NOE(48, 490, 76, 508, "#a2695a")
NOE(40, 478, 90, 488, "#f2e4da")
for sx in (52, 70):
    L([(sx, 474), (sx + 6, 458), (sx - 2, 442), (sx + 4, 426)], "#efe6ea", 3)
R(292, 636, 372, 686, 12, "#d8b48c")
A(292, 636, 372, 686, 200, 340, "#eacaa4", 4)
L([(296, 656), (368, 656)], WOOD_D, 3)
L([(299, 672), (365, 672)], WOOD_D, 3)

# ================= 蒸汽 =================
steam = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
sd = ImageDraw.Draw(steam)
for (x, y, rx, ry, a) in [(240, 500, 130, 56, 38), (500, 470, 150, 60, 34),
                          (760, 500, 130, 56, 30), (1000, 460, 140, 58, 30),
                          (1300, 480, 150, 60, 28), (420, 640, 160, 30, 40),
                          (820, 650, 170, 32, 38), (1240, 655, 150, 30, 34)]:
    sd.ellipse([(x - rx) * S, (y - ry) * S, (x + rx) * S, (y + ry) * S], fill=(255, 255, 255, a))
steam = steam.filter(ImageFilter.GaussianBlur(24 * S))
img.paste(Image.alpha_composite(img.convert("RGBA"), steam).convert("RGB"), (0, 0))
d = ImageDraw.Draw(img)

# ================= 雪 + 枫叶 =================
for (x, y, r) in [(200, 340, 4), (360, 290, 3), (520, 220, 3.5), (700, 280, 4),
                  (880, 330, 3), (1040, 250, 3.5), (1200, 340, 3), (1420, 400, 3.5),
                  (640, 380, 2.6), (60, 430, 3), (1480, 620, 3), (400, 440, 2.6)]:
    NOE(x - r, y - r, x + r, y + r, "#fdfbf6")
for (x, y, c, s, r) in [(640, 200, "#d9553f", 1.0, 0.6), (300, 250, "#e87a4a", 0.95, -0.5),
                        (1150, 300, "#c8452f", 0.9, 0.3), (860, 180, "#e87a4a", 0.85, -0.2)]:
    maple(x, y, c, s, r)

# ================= 灯光 =================
glow = Image.new("RGB", (W * S, H * S), (0, 0, 0))
gd = ImageDraw.Draw(glow)
gd.ellipse([1330 * S, 470 * S, 1500 * S, 640 * S], fill=(255, 208, 130))
gd.ellipse([150 * S, 560 * S, 1050 * S, 860 * S], fill=(255, 226, 180))
gd.ellipse([1180 * S, 80 * S, 1400 * S, 260 * S], fill=(170, 190, 240))
glow = glow.filter(ImageFilter.GaussianBlur(60 * S))
img.paste(Image.blend(img, glow, 0.20))
d = ImageDraw.Draw(img)

# ================= 收尾 =================
out = img.resize((W, H), Image.LANCZOS)
g2 = Image.new("L", (W, H), 0)
ImageDraw.Draw(g2).ellipse([260, 380, 1260, 880], fill=60)
g2 = g2.filter(ImageFilter.GaussianBlur(80))
warm = Image.new("RGB", (W, H), (255, 222, 176))
out = Image.composite(warm, out, g2.point(lambda v: int(v * 0.24)))

dst = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp", "xiaod-onsen-group.png")
out.save(dst)
print("saved", dst, out.size)
