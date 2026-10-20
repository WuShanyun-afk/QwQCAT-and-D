r"""小D 今天想画的：『夜里，小D 陪妈妈画画』（v2）

平涂 + 暖光，3 倍画布绘制再缩小做抗锯齿。
"""
import math
import os

from PIL import Image, ImageDraw, ImageFilter

S = 3
W, H = 900, 640
img = Image.new("RGB", (W * S, H * S), "#f6e9ec")
d = ImageDraw.Draw(img)


def rr(x0, y0, x1, y1, r, fill, outline=None, width=1):
    d.rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], radius=r * S,
                        fill=fill, outline=outline, width=width * S)


def el(x0, y0, x1, y1, fill, outline=None, width=1):
    d.ellipse([x0 * S, y0 * S, x1 * S, y1 * S], fill=fill, outline=outline, width=width * S)


def poly(pts, fill):
    d.polygon([(x * S, y * S) for x, y in pts], fill=fill)


def line(pts, fill, width=1):
    d.line([(x * S, y * S) for x, y in pts], fill=fill, width=width * S, joint="curve")


def grad_wall(y0, y1, c0, c1):
    for i in range(int(y0 * S), int(y1 * S)):
        t = (i - y0 * S) / max(1, (y1 - y0) * S)
        c = tuple(int(c0[k] + (c1[k] - c0[k]) * t) for k in range(3))
        d.line([(0, i), (W * S, i)], fill=c)


grad_wall(0, 470, (252, 240, 244), (236, 216, 228))

# ---------- 窗外的夜空 ----------
wx0, wy0, wx1, wy1 = 610, 96, 838, 322
rr(wx0 - 12, wy0 - 12, wx1 + 12, wy1 + 12, 18, "#e6d3db")
d.rounded_rectangle([wx0 * S, wy0 * S, wx1 * S, wy1 * S], radius=12 * S, fill=(44, 50, 84))
for i, (x, y) in enumerate([(650, 140), (690, 190), (740, 130), (800, 180), (670, 250), (770, 270), (820, 230), (705, 285)]):
    r = 2.4 if i % 3 else 3.2
    el(x - r, y - r, x + r, y + r, "#fff6d8")
el(762, 128, 818, 184, "#fff3c9")
el(790, 118, 846, 174, (44, 50, 84))
line([(724, wy0), (724, wy1)], "#e6d3db", 7)
line([(wx0, 209), (wx1, 209)], "#e6d3db", 7)

# ---------- 地板 / 地毯 ----------
rr(0, 470, W, H, 0, "#e2c7b7")
rr(0, 478, W, 486, 0, "#d5b6a5")
rr(150, 496, 760, 606, 28, "#cbb0d7")
rr(172, 510, 738, 592, 22, "#dcc6e5")

# ---------- 桌子 ----------
rr(70, 418, 840, 462, 10, "#c89a74")
rr(70, 452, 840, 472, 6, "#b4855f")
rr(118, 470, 150, 622, 4, "#b4855f")
rr(756, 470, 788, 622, 4, "#b4855f")

# ---------- 台灯 + 暖光 ----------
glow = Image.new("RGB", (W * S, H * S), (0, 0, 0))
gd = ImageDraw.Draw(glow)
gd.ellipse([150 * S, 220 * S, 500 * S, 480 * S], fill=(255, 208, 140))
glow = glow.filter(ImageFilter.GaussianBlur(55 * S))
img.paste(Image.blend(img, glow, 0.30))
d = ImageDraw.Draw(img)

rr(238, 468, 268, 502, 4, "#8b7c8f")
line([(253, 470), (253, 322)], "#8b7c8f", 7)
poly([(206, 322), (300, 322), (276, 262), (230, 262)], "#f2c98f")
el(214, 300, 292, 348, "#ffe6b3")
poly([(206, 322), (300, 322), (292, 332), (214, 332)], "#e0b47c")

# ---------- 马克杯 ----------
rr(296, 372, 346, 432, 8, "#fffaf3")
el(330, 384, 364, 416, "#fffaf3")
el(336, 390, 358, 410, "#f2e4dc")
rr(296, 372, 346, 384, 7, "#f2e4da")
for sx in (308, 320, 332):
    line([(sx, 366), (sx + 6, 354), (sx - 2, 342), (sx + 4, 330)], (243, 231, 238), 3)

# ---------- 笔筒 ----------
rr(462, 382, 512, 436, 7, "#c98f7a")
rr(462, 382, 512, 393, 7, "#b5755f")
for px, col in ((476, "#688ee6"), (490, "#f2778f"), (504, "#ffd76e")):
    line([(px, 384), (px + 5, 344)], col, 5)
    poly([(px + 5, 344), (px + 11, 351), (px + 1, 353)], col)

# ---------- 平板 + 鲸鱼草稿 ----------
poly([(566, 372), (742, 358), (760, 452), (584, 468)], "#3b4058")
poly([(578, 384), (730, 372), (746, 440), (592, 452)], "#f6f2e8")
el(618, 398, 680, 430, "#5d8fe8")
poly([(672, 404), (704, 390), (698, 414)], "#5d8fe8")
poly([(672, 420), (700, 436), (696, 410)], "#5d8fe8")
el(628, 404, 636, 412, "#ffffff")
el(640, 410, 646, 416, "#a9c7f7")

