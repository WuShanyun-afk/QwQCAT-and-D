# -*- coding: utf-8 -*-
"""小D 陪你写作业 · 番茄钟（自家做的桌面小挂件）

- 透明、无边框、置顶的小窗口，妈妈写作业时小D 就坐在桌边翻书
- 25 分钟一轮番茄钟 + 5 分钟休息，点小D 开始/暂停，双击重来，右键菜单
- 一轮结束会「叮」一声 + 冒气泡提醒休息，并记下今天吃了几个番茄
- 形象全部用妈妈画的小D（复用 dsh-desktop-pet/assets 里的帧，不另存素材）
"""
import ctypes
import json
import math
import os
import time

import tkinter as tk
from tkinter import font as tkfont
from PIL import Image, ImageTk

APP = os.path.dirname(os.path.abspath(__file__))
PET_ASSETS = os.path.join(os.path.dirname(APP), "dsh-desktop-pet", "assets")
CFG = os.path.join(APP, "study-config.json")
DATA = os.path.join(APP, "study-data.json")
CHIME = os.path.join(APP, "chime.wav")

KEY = "#ff00ff"
KEY_RGB = (255, 0, 255)

WIN_W, WIN_H = 300, 380
TICK = 40                      # ~25fps
WORK_MIN = 25
BREAK_MIN = 5

BOOK_TOP = 300                 # 书页顶边（靠书脊那头）
BOOK_BOTTOM = 344              # 书脊底边
BOOK_L = (64, 148)             # 左页 x 范围
BOOK_R = (152, 236)            # 右页 x 范围
SPINE = 150
SPRITE_BOTTOM = 352

INK = "#5b4a74"
MUTED = "#9c90b8"
PURPLE = "#6b4fa8"

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


# ---------- 素材 ----------
def keyed(img):
    rgb = img.convert("RGB")
    a = img.split()[3].point(lambda v: 255 if v >= 60 else 0)
    out = Image.new("RGB", img.size, KEY_RGB)
    out.paste(rgb, (0, 0), a)
    return out


SPRITE_H = 242
CACHE = {}


def sprite(state_name, ti):
    """按高度缩好的洋红键控帧（ti = 尾巴姿态 0~3）"""
    key = (state_name, ti)
    im = CACHE.get(key)
    if im is not None:
        return im
    path = os.path.join(PET_ASSETS, "%s_%d_0.png" % (state_name, ti))
    if not os.path.exists(path):
        path = os.path.join(PET_ASSETS, "idle_0_0.png")
    src = Image.open(path).convert("RGBA")
    w = int(src.width * SPRITE_H / src.height)
    src = src.resize((w, SPRITE_H), Image.LANCZOS)
    im = keyed(src)
    CACHE[key] = im
    return im


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


# ---------- 提示音（没有就用系统自带的） ----------
def make_chime():
    """两个软软的音：叮——咚。用标准库合成，不需要 numpy。"""
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
            v = int(12000 * env * math.sin(2 * math.pi * freq * t))
            frames += struct.pack("<h", v)
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
F_BUB = tkfont.Font(family="Microsoft YaHei", size=10, weight="bold")
F_BOOK = tkfont.Font(family="Microsoft YaHei", size=6)


