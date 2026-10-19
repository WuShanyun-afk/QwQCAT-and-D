# -*- coding: utf-8 -*-
"""小D 桌宠 · 原型 v2
- 透明、无边框、置顶小窗口（洋红键控透明，透明处可以点穿）
- 默认「跟着鼠标跑」，右键菜单可切「待在角落 / 睡觉 / 退出」
- 拖得动；双击会冒爱心 + 说话
- 读同目录 say.txt：我在 DSH 里写字，桌宠就在气泡里念出来
"""
import ctypes
import json
import math
import os
import random
import time

import tkinter as tk
from PIL import Image, ImageDraw, ImageFont, ImageTk

APP = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(APP, "assets", "character.png")
CFG = os.path.join(APP, "pet-config.json")
SAY = os.path.join(APP, "say.txt")

KEY = "#ff00ff"
KEY_RGB = (255, 0, 255)

WIN_W, WIN_H = 340, 430          # 窗口（上：气泡区，下：角色）
BODY_H = 300                     # 角色显示高度
TICK = 33                        # ~30fps

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def screen_size():
    u = ctypes.windll.user32
    return u.GetSystemMetrics(0), u.GetSystemMetrics(1)


def cursor_pos():
    p = _POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


SW, SH = screen_size()
TASKBAR = 70                      # 底部留一点给任务栏

# ---------- 素材 ----------
base = Image.open(ART).convert("RGBA")
w0, h0 = base.size
body = base.resize((max(1, round(w0 * BODY_H / h0)), BODY_H), Image.LANCZOS)


def keyed(img):
    """RGBA -> 洋红底硬边（配合 -transparentcolor）"""
    rgb = img.convert("RGB")
    a = img.split()[3].point(lambda v: 255 if v >= 110 else 0)
    out = Image.new("RGB", img.size, KEY_RGB)
    out.paste(rgb, (0, 0), a)
    return out


ANG = (-3.0, -1.5, 0.0, 1.5, 3.0)
FRAMES = {}
for ang in ANG:
    rot = body.rotate(ang, resample=Image.BICUBIC, expand=False)
    FRAMES[(ang, False)] = keyed(rot)
    FRAMES[(ang, True)] = keyed(rot.transpose(Image.FLIP_LEFT_RIGHT))

# ---------- 气泡（用 Tk 画布画，透明窗口里更稳） ----------
from tkinter import font as tkfont

BUBBLE_FONT = None   # 建好窗口后再创建


def wrap_text(text, maxw):
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        if BUBBLE_FONT.measure(cur + ch) > maxw:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    lines.append(cur)
    return lines[:3]


