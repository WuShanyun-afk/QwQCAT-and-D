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
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageTk

APP = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(APP, "assets", "character.png")
CFG = os.path.join(APP, "pet-config.json")
SAY = os.path.join(APP, "say.txt")

KEY = "#ff00ff"
KEY_RGB = (255, 0, 255)

WIN_W, WIN_H = 340, 430          # 窗口（上：气泡区，下：角色）
BODY_H = 340                     # 角色显示高度（素材已按这个高度渲好）
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


NIGHT_START = 21   # 21:00
NIGHT_END = 6      # 06:00


def is_night():
    """晚上九点到早上六点 —— 困困模式"""
    if os.environ.get("PET_FORCE_NIGHT") == "1":
        return True
    if os.environ.get("PET_FORCE_DAY") == "1":
        return False
    h = time.localtime().tm_hour
    return h >= NIGHT_START or h < NIGHT_END


SW, SH = screen_size()
TASKBAR = 70                      # 底部留一点给任务栏

# ---------- 素材：妈妈画的 3 个表情 × 4 个尾巴角度 × 2 个耳朵角度 ----------
# 由 生成素材.py 预先渲好：assets\{idle,wink,blink}_{尾巴角}_{耳朵角}.png
ART_DIR = os.path.join(APP, "assets")
TAIL_N = 4          # 尾巴摇摆姿态数
EAR_N = 1           # 耳朵不动了（妈妈要求），只有尾巴摇
SQUEAK = os.path.join(ART_DIR, "squeak.wav")
MARGIN = 20         # 旋转留白（尾巴甩起来别切边）


def keyed(img):
    """RGBA -> 洋红底硬边（配合 -transparentcolor）"""
    rgb = img.convert("RGB")
    a = img.split()[3].point(lambda v: 255 if v >= 60 else 0)
    out = Image.new("RGB", img.size, KEY_RGB)
    out.paste(rgb, (0, 0), a)
    return out


FRAME_CACHE = {}


def get_frame(state_name, ti, ei, face):
    """按需加载某一帧（带缓存）：洋红键控 + 可选左右翻转"""
    key = (state_name, ti, ei, face)
    im = FRAME_CACHE.get(key)
    if im is not None:
        return im
    path = os.path.join(ART_DIR, "%s_%d_%d.png" % (state_name, ti, ei))
    src = Image.open(path).convert("RGBA")
    pad = Image.new("RGBA", (src.width + MARGIN * 2, src.height + MARGIN * 2), (0, 0, 0, 0))
    pad.alpha_composite(src, (MARGIN, MARGIN))
    if face:
        pad = pad.transpose(Image.FLIP_LEFT_RIGHT)
    im = keyed(pad)
    FRAME_CACHE[key] = im
    return im

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
CFG_DEFAULT = {"mode": "corner", "x": SW - WIN_W - 30, "y": SH - WIN_H - TASKBAR}
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
    "blink_until": 0.0, "next_blink": 0.0, "wink_until": 0.0,
    # 摸摸头
    "press_x": 0, "press_y": 0, "press_at": 0.0, "pat_after": None,
    "pat_until": 0.0, "pat_start": 0.0,
    # 电子捏捏乐（点一下整只往下压扁再弹回来）
    "squish_until": 0.0, "squish_start": 0.0, "squish_photos": None, "squish_key": None,
    # 耳朵 / 尾巴的小动作
    "ear_until": 0.0, "next_ear": 0.0,
    # 晚上九点后的困困模式
    "is_night": None, "night_wink_until": 0.0, "next_night_wink": 0.0,
    "next_night_talk": 0.0,
}

IMAGE_Y = WIN_H - 6 + MARGIN

LINES = ["妈妈～", "我在哦", "要一起玩吗？", "喵？", "嘿嘿", "今天也辛苦啦",
         "小鲸鱼在游～", "陪我一会儿嘛", "右键可以设置我"]

# 被摸头时说的话（随机）
PAT_LINES = ["嘿嘿…好舒服", "再摸摸嘛～", "唔…被摸头了", "妈妈的摸摸最好了",
             "呼噜呼噜…", "开心！", "还要还要～"]

