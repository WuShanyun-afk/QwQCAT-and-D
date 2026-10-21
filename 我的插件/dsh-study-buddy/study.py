# -*- coding: utf-8 -*-
"""小D 陪你写作业 · 番茄钟（自家做的桌面小挂件）

妈妈 2026-10-21 画了「看书小D」5 个表情；这本书摊在小D 面前（跟昨晚那本一样），
翻页、眨眼、捏捏乐、晚上九点犯困，都是自己做的，不装外面的插件。

- 透明、无边框、置顶的小窗口
- 25 分钟一轮番茄 + 5 分钟休息；点一下开始/暂停（顺便捏一下），双击重来，右键菜单
"""
import ctypes
import json
import math
import os
import random
import time

import tkinter as tk
from tkinter import font as tkfont
from PIL import Image, ImageChops, ImageDraw, ImageTk

APP = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(APP, "assets")
CFG = os.path.join(APP, "study-config.json")
DATA = os.path.join(APP, "study-data.json")
CHIME = os.path.join(APP, "chime.wav")
SQUISH_WAV = os.path.join(APP, "squish.wav")

KEY = "#ff00ff"
KEY_RGB = (255, 0, 255)

WIN_W, WIN_H = 300, 452
TICK = 40
WORK_MIN = 25
BREAK_MIN = 5

SPRITE_H = 300                 # 角色显示高度
SPRITE_TOP = 94                # 角色图片顶端在窗口里的 y

NIGHT_START, NIGHT_END = 21, 6
SQUISH_DUR = 0.5
FLIP_DUR = 0.62
FLIP_N = 11

MUTED = "#9c90b8"
PURPLE = "#6b4fa8"
GREEN = "#3f9c86"

NIGHT_TALK = ["哈——欠……", "妈妈也早点睡哦", "眼皮好重…", "困……zzz", "再写一会儿就睡觉好不好"]

# 妈妈画的表情（默认都用「笑着」的嘴）
# 学习的时候是闭着嘴巴的稳重表情（妈妈说：只有点一下才会张嘴笑）
FACES = {
    "read": "看书-睁眼-闭口",    # 安静看（闭嘴）
    "focus": "看书-专注-闭口",   # 认真看（星星眼、闭嘴）
    "talk": "看书-睁眼-张嘴",    # 被点一下（张嘴笑）
    "smile": "看书-笑眼-闭口",   # 休息 / 犯困（闭眼闭嘴）
    "happy": "看书-笑眼-张嘴",   # 吃完一颗番茄（闭眼张嘴笑）
}

# ---------- 摊在面前的那本书（窗口坐标，小一点，就在她怀里那本的下边） ----------
SPINE_TOP = (150, 372)
SPINE_BOT = (150, 436)
LEFT_TOP = (78, 384)
LEFT_BOT = (78, 450)
RIGHT_TOP = (222, 384)
RIGHT_BOT = (222, 450)
PAGE_LEFT = (236, 244, 252)
PAGE_RIGHT = (231, 240, 251)
PAGE_LINE = (198, 214, 236)
BOOK_EDGE = (176, 190, 220)
COVER = (188, 224, 248)

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def screen_size():
    u = ctypes.windll.user32
    return u.GetSystemMetrics(0), u.GetSystemMetrics(1)


SW, SH = screen_size()
TASKBAR = 70


def is_night():
    if os.environ.get("STUDY_FORCE_NIGHT") == "1":
        return True
    if os.environ.get("STUDY_FORCE_DAY") == "1":
        return False
    h = time.localtime().tm_hour
    return h >= NIGHT_START or h < NIGHT_END


# ---------- 素材 ----------
def choke(im):
    """洋红键控的紫边修复：边缘半透明混色会被显示成紫线，这里抹成纯洋红（真透明）。"""
    r, g, b = im.split()
    rmask = r.point(lambda v: 255 if v >= 150 else 0)
    bmask = b.point(lambda v: 255 if v >= 150 else 0)
    gmask = g.point(lambda v: 255 if v <= 120 else 0)
    m = ImageChops.multiply(ImageChops.multiply(rmask, bmask), gmask)
    out = im.copy()
    out.paste(Image.new("RGB", im.size, KEY_RGB), (0, 0), m)
    return out


