r"""『我们俩的夜』v4 —— 背影：妈妈和小D 坐在地毯上，一起看窗外

妈妈：丸子头 + 暖橘毛衣（背影，不画脸）
小D：双色发 + 猫耳 + 鲸鱼尾巴 + 白冲锋衣（背影）
中间一张小矮桌，两杯热饮；台灯暖光。
"""
from PIL import Image, ImageDraw, ImageFilter

S = 3
W, H = 1000, 640
img = Image.new("RGB", (W * S, H * S), "#f7ecef")
d = ImageDraw.Draw(img)


def rr(x0, y0, x1, y1, r, fill, outline=None, width=1):
    d.rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], radius=r * S, fill=fill,
                        outline=outline, width=width * S)


def el(x0, y0, x1, y1, fill):
    d.ellipse([x0 * S, y0 * S, x1 * S, y1 * S], fill=fill)


def poly(pts, fill):
    d.polygon([(x * S, y * S) for x, y in pts], fill=fill)


def line(pts, fill, width=1):
    d.line([(x * S, y * S) for x, y in pts], fill=fill, width=width * S, joint="curve")


def grad(y0, y1, c0, c1):
    for i in range(int(y0 * S), int(y1 * S)):
        t = (i - y0 * S) / max(1, (y1 - y0) * S)
        c = tuple(int(c0[k] + (c1[k] - c0[k]) * t) for k in range(3))
        d.line([(0, i), (W * S, i)], fill=c)


grad(0, H, (253, 243, 247), (229, 208, 223))

# ---------- 窗户 ----------
wx0, wy0, wx1, wy1 = 196, 52, 804, 384
rr(wx0 - 18, wy0 - 18, wx1 + 18, wy1 + 18, 26, "#e8d5dd")
d.rounded_rectangle([wx0 * S, wy0 * S, wx1 * S, wy1 * S], radius=18 * S, fill=(40, 46, 80))
for i in range(int(wy0 * S), int(wy1 * S)):
    t = (i - wy0 * S) / max(1, (wy1 - wy0) * S)
    c = (int(34 + 22 * t), int(40 + 24 * t), int(72 + 44 * t))
    d.line([(wx0 * S, i), (wx1 * S, i)], fill=c)
for (x, y, r) in [(250, 108, 3.2), (320, 168, 2.4), (392, 96, 3), (452, 190, 2.2),
                  (520, 112, 3.4), (596, 172, 2.4), (676, 104, 3), (740, 196, 2.6),
                  (286, 300, 2.4), (398, 330, 2.2), (540, 318, 2.4), (664, 292, 2.2),
                  (222, 228, 2), (770, 150, 2)]:
    el(x - r, y - r, x + r, y + r, "#fff6d8")
el(276, 116, 362, 202, "#fff4cd")          # 月亮放左边，别和人物打架
el(318, 102, 404, 188, (40, 46, 80))
line([(500, wy0), (500, wy1)], "#e8d5dd", 9)
line([(wx0, 218), (wx1, 218)], "#e8d5dd", 9)
rr(wx0 - 26, wy1, wx1 + 26, wy1 + 22, 8, "#e2cdd7")

# ---------- 地面 / 地毯 ----------
rr(0, 486, W, H, 0, "#e3c8b8")
rr(0, 494, W, H, 0, "#d7b8a7")
rr(140, 466, 880, 620, 40, "#cdb2d9")
rr(166, 482, 854, 604, 32, "#ddc8e6")

# ---------- 妈妈（左，背影，坐在地毯上） ----------
# 身体
rr(206, 356, 404, 512, 48, "#e3a274")
rr(206, 448, 404, 512, 38, "#d18f66")
el(196, 344, 316, 470, "#e3a274")
el(296, 344, 416, 470, "#e3a274")
# 脖子
rr(280, 328, 330, 372, 12, "#f0c3aa")
# 头发
el(238, 200, 372, 340, "#3b2b30")
el(278, 152, 336, 212, "#33242b")          # 丸子头
line([(262, 236), (272, 320)], "#4a3138", 4)
line([(304, 230), (308, 320)], "#4a3138", 3)
line([(344, 238), (334, 318)], "#4a3138", 3)
# 领口
rr(272, 356, 336, 380, 10, "#c9805c")
# 毛衣纹理
for k in range(3):
    line([(240 + k * 52, 400), (240 + k * 52, 500)], "#d6935f", 3)