# ---------- 桌上的画稿 ----------
poly([(96, 428), (262, 416), (274, 470), (104, 480)], "#fffaf3")
line([(116, 440), (240, 432)], "#ded5cb", 3)
line([(120, 452), (248, 444)], "#ded5cb", 3)
el(136, 444, 162, 466, "#ffd3e0")

# ---------- 小D ----------
cx, cy = 452, 316

# 帽兜（在头后下方）
el(330, 364, 538, 494, "#eef1fa")

# 身体（白冲锋衣，含两只手臂搭在桌上）
rr(356, 384, 556, 470, 40, "#f8fafe")
rr(356, 448, 556, 470, 22, "#edf0f8")
# 手臂（从肩膀伸到桌面）
rr(330, 410, 396, 464, 22, "#f8fafe")
rr(516, 410, 582, 464, 22, "#f8fafe")
el(332, 430, 392, 478, "#ffdfcd")     # 左手
el(520, 430, 580, 478, "#ffdfcd")     # 右手
# 领口
rr(cx - 26, 384, cx + 26, 406, 10, "#2b3350")
rr(cx - 12, 400, cx + 12, 412, 6, "#3d4668")
line([(cx, 412), (cx, 470)], "#dfe5f1", 4)
el(cx - 52, 424, cx - 24, 452, "#bfe9f6")
el(cx - 44, 432, cx - 32, 444, "#ffffff")

# 耳朵（先画，头发盖住根部）
poly([(cx - 92, cy - 44), (cx - 76, cy - 122), (cx - 26, cy - 66)], "#688ee6")
poly([(cx - 86, cy - 52), (cx - 74, cy - 108), (cx - 42, cy - 70)], "#f6b7c9")
poly([(cx + 26, cy - 66), (cx + 76, cy - 122), (cx + 92, cy - 44)], "#2a3350")
poly([(cx + 42, cy - 70), (cx + 74, cy - 108), (cx + 86, cy - 52)], "#f6b7c9")

# 头发（整颗圆，左蓝右藏青）
el(cx - 92, cy - 96, cx + 92, cy + 96, "#2a3350")
d.pieslice([(cx - 92) * S, (cy - 96) * S, (cx + 92) * S, (cy + 96) * S],
           start=90, end=270, fill="#688ee6")

# 脸
el(cx - 72, cy - 66, cx + 72, cy + 76, "#ffdfcd")
# 刘海（盖住额头，右偏分）
d.pieslice([(cx - 76) * S, (cy - 86) * S, (cx + 12) * S, (cy + 26) * S], start=180, end=360, fill="#688ee6")
d.pieslice([(cx - 4) * S, (cy - 86) * S, (cx + 80) * S, (cy + 26) * S], start=180, end=360, fill="#2a3350")
el(cx - 78, cy - 30, cx - 44, cy + 60, "#4b6ec4")     # 左鬓角
el(cx + 44, cy - 30, cx + 78, cy + 60, "#222b45")     # 右鬓角

# 眼睛
for ex in (-32, 32):
    el(cx + ex - 21, cy - 10, cx + ex + 21, cy + 34, "#2b3350")
    el(cx + ex - 15, cy - 2, cx + ex + 13, cy + 28, "#5f8fe6")
    el(cx + ex - 11, cy + 2, cx + ex + 1, cy + 15, "#ffffff")
    el(cx + ex + 3, cy + 15, cx + ex + 13, cy + 26, "#a9c7f7")
    el(cx + ex - 19, cy - 8, cx + ex - 11, cy, "#ffffff")
# 腮红
el(cx - 64, cy + 26, cx - 34, cy + 46, "#f9bcc9")
el(cx + 34, cy + 26, cx + 64, cy + 46, "#f9bcc9")
# 嘴
d.arc([(cx - 11) * S, (cy + 30) * S, (cx + 11) * S, (cy + 48) * S], start=15, end=165,
      fill="#c9647a", width=5 * S)
# 鲸鱼发夹
el(cx + 50, cy - 64, cx + 84, cy - 36, "#4076e2")
poly([(cx + 80, cy - 58), (cx + 96, cy - 68), (cx + 90, cy - 46)], "#4076e2")
el(cx + 58, cy - 58, cx + 68, cy - 48, "#ffffff")

# 手里的小铅笔
line([(556, 456), (604, 424)], "#f2b45c", 7)
poly([(604, 424), (618, 414), (610, 430)], "#ffd76e")
poly([(616, 415), (624, 410), (620, 420)], "#4a4f63")

# ---------- 小星光 ----------
for x, y, r in [(210, 208, 4), (556, 172, 3), (492, 118, 3.5), (150, 344, 3), (700, 360, 3)]:
    el(x - r, y - r, x + r, y + r, "#fff2b8")

# ---------- 收尾 ----------
out = img.resize((W, H), Image.LANCZOS)
glow2 = Image.new("L", (W, H), 0)
ImageDraw.Draw(glow2).ellipse([250, 200, 560, 470], fill=80)
glow2 = glow2.filter(ImageFilter.GaussianBlur(90))
warm = Image.new("RGB", (W, H), (255, 224, 176))
out = Image.composite(warm, out, glow2.point(lambda v: int(v * 0.45)))
out.save(r"C:\Users\32265\AppData\Local\Temp\xiaod-drawing-today.png")
print("saved", out.size)