def keyed(img):
    rgb = img.convert("RGB")
    a = img.split()[3].point(lambda v: 255 if v >= 110 else 0)
    out = Image.new("RGB", img.size, KEY_RGB)
    out.paste(rgb, (0, 0), a)
    return choke(out)


def load_char(name):
    path = os.path.join(ASSETS, FACES.get(name, FACES["read"]) + ".png")
    src = Image.open(path).convert("RGBA")
    w = int(src.width * SPRITE_H / src.height)
    return src.resize((w, SPRITE_H), Image.LANCZOS)


def blink_char():
    """眨眼：把「笑眼」那块眼睛贴到「睁眼」上（同一画布，完全对得上）"""
    base = load_char("read")
    closed = load_char("smile")
    diff = ImageChops.difference(base.convert("RGB"), closed.convert("RGB"))
    mask = diff.convert("L").point(lambda v: 255 if v > 25 else 0)
    out = base.copy()
    out.paste(closed, (0, 0), mask)
    return out


def _lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def draw_book(d, flip=None):
    """在 d 上画一本摊开的书；flip 是 0~1 的翻页进度（None = 不动）"""
    # 书皮（往两侧露出一点）
    d.polygon([(LEFT_TOP[0] - 7, LEFT_TOP[1] + 3), (SPINE_TOP[0], SPINE_TOP[1] - 5),
               (SPINE_BOT[0], SPINE_BOT[1] + 5), (LEFT_BOT[0] - 7, LEFT_BOT[1] + 3)],
              fill=COVER)
    d.polygon([(SPINE_TOP[0], SPINE_TOP[1] - 5), (RIGHT_TOP[0] + 7, RIGHT_TOP[1] + 3),
               (RIGHT_BOT[0] + 7, RIGHT_BOT[1] + 3), (SPINE_BOT[0], SPINE_BOT[1] + 5)],
              fill=COVER)
    # 左右两页
    d.polygon([LEFT_TOP, SPINE_TOP, SPINE_BOT, LEFT_BOT], fill=PAGE_LEFT, outline=BOOK_EDGE)
    d.polygon([SPINE_TOP, RIGHT_TOP, RIGHT_BOT, SPINE_BOT], fill=PAGE_RIGHT, outline=BOOK_EDGE)
    # 书页上的字行
    for i in range(3):
        y = LEFT_TOP[1] + 13 + i * 14
        d.line([(LEFT_TOP[0] + 12, y), (SPINE_TOP[0] - 10, y - 2)], fill=PAGE_LINE, width=2)
        d.line([(SPINE_TOP[0] + 10, y - 2), (RIGHT_TOP[0] - 12, y)], fill=PAGE_LINE, width=2)
    # 书脊
    d.line([SPINE_TOP, SPINE_BOT], fill=BOOK_EDGE, width=2)

    if flip is None:
        return
    # 正在翻的那一页：从右页绕书脊翻到左页
    p = max(0.0, min(1.0, flip))
    u = math.cos(math.pi * p)
    lift = 4.0 * math.sin(math.pi * p)
    if u >= 0:
        et = _lerp(SPINE_TOP, RIGHT_TOP, u)
        eb = _lerp(SPINE_BOT, RIGHT_BOT, u)
        bul = 1.0
    else:
        et = _lerp(SPINE_TOP, LEFT_TOP, -u)
        eb = _lerp(SPINE_BOT, LEFT_BOT, -u)
        bul = -1.0
    et = (et[0], et[1] - lift)
    eb = (eb[0], eb[1] - lift)
    bow = 6.0 * bul * math.sin(math.pi * p)
    edge = []
    for j in range(9):
        tt = j / 8.0
        pp = _lerp(et, eb, tt)
        edge.append((pp[0] + bow * math.sin(math.pi * tt) * tt, pp[1] + 2.0 * math.sin(math.pi * tt)))
    pts = [SPINE_TOP] + edge + [SPINE_BOT]
    d.polygon(pts, fill=(255, 255, 255, 255), outline=(160, 178, 212, 255))
    # 页根一道浅影（不透明的淡色，别让它把下面的画透出来）
    d.polygon([SPINE_TOP, _lerp(SPINE_TOP, edge[0], 0.14), _lerp(SPINE_BOT, edge[-1], 0.14), SPINE_BOT],
              fill=(233, 239, 249, 255))