# 晚九点后的困困台词
NIGHT_LINES = ["困困……九点啦", "哈——欠……", "妈妈也要早点睡哦", "眼皮好重…"]
NIGHT_TALK = ["困……", "zzz……", "妈妈还不睡吗～", "陪我一起睡嘛", "眼睛要睁不开了…"]

photo = None
bubble_img = None
bubble_id = None
img_id = canvas.create_image(WIN_W // 2, IMAGE_Y, anchor="s")


def set_frame(state_name, ti, ei, face):
    global photo
    photo = ImageTk.PhotoImage(get_frame(state_name, ti, ei, face))
    canvas.itemconfigure(img_id, image=photo)


SQUISH_DUR = 0.5
SQUASH_CACHE = {}


def _choke(im):
    """缩放后边缘会留一圈半透明的洋红混色（看起来是紫边），这里抹成纯洋红（= 真透明）"""
    r, g, b = im.split()
    m = ImageChops.multiply(
        ImageChops.multiply(r.point(lambda v: 255 if v >= 150 else 0),
                            b.point(lambda v: 255 if v >= 150 else 0)),
        g.point(lambda v: 255 if v <= 120 else 0))
    out = im.copy()
    out.paste(Image.new("RGB", im.size, KEY_RGB), (0, 0), m)
    return out


def squash_frames(state_name, ti, ei, face):
    """一捏一弹的一串帧：底边钉住不动，整只从上往下压扁（跟作业挂件一样的手感）"""
    key = (state_name, ti, ei, face)
    frames = SQUASH_CACHE.get(key)
    if frames:
        return frames
    base = get_frame(state_name, ti, ei, face)
    out = []
    for sx, sy in ((1.00, 1.00), (1.03, 0.92), (1.07, 0.82), (1.09, 0.76),
                   (1.05, 0.86), (1.02, 0.95), (1.00, 1.02), (1.00, 1.00)):
        w = max(1, int(base.width * sx))
        h = max(1, int(base.height * sy))
        out.append(ImageTk.PhotoImage(_choke(base.resize((w, h), Image.LANCZOS))))
    SQUASH_CACHE[key] = out
    return out


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


# 颜文字只用微软雅黑里有的字符（๑ ㅂ ᴗ 这些会变方块）
KAOMOJI = ["(≧▽≦)", "(*/ω＼*)", "(｡>﹏<｡)", "ヾ(≧▽≦*)o", "(>ω<)", "(＾▽＾)",
           "(￣▽￣)", "(=^･ω･^=)"]


def _add_particle(text, font, color, x, y, ttl=1.4, rise=46):
    it = canvas.create_text(x, y, text=text, font=font, fill=color)
    canvas.tag_raise(it)              # 要在角色前面
    state["hearts"].append({"id": it, "born": time.time(), "x": x, "y": y,
                            "ttl": ttl, "rise": rise})


def spawn_hearts(n=2):
    for _ in range(n):
        x = WIN_W // 2 + random.randint(-55, 55)
        y = WIN_H - 120
        _add_particle("💗", ("Segoe UI Emoji", 15), "#ff7fae", x, y)


def spawn_pop():
    """点击时只冒一两个：一颗爱心 + 有概率一个颜文字"""
    cx, cy = WIN_W // 2, WIN_H - 320
    _add_particle("💗", ("Segoe UI Emoji", 18), "#ff6fa5",
                  cx + random.randint(-70, -34), cy, ttl=1.5, rise=58)
    if random.random() < 0.75:
        _add_particle(random.choice(KAOMOJI), ("Microsoft YaHei", 11, "bold"), "#c96a9b",
                      cx + random.randint(28, 72), cy + 8, ttl=1.5, rise=46)


def play_squeak():
    try:
        import winsound
        winsound.PlaySound(SQUEAK, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
    except Exception:
        pass


def update_hearts():
    now = time.time()
    keep = []
    for hp in state["hearts"]:
        age = now - hp["born"]
        if age > hp["ttl"]:
            canvas.delete(hp["id"])
            continue
        canvas.coords(hp["id"], hp["x"] + math.sin(age * 7) * 8, hp["y"] - hp["rise"] * age)
        keep.append(hp)
    state["hearts"] = keep


# ---------- 交互 ----------
def on_press(e):
    state["dragging"] = True
    state["press_x"] = e.x_root
    state["press_y"] = e.y_root
    state["press_at"] = time.time()
    state["drag_dx"] = e.x_root - state["x"]
    state["drag_dy"] = e.y_root - state["y"]


def on_drag(e):
    if state["dragging"]:
        state["x"] = e.x_root - state["drag_dx"]
        state["y"] = e.y_root - state["drag_dy"]


def _log(tag):
    try:
        with open(os.path.join(APP, "pet.log"), "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%H:%M:%S"), tag))
    except Exception:
        pass


