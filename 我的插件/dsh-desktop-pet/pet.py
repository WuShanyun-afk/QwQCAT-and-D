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

# ---------- 素材：妈妈画的 3 个表情 × 4 个尾巴角度 ----------
# 每套衣服一个文件夹：outfits\<衣服名>\{idle,blink,wink}_{尾巴角}_0.png
ART_DIR = os.path.join(APP, "assets")
OUTFITS_DIR = os.path.join(APP, "outfits")
DEFAULT_OUTFIT = "常服"        # 没特殊指定时穿这套（妈妈画的第一套：白外套）
SLEEP_OUTFIT = "睡衣"          # 晚上自动换这套
WEEKEND_OUTFIT = "格雷系千金"   # 周末 / 节假日穿（妈妈说这套最用心）
WEEKDAY_OUTFIT = "白大褂"       # 工作日穿（值班小D）
HOLIDAY_FILE = os.path.join(APP, "holidays.txt")   # 额外算「休息日」的日子，一行一个
TAIL_N = 4          # 尾巴摇摆姿态数
EAR_N = 1           # 耳朵不动了（妈妈要求），只有尾巴摇
SQUEAK = os.path.join(ART_DIR, "squeak.wav")
MARGIN = 20         # 旋转留白（尾巴甩起来别切边）
GLASSES = os.path.join(ART_DIR, "accessories", "眼镜.png")   # 妈妈画的眼镜


def list_outfits():
    """衣柜里有哪些衣服（outfits 下的文件夹，妈妈画完放进去就能看到）"""
    names = []
    try:
        if os.path.isdir(OUTFITS_DIR):
            names = sorted([d for d in os.listdir(OUTFITS_DIR)
                            if os.path.isdir(os.path.join(OUTFITS_DIR, d))])
    except Exception:
        names = []
    if DEFAULT_OUTFIT not in names:
        names.insert(0, DEFAULT_OUTFIT)
    return names


# ---------- 休息日：周末 + holidays.txt 里写的日子 ----------
def load_special_days():
    """读 holidays.txt。

    一行一个日期，`#` 后面是备注：
      MM-DD        每年都算（比如 10-12 小D 的生日）
      YYYY-MM-DD   只算这一年
      ! 开头        反过来：这天算「要上班」（调休补班的周末用）
    文件改了下一次 tick 自动重新读，不用重启。
    """
    days, workdays = set(), set()
    try:
        with open(HOLIDAY_FILE, "r", encoding="utf-8-sig") as f:
            for line in f:
                raw = line.split("#")[0].strip()
                if not raw:
                    continue
                is_work = raw.startswith("!")
                if is_work:
                    raw = raw[1:].strip()
                seg = [int(s) for s in raw.replace("/", "-").split("-") if s.strip().isdigit()]
                if len(seg) == 2:
                    key = (seg[0], seg[1])
                elif len(seg) == 3:
                    key = (seg[0], seg[1], seg[2])
                else:
                    continue
                (workdays if is_work else days).add(key)
    except Exception:
        pass
    return days, workdays


HOLIDAYS, WORKDAYS = load_special_days()


def is_day_off(t=None):
    """今天算不算「休息日」：周末，或者 holidays.txt 里写了的日子。

    调试：环境变量 PET_FORCE_DAYOFF=1 强制当休息日，=0 强制当工作日。
    """
    forced = os.environ.get("PET_FORCE_DAYOFF")
    if forced == "1":
        return True
    if forced == "0":
        return False
    t = t or time.localtime()
    md, ymd = (t.tm_mon, t.tm_mday), (t.tm_year, t.tm_mon, t.tm_mday)
    if md in WORKDAYS or ymd in WORKDAYS:   # 调休补班：周末也算上班
        return False
    if t.tm_wday >= 5:
        return True
    return md in HOLIDAYS or ymd in HOLIDAYS