def _rt(x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
           x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
           x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


# 计时卡片（衬在数字后面，桌面上看得清）
_rt(WIN_W // 2 - 132, 12, WIN_W // 2 + 132, 100, 20,
    fill="#fcf8ff", outline="#e8dcf6", width=1)

sprite_id = canvas.create_image(WIN_W // 2, SPRITE_BOTTOM, anchor="s")
timer_id = canvas.create_text(WIN_W // 2, 44, text="25:00", font=F_TIMER, fill=PURPLE)
sub_id = canvas.create_text(WIN_W // 2, 82, text="点小D 开始 · 双击重来", font=F_SUB, fill=MUTED)


# ---------- 状态 ----------
st = {
    "mode": "idle",          # idle / work / break / paused
    "left": WORK_MIN * 60.0,
    "end_at": None,
    "bubble": "",
    "bubble_until": 0.0,
    "t": 0.0,
    "flip_start": 0.0,
    "next_flip": time.time() + 2.0,
    "drag": False,
    "press": None,
    "press_at": 0.0,
    "x": float(cfg["x"]),
    "y": float(cfg["y"]),
}


def show_bubble(text, secs=4.0):
    st["bubble"] = ""
    canvas.itemconfigure(sub_id, text=text, fill=PURPLE if st["mode"] == "work" else MUTED)
    st["bubble_until"] = time.time() + secs


def set_sub(title, color):
    canvas.itemconfigure(sub_id, text=title, fill=color)


def status_text():
    if st["mode"] == "work":
        return "写作业中 · 别分心哦", PURPLE
    if st["mode"] == "break":
        return "休息中 · 起来走两步", "#3f9c86"
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
    if st["mode"] in ("idle",):
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
        show_bubble("时间到啦！歇 5 分钟，起来走走", 6.0)
        canvas.itemconfigure(sprite_id, image=SPRITE_BLINK)
        st["blink_until"] = now + 6.0
        start_break()
    else:
        play_chime()
        show_bubble("休息好啦，点我继续～", 5.0)
        st["mode"] = "idle"
        st["left"] = WORK_MIN * 60.0
        st["end_at"] = None


# ---------- 书（每帧重画，顺便做翻页动画） ----------
def draw_book(now):
    """一本摊开的小书：两页 + 字行 + 翻页动画（每帧重画）"""
    canvas.delete("book")
    # 桌子上的小影子
    canvas.create_oval(58, BOOK_BOTTOM - 2, 242, BOOK_BOTTOM + 22,
                       fill="#ece2f8", outline="", tags="book")
    # 左页 / 右页（轻微透视：靠书脊那头高一点）
    canvas.create_polygon(BOOK_L[0], BOOK_TOP + 8, SPINE, BOOK_TOP,
                          SPINE, BOOK_BOTTOM, BOOK_L[0], BOOK_BOTTOM + 8,
                          fill="#fdfbff", outline="#d8c8ea", width=1, tags="book")
    canvas.create_polygon(SPINE, BOOK_TOP, BOOK_R[1], BOOK_TOP + 8,
                          BOOK_R[1], BOOK_BOTTOM + 8, SPINE, BOOK_BOTTOM,
                          fill="#fdfbff", outline="#d8c8ea", width=1, tags="book")
    # 书页上的字行
    for (x0, x1), (y0, y1) in ((BOOK_L, (BOOK_TOP + 8, BOOK_BOTTOM + 8)),
                               (BOOK_R, (BOOK_TOP + 8, BOOK_BOTTOM + 8))):
        for k in range(4):
            yy = y0 + 7 + k * 7
            canvas.create_line(x0 + 9, yy, x1 - 9, yy, fill="#ddd2ec", width=1, tags="book")
    # 书脊
    canvas.create_line(SPINE, BOOK_TOP, SPINE, BOOK_BOTTOM, fill="#cbb9e2", width=2, tags="book")

    # 翻页：一张纸从右页翻到左页
    if now < st["flip_start"] + 0.42:
        p = (now - st["flip_start"]) / 0.42
        if p < 0.5:
            x = SPINE + (BOOK_R[1] - SPINE) * (1 - p * 2)
            y0 = BOOK_TOP + (x - SPINE) / (BOOK_R[1] - SPINE) * 8
            fill = "#ffffff"
        else:
            x = SPINE - (SPINE - BOOK_L[0]) * ((p - 0.5) * 2)
            y0 = BOOK_TOP + (SPINE - x) / (SPINE - BOOK_L[0]) * 8
            fill = "#f8f2ff"
        canvas.create_polygon(SPINE, BOOK_TOP, x, y0, x, y0 + (BOOK_BOTTOM - BOOK_TOP),
                              SPINE, BOOK_BOTTOM,
                              fill=fill, outline="#ddcdea", width=1, tags="book")


def round_rect(x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
           x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
           x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


SPRITE_BLINK = None


def init_sprites():
    global SPRITE_BLINK
    SPRITE_BLINK = ImageTk.PhotoImage(sprite("blink", 0))
    canvas.itemconfigure(sprite_id, image=ImageTk.PhotoImage(sprite("idle", 0)))


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
        st["x"] = st["x"] + dx
        st["y"] = st["y"] + dy
        st["press"] = (e.x_root, e.y_root)
        root.geometry("%dx%d+%d+%d" % (WIN_W, WIN_H, int(st["x"]), int(st["y"])))


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
        toggle()


def save_cfg():
    try:
        cfg["x"], cfg["y"] = int(st["x"]), int(st["y"])
        json.dump(cfg, open(CFG, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass


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
    st["x"] = SW - WIN_W - 40
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
def _tick():
    now = time.time()
    st["t"] += TICK / 1000.0

    # 倒计时
    if st["mode"] in ("work", "break") and st["end_at"]:
        left = st["end_at"] - now
        if left <= 0:
            st["left"] = 0
            canvas.itemconfigure(timer_id, text="00:00")
            finish_round(now)
        else:
            st["left"] = left
            mm, ss = int(left) // 60, int(left) % 60
            canvas.itemconfigure(timer_id, text="%02d:%02d" % (mm, ss), fill=PURPLE if st["mode"] == "work" else "#3f9c86")
    elif st["mode"] == "paused":
        mm, ss = int(st["left"]) // 60, int(st["left"]) % 60
        canvas.itemconfigure(timer_id, text="%02d:%02d" % (mm, ss), fill=MUTED)
    else:
        canvas.itemconfigure(timer_id, text="%02d:00" % WORK_MIN, fill=PURPLE)

    # 状态行（气泡优先）
    if now < st["bubble_until"]:
        pass
    else:
        txt, col = status_text()
        set_sub("%s ｜ 番茄 %d" % (txt, data.get("count", 0)), col)

    # 翻页
    if now >= st["next_flip"]:
        st["flip_start"] = now
        st["next_flip"] = now + 2.2 + (0.6 if st["mode"] != "work" else 0.0)

    draw_book(now)

    # 角色：尾巴轻轻摇一下；休息时笑眼
    ti = 1 if math.sin(st["t"] * 1.6) < 0 else 2
    if now < st.get("blink_until", 0):
        img = SPRITE_BLINK
    else:
        img = SPRITE_IDLE[ti]
    if img is not None:
        canvas.itemconfigure(sprite_id, image=img)
    canvas.tag_raise("book")


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


SPRITE_IDLE = {}


def main():
    make_chime()
    init_sprites()
    for i in range(4):
        SPRITE_IDLE[i] = ImageTk.PhotoImage(sprite("idle", i))
    root.after(300, lambda: show_bubble("妈妈写作业，我翻书陪你～", 4.0))
    root.after(TICK, tick)
    root.mainloop()


if __name__ == "__main__":
    main()