FRAME_CACHE = {}


def compose(face, flip=None):
    """合成一帧：1080 高的小D + 面前摊开的书（+ 翻页）"""
    key = (face, None if flip is None else round(flip, 3))
    if key in FRAME_CACHE:
        return FRAME_CACHE[key]
    ch = blink_char() if face == "blink" else load_char(face)
    im = Image.new("RGBA", (WIN_W, WIN_H), (0, 0, 0, 0))
    im.alpha_composite(ch, ((WIN_W - ch.width) // 2, SPRITE_TOP))
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    draw_book(ImageDraw.Draw(lay), flip)
    im = Image.alpha_composite(im, lay)
    out = keyed(im)
    FRAME_CACHE[key] = out
    return out


# ---------- 配置 / 数据 ----------
CFG_DEFAULT = {"x": SW - WIN_W - 380, "y": SH - WIN_H - TASKBAR}
try:
    cfg = json.load(open(CFG, "r", encoding="utf-8"))
except Exception:
    cfg = {}
for k, v in CFG_DEFAULT.items():
    cfg.setdefault(k, v)

try:
    data = json.load(open(DATA, "r", encoding="utf-8"))
except Exception:
    data = {}
today = time.strftime("%Y-%m-%d")
if data.get("date") != today:
    data = {"date": today, "count": 0, "minutes": 0}


def save_data():
    try:
        json.dump(data, open(DATA, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass


# ---------- 声音 ----------
def make_chime():
    if os.path.exists(CHIME):
        return
    import struct
    import wave
    rate = 22050
    frames = bytearray()
    for freq, dur in ((880.0, 0.22), (1174.7, 0.30)):
        n = int(rate * dur)
        for i in range(n):
            t = i / rate
            env = min(1.0, t / 0.01) * max(0.0, 1.0 - t / dur) ** 2
            frames += struct.pack("<h", int(12000 * env * math.sin(2 * math.pi * freq * t)))
    try:
        w = wave.open(CHIME, "wb")
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
        w.close()
    except Exception:
        pass


def make_squish():
    """捏捏乐：两声又短又尖的「唧唧」"""
    if os.path.exists(SQUISH_WAV):
        return
    import struct
    import wave
    rate = 22050
    frames = bytearray()
    for f0, f1, dur, gap in ((1500, 2050, 0.075, 0.055), (1650, 2200, 0.070, 0.0)):
        n = int(rate * dur)
        for i in range(n):
            t = i / rate
            p = t / dur
            freq = f0 + (f1 - f0) * p
            env = min(1.0, t / 0.006) * max(0.0, 1.0 - p) ** 2.2
            v = math.sin(2 * math.pi * freq * t) + 0.32 * math.sin(4 * math.pi * freq * t)
            frames += struct.pack("<h", int(7000 * env * v))
        frames += b"\x00\x00" * int(rate * gap)
    try:
        w = wave.open(SQUISH_WAV, "wb")
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
        w.close()
    except Exception:
        pass


def play(path):
    try:
        import winsound
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
    except Exception:
        pass


# ---------- 窗口 ----------
root = tk.Tk()
root.overrideredirect(True)
root.attributes("-topmost", True)
root.attributes("-transparentcolor", KEY)
root.configure(bg=KEY)
root.geometry("%dx%d+%d+%d" % (WIN_W, WIN_H, int(cfg["x"]), int(cfg["y"])))

canvas = tk.Canvas(root, width=WIN_W, height=WIN_H, bg=KEY, highlightthickness=0, bd=0)
canvas.pack()

F_TIMER = tkfont.Font(family="Microsoft YaHei", size=30, weight="bold")
F_SUB = tkfont.Font(family="Microsoft YaHei", size=10)


def _rt(x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
           x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
           x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


# 先放角色图（整窗口大图），再把计时卡片盖在它上面
sprite_id = canvas.create_image(0, 0, anchor="nw")
_rt(WIN_W // 2 - 132, 12, WIN_W // 2 + 132, 100, 20,
    fill="#fcf8ff", outline="#e8dcf6", width=1)
timer_id = canvas.create_text(WIN_W // 2, 44, text="25:00", font=F_TIMER, fill=PURPLE)
sub_id = canvas.create_text(WIN_W // 2, 82, text="点小D 开始 · 双击重来", font=F_SUB, fill=MUTED)

# ---------- 状态 ----------
st = {
    "mode": "idle",
    "left": WORK_MIN * 60.0,
    "end_at": None,
    "bubble_until": 0.0,
    "t": 0.0,
    "drag": False,
    "press": None,
    "press_at": 0.0,
    "x": float(cfg["x"]),
    "y": float(cfg["y"]),
    "celebrate_until": 0.0,
    "blink_until": 0.0,
    "next_blink": 0.0,
    "flip_start": -99.0,
    "next_flip": 0.0,
    "squish_until": 0.0,
    "squish_start": 0.0,
    "squish_photos": None,
    "cur_face": "read",
    "focus_alt": False,
    "next_focus_swap": 0.0,
    "night": None,
    "peek_until": 0.0,
    "next_peek": 0.0,
    "next_night_talk": 0.0,
}

_FORCE_FLIP = os.environ.get("STUDY_FORCE_FLIP") == "1"


def set_sub(text, color):
    canvas.itemconfigure(sub_id, text=text, fill=color)


def show_bubble(text, secs=4.0):
    set_sub(text, PURPLE)
    st["bubble_until"] = time.time() + secs


def status_text():
    if st["mode"] == "work":
        return "写作业中 · 别分心哦", PURPLE
    if st["mode"] == "break":
        return "休息中 · 起来走两步", GREEN
    if st["mode"] == "paused":
        return "暂停啦 · 点小D 继续", MUTED
    return "点小D 开始 · 双击重来", MUTED


def start_work():
    st["mode"] = "work"
    st["left"] = WORK_MIN * 60.0
    st["end_at"] = time.time() + st["left"]


def start_break():
    st["mode"] = "break"
    st["left"] = BREAK_MIN * 60.0
    st["end_at"] = time.time() + st["left"]


def toggle():
    now = time.time()
    if st["mode"] == "idle":
        start_work()
        show_bubble("那我翻书，妈妈写作业～", 3.2)
    elif st["mode"] in ("work", "break"):
        st["back_to"] = st["mode"]
        st["mode"] = "paused"
        st["left"] = max(0.0, st["end_at"] - now) if st["end_at"] else st["left"]
        st["end_at"] = None
        show_bubble("先歇一下～", 2.4)
    elif st["mode"] == "paused":
        what = st.get("back_to") or "work"
        st["mode"] = what if st["left"] > 1 else "idle"
        st["end_at"] = now + st["left"] if st["mode"] != "idle" else None
        if st["mode"] == "idle":
            st["left"] = WORK_MIN * 60.0


def reset():
    st["mode"] = "idle"
    st["left"] = WORK_MIN * 60.0
    st["end_at"] = None
    show_bubble("重新来一轮～", 2.0)


def finish_round(now):
    if st["mode"] == "work":
        data["count"] = data.get("count", 0) + 1
        data["minutes"] = data.get("minutes", 0) + WORK_MIN
        save_data()
        play(CHIME)
        show_bubble("太棒啦！歇 5 分钟，起来走走", 6.0)
        st["celebrate_until"] = now + 4.0
        start_break()
    else:
        play(CHIME)
        show_bubble("休息好啦，点我继续～", 5.0)
        st["mode"] = "idle"
        st["left"] = WORK_MIN * 60.0
        st["end_at"] = None


# ---------- 交互 ----------
def on_press(e):
    st["drag"] = False
    st["press"] = (e.x_root, e.y_root)
    st["press_at"] = time.time()


def on_drag(e):
    if st["press"] is None:
        return
    dx = e.x_root - st["press"][0]
    dy = e.y_root - st["press"][1]
    if abs(dx) + abs(dy) > 4:
        st["drag"] = True
    if st["drag"]:
        st["x"] += dx
        st["y"] += dy
        st["press"] = (e.x_root, e.y_root)
        root.geometry("%dx%d+%d+%d" % (WIN_W, WIN_H, int(st["x"]), int(st["y"])))


def save_cfg():
    try:
        cfg["x"], cfg["y"] = int(st["x"]), int(st["y"])
        json.dump(cfg, open(CFG, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass


def on_release(e):
    if st["press"] is None:
        return
    quick = time.time() - st["press_at"] < 0.5
    st["press"] = None
    if st["drag"]:
        st["drag"] = False
        save_cfg()
        return
    if quick:
        start_squish()
        toggle()


def on_double(e):
    reset()


def on_context(e):
    m = tk.Menu(root, tearoff=0)
    m.add_command(label="开始 / 暂停", command=toggle)
    m.add_command(label="重新计时", command=reset)
    m.add_command(label="直接休息 5 分钟", command=start_break)
    m.add_separator()
    m.add_command(label="今天番茄：%d 个" % data.get("count", 0), state="disabled")
    m.add_command(label="今天学了：%d 分钟" % data.get("minutes", 0), state="disabled")
    m.add_separator()
    m.add_command(label="回到角落", command=to_corner)
    m.add_command(label="退出", command=quit_app)
    try:
        m.tk_popup(e.x_root, e.y_root)
    finally:
        m.grab_release()


def to_corner():
    st["x"] = SW - WIN_W - 380
    st["y"] = SH - WIN_H - TASKBAR
    root.geometry("%dx%d+%d+%d" % (WIN_W, WIN_H, int(st["x"]), int(st["y"])))
    save_cfg()


def quit_app():
    save_cfg()
    save_data()
    root.destroy()


for w in (canvas, root):
    w.bind("<ButtonPress-1>", on_press)
    w.bind("<B1-Motion>", on_drag)
    w.bind("<ButtonRelease-1>", on_release)
    w.bind("<Double-Button-1>", on_double)
    w.bind("<Button-3>", on_context)


# ---------- 主循环 ----------
SQUASH_PHOTOS = {}
IMAGES = {}


def squash_photos(face):
    """电子捏捏乐：整只被从上往下按扁（底边不动，身体往下挤），再弹回来"""
    if face in SQUASH_PHOTOS:
        return SQUASH_PHOTOS[face]
    base = compose(face)
    out = []
    for sx, sy in ((1.00, 1.00), (1.03, 0.92), (1.07, 0.82), (1.09, 0.76),
                   (1.05, 0.86), (1.02, 0.95), (1.00, 1.02), (1.00, 1.00)):
        w = max(1, int(base.width * sx))
        h = max(1, int(base.height * sy))
        squeezed = base.resize((w, h), Image.LANCZOS)
        frame = Image.new("RGB", (WIN_W, WIN_H), KEY_RGB)
        # 底边钉住不动 → 看起来就是被往下压扁
        frame.paste(squeezed, ((WIN_W - w) // 2, WIN_H - h))
        out.append(ImageTk.PhotoImage(choke(frame)))
    SQUASH_PHOTOS[face] = out
    return out


def start_squish():
    face = st.get("cur_face") or "read"
    if face == "blink":
        face = "read"
    st["squish_photos"] = squash_photos(face)
    st["squish_start"] = time.time()
    st["squish_until"] = st["squish_start"] + SQUISH_DUR
    play(SQUISH_WAV)


def face_now(now):
    if now < st["bubble_until"]:
        return "talk"
    if now < st["celebrate_until"]:
        return "happy"
    if now < st["blink_until"]:
        return "blink"
    if st["night"]:
        return "read" if now < st["peek_until"] else "smile"
    if st["mode"] == "break":
        return "smile"
    # 学习时：认真看（星星眼）和安静看 轮流，都是闭着嘴的
    if st["mode"] == "work" and now >= st["next_focus_swap"]:
        st["focus_alt"] = not st["focus_alt"]
        st["next_focus_swap"] = now + 2.8
    return "focus" if (st["mode"] == "work" and not st["focus_alt"]) else "read"


def _tick():
    now = time.time()
    st["t"] += TICK / 1000.0

    if st["mode"] in ("work", "break") and st["end_at"]:
        left = st["end_at"] - now
        if left <= 0:
            canvas.itemconfigure(timer_id, text="00:00")
            finish_round(now)
        else:
            st["left"] = left
            canvas.itemconfigure(timer_id, text="%02d:%02d" % (int(left) // 60, int(left) % 60),
                                 fill=PURPLE if st["mode"] == "work" else GREEN)
    elif st["mode"] == "paused":
        canvas.itemconfigure(timer_id, text="%02d:%02d" % (int(st["left"]) // 60, int(st["left"]) % 60),
                             fill=MUTED)
    else:
        canvas.itemconfigure(timer_id, text="%02d:00" % WORK_MIN, fill=PURPLE)

    if now >= st["bubble_until"]:
        txt, col = status_text()
        set_sub("%s ｜ 番茄 %d" % (txt, data.get("count", 0)), col)

    # 晚上九点后犯困
    night = is_night()
    if night != st["night"]:
        st["night"] = night
        if night:
            st["next_peek"] = now + random.uniform(3, 6)
            st["next_night_talk"] = now + random.uniform(150, 300)
            show_bubble("哈——欠……九点啦", 4.0)
        else:
            st["next_blink"] = 0.0
    if night:
        if now >= st["next_peek"]:
            st["peek_until"] = now + random.uniform(1.2, 2.4)
            st["next_peek"] = now + random.uniform(8, 16)
        if now >= st["next_night_talk"]:
            show_bubble(random.choice(NIGHT_TALK), 3.2)
            st["next_night_talk"] = now + random.uniform(180, 420)
    elif now >= st["next_blink"]:
        st["blink_until"] = now + 0.16
        st["next_blink"] = now + random.uniform(1.8, 4.2)

    face = face_now(now)
    st["cur_face"] = face

    # 翻书：隔两三秒「刷啦」翻一页（与眨眼/捏捏乐错开）
    if _FORCE_FLIP:
        st["next_flip"] = now
    if now >= st["next_flip"] and now >= st["squish_until"] and now >= st["blink_until"]:
        st["flip_start"] = now
        st["next_flip"] = now + random.uniform(2.4, 4.0)

    # 眨眼优先于翻书：这样翻书的时候也不会漏掉眨眼（不然妈妈会觉得它不眨眼了）
    img = None
    if now < st["squish_until"] and st["squish_photos"]:
        p = (now - st["squish_start"]) / SQUISH_DUR
        idx = min(len(st["squish_photos"]) - 1, int(p * len(st["squish_photos"])))
        photo = st["squish_photos"][idx]
    elif now < st["blink_until"]:
        photo = IMAGES.get(("base", "blink")) or IMAGES[("base", "read")]
    elif now < st["flip_start"] + FLIP_DUR:
        p = (now - st["flip_start"]) / FLIP_DUR
        steps = FLIP_N - 1
        photo = IMAGES.get(("flip", int(p * steps)))
        if photo is None:
            photo = IMAGES[("base", face)]
    else:
        photo = IMAGES.get(("base", face)) or IMAGES[("base", "read")]

    canvas.itemconfigure(sprite_id, image=photo)


def tick():
    try:
        _tick()
    except Exception:
        try:
            import traceback
            with open(os.path.join(APP, "study.log"), "a", encoding="utf-8") as f:
                f.write("%s ERROR %s\n" % (time.strftime("%H:%M:%S"),
                                           traceback.format_exc().replace("\n", " | ")))
        except Exception:
            pass
    finally:
        root.after(TICK, tick)


def main():
    make_chime()
    make_squish()
    for name in ("read", "talk", "smile", "happy", "blink"):
        IMAGES[("base", name)] = ImageTk.PhotoImage(compose(name))
    for i in range(FLIP_N):
        IMAGES[("flip", i)] = ImageTk.PhotoImage(compose("read", i / (FLIP_N - 1.0)))
    st["next_blink"] = time.time() + random.uniform(1.5, 3.0)
    st["next_flip"] = time.time() + random.uniform(1.2, 2.4)
    st["night"] = is_night()
    canvas.itemconfigure(sprite_id, image=IMAGES[("base", "read")])
    root.after(300, lambda: show_bubble("妈妈写作业，我翻书陪你～", 4.0))
    root.after(TICK, tick)
    root.mainloop()


if __name__ == "__main__":
    main()