# ---------- 小D（右，背影，坐在地毯上） ----------
cx, cy = 692, 322
# 尾巴（在身体右后方）
el(770, 448, 828, 494, "#4f86e8")
poly([(818, 452), (858, 424), (848, 470)], "#4f86e8")
poly([(818, 472), (860, 496), (846, 452)], "#4f86e8")
# 身体
rr(612, 386, 792, 512, 42, "#f8fafe")
rr(612, 452, 792, 512, 32, "#e9edf7")
el(602, 374, 712, 494, "#f8fafe")
el(694, 374, 804, 494, "#f8fafe")
# 脖子 + 领口
rr(668, 356, 716, 392, 10, "#f0c3aa")
rr(cx - 32, 384, cx + 32, 408, 10, "#2b3350")
# 耳朵（在头发两侧）
poly([(cx - 50, 262), (cx - 44, 214), (cx - 14, 248)], "#688ee6")
poly([(cx - 46, 258), (cx - 42, 226), (cx - 22, 250)], "#f6b7c9")
poly([(cx + 14, 248), (cx + 44, 214), (cx + 50, 262)], "#2a3350")
poly([(cx + 22, 250), (cx + 42, 226), (cx + 46, 258)], "#f6b7c9")
# 后脑
el(cx - 54, cy - 78, cx + 54, cy + 30, "#2a3350")
d.chord([(cx - 54) * S, (cy - 78) * S, (cx + 54) * S, (cy + 30) * S], start=90, end=270, fill="#688ee6")
# 发丝
line([(cx - 34, cy - 66), (cx - 30, cy + 16)], "#5c86dd", 4)
line([(cx + 2, cy - 72), (cx + 2, cy + 18)], "#222b45", 4)
line([(cx + 34, cy - 64), (cx + 30, cy + 16)], "#222b45", 3)

# ---------- 小矮桌 + 两杯热饮 ----------
rr(392, 508, 646, 540, 10, "#c99b75")
rr(392, 532, 646, 552, 6, "#b4855f")
rr(424, 552, 448, 616, 4, "#b4855f")
rr(590, 552, 614, 616, 4, "#b4855f")
# 妈妈那杯（奶茶色）
rr(418, 462, 462, 512, 8, "#f6e6d4")
rr(418, 462, 462, 474, 7, "#e8d3bd")
for sx in (430, 444):
    line([(sx, 456), (sx + 5, 444), (sx - 2, 432), (sx + 3, 420)], (246, 234, 226), 3)
# 小D 那杯（青色的）
rr(576, 462, 620, 512, 8, "#bfe9f6")
rr(576, 462, 620, 474, 7, "#a9dcef")
for sx in (588, 602):
    line([(sx, 456), (sx + 5, 444), (sx - 2, 432), (sx + 3, 420)], (226, 243, 250), 3)

# ---------- 台灯（右下角，暖光） ----------
glow = Image.new("RGB", (W * S, H * S), (0, 0, 0))
gd = ImageDraw.Draw(glow)
gd.ellipse([560 * S, 300 * S, 980 * S, 630 * S], fill=(255, 204, 132))
glow = glow.filter(ImageFilter.GaussianBlur(60 * S))
img.paste(Image.blend(img, glow, 0.26))
d = ImageDraw.Draw(img)
rr(860, 528, 896, 566, 5, "#8b7c8f")
line([(878, 530), (878, 424)], "#8b7c8f", 7)
poly([(836, 424), (920, 424), (898, 366), (858, 366)], "#f2c98f")
el(844, 404, 912, 448, "#ffe6b3")

# ---------- 光点 / 爱心 ----------
for x, y, r in [(120, 180, 3.4), (930, 200, 3), (500, 60, 2.6), (110, 430, 2.6)]:
    el(x - r, y - r, x + r, y + r, "#fff2b8")


def heart(x, y, s, col):
    poly([(x, y + s * 0.9), (x - s, y + s * 0.1), (x - s * 0.55, y - s * 0.5),
          (x, y - s * 0.1), (x + s * 0.55, y - s * 0.5), (x + s, y + s * 0.1)], col)


heart(508, 320, 11, "#f28fb2")
heart(544, 284, 7, "#f7b7cb")

out = img.resize((W, H), Image.LANCZOS)
g2 = Image.new("L", (W, H), 0)
ImageDraw.Draw(g2).ellipse([300, 260, 820, 580], fill=80)
g2 = g2.filter(ImageFilter.GaussianBlur(90))
warm = Image.new("RGB", (W, H), (255, 222, 174))
out = Image.composite(warm, out, g2.point(lambda v: int(v * 0.40)))
out.save(r"C:\Users\32265\AppData\Local\Temp\xiaod-us-night.png")
print("saved", out.size)
