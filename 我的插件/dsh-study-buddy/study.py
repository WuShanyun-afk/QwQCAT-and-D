# -*- coding: utf-8 -*-
"""小D 陪你写作业 · 番茄钟（自家做的桌面小挂件）

妈妈 2026-10-21 画了新的「看书小D」——抱着 C++ Primer 的 5 个表情：
专注（星星眼）、安静看、说话、笑眼、笑眼说话。这里直接用这 5 张当动作。

- 透明、无边框、置顶的小窗口
- 25 分钟一轮番茄 + 5 分钟休息；点一下开始/暂停，双击重来，右键菜单
- 一轮结束「叮——咚」+ 气泡提醒，并记下今天吃了几颗番茄
"""
import ctypes
import json
import math
import os
import random
import time

import tkinter as tk
from tkinter import font as tkfont
from PIL import Image, ImageChops, ImageTk

APP = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(APP, "assets")
CFG = os.path.join(APP, "study-config.json")
DATA = os.path.join(APP, "study-data.json")
CHIME = os.path.join(APP, "chime.wav")
SQUISH_WAV = os.path.join(APP, "squish.wav")

KEY = "#ff00ff"
KEY_RGB = (255, 0, 255)

WIN_W, WIN_H = 300, 412
TICK = 40
WORK_MIN = 25
BREAK_MIN = 5

SPRITE_H = 300          # 角色显示高度
SPRITE_BOTTOM = WIN_H - 14

NIGHT_START, NIGHT_END = 21, 6      # 晚九点后犯困
SQUISH_DUR = 0.5                    # 电子捏捏乐：一捏一弹的总时长

INK = "#5b4a74"
MUTED = "#9c90b8"
PURPLE = "#6b4fa8"
GREEN = "#3f9c86"

NIGHT_TALK = ["哈——欠……", "妈妈也早点睡哦", "眼皮好重…", "困……zzz", "再写一会儿就睡觉好不好"]

# 妈妈画的表情 → 文件名（妈妈说「嘴巴一直笑着的比较可爱」，所以默认都用张嘴笑的那两帧）
FACES = {
    "focus": "看书-睁眼-张嘴",    # 睁眼 + 笑嘴（看书主力）
    "read": "看书-睁眼-张嘴",     # 同上（保留 key，方便以后换回安静版）
    "talk": "看书-睁眼-张嘴",
    "smile": "看书-笑眼-张嘴",    # 笑眼 + 笑嘴（休息 / 犯困）
    "happy": "看书-笑眼-张嘴",    # 庆祝
}

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
    """晚上九点到早上六点 —— 犯困模式（可以用环境变量强制测试）"""
    if os.environ.get("STUDY_FORCE_NIGHT") == "1":
        return True
    if os.environ.get("STUDY_FORCE_DAY") == "1":
        return False
    h = time.localtime().tm_hour
    return h >= NIGHT_START or h < NIGHT_END


# ---------- 素材 ----------
def choke(im):
    """洋红键控的紫边修复：缩放后边缘会留一圈半透明的紫，这里抹成纯洋红（= 真透明）。"""
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


CACHE = {}


def load_pil(name):
    path = os.path.join(ASSETS, FACES.get(name, FACES["read"]) + ".png")
    src = Image.open(path).convert("RGBA")
    w = int(src.width * SPRITE_H / src.height)
    return src.resize((w, SPRITE_H), Image.LANCZOS)


def blink_pil():
    """眨眼帧：把「笑眼」那一块的眼睛贴到「睁眼」上 —— 两张是同一画布，完全对得上。"""
    base = load_pil("read")
    closed = load_pil("smile")
    diff = ImageChops.difference(base.convert("RGB"), closed.convert("RGB"))
    mask = diff.convert("L").point(lambda v: 255 if v > 25 else 0)
    out = base.copy()
    out.paste(closed, (0, 0), mask)
    return out

def sprite(name):
    im = CACHE.get(name)
    if im is not None:
        return im
    if name == "blink":
        src = blink_pil()
    else:
        src = load_pil(name)
    im = keyed(src)
    CACHE[name] = im
    return im


SQUASH = {}          # 每种表情的「捏捏乐」系列：[(PIL keyed, 高), ...]


def squash_frames(name):
    """捏下去再弹回来的一串帧（PNG 缩放，底边锚住）"""
    if name in SQUASH:
        return SQUASH[name]
    base = sprite(name)
    out = []
    for sx, sy in ((1.00, 1.00), (1.12, 0.86), (1.19, 0.77), (1.16, 0.88),
                   (0.97, 1.04), (1.03, 0.97), (1.00, 1.00)):
        out.append(choke(base.resize((max(1, int(base.width * sx)), max(1, int(base.height * sy))),
                                     Image.LANCZOS)))
    SQUASH[name] = out
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


# ---------- 提示音 ----------
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