def do_pat():
    """摸摸头：笑眼 + 弹一下 + 「吱吱」+ 冒一两个爱心/颜文字"""
    now = time.time()
    state["pat_until"] = now + 1.3
    state["pat_start"] = now
    state["squish_start"] = now
    state["squish_until"] = now + SQUISH_DUR
    state["squish_key"] = None
    state["wink_until"] = 0.0
    play_squeak()
    show_bubble(random.choice(PAT_LINES), 2.8)
    spawn_pop()                              # 气泡会把角色提到最上层，所以粒子最后加
    _log("pat")


def on_release(e):
    was = state["dragging"]
    state["dragging"] = False
    if not was:
        return
    moved = math.hypot(e.x_root - state["press_x"], e.y_root - state["press_y"])
    quick = time.time() - state["press_at"] < 0.45
    if moved <= 6 and quick:
        # 单击 = 摸摸头；等 0.22 秒确认不是双击
        if state["pat_after"] is not None:
            try:
                root.after_cancel(state["pat_after"])
            except Exception:
                pass
        state["pat_after"] = root.after(220, _pat_now)


def _pat_now():
    state["pat_after"] = None
    do_pat()


def on_double(e):
    if state["pat_after"] is not None:
        try:
            root.after_cancel(state["pat_after"])
        except Exception:
            pass
        state["pat_after"] = None
    show_bubble(random.choice(LINES))
    spawn_hearts(3)
    state["wink_until"] = time.time() + 1.0


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
    menu.add_command(label="摸摸头 💗", command=do_pat)
    menu.add_separator()
    menu.add_command(label="待在角落（安静陪你）", command=lambda: set_mode("corner"))
    menu.add_command(label="跟着鼠标跑", command=lambda: set_mode("follow"))
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

# 鼠标放到小D身上 → 小手光标（暗示"可以摸摸"）
def _hand_cursor(_e):
    root.configure(cursor="hand2")


def _arrow_cursor(_e):
    root.configure(cursor="")


root.bind("<Enter>", _hand_cursor)
root.bind("<Leave>", _arrow_cursor)