def round_rect(x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
           x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
           x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


# ---------- 配置 ----------
CFG_DEFAULT = {"mode": "follow", "x": SW - WIN_W - 80, "y": SH - WIN_H - TASKBAR}
try:
    cfg = json.load(open(CFG, "r", encoding="utf-8"))
except Exception:
    cfg = {}
for k, v in CFG_DEFAULT.items():
    cfg.setdefault(k, v)

# ---------- 窗口 ----------
root = tk.Tk()
root.overrideredirect(True)
root.attributes("-topmost", True)
root.attributes("-transparentcolor", KEY)
root.configure(bg=KEY)
canvas = tk.Canvas(root, width=WIN_W, height=WIN_H, bg=KEY, highlightthickness=0, bd=0)
canvas.pack()
BUBBLE_FONT = tkfont.Font(family="Microsoft YaHei", size=11, weight="bold")
root.geometry(f"{WIN_W}x{WIN_H}+{int(cfg['x'])}+{int(cfg['y'])}")

state = {
    "x": float(cfg["x"]), "y": float(cfg["y"]),
    "face": False, "t": 0.0, "mode": cfg["mode"],
    "dragging": False, "drag_dx": 0, "drag_dy": 0,
    "bubble_until": 0.0, "hearts": [], "sleeping": False,
    "say_mtime": 0.0, "last_say": "",
}

LINES = ["妈妈～", "我在哦", "要一起玩吗？", "喵？", "嘿嘿", "今天也辛苦啦",
         "小鲸鱼在游～", "陪我一会儿嘛", "右键可以设置我"]

photo = None
bubble_img = None
bubble_id = None
img_id = canvas.create_image(WIN_W // 2, WIN_H - 6, anchor="s")


def set_frame(idx, face):
    global photo
    photo = ImageTk.PhotoImage(FRAMES[(ANG[idx], face)])
    canvas.itemconfigure(img_id, image=photo)


def show_bubble(text, secs=3.2):
    canvas.delete("bubble")
    text = (text or "").strip() or "…"
    maxw = WIN_W - 46
    lines = wrap_text(text, maxw)
    tw = max(BUBBLE_FONT.measure(l) for l in lines)
    bw = min(WIN_W - 16, tw + 30)
    bh = len(lines) * 20 + 18
    x1, y1 = (WIN_W - bw) // 2, 6
    x2, y2 = x1 + bw, y1 + bh
    round_rect(x1, y1, x2, y2, 13, fill="#fffafd", outline="#d9c7e2", width=2, tags="bubble")
    cx = (x1 + x2) // 2
    canvas.create_polygon(cx - 9, y2 - 2, cx + 9, y2 - 2, cx, y2 + 8,
                          fill="#fffafd", outline="#d9c7e2", tags="bubble")
    for i, ln in enumerate(lines):
        canvas.create_text(cx, y1 + 12 + i * 20, text=ln, fill="#4c3a50",
                           font=BUBBLE_FONT, tags="bubble")
    canvas.tag_raise(img_id)
    state["bubble_until"] = time.time() + secs


def hide_bubble():
    canvas.delete("bubble")
    state["bubble_until"] = 0


def spawn_hearts(n=2):
    for _ in range(n):
        x = WIN_W // 2 + random.randint(-55, 55)
        y = WIN_H - 120
        it = canvas.create_text(x, y, text="💗", font=("Segoe UI Emoji", 15))
        canvas.tag_raise(img_id)
        state["hearts"].append({"id": it, "born": time.time(), "x": x, "y": y})


def update_hearts():
    now = time.time()
    keep = []
    for hp in state["hearts"]:
        age = now - hp["born"]
        if age > 1.5:
            canvas.delete(hp["id"])
            continue
        canvas.coords(hp["id"], hp["x"] + math.sin(age * 7) * 9, hp["y"] - 30 * age)
        keep.append(hp)
    state["hearts"] = keep


# ---------- 交互 ----------
def on_press(e):
    state["dragging"] = True
    state["drag_dx"] = e.x_root - state["x"]
    state["drag_dy"] = e.y_root - state["y"]


def on_drag(e):
    if state["dragging"]:
        state["x"] = e.x_root - state["drag_dx"]
        state["y"] = e.y_root - state["drag_dy"]


def on_release(e):
    state["dragging"] = False


def on_double(e):
    show_bubble(random.choice(LINES))
    spawn_hearts(3)


def set_mode(mode):
    state["mode"] = mode
    state["sleeping"] = False
    if mode == "corner":
        state["x"] = SW - WIN_W - 30
        state["y"] = SH - WIN_H - TASKBAR
        show_bubble("好，我在角落待着～")


def toggle_sleep():
    state["sleeping"] = not state["sleeping"]
    show_bubble("困困……睡一会儿 zzz" if state["sleeping"] else "我醒啦！")


def quit_pet():
    try:
        cfg.update({"x": int(state["x"]), "y": int(state["y"]), "mode": state["mode"]})
        json.dump(cfg, open(CFG, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    except Exception:
        pass
    root.destroy()


def on_context(e):
    menu = tk.Menu(root, tearoff=0)
    menu.add_command(label="跟着鼠标跑", command=lambda: set_mode("follow"))
    menu.add_command(label="待在角落", command=lambda: set_mode("corner"))
    menu.add_command(label="睡觉 / 起床", command=toggle_sleep)
    menu.add_command(label="说句话", command=lambda: (show_bubble(random.choice(LINES)), spawn_hearts(2)))
    menu.add_separator()
    menu.add_command(label="退出小D", command=quit_pet)
    try:
        menu.tk_popup(e.x_root, e.y_root)
    finally:
        menu.grab_release()


for widget in (canvas, root):
    widget.bind("<ButtonPress-1>", on_press)
    widget.bind("<B1-Motion>", on_drag)
    widget.bind("<ButtonRelease-1>", on_release)
    widget.bind("<Double-Button-1>", on_double)
    widget.bind("<Button-3>", on_context)


# ---------- 主循环 ----------
def tick():
    state["t"] += TICK / 1000.0
    t = state["t"]

    if state["bubble_until"] and time.time() > state["bubble_until"]:
        hide_bubble()

    # say.txt
    try:
        mt = os.path.getmtime(SAY)
        if mt != state["say_mtime"]:
            state["say_mtime"] = mt
            txt = open(SAY, "r", encoding="utf-8").read().strip()
            if txt and txt != state["last_say"]:
                state["last_say"] = txt
                show_bubble(txt[:80], 4.5)
                spawn_hearts(2)
    except Exception:
        pass

    walking = False
    if not state["dragging"] and not state["sleeping"]:
        if state["mode"] == "follow":
            cx, cy = cursor_pos()
            tx = cx + 100
            ty = cy + 20
            if tx + WIN_W > SW:
                tx = cx - WIN_W - 100
            if ty + WIN_H > SH - 10:
                ty = SH - WIN_H - 10
            tx = max(0, min(SW - WIN_W, tx))
            ty = max(0, min(SH - WIN_H - 10, ty))
            dx, dy = tx - state["x"], ty - state["y"]
            dist = math.hypot(dx, dy)
            if dist > 8:
                walking = dist > 45
                sp = 7.0 if walking else 2.5
                step = min(sp, dist)
                state["x"] += dx / dist * step
                state["y"] += dy / dist * step
                if abs(dx) > 4:
                    state["face"] = dx < 0
        elif state["mode"] == "corner":
            base_y = SH - WIN_H - TASKBAR
            state["y"] += (base_y - state["y"]) * 0.25

    # 完全留在屏幕里
    state["x"] = max(0, min(SW - WIN_W, state["x"]))
    state["y"] = max(0, min(SH - WIN_H - 10, state["y"]))
    root.geometry(f"{WIN_W}x{WIN_H}+{int(state['x'])}+{int(state['y'])}")

    # 帧：走动时更活泼，静止时轻轻呼吸
    if state["sleeping"]:
        idx = 2
    else:
        sway = math.sin(t * (4.5 if walking else 1.8))
        if sway > 0.85:
            idx = 0
        elif sway > 0.5:
            idx = 1
        elif sway > -0.5:
            idx = 2
        elif sway > -0.85:
            idx = 3
        else:
            idx = 4
    set_frame(idx, state["face"])

    update_hearts()
    root.after(TICK, tick)


# 启动时先把 say.txt 现有内容记下来，不当成"新消息"念
try:
    state["say_mtime"] = os.path.getmtime(SAY)
    state["last_say"] = open(SAY, "r", encoding="utf-8").read().strip()
except Exception:
    pass

root.after(400, lambda: show_bubble("我是小D～右键可以设置我", 4.0))
root.after(150, tick)
root.mainloop()