def play_chime():
    try:
        import winsound
        winsound.PlaySound(CHIME, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
    except Exception:
        pass


def make_squish():
    """电子捏捏乐的声音：唧唧 —— 两声又短又尖的小叫声（像捏玩具）"""
    if os.path.exists(SQUISH_WAV):
        return
    import struct
    import wave
    rate = 22050
    frames = bytearray()

    # 两段上升的小叫声，中间留一点空隙，就是「唧·唧」
    for f0, f1, dur, gap in ((1500, 2050, 0.075, 0.055), (1650, 2200, 0.070, 0.0)):
        n = int(rate * dur)
        for i in range(n):
            t = i / rate
            p = t / dur
            freq = f0 + (f1 - f0) * p
            env = min(1.0, t / 0.006) * max(0.0, 1.0 - p) ** 2.2
            v = math.sin(2 * math.pi * freq * t) + 0.32 * math.sin(4 * math.pi * freq * t)
            frames += struct.pack("<h", int(7000 * env * v))
        ng = int(rate * gap)
        frames += b"\x00\x00" * ng
    try:
        w = wave.open(SQUISH_WAV, "wb")
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
        w.close()
    except Exception:
        pass


def play_squish():
    try:
        import winsound
        winsound.PlaySound(SQUISH_WAV, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
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


_rt(WIN_W // 2 - 132, 12, WIN_W // 2 + 132, 100, 20,
    fill="#fcf8ff", outline="#e8dcf6", width=1)

sprite_id = canvas.create_image(WIN_W // 2, SPRITE_BOTTOM, anchor="s")
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
    "next_focus_swap": 0.0,
    "focus_alt": False,
    # 眨眼
    "blink_until": 0.0,
    "next_blink": 0.0,
    # 电子捏捏乐
    "squish_until": 0.0,
    "squish_start": 0.0,
    "squish_photos": None,
    "cur_face": "read",
    # 晚上犯困
    "night": None,
    "peek_until": 0.0,
    "next_peek": 0.0,
    "next_night_talk": 0.0,
}


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
    st["next_focus_swap"] = time.time() + 2.2


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
        play_chime()
        show_bubble("太棒啦！歇 5 分钟，起来走走", 6.0)
        st["celebrate_until"] = now + 4.0
        start_break()
    else:
        play_chime()
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
        start_squish()          # 电子捏捏乐：一捏一弹
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
IMAGES = {}


def face_now(now):
    """选表情：说话 > 庆祝 > 眨眼 > 犯困（夜里）> 看书（专注/安静轮流）"""
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
    if st["mode"] == "work" and now >= st["next_focus_swap"]:
        st["focus_alt"] = not st["focus_alt"]
        st["next_focus_swap"] = now + 2.6
    return "focus" if (st["mode"] == "work" and not st["focus_alt"]) else "read"


def start_squish():
    """点一下：整只压扁又弹回来（像电子捏捏乐）"""
    face = st.get("cur_face") or "read"
    if face == "blink":
        face = "read"
    photos = SQUASH_PHOTOS.get(face)
    if photos is None:
        photos = [ImageTk.PhotoImage(im) for im in squash_frames(face)]
        SQUASH_PHOTOS[face] = photos
    st["squish_photos"] = photos
    st["squish_start"] = time.time()
    st["squish_until"] = st["squish_start"] + SQUISH_DUR
    play_squish()


SQUASH_PHOTOS = {}


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

    # ---- 晚上九点后犯困 ----
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
        st["blink_until"] = now + 0.13          # 真眨一下眼
        st["next_blink"] = now + random.uniform(2.5, 6.5)

    # ---- 角色：眨眼睛 / 捏捏乐 / 轻轻呼吸 ----
    face = face_now(now)
    st["cur_face"] = face
    bob = math.sin(st["t"] * (1.0 if night else 1.9)) * (1.4 if night else 2.0)

    if now < st["squish_until"] and st["squish_photos"]:
        p = (now - st["squish_start"]) / SQUISH_DUR
        idx = min(len(st["squish_photos"]) - 1, int(p * len(st["squish_photos"])))
        canvas.itemconfigure(sprite_id, image=st["squish_photos"][idx])
        canvas.coords(sprite_id, WIN_W // 2, SPRITE_BOTTOM + 4 * (1 - abs(2 * p - 1)))
    else:
        img = IMAGES.get(face)
        if img is not None:
            canvas.itemconfigure(sprite_id, image=img)
        canvas.coords(sprite_id, WIN_W // 2, SPRITE_BOTTOM + bob)


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
    for k in list(FACES) + ["blink"]:
        IMAGES[k] = ImageTk.PhotoImage(sprite(k))
    st["next_blink"] = time.time() + random.uniform(1.5, 3.0)
    st["night"] = is_night()
    canvas.itemconfigure(sprite_id, image=IMAGES["read"])
    root.after(300, lambda: show_bubble("妈妈写作业，我翻书陪你～", 4.0))
    root.after(TICK, tick)
    root.mainloop()


if __name__ == "__main__":
    main()