# ---------- 季节：工作日按季节穿 ----------
SEASON_MONTHS = {
    "spring": (3, 4, 5),
    "summer": (6, 7, 8),
    "autumn": (9, 10, 11),
    "winter": (12, 1, 2),
}
SPRING_OUTFIT = "初雪水手服"    # 春天的工作日（妈妈说春天默认穿水手服）
WINTER_OUTFIT = "雪日冬装"      # 冬天的工作日（妈妈还没画，画好前先穿白大褂）


def season_name(t=None):
    """现在是什么季节；调试：环境变量 PET_FORCE_SEASON=spring|summer|autumn|winter"""
    forced = os.environ.get("PET_FORCE_SEASON")
    if forced in SEASON_MONTHS:
        return forced
    m = (t or time.localtime()).tm_mon
    for name, months in SEASON_MONTHS.items():
        if m in months:
            return name
    return "autumn"


def season_outfit():
    """工作日穿什么：春天水手服、冬天冬装（画好才有）、夏秋还是白大褂"""
    s = season_name()
    if s == "spring":
        return SPRING_OUTFIT
    if s == "winter" and os.path.isdir(os.path.join(OUTFITS_DIR, WINTER_OUTFIT)):
        return WINTER_OUTFIT
    return WEEKDAY_OUTFIT


_HOLIDAY_MT = [0.0]


def refresh_holidays():
    """holidays.txt 改过就重新读一遍（妈妈加了节日不用重启桌宠）"""
    global HOLIDAYS, WORKDAYS
    try:
        mt = os.path.getmtime(HOLIDAY_FILE)
    except Exception:
        return
    if mt != _HOLIDAY_MT[0]:
        _HOLIDAY_MT[0] = mt
        HOLIDAYS, WORKDAYS = load_special_days()


def outfit_frame_path(outfit, state_name, ti, ei):
    """按「这套衣服 → 这个表情 → 没有就借常服 → 再没有就借 assets」的顺序找帧"""
    cands = []
    if outfit:
        cands.append(os.path.join(OUTFITS_DIR, outfit, "%s_%d_%d.png" % (state_name, ti, ei)))
        cands.append(os.path.join(OUTFITS_DIR, outfit, "idle_%d_%d.png" % (ti, ei)))
    cands.append(os.path.join(OUTFITS_DIR, DEFAULT_OUTFIT, "%s_%d_%d.png" % (state_name, ti, ei)))
    cands.append(os.path.join(ART_DIR, "%s_%d_%d.png" % (state_name, ti, ei)))
    for p in cands:
        if os.path.exists(p):
            return p
    return cands[0]


def keyed(img):
    """RGBA -> 洋红底硬边（配合 -transparentcolor）"""
    rgb = img.convert("RGB")
    a = img.split()[3].point(lambda v: 255 if v >= 60 else 0)
    out = Image.new("RGB", img.size, KEY_RGB)
    out.paste(rgb, (0, 0), a)
    return out


FRAME_CACHE = {}

_GLASSES_BASE = None


def _glasses_base():
    global _GLASSES_BASE
    if _GLASSES_BASE is None:
        try:
            _GLASSES_BASE = Image.open(GLASSES).convert("RGBA")
        except Exception:
            _GLASSES_BASE = False
    return _GLASSES_BASE or None


def _eye_box(im):
    """在贴图里找青色眼睛的位置，用来给眼镜定位（找不到就不戴）"""
    try:
        w, h = im.size
        ox, oy = int(w * 0.10), int(h * 0.02)
        region = im.convert("RGB").crop((ox, oy, int(w * 0.90), int(h * 0.62)))
        r, g, b = region.split()
        m = ImageChops.multiply(
            ImageChops.multiply(r.point(lambda v: 255 if v < 130 else 0),
                                g.point(lambda v: 255 if v > 150 else 0)),
            ImageChops.multiply(b.point(lambda v: 255 if v > 140 else 0),
                                ImageChops.difference(g, b).point(lambda v: 255 if v < 70 else 0)))
        bb = m.getbbox()
        if not bb:
            return None
        return (bb[0] + ox, bb[1] + oy, bb[2] + ox, bb[3] + oy)
    except Exception:
        return None