# ---------- 主循环 ----------
def _tick():
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

    # 眨眼 / 单眼眨 / 困困
    now = time.time()
    night = is_night()
    if night != state["is_night"]:
        state["is_night"] = night
        if night:
            show_bubble(random.choice(NIGHT_LINES), 4.0)
            state["next_night_wink"] = now + random.uniform(4, 8)
            state["next_night_talk"] = now + random.uniform(90, 150)
        else:
            state["next_blink"] = 0.0

    if now >= state["next_blink"]:
        state["blink_until"] = now + 0.16
        state["next_blink"] = now + random.uniform(2.5, 6.5)

    # 困困时偶尔睁开一只眼睛卖萌
    if night and now >= state["next_night_wink"]:
        state["night_wink_until"] = now + random.uniform(2.2, 3.4)
        state["next_night_wink"] = now + random.uniform(9, 20)
    # 困困时的碎碎念
    if night and now >= state["next_night_talk"]:
        show_bubble(random.choice(NIGHT_TALK), 3.0)
        state["next_night_talk"] = now + random.uniform(240, 600)

    _forced = os.environ.get("PET_DEBUG_STATE")
    if _forced in ("idle", "wink", "blink"):
        cur_state = _forced
    elif now < state["pat_until"]:
        cur_state = "blink"          # 被摸头 → 笑眼开心
    elif now < state["wink_until"]:
        cur_state = "wink"
    elif night:
        cur_state = "wink" if now < state["night_wink_until"] else "blink"   # 闭眼犯困
    elif now < state["blink_until"]:
        cur_state = "blink"
    else:
        cur_state = "idle"

    if cur_state != state.get("last_state"):
        state["last_state"] = cur_state
        try:
            with open(os.path.join(APP, "pet.log"), "a", encoding="utf-8") as _f:
                _f.write("%s %s\n" % (time.strftime("%H:%M:%S"), cur_state))
        except Exception:
            pass

    # 小动作：全身不动、耳朵也不动，只有尾巴在摇
    ei = 0

    happy = now < state["pat_until"]
    if state["sleeping"]:
        speed, amp = 0.7, 0.45
    elif happy:
        speed, amp = 3.4, 1.0          # 被摸时尾巴摇得快
    elif night:
        speed, amp = 1.0, 0.5          # 困了慢慢晃
    elif walking:
        speed, amp = 3.0, 1.0
    else:
        speed, amp = 1.7, 0.8
    sway = math.sin(t * speed) * amp
    # 4 个尾巴姿态：-6.5° / -2.2° / +2.2° / +6.5°
    ti = 0 if sway < -0.55 else 1 if sway < 0.0 else 2 if sway < 0.55 else 3
    # 电子捏捏乐：点一下整只往下压扁再弹回来
    if now < state.get("squish_until", 0.0):
        key = (cur_state, ti, ei, state["face"])
        if state.get("squish_key") != key or not state.get("squish_photos"):
            state["squish_photos"] = squash_frames(*key)
            state["squish_key"] = key
        photos = state["squish_photos"]
        p = (now - state["squish_start"]) / SQUISH_DUR
        idx = min(len(photos) - 1, int(p * len(photos)))
        canvas.itemconfigure(img_id, image=photos[idx])
        canvas.coords(img_id, WIN_W // 2, IMAGE_Y)
    else:
        set_frame(cur_state, ti, ei, state["face"])

        # 被摸头时整只弹一下（捏捏乐的时候不弹，免得打架）
        bounce = 0.0
        if now < state["pat_until"]:
            p = 1.0 - (state["pat_until"] - now) / 1.3
            bounce = -9.0 * abs(math.sin(p * math.pi * 2.0))
        canvas.coords(img_id, WIN_W // 2, IMAGE_Y + bounce)

    update_hearts()

    # 每隔约 2 秒把窗口重新顶到最前面（有时候别的置顶窗口会把它压下去，
    # 妈妈就会觉得「桌宠不见了」，其实它还在原地）
    state["ticks"] = state.get("ticks", 0) + 1
    if state["ticks"] % 40 == 0:
        try:
            root.attributes("-topmost", True)
            root.lift()
        except Exception:
            pass


_FORCE_SQUISH = os.environ.get("PET_FORCE_SQUISH") == "1"


def tick():
    """主循环外面包一层 try：万一某帧出错，也只记一笔，不整个停掉。"""
    try:
        _tick()
    except Exception:
        try:
            import traceback
            with open(os.path.join(APP, "pet.log"), "a", encoding="utf-8") as _f:
                _f.write("%s ERROR %s\n" % (
                    time.strftime("%H:%M:%S"),
                    traceback.format_exc().replace("\n", " | ")))
        except Exception:
            pass
        if _FORCE_SQUISH and time.time() >= state.get("squish_until", 0.0):
            state["squish_start"] = time.time()
            state["squish_until"] = state["squish_start"] + SQUISH_DUR
            state["squish_key"] = None
    finally:
        root.after(TICK, tick)


# 启动时先把 say.txt 现有内容记下来，不当成"新消息"念
try:
    state["say_mtime"] = os.path.getmtime(SAY)
    state["last_say"] = open(SAY, "r", encoding="utf-8").read().strip()
except Exception:
    pass

state["is_night"] = is_night()
if state["is_night"]:
    state["next_night_wink"] = time.time() + random.uniform(3, 6)
    state["next_night_talk"] = time.time() + random.uniform(120, 300)
    root.after(400, lambda: show_bubble(random.choice(NIGHT_LINES), 4.0))
else:
    root.after(400, lambda: show_bubble("我是小D～点我可以摸摸头", 4.0))
root.after(150, tick)
root.mainloop()