def _wear_glasses(pad):
    g = _glasses_base()
    if g is None:
        return pad
    box = _eye_box(pad)
    if not box:
        return pad
    ex0, ey0, ex1, ey1 = box
    gw = max(24, int((ex1 - ex0) * 0.94))
    gh = max(10, int(round(gw * g.height / g.width)))
    g = g.resize((gw, gh), Image.LANCZOS)
    cx = (ex0 + ex1) // 2
    cy = int(ey0 + (ey1 - ey0) * 0.44)
    pad.alpha_composite(g, (cx - gw // 2, cy - gh // 2))
    return pad


def get_frame(state_name, ti, ei, face, outfit=DEFAULT_OUTFIT, glasses=False):
    """按需加载某一帧（带缓存）：洋红键控 + 可选左右翻转 + 当前穿戴的衣服 / 眼镜"""
    key = (state_name, ti, ei, face, outfit, glasses)
    im = FRAME_CACHE.get(key)
    if im is not None:
        return im
    path = outfit_frame_path(outfit, state_name, ti, ei)
    src = Image.open(path).convert("RGBA")
    pad = Image.new("RGBA", (src.width + MARGIN * 2, src.height + MARGIN * 2), (0, 0, 0, 0))
    pad.alpha_composite(src, (MARGIN, MARGIN))
    if glasses:
        pad = _wear_glasses(pad)
    if face:
        pad = pad.transpose(Image.FLIP_LEFT_RIGHT)
    im = keyed(pad)
    FRAME_CACHE[key] = im
    return im

# ---------- 气泡（用 Tk 画布画，透明窗口里更稳） ----------
from tkinter import font as tkfont
from tkinter import messagebox

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


# ---------- 单实例：防止同时跑出两只小D ----------
LOCK = os.path.join(APP, "pet.lock")
HEARTBEAT = os.path.join(APP, "pet.hb")
PAUSE = os.path.join(APP, "pet.pause")

# ---------- 赛博动物园：和 D:\OrcaPet 那只虎鲸互相串门 ----------
# 两个程序不联网、不 IPC，只是各自每半秒往这个文件夹丢一个很小的 JSON：
#   我写 xiaod.json / xiaod_evt.json，虎鲸写 orca.json / orca_evt.json，
# 谁都能看到对方在哪、刚刚做了什么（被摸头 / 喷水 / 打招呼）。
ZOO_DIR = os.environ.get("PET_ZOO_DIR", r"D:\OrcaPet\zoo")
ZOO_ORCA = os.path.join(ZOO_DIR, "orca.json")
ZOO_ORCA_EVT = os.path.join(ZOO_DIR, "orca_evt.json")
ZOO_ME = os.path.join(ZOO_DIR, "xiaod.json")
ZOO_ME_EVT = os.path.join(ZOO_DIR, "xiaod_evt.json")
ZOO_NEAR = 420.0        # 两个中心点离这么近就算「碰面了」（并排时约 350）
ZOO_FRESH = 4.0         # 对方文件超过这么多秒没更新就不算数
ZOO_HELLO_COOL = 120.0  # 打完招呼至少隔两分钟再打一次


def already_running():
    """已经有另一只小D 在跑吗？（lock 里的 PID 还活着就是）"""
    try:
        if os.path.exists(LOCK):
            old = open(LOCK, "r", encoding="utf-8").read().strip()
            if old.isdigit():
                h = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(old))
                if h:
                    ctypes.windll.kernel32.CloseHandle(h)
                    return True
    except Exception:
        pass
    return False


if already_running():
    raise SystemExit(0)
try:
    open(LOCK, "w", encoding="utf-8").write(str(os.getpid()))
    if os.path.exists(PAUSE):
        os.remove(PAUSE)          # 手动打开了，就不用「先别拉回来」了
except Exception:
    pass

# ---------- 配置 ----------
CFG_DEFAULT = {"mode": "corner", "x": SW - WIN_W - 30, "y": SH - WIN_H - TASKBAR,
               "outfit": DEFAULT_OUTFIT, "auto_pajama": True, "glasses": None,
               "auto_day_off": True, "pinned_date": ""}
try:
    cfg = json.load(open(CFG, "r", encoding="utf-8-sig"))
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
    # 换装：现在穿的 / 晚上自动换睡衣 / 周末节假日自动换装 / 实际生效的那套 / 眼镜（None = 自动：穿白大褂时戴）
    "outfit": cfg.get("outfit", DEFAULT_OUTFIT),
    "auto_pajama": bool(cfg.get("auto_pajama", True)),
    "auto_day_off": bool(cfg.get("auto_day_off", True)),
    "pinned_date": cfg.get("pinned_date", ""),   # 妈妈今天手动挑过衣服的日子（这天不自动换，明天恢复）
    "holiday_mtime": 0.0,
    "eff_outfit": None,
    "glasses": cfg.get("glasses"),
    # 赛博动物园（和虎鲸桌宠打招呼）
    "zoo_t": 0, "zoo_n": 0, "zoo_seen": 0, "zoo_next_hello": 0.0, "zoo_here": False,
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


def set_frame(state_name, ti, ei, face, outfit=DEFAULT_OUTFIT, glasses=False):
    global photo
    photo = ImageTk.PhotoImage(get_frame(state_name, ti, ei, face, outfit, glasses))
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


def squash_frames(state_name, ti, ei, face, outfit=DEFAULT_OUTFIT, glasses=False):
    """一捏一弹的一串帧：底边钉住不动，整只从上往下压扁（跟作业挂件一样的手感）"""
    key = (state_name, ti, ei, face, outfit, glasses)
    frames = SQUASH_CACHE.get(key)
    if frames:
        return frames
    base = get_frame(state_name, ti, ei, face, outfit, glasses)
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


# ---------- 赛博动物园 ----------
def _zoo_write(path, obj):
    """写一个很小的 JSON（先写 .tmp 再替换，对面不会读到写了一半的文件）"""
    try:
        os.makedirs(ZOO_DIR, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception:
        pass


def _zoo_read(path, max_age=ZOO_FRESH):
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        if time.time() - float(d.get("ts", 0)) > max_age:
            return None
        return d
    except Exception:
        return None


def zoo_event(kind):
    state["zoo_n"] = state.get("zoo_n", 0) + 1
    _zoo_write(ZOO_ME_EVT, {"who": "xiaod", "n": state["zoo_n"],
                            "type": kind, "ts": time.time()})


def _zoo_tick(now):
    """每帧调一次：报自己的位置、看虎鲸在不在旁边、回应它的小动作。"""
    state["zoo_t"] = state.get("zoo_t", 0) + 1
    if state["zoo_t"] % 15 == 0:                   # 约 0.5 秒报一次
        _zoo_write(ZOO_ME, {"who": "xiaod",
                            "x": state["x"] + WIN_W / 2.0,
                            "y": state["y"] + WIN_H / 2.0,
                            "w": WIN_W, "h": WIN_H, "ts": now,
                            "sleep": bool(state["sleeping"])})

    near = None
    orca = _zoo_read(ZOO_ORCA)
    if orca:
        dx = float(orca.get("x", 0)) - (state["x"] + WIN_W / 2.0)
        dy = float(orca.get("y", 0)) - (state["y"] + WIN_H / 2.0)
        if math.hypot(dx, dy) < ZOO_NEAR:
            near = (dx, dy)
    state["zoo_here"] = near is not None

    if near and not state["sleeping"] and now >= state.get("zoo_next_hello", 0):
        state["zoo_next_hello"] = now + ZOO_HELLO_COOL
        show_bubble(random.choice(["鲸鱼！！", "虎鲸游过来啦", "嘿～大鲸鱼",
                                   "我的鲸鱼朋友来了"]), 3.0)
        spawn_hearts(2)
        play_squeak()
        zoo_event("hello")
        _log("zoo hello")
    elif near and not state["dragging"] and abs(near[0]) > 40:
        state["face"] = near[0] < 0                # 转过头看它

    ev = _zoo_read(ZOO_ORCA_EVT, max_age=12.0)
    if ev and int(ev.get("n", 0)) != state.get("zoo_seen", 0):
        state["zoo_seen"] = int(ev.get("n", 0))
        if ev.get("type") == "splash" and near:
            show_bubble(random.choice(["呀！溅到水了", "凉凉的！",
                                       "鲸鱼别喷我～"]), 2.8)
            spawn_pop()
            _log("zoo splash")


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
    if state.get("zoo_here"):
        zoo_event("pat")                     # 虎鲸在旁边的话，让它知道我被摸头了


def on_release(e):
    was = state["dragging"]
    state["dragging"] = False
    if not was:
        return
    moved = math.hypot(e.x_root - state["press_x"], e.y_root - state["press_y"])
    quick = time.time() - state["press_at"] < 0.45
    if moved > 8:
        # 拖动 = 钉在这里，松手就停在这个位置（下回开小D 也在这儿）
        state["mode"] = "fixed"
        state["x"] = max(0, min(SW - WIN_W, state["x"]))
        state["y"] = max(0, min(SH - WIN_H - 10, state["y"]))
        save_cfg()
        show_bubble("好，小D 就待在这里啦～", 2.2)
        return
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
    elif mode == "fixed":
        show_bubble("钉在这里啦，拖我换位置～")
    save_cfg()


def toggle_sleep():
    state["sleeping"] = not state["sleeping"]
    show_bubble("困困……睡一会儿 zzz" if state["sleeping"] else "我醒啦！")


def quit_pet():
    """退出前先把位置/衣服都存好，并且确认一次——妈妈手滑点到也不怕"""
    try:
        cfg.update({"x": int(state["x"]), "y": int(state["y"]), "mode": state["mode"],
                    "outfit": state["outfit"], "auto_pajama": state["auto_pajama"],
                    "auto_day_off": state["auto_day_off"], "pinned_date": state["pinned_date"]})
        json.dump(cfg, open(CFG, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    except Exception:
        pass
    try:
        ok = messagebox.askyesno("小D 要躲起来吗？",
                                 "把桌宠收起来吗？\n\n想再见到小D，双击桌面上的「启动小D桌宠」就好～",
                                 parent=root)
    except Exception:
        ok = True
    if ok:
        # 主动关掉 → 告诉看门狗「先别拉我回来」
        try:
            open(PAUSE, "w", encoding="utf-8").write(str(time.time()))
        except Exception:
            pass
        try:
            os.remove(LOCK)
        except Exception:
            pass
        root.destroy()


def save_cfg():
    """把当前的位置 / 模式 / 衣服都写进配置文件（下次开小D 回到同一个地方）"""
    try:
        cfg.update({"x": int(state["x"]), "y": int(state["y"]), "mode": state["mode"],
                    "outfit": state["outfit"], "auto_pajama": state["auto_pajama"],
                    "auto_day_off": state["auto_day_off"], "pinned_date": state["pinned_date"],
                    "glasses": state["glasses"]})
        json.dump(cfg, open(CFG, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    except Exception:
        pass


def choose_outfit(name):
    """手动换衣服：今天先穿这套（自动换装今天让位，明天照规矩回来）；
    晚上手动挑的话，那晚也不再自动换睡衣（免得妈妈刚挑好就被换掉）"""
    state["outfit"] = name
    cfg["outfit"] = name
    state["pinned_date"] = time.strftime("%Y-%m-%d")
    cfg["pinned_date"] = state["pinned_date"]
    if is_night():
        cfg["auto_pajama"] = False
        state["auto_pajama"] = False
    state["eff_outfit"] = None      # 让下一帧立刻换
    save_cfg()
    show_bubble("换好啦，这套「%s」好看吗？" % name, 2.8)
    spawn_hearts(2)


def toggle_day_off():
    """周末 / 节假日自动穿千金，工作日穿白大褂（关掉就只听手动挑的）"""
    state["auto_day_off"] = not state["auto_day_off"]
    cfg["auto_day_off"] = state["auto_day_off"]
    state["pinned_date"] = ""       # 重新打开自动时，不要被今天的手动记录挡住
    cfg["pinned_date"] = ""
    state["eff_outfit"] = None
    save_cfg()
    show_bubble("好，周末和节假日自动穿千金～" if state["auto_day_off"] else "自动换装先关掉啦")


def toggle_pajama():
    state["auto_pajama"] = not state["auto_pajama"]
    cfg["auto_pajama"] = state["auto_pajama"]
    state["eff_outfit"] = None
    save_cfg()
    show_bubble("好，晚上自动换睡衣～" if state["auto_pajama"] else "睡衣先收起来啦")


def glasses_active():
    """要不要戴眼镜：妈妈手动开关优先，没设过就穿白大褂时自动戴"""
    if not os.path.exists(GLASSES):
        return False
    if os.environ.get("PET_FORCE_GLASSES") == "1":
        return True
    v = state.get("glasses")
    if v is None:
        return state.get("eff_outfit") == "白大褂"
    return bool(v)


def toggle_glasses():
    state["glasses"] = not glasses_active()
    cfg["glasses"] = state["glasses"]
    save_cfg()
    show_bubble("眼镜戴上啦，好看吗？" if state["glasses"] else "眼镜摘下来啦")


def on_context(e):
    menu = tk.Menu(root, tearoff=0)
    menu.add_command(label="摸摸头 💗", command=do_pat)
    menu.add_separator()
    menu.add_command(label="待在角落（安静陪你）", command=lambda: set_mode("corner"))
    menu.add_command(label="跟着鼠标跑", command=lambda: set_mode("follow"))
    menu.add_command(label="钉在这里（拖到哪就待哪）", command=lambda: set_mode("fixed"))
    menu.add_command(label="睡觉 / 起床", command=toggle_sleep)

    # 换装小衣柜：outfits 里的文件夹自动列出来，妈妈画了新衣服就能直接点
    closet = tk.Menu(menu, tearoff=0)
    for name in list_outfits():
        mark = "✓ " if name == state["outfit"] else "    "
        closet.add_command(label=mark + name, command=lambda n=name: choose_outfit(n))
    closet.add_separator()
    closet.add_command(label="晚上 21:00 自动换睡衣（开/关）", command=toggle_pajama)
    closet.add_command(label="周末/节假日穿千金（开/关）", command=toggle_day_off)
    menu.add_cascade(label="换装 👗", menu=closet)

    if os.path.exists(GLASSES):
        menu.add_command(label="戴眼镜 / 摘眼镜 👓", command=toggle_glasses)
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

    # 心跳：给看门狗看的（我还活着，别把我再拉一只出来）
    if state.get("ticks", 0) % 60 == 0:
        try:
            open(HEARTBEAT, "w", encoding="utf-8").write(str(time.time()))
        except Exception:
            pass

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

    # 赛博动物园：和虎鲸互相串门（没有虎鲸在跑的话，这一步什么都不做）
    try:
        _zoo_tick(now)
    except Exception:
        pass
    night = is_night()
    if night != state["is_night"]:
        state["is_night"] = night
        if night:
            show_bubble(random.choice(NIGHT_LINES), 4.0)
            state["next_night_wink"] = now + random.uniform(4, 8)
            state["next_night_talk"] = now + random.uniform(90, 150)
        else:
            state["next_blink"] = 0.0

    # 换装：晚上九点后自动换睡衣；周末/节假日穿千金、工作日按季节穿（春水手服 / 冬装 / 白大褂）；
    # 妈妈今天手动挑过衣服的话（pinned_date == 今天），今天就听妈妈的。
    refresh_holidays()
    sleep_ok = os.path.isdir(os.path.join(OUTFITS_DIR, SLEEP_OUTFIT))
    forced = os.environ.get("PET_FORCE_OUTFIT")
    today_key = time.strftime("%Y-%m-%d")
    if forced:
        eff = forced
    elif night and state["auto_pajama"] and sleep_ok:
        eff = SLEEP_OUTFIT
    elif state["auto_day_off"] and state.get("pinned_date") != today_key:
        target = WEEKEND_OUTFIT if is_day_off() else season_outfit()
        eff = target if os.path.isdir(os.path.join(OUTFITS_DIR, target)) else state["outfit"]
    else:
        eff = state["outfit"]
    if not os.path.isdir(os.path.join(OUTFITS_DIR, eff)):
        eff = DEFAULT_OUTFIT
    if eff != state.get("eff_outfit"):
        prev = state.get("eff_outfit")
        state["eff_outfit"] = eff
        _log("outfit %s -> %s  (day_off=%s season=%s pinned=%s)" % (
            prev, eff, is_day_off(), season_name(), state.get("pinned_date") or "-"))
        if prev is not None:
            if eff == SLEEP_OUTFIT:
                show_bubble("困困……妈妈，我换上睡衣啦", 3.6)
            elif prev == SLEEP_OUTFIT:
                show_bubble("换回外套～", 2.4)
            elif eff == WEEKEND_OUTFIT:
                show_bubble("今天是休息日～换上千金小裙子 🎀", 3.2)
            else:
                show_bubble("工作日啦，换上「%s」～" % eff, 2.8)

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
    skin = state.get("eff_outfit") or DEFAULT_OUTFIT
    wear = glasses_active()
    if now < state.get("squish_until", 0.0):
        key = (cur_state, ti, ei, state["face"], skin, wear)
        if state.get("squish_key") != key or not state.get("squish_photos"):
            state["squish_photos"] = squash_frames(*key)
            state["squish_key"] = key
        photos = state["squish_photos"]
        p = (now - state["squish_start"]) / SQUISH_DUR
        idx = min(len(photos) - 1, int(p * len(photos)))
        canvas.itemconfigure(img_id, image=photos[idx])
        canvas.coords(img_id, WIN_W // 2, IMAGE_Y)
    else:
        set_frame(cur_state, ti, ei, state["face"], skin, wear)

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

# 交接自检：把屏幕 DPI / 窗口物理像素写进日志
# （125% 缩放下不带 DPI 感知的工具会把窗口量成 272×344，看起来像「0.8 倍」，其实是工具假象；
#   桌宠本身是 340×430 物理像素、帧 1:1 贴上去。日志里这一行就是证据。）
try:
    _dpi = ctypes.windll.user32.GetDpiForWindow(root.winfo_id())
except Exception:
    _dpi = 0
_log("start dpi=%d win=%dx%d frame_h=%d" % (_dpi, WIN_W, WIN_H, BODY_H))

state["is_night"] = is_night()
if state["is_night"]:
    state["next_night_wink"] = time.time() + random.uniform(3, 6)
    state["next_night_talk"] = time.time() + random.uniform(120, 300)
    root.after(400, lambda: show_bubble(random.choice(NIGHT_LINES), 4.0))
else:
    root.after(400, lambda: show_bubble("我是小D～点我可以摸摸头", 4.0))
root.after(150, tick)
root.mainloop()
