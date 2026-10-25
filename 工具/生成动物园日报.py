#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""赛博动物园 · 今日日报 —— 生成器

用本机实时数据重新生成 `游戏专区/zoo-daily.html`。
页面视觉和原来那版一模一样（CSS 全部内联、无外部字体/图片/CDN/JS），
只有数字、文案、时间线这些跟着真实数据走。

用法（在 D:\\小鲸鱼的专属文件夹 下）：
    python 工具\\生成动物园日报.py
    python 工具\\生成动物园日报.py --out 某个\\别的位置.html

数据来源（全部只读）：
    D:\\OrcaPet\\state.json                       fed / pats / hunger / mood / zoo
    D:\\OrcaPet\\zoo\\xiaod.json, orca.json        两只的中心坐标
    D:\\OrcaPet\\main.py                          体型公式 1 + min(0.16, fed * 0.0016)
    我的插件\\dsh-desktop-pet\\pet-config.json      outfit / auto_pajama / pinned_date
    我的插件\\dsh-desktop-pet\\pet.log              今晚这一段的事件（日志没有日期）

只用 Python 标准库。脚本可以反复运行：数据没变时不会重写文件。
算不出来的东西一律显示「—」，不编数字。
"""

import argparse
import ctypes
import html
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parent
OUT_DEFAULT = WORKSPACE / "游戏专区" / "zoo-daily.html"

ORCA_DIR = Path(r"D:\OrcaPet")
STATE_PATH = ORCA_DIR / "state.json"
XIAOD_PATH = ORCA_DIR / "zoo" / "xiaod.json"
ORCA_PATH = ORCA_DIR / "zoo" / "orca.json"
PET_DIR = WORKSPACE / "我的插件" / "dsh-desktop-pet"
CONFIG_PATH = PET_DIR / "pet-config.json"
LOG_PATH = PET_DIR / "pet.log"

EM = "—"
ACT_MSGS = ("pat", "zoo hello", "zoo splash")


# ------------------------------------------------------------------ 读文件
def read_json(path):
    """读一个 json；读不到就返回 None（页面显示「—」）。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def read_log(path):
    """把 pet.log 拆成 [{sec, hms, msg}]；带时间戳的行才要。"""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception:
        return []
    rows = []
    line_re = re.compile(r"^\s*(\d{1,2}):(\d{2}):(\d{2})\s+(.*?)\s*$")
    for line in text.splitlines():
        m = line_re.match(line)
        if not m:
            continue
        hh = int(m.group(1))
        rows.append({
            "sec": hh * 3600 + int(m.group(2)) * 60 + int(m.group(3)),
            "hms": "%02d:%s:%s" % (hh, m.group(2), m.group(3)),
            "msg": m.group(4),
        })
    return rows


# ------------------------------------------------ 从没有日期的日志里认「今晚」
def pick_evening_start(rows):
    """返回「今晚这一段」在 rows 里的起始下标。

    pet.log 是追加日志、只有 HH:MM:SS、没有日期，而且夜里重启还会再写
    `start dpi=`。所以不能真的取「最后一条 start dpi=」（那会落到最近一次重启，
    页面就空了）。这里的判据：
      1. 取 17:00–20:00 之间最后一条 `start dpi=` —— 也就是晚上正式开张那一批
         启动行里最后一条（18:49:39 这条，和原稿 62 次被摸、18:49–22:07 的
         口径一致）。不按「最后一天」划死，是为了半夜 0 点后重新生成时还能
         找回上一个晚上这一段；
      2. 没有傍晚启动行时，取最后一天里「今晚第一件互动（pat/hello/splash）
         之前」的最后一条启动行；
      3. 再不行就取最后一天/全日志最后一条启动行。
    """
    if not rows:
        return 0
    starts = [i for i, r in enumerate(rows) if r["msg"].startswith("start dpi=")]
    if not starts:
        return 0

    day0 = 0
    for i in range(1, len(rows)):
        if rows[i]["sec"] < rows[i - 1]["sec"] - 4 * 3600:
            day0 = i

    evening_starts = [i for i in starts if 17 * 3600 <= rows[i]["sec"] < 20 * 3600]
    if evening_starts:
        return evening_starts[-1]

    act_idx = [i for i in range(day0, len(rows))
               if rows[i]["sec"] >= 17 * 3600 and rows[i]["msg"] in ACT_MSGS]
    if act_idx:
        before = [i for i in starts if day0 <= i < act_idx[0]]
        if before:
            return before[-1]

    day_starts = [i for i in starts if i >= day0]
    return day_starts[-1] if day_starts else starts[-1]


# ------------------------------------------ 先看日志里的日期分隔线（新格式）
DATE_LINE_RE = re.compile(r"^== (\d{4}-\d{2}-\d{2}) ==$")


def date_lines(rows):
    """日志里的日期分隔线：返回 [(行下标, 'YYYY-MM-DD'), ...]。

    桌宠写出来的整行形如 `22:30:01 == 2026-10-25 ==`，只有它知道日志是哪天。
    """
    marks = []
    for i, row in enumerate(rows):
        m = DATE_LINE_RE.match(row["msg"])
        if m:
            marks.append((i, m.group(1)))
    return marks


def pick_segment(rows, today_iso):
    """认出「今天这一段」，返回 (起始下标, 日志日期 or None, 方式)。

    方式有三种：
      - "date"        ：今天日期线的时间在 00:00–05:59 —— 正常跨天写下的当天起点，
                        严格从这条往后统计，不做任何保护；
      - "date-midday" ：今天日期线的时间在 06:00–23:59 —— 旧代码白天/半路补记的
                        （今晚 22:28 那条），日期照用，但段起点退回当天的晚间启动
                        启发式，避免把当天更早的活动丢掉；
      - "fallback"    ：日志里没有今天的日期分隔线（旧格式 / 今天还没写过），
                        退回晚间启动启发式。

    同一天有多条日期线时取最后一条。新 pet.py 保证同一天只在真正的当天起点写
    一条，所以这种情况只会出现在像今晚这样旧代码留下的历史日志里。
    """
    if not rows:
        return 0, None, "fallback"

    today_marks = [(i, d) for i, d in date_lines(rows) if d == today_iso]
    if not today_marks:
        return pick_evening_start(rows), None, "fallback"

    last_i, day = today_marks[-1]
    hour = rows[last_i]["sec"] // 3600
    if hour < 6:                       # 00:00–05:59：正常跨天，严格从这条开始
        return last_i + 1, day, "date"
    return pick_evening_start(rows), day, "date-midday"


# ------------------------------------------------------------------ 解析事件
OUTFIT_RE = re.compile(r"^outfit (.+?) -> (.+?)(?:\s+\((.+)\))?$")
FLAG_RE = re.compile(r"(\w+)=([^\s)]+)")


def _flags(text):
    return dict(FLAG_RE.findall(text or ""))


def parse_events(seg):
    """把日志段里关心的事件挑出来：换衣 outfit / pat / zoo hello / zoo splash。"""
    events = []
    for row in seg:
        msg = row["msg"]
        kind = None
        extra = {}
        if msg == "pat":
            kind = "pat"
        elif msg == "zoo hello":
            kind = "hello"
        elif msg == "zoo splash":
            kind = "splash"
        elif msg.startswith("outfit "):
            m = OUTFIT_RE.match(msg)
            if m:
                kind = "outfit"
                prev = m.group(1).strip()
                extra = {
                    "prev": None if prev == "None" else prev,
                    "new": m.group(2).strip(),
                    "flags": _flags(m.group(3)),
                }
        if kind:
            ev = {"kind": kind, "sec": row["sec"], "hms": row["hms"]}
            ev.update(extra)
            events.append(ev)
    return events


def bursts(events, kind, max_gap=60):
    """把挨在一起的同类事件合成一小段（比如 21:43:15/17/19 三次水花）。"""
    out = []
    for ev in events:
        if ev["kind"] != kind:
            continue
        if out and ev["sec"] - out[-1]["last"] <= max_gap:
            out[-1]["last"] = ev["sec"]
            out[-1]["hms"].append(ev["hms"])
            out[-1]["n"] += 1
        else:
            out.append({"first": ev["sec"], "last": ev["sec"],
                        "hms": [ev["hms"]], "n": 1})
    return out


# ------------------------------------------------------------------ 小工具
def num(value):
    """能变成数字就变，否则 None。"""
    try:
        if value is None or isinstance(value, bool):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def coord(value):
    """坐标显示成原稿那样：整数不带小数点，半个像素保留一位。"""
    v = num(value)
    if v is None:
        return None
    if abs(v - round(v)) < 1e-6:
        return str(int(round(v)))
    return "%.1f" % v


def screen_size():
    """屏幕参考尺寸，用来把坐标说成「屏幕左下」、把小地图的点摆对位置。

    pet.log 的坐标是桌宠窗口中心的屏幕坐标；原稿的小地图是按 1536×960
    （DPI 缩放后的逻辑屏幕，Python 进程 DPI 未感知时 GetSystemMetrics 得到的
    就是它：170→11.1%、476.5→31%）来折算的，这里沿用同一个口径。
    """
    try:
        user32 = ctypes.windll.user32
        w = int(user32.GetSystemMetrics(0))
        h = int(user32.GetSystemMetrics(1))
        if w > 0 and h > 0:
            return float(w), float(h)
    except Exception:
        pass
    return 1536.0, 960.0


def region_text(x, y, sw, sh):
    """把坐标说成「屏幕左下 / 屏幕中下方」这类话。"""
    hx = 0 if x < sw / 3.0 else (1 if x < 2.0 * sw / 3.0 else 2)
    hy = 0 if y < sh * 0.42 else (1 if y < sh * 0.72 else 2)
    names = [["左上", "中上方", "右上"],
             ["左侧", "正中", "右侧"],
             ["左下", "中下方", "右下"]]
    return "屏幕" + names[hy][hx]


def dot_left(x, sw):
    """小地图圆点的横向位置（百分比）。"""
    v = num(x)
    if v is None:
        return None
    pct = v / sw * 100.0
    return min(94.0, max(6.0, pct))


def cn_count(n):
    table = {0: "零", 1: "一", 2: "两", 3: "三", 4: "四",
             5: "五", 6: "六", 7: "七", 8: "八", 9: "九", 10: "十"}
    return table.get(n, str(n))


def short_times(times):
    """21:43:15、21:43:17、21:43:19 -> 21:43:15、17、19"""
    if not times:
        return ""
    first = times[0]
    out = [first]
    for t in times[1:]:
        out.append(t[6:8] if t[:5] == first[:5] else t)
    return "、".join(out)


# ------------------------------------------------------------------ 时间线
def build_timeline(events, pat_total, hello_total, last_hello_hms, today_iso):
    """从事件里挑最多 6 条，按时间排好，做成「今日大事记」。

    挑法（稳定的规则，不是拍脑袋）：
      1. 开张那一下换上的衣服；
      2. 今晚最后一次真正的换衣（比如 21:00 换成睡衣）；
      3. 换衣之后第一次「被摸摸」；
      4. 换衣之后第一声 zoo hello（文案里带上整晚总声数）；
      5. 换衣之后水花最多的那一小段 splash；
      6. 今晚最后一小段「被摸摸」（当成睡前摸摸）。
    没有换衣事件时，3–6 就按整晚来取。最多 6 条。
    """
    entries = []

    def add(sec, hms, title, text):
        entries.append({"sec": sec, "time": hms[:5], "title": title, "text": text})

    outfits = [e for e in events if e["kind"] == "outfit"]
    opening = next((e for e in outfits if e["prev"] is None), None)
    changes = [e for e in outfits if e["prev"] is not None]
    change = changes[-1] if changes else None
    pat_bursts = bursts(events, "pat")
    splash_bursts = bursts(events, "splash")
    hellos = [e for e in events if e["kind"] == "hello"]

    if opening:
        pinned_today = bool(opening.get("flags", {}).get("pinned") == today_iso)
        if pinned_today:
            text = "今天这套是妈妈亲手点的，衣柜一整天都听妈妈的。"
        else:
            text = "开机时衣柜自己挑的「%s」，一整天都乖乖穿着。" % opening["new"]
        add(opening["sec"], opening["hms"], "换上「%s」" % opening["new"], text)

    if change:
        title = "困意准时上门" if change["new"] == "睡衣" else "换装小衣柜悄悄换了衣服"
        add(change["sec"], change["hms"], title,
            "换装小衣柜把「%s」悄悄换成了「%s」。" % (change["prev"], change["new"]))

    act_from = change["sec"] if change else (opening["sec"] if opening else 0)

    def pat_text(burst):
        n = burst["n"]
        times = burst["hms"]
        if n == 1:
            return "%s，被轻轻摸了一下，笑眼应该都出来了。" % times[0]
        if n == 2:
            return "%s 和 %s，一下接着一下，笑眼大概都出来了。" % (times[0], times[1])
        if burst["last"] - burst["first"] <= 60:
            return "%s，连着%s下，笑眼都出来啦。" % (short_times(times), cn_count(n))
        return "从 %s 到 %s，连着 %d 下，笑眼都出来啦。" % (times[0], times[-1], n)

    later_pats = [b for b in pat_bursts if b["first"] >= act_from]
    first_pat = later_pats[0] if later_pats else None
    if first_pat:
        add(first_pat["first"], first_pat["hms"][0],
            "被摸摸%s下" % cn_count(first_pat["n"]), pat_text(first_pat))

    later_hello = [e for e in hellos if e["sec"] >= act_from]
    if later_hello:
        first_hello = later_hello[0]
        add(first_hello["sec"], first_hello["hms"], "溜到串门池报了声 hello",
            "从这一声开始，整晚隔一阵就来打个招呼，到 %s 一共 %d 声。"
            % (last_hello_hms[:5], hello_total))

    later_splash = [b for b in splash_bursts if b["first"] >= act_from]
    if later_splash:
        best = max(later_splash, key=lambda b: (b["n"], -b["first"]))
        follow = sum(1 for e in events
                     if e["kind"] == "pat" and best["last"] < e["sec"] <= best["last"] + 30)
        text = "%s 连续%s次水花" % (short_times(best["hms"]), cn_count(best["n"]))
        if follow:
            text += "，扑腾完又被连着摸了%s下。" % cn_count(follow)
        else:
            text += "，扑腾完自己又玩了一会儿。"
        add(best["first"], best["hms"][0],
            "池子里扑腾%s下" % cn_count(best["n"]), text)

    last_pat = pat_bursts[-1] if pat_bursts else None
    if last_pat and (first_pat is None or last_pat["first"] != first_pat["first"]):
        title = ("睡前的最后%s下摸摸" % cn_count(last_pat["n"])) if first_pat \
            else ("被摸摸%s下" % cn_count(last_pat["n"]))
        add(last_pat["first"], last_pat["hms"][0], title, pat_text(last_pat))

    entries.sort(key=lambda e: e["sec"])
    return entries[:6]


# ------------------------------------------------------------------ 组装页面
def build_report():
    now = datetime.now()
    today_iso = now.strftime("%Y-%m-%d")
    notes = []

    state = read_json(STATE_PATH) or {}
    xiaod = read_json(XIAOD_PATH) or {}
    orca = read_json(ORCA_PATH) or {}
    cfg = read_json(CONFIG_PATH) or {}
    rows = read_log(LOG_PATH)

    if not rows:
        notes.append("没读到 pet.log，今晚的事记只能显示「—」。")
    if not state:
        notes.append("没读到 D:\\OrcaPet\\state.json，虎鲸的饱腹/心情/吃鱼只能显示「—」。")

    if rows:
        start_idx, log_date, seg_mode = pick_segment(rows, today_iso)
        seg = rows[start_idx:]
    else:
        log_date, seg_mode, seg = None, "fallback", []
    report_iso = log_date or today_iso
    try:
        report_day = datetime.strptime(report_iso, "%Y-%m-%d").date()
    except ValueError:
        log_date = None
        report_iso = today_iso
        report_day = now.date()
    events = parse_events(seg)
    seg_start = seg[0]["hms"] if seg else ""
    seg_end = seg[-1]["hms"] if seg else ""

    pat_count = sum(1 for e in events if e["kind"] == "pat")
    hello_events = [e for e in events if e["kind"] == "hello"]
    splash_events = [e for e in events if e["kind"] == "splash"]
    hello_count = len(hello_events)
    splash_count = len(splash_events)
    last_hello_hms = hello_events[-1]["hms"] if hello_events else seg_end

    outfits = [e for e in events if e["kind"] == "outfit"]
    opening = next((e for e in outfits if e["prev"] is None), None)
    changes = [e for e in outfits if e["prev"] is not None]
    change = changes[-1] if changes else None
    sleep_change = None
    for c in reversed(changes):
        if c["new"] == "睡衣":
            sleep_change = c
            break

    current_outfit = outfits[-1]["new"] if outfits else None
    if current_outfit is None and isinstance(cfg.get("outfit"), str):
        current_outfit = cfg["outfit"]

    # --- 页头（日期优先用日志里的日期分隔线）
    weekdays = "一二三四五六日"
    month = report_day.month
    season = "春" if 3 <= month <= 5 else ("夏" if 6 <= month <= 8 else ("秋" if 9 <= month <= 11 else "冬"))
    date_line = "%d 年 %d 月 %d 日 · 星期%s · %s" % (
        report_day.year, report_day.month, report_day.day,
        weekdays[report_day.weekday()], season)

    def pill(flag):
        if flag is True:
            return "开"
        if flag is False:
            return "关"
        return EM

    zoo_switch = pill(state.get("zoo"))
    xiaod_state = "睡着" if xiaod.get("sleep") is True else ("醒着" if xiaod.get("sleep") is False else EM)
    if orca.get("zoo") is True:
        orca_state = "在串门"
    elif orca.get("zoo") is False:
        orca_state = "没在串门"
    else:
        orca_state = EM

    day_off = None
    if opening:
        flag = opening.get("flags", {}).get("day_off")
        if flag == "True":
            day_off = True
        elif flag == "False":
            day_off = False
    sub_head = "休息日的晚上。" if day_off is True else ("平常的晚上。" if day_off is False else "今天晚上。")
    if xiaod.get("sleep") is True:
        sub_x = "一只已经睡着了"
    elif current_outfit == "睡衣":
        sub_x = "一只已经换好睡衣"
    elif current_outfit:
        sub_x = "一只还穿着「%s」" % current_outfit
    else:
        sub_x = "一只窝在屏幕边上"
    if orca.get("zoo") is True:
        sub_o = "一只还在串门池里慢慢巡夜。"
    elif orca.get("zoo") is False:
        sub_o = "一只在屏幕角落里安静待着。"
    else:
        sub_o = "另一只这次没读到。"
    sub_line = sub_head + sub_x + "，" + sub_o

    # --- 小D 卡
    if current_outfit is None:
        outfit_hint = "这次没从日志里读出此刻穿着"
    elif current_outfit == "睡衣":
        outfit_hint = ("%s 到点，衣柜自己换上的晚安款" % sleep_change["hms"][:5]) if sleep_change \
            else "夜里了，衣柜换上的晚安款"
    else:
        outfit_hint = "今天穿着「%s」" % current_outfit

    cfg_outfit = cfg.get("outfit") if isinstance(cfg.get("outfit"), str) else None
    pinned = cfg.get("pinned_date") if isinstance(cfg.get("pinned_date"), str) else ""
    picked_html = html.escape(cfg_outfit) if (cfg_outfit and pinned == report_iso) else EM

    if opening and current_outfit:
        if opening["new"] == current_outfit:
            change_html = "今天没换过衣服"
        else:
            change_html = html.escape(opening["new"]) + " → " + html.escape(current_outfit)
    else:
        change_html = EM

    xiaod_pats_html = ("%d <em>次</em>" % pat_count) if rows else EM
    chips = []
    if opening:
        chips.append("%s 换上%s" % (opening["hms"][:5], opening["new"]))
    if sleep_change:
        chips.append("%s 换成%s" % (sleep_change["hms"][:5], sleep_change["new"]))
    chips_html = "\n".join('        <span class="chip">%s</span>' % html.escape(c)
                           for c in chips)

    # --- 虎鲸卡
    hunger = num(state.get("hunger"))
    mood = num(state.get("mood"))
    fed = num(state.get("fed"))
    orca_pats = num(state.get("pats"))

    hunger_txt = ("%.1f%%" % hunger) if hunger is not None else EM
    hunger_w = ("%.1f%%" % min(max(hunger, 0.0), 100.0)) if hunger is not None else "0%"
    mood_txt = ("%.1f%%" % mood) if mood is not None else EM
    mood_w = ("%.1f%%" % min(max(mood, 0.0), 100.0)) if mood is not None else "0%"

    if fed is not None:
        fed_html = "%s <em>条</em>" % (int(fed) if abs(fed - round(fed)) < 1e-6 else "%.1f" % fed)
        growth = min(0.16, max(0.0, fed) * 0.0016)
        growth_html = "%.1f%% <em class=\"small\">＋%.1f%%</em>" % ((1.0 + growth) * 100.0, growth * 100.0)
    else:
        fed_html = EM
        growth_html = EM

    orca_pats_html = ("%d <em>次</em>" % int(orca_pats)) if orca_pats is not None else EM

    # --- 坐标 / 小地图
    sw, sh = screen_size()

    def pos_html(obj):
        if not obj:
            return EM
        x, y = num(obj.get("x")), num(obj.get("y"))
        xs, ys = coord(x), coord(y)
        if x is None or y is None or xs is None or ys is None:
            return EM
        return '%s <em class="small">(%s, %s)</em>' % (region_text(x, y, sw, sh), xs, ys)

    xiaod_pos_html = pos_html(xiaod)
    orca_pos_html = pos_html(orca)

    d1 = dot_left(xiaod.get("x"), sw)
    d2 = dot_left(orca.get("x"), sw)

    dist = None
    if xiaod and orca:
        try:
            dist = math.hypot(float(orca["x"]) - float(xiaod["x"]),
                              float(orca["y"]) - float(xiaod["y"]))
        except (KeyError, TypeError, ValueError):
            dist = None
    if dist is None:
        map_note = "两只的位置这次没读到，小地图先空着。"
    else:
        both_low = all(num(o.get("y")) is not None and num(o.get("y")) > sh * 0.7
                       for o in (xiaod, orca))
        map_note = ("两只都在屏幕下沿活动，相距约 %d 像素。" if both_low
                    else "两只相距约 %d 像素。") % int(dist + 0.5)
    if num(xiaod.get("y")) is not None and num(xiaod.get("y")) > 1000:
        notes.append("小D 的 y 坐标超过屏幕参考高度 960，这是桌宠坐标和 DPI 缩放的老问题，页面上按原坐标显示。")

    # --- 计时 / 时间线
    timeline_entries = build_timeline(events, pat_count, hello_count, last_hello_hms, report_iso)
    if not timeline_entries:
        timeline_entries = [{"time": EM, "title": "今晚还没有留下记录",
                             "text": "等小D 再活动一会儿，再重新生成一次吧。"}]
    timeline_html = "\n".join(
        '      <li>\n        <time>%s</time>\n        <h3>%s</h3>\n        <p>%s</p>\n      </li>'
        % (html.escape(e["time"]), html.escape(e["title"]), html.escape(e["text"]))
        for e in timeline_entries)

    seg_label = "今晚" if (seg and int(seg_start[:2]) >= 17) else "今天"
    timeline_range = ("%s %s–%s · 小D 桌宠日志里的真实时间戳" % (seg_label, seg_start[:5], seg_end[:5])
                      if seg else "今晚还没有读到小D 的日志")

    stat_pat = str(pat_count) if rows else EM
    stat_hello = str(hello_count) if rows else EM
    stat_splash = str(splash_count) if rows else EM

    log_date_text = "未标注"
    if log_date:
        log_date_text = log_date + (" · 中途补记" if seg_mode == "date-midday" else "")
    data_time = "数据取于 %s %s（日志日期：%s）· 来自两只桌宠写在本机的小记录" % (
        now.strftime("%Y-%m-%d"), now.strftime("%H:%M"), log_date_text)

    values = {
        "DATE": html.escape(date_line),
        "SUB": html.escape(sub_line),
        "ZOO_SWITCH": html.escape(zoo_switch),
        "XIAOD_STATE": html.escape(xiaod_state),
        "ORCA_STATE": html.escape(orca_state),
        "XIAOD_OUTFIT": html.escape(current_outfit) if current_outfit else EM,
        "XIAOD_HINT": html.escape(outfit_hint),
        "XIAOD_PICKED": picked_html,
        "XIAOD_PATS": xiaod_pats_html,
        "XIAOD_CHANGE": change_html,
        "XIAOD_POS": xiaod_pos_html,
        "CHIPS": chips_html,
        "HUNGER": hunger_txt,
        "HUNGER_W": hunger_w,
        "MOOD": mood_txt,
        "MOOD_W": mood_w,
        "FED": fed_html,
        "ORCA_PATS": orca_pats_html,
        "GROWTH": growth_html,
        "ORCA_POS": orca_pos_html,
        "DOT1": ("%.1f%%" % d1) if d1 is not None else "11.1%",
        "DOT2": ("%.1f%%" % d2) if d2 is not None else "31.0%",
        "MAP_NOTE": html.escape(map_note),
        "TIMELINE_RANGE": html.escape(timeline_range),
        "TIMELINE": timeline_html,
        "STAT_PATS": stat_pat,
        "STAT_HELLO": stat_hello,
        "STAT_SPLASH": stat_splash,
        "DATA_TIME": html.escape(data_time),
    }

    summary = {
        "pat_count": pat_count if rows else None,
        "hello_count": hello_count if rows else None,
        "splash_count": splash_count if rows else None,
        "seg": (seg_start, seg_end) if seg else None,
        "seg_mode": seg_mode,
        "log_date": log_date,
        "today_iso": today_iso,
        "timeline_n": len(timeline_entries),
        "current_outfit": current_outfit,
        "opening_outfit": opening["new"] if opening else None,
        "hunger": hunger,
        "mood": mood,
        "fed": fed,
        "orca_pats": orca_pats,
        "growth": (min(0.16, max(0.0, fed) * 0.0016) if fed is not None else None),
        "xiaod_pos": (coord(xiaod.get("x")), coord(xiaod.get("y"))) if xiaod else None,
        "orca_pos": (coord(orca.get("x")), coord(orca.get("y"))) if orca else None,
        "dist": dist,
        "data_time": data_time,
    }
    return values, summary, notes


def render(values):
    out = TEMPLATE
    for key, val in values.items():
        out = out.replace("@@" + key + "@@", val)
    left = re.findall(r"@@[A-Z0-9_]+@@", out)
    if left:
        raise SystemExit("模板里还有没替换的占位符: %s" % ", ".join(sorted(set(left))))
    return out


# ------------------------------------------------------------------ 入口
def main(argv=None):
    parser = argparse.ArgumentParser(
        description="用本机实时数据重新生成「赛博动物园 · 今日日报」")
    parser.add_argument("--out", default=str(OUT_DEFAULT),
                        help="输出 HTML 路径（默认 游戏专区/zoo-daily.html）")
    args = parser.parse_args(argv)

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = Path.cwd() / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    values, info, notes = build_report()
    page = render(values)

    old_text = None
    try:
        with open(out_path, "r", encoding="utf-8") as f:
            old_text = f.read()
    except Exception:
        old_text = None

    if old_text == page:
        changed = False
    else:
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(page)
        changed = True

    def plain(v):
        if v is None:
            return EM
        v = float(v)
        return str(int(v)) if abs(v - round(v)) < 1e-6 else "%.1f" % v

    def percent(v):
        return EM if v is None else "%.1f%%" % v

    print("生成完成 -> %s（%s）" % (out_path, "内容有更新" if changed else "数据没变，保持原样"))
    print("  小D：今晚被摸 %s 次；此刻穿着 %s；开张换的是 %s" % (
        plain(info["pat_count"]),
        info["current_outfit"] or EM,
        info["opening_outfit"] or EM))
    print("  虎鲸：饱腹 %s / 心情 %s / 吃鱼 %s 条 / 体型 %s / 被摸 %s 次" % (
        percent(info["hunger"]),
        percent(info["mood"]),
        plain(info["fed"]),
        percent((1 + info["growth"]) * 100 if info["growth"] is not None else None),
        plain(info["orca_pats"])))
    print("  串门：hello %s 声 / 扑腾 %s 次；日志段 %s；大事记 %d 条" % (
        plain(info["hello_count"]),
        plain(info["splash_count"]),
        ("%s–%s" % info["seg"]) if info["seg"] else EM,
        info["timeline_n"]))
    if info["seg_mode"] == "date":
        print("  统计依据：日志日期分隔线（%s，00:00–05:59 正常跨天写入，严格从这条往后统计）"
              % info["log_date"])
    elif info["seg_mode"] == "date-midday":
        print("  统计依据：日志日期分隔线（%s · 中途补记，段起点退回当天晚间启动启发式）"
              % info["log_date"])
    else:
        print("  注意：用的是旧的启动段兜底（pet.log 里没有 %s 的日期分隔线）" % info["today_iso"])
    if info["seg"]:
        print("  统计段：%s–%s；pat=%s / hello=%s / splash=%s" % (
            info["seg"][0], info["seg"][1],
            plain(info["pat_count"]), plain(info["hello_count"]), plain(info["splash_count"])))
    print("  %s" % info["data_time"])
    for note in notes:
        print("  注意：%s" % note)
    return 0


TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>赛博动物园 · 今日日报</title>
<style>
  :root{
    --ink:#4c4653;
    --ink-soft:#7b7385;
    --ink-faint:#a79fae;
    --pink:#e9aebd;
    --pink-deep:#c68196;
    --pink-line:#f5dde6;
    --pink-soft:#fdf1f5;
    --blue:#a8c1d9;
    --blue-deep:#7d98b4;
    --blue-line:#dde9f3;
    --blue-soft:#f0f6fc;
    --card-shadow:0 26px 50px -34px rgba(118,96,112,.42);
  }
  *{box-sizing:border-box}
  html{-webkit-text-size-adjust:100%}
  body{
    margin:0;
    overflow-x:hidden;
    color:var(--ink);
    font-family:"Microsoft YaHei UI","Microsoft YaHei","PingFang SC","Hiragino Sans GB","Noto Sans SC",sans-serif;
    line-height:1.8;
    background:
      radial-gradient(1100px 620px at 6% -6%, #fde8ef 0%, rgba(253,232,239,0) 62%),
      radial-gradient(1000px 620px at 102% 2%, #e7f0fa 0%, rgba(231,240,250,0) 58%),
      linear-gradient(180deg,#fdfaf8 0%, #fbf8f7 42%, #f5f9fc 100%);
    min-height:100vh;
  }
  body::before,
  body::after{
    content:"";
    position:fixed;
    z-index:0;
    width:420px;
    height:420px;
    border-radius:50%;
    pointer-events:none;
    opacity:.65;
  }
  body::before{left:-150px;top:34%;background:radial-gradient(circle,#fbe1e9 0%,rgba(251,225,233,0) 70%)}
  body::after{right:-170px;top:8%;background:radial-gradient(circle,#dcebf7 0%,rgba(220,235,247,0) 70%)}

  .page{
    position:relative;
    z-index:1;
    max-width:980px;
    margin:0 auto;
    padding:clamp(30px,6vw,72px) clamp(18px,4.5vw,40px) 60px;
  }

  /* ---------- 页头 ---------- */
  .hero{text-align:center;margin-bottom:clamp(28px,4.5vw,44px)}
  .kicker{
    margin:0 0 16px;
    font-size:11px;
    font-weight:700;
    letter-spacing:.36em;
    text-transform:uppercase;
    color:var(--pink-deep);
    opacity:.72;
  }
  h1{
    margin:0 0 16px;
    font-size:clamp(27px,5.6vw,44px);
    font-weight:800;
    letter-spacing:.08em;
    color:#564b5b;
    text-shadow:0 2px 0 rgba(255,255,255,.8);
  }
  .date{
    display:inline-block;
    padding:6px 18px;
    font-size:13.5px;
    letter-spacing:.14em;
    color:var(--ink-soft);
    background:rgba(255,255,255,.78);
    border:1px solid var(--pink-line);
    border-radius:999px;
    box-shadow:0 12px 22px -18px rgba(150,110,128,.7);
  }
  .sub{
    max-width:34em;
    margin:18px auto 0;
    font-size:14.5px;
    color:var(--ink-soft);
  }
  .pills{display:flex;flex-wrap:wrap;justify-content:center;gap:8px;margin-top:20px}
  .pill{
    padding:4px 13px;
    font-size:12px;
    letter-spacing:.07em;
    color:#7d6e78;
    background:rgba(255,255,255,.72);
    border:1px solid #f1e4ea;
    border-radius:999px;
  }
  .pill b{font-weight:700;color:var(--pink-deep)}

  /* ---------- 卡片 ---------- */
  .grid{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));
    gap:clamp(16px,2.6vw,24px);
    align-items:start;
  }
  .card{
    position:relative;
    overflow:hidden;
    padding:clamp(20px,3.2vw,30px);
    border-radius:28px;
    border:1px solid transparent;
    box-shadow:var(--card-shadow);
    animation:rise .7s ease both;
  }
  .card::before{
    content:"";
    position:absolute;
    right:-60px;
    bottom:-70px;
    width:200px;
    height:200px;
    border-radius:50%;
    opacity:.55;
    pointer-events:none;
  }
  .card-xiaod{
    background:linear-gradient(165deg,#fffbfc 0%,#fdf1f5 58%,#fbe9f0 100%);
    border-color:#f6dde7;
  }
  .card-xiaod::before{background:radial-gradient(circle,#f8d7e2 0%,rgba(248,215,226,0) 70%)}
  .card-orca{
    background:linear-gradient(165deg,#ffffff 0%,#f0f6fb 58%,#e7f1fa 100%);
    border-color:#dde9f3;
    animation-delay:.1s;
  }
  .card-orca::before{background:radial-gradient(circle,#d5e6f4 0%,rgba(213,230,244,0) 70%)}

  .card-head{display:flex;align-items:center;gap:14px;margin-bottom:18px}
  .card-head h2{margin:0;font-size:19px;letter-spacing:.08em;color:#564b5b}
  .tagline{margin:2px 0 0;font-size:12.5px;letter-spacing:.04em;color:var(--ink-faint)}

  /* 纯 CSS 小脸 */
  .avatar{
    position:relative;
    flex:none;
    width:58px;
    height:58px;
    border-radius:50%;
    box-shadow:inset 0 -7px 14px rgba(120,95,110,.06), 0 12px 20px -14px rgba(118,96,112,.75);
  }
  .avatar.xiaod{
    background:radial-gradient(circle at 50% 36%,#fff8f4 0%,#ffe5dd 68%,#f9d2cb 100%);
    border:2px solid #fff;
  }
  .avatar.xiaod .eye{
    position:absolute;
    top:23px;
    width:6px;
    height:7px;
    border-radius:50%;
    background:#6d5a61;
  }
  .avatar.xiaod .eye.l{left:17px}
  .avatar.xiaod .eye.r{right:17px}
  .avatar.xiaod .blush{
    position:absolute;
    top:32px;
    width:9px;
    height:5px;
    border-radius:50%;
    background:#f3b8c4;
    opacity:.75;
  }
  .avatar.xiaod .blush.l{left:10px}
  .avatar.xiaod .blush.r{right:10px}
  .avatar.xiaod .mouth{
    position:absolute;
    top:32px;
    left:50%;
    width:10px;
    height:5px;
    margin-left:-5px;
    border-bottom:2px solid #c08e9c;
    border-radius:0 0 12px 12px;
  }
  .avatar.orca{
    background:linear-gradient(158deg,#9db1cd 0%,#7f97b8 52%,#6d86a9 100%);
    border:2px solid #fff;
  }
  .avatar.orca .belly{
    position:absolute;
    left:50%;
    bottom:7px;
    width:32px;
    height:19px;
    margin-left:-16px;
    border-radius:50%;
    background:#f2f7fc;
    opacity:.95;
  }
  .avatar.orca .eye{
    position:absolute;
    top:19px;
    width:9px;
    height:9px;
    border-radius:50%;
    background:#fff;
  }
  .avatar.orca .eye.l{left:15px}
  .avatar.orca .eye.r{right:15px}
  .avatar.orca .eye::after{
    content:"";
    position:absolute;
    left:3px;
    top:3px;
    width:4px;
    height:4px;
    border-radius:50%;
    background:#4d637f;
  }

  /* 小D：此刻穿着 */
  .outfit-now{
    display:flex;
    flex-direction:column;
    gap:1px;
    margin-bottom:16px;
    padding:14px 18px;
    background:rgba(255,255,255,.72);
    border:1px solid #f8e6ed;
    border-radius:20px;
  }
  .outfit-now .label{font-size:11px;letter-spacing:.2em;color:var(--pink-deep);opacity:.85}
  .outfit-now .big{font-size:24px;font-weight:800;letter-spacing:.06em;color:#5b4b56}
  .outfit-now .hint{font-size:12px;color:var(--ink-faint)}

  .facts{list-style:none;margin:0 0 15px;padding:0;display:grid;gap:9px}
  .facts li{
    display:flex;
    justify-content:space-between;
    align-items:baseline;
    gap:14px;
    padding-bottom:9px;
    font-size:13.5px;
    color:var(--ink-soft);
    border-bottom:1px dashed rgba(186,156,170,.25);
  }
  .facts li:last-child{padding-bottom:0;border-bottom:0}
  .facts strong{font-size:15.5px;font-weight:700;color:#5a4d58;text-align:right}
  .facts em{font-style:normal;margin-left:2px;font-size:12px;color:var(--ink-faint)}
  .facts .small{font-size:12px;color:var(--ink-faint);font-weight:400}

  .chips{display:flex;flex-wrap:wrap;gap:8px}
  .chip{
    padding:5px 12px;
    font-size:12px;
    letter-spacing:.03em;
    border-radius:999px;
    background:rgba(255,255,255,.85);
    border:1px solid #f3dfe7;
    color:#a17f8b;
  }
  .card-orca .chip{background:rgba(255,255,255,.85);border-color:#e1ecf5;color:#7e94aa}

  /* 虎鲸：进度条 */
  .bars{display:grid;gap:15px;margin:6px 0 20px}
  .bar-label{
    display:flex;
    justify-content:space-between;
    align-items:baseline;
    margin-bottom:6px;
    font-size:12.5px;
    color:var(--ink-soft);
  }
  .bar-label b{font-size:13.5px;color:#5a4d58}
  .bar{
    height:11px;
    border-radius:999px;
    background:rgba(226,233,241,.75);
    overflow:hidden;
  }
  .bar i{
    display:block;
    height:100%;
    border-radius:999px;
    background:linear-gradient(90deg,#d2e1ee 0%,#aac5dd 100%);
    box-shadow:inset 0 0 8px rgba(255,255,255,.65);
  }
  .bar.mood i{background:linear-gradient(90deg,#f8dae2 0%,#eab0bf 100%)}

  /* 虎鲸：站位小地图 */
  .map-wrap{margin-top:2px}
  .map{
    position:relative;
    height:88px;
    border-radius:20px;
    background:linear-gradient(180deg,rgba(255,255,255,.9) 0%,rgba(238,246,252,.92) 100%);
    border:1px solid #e2edf6;
    overflow:hidden;
  }
  .map::after{
    content:"";
    position:absolute;
    left:14px;
    right:14px;
    bottom:14px;
    height:7px;
    border-radius:99px;
    background:linear-gradient(90deg,#e8eff6,#dbe7f1);
  }
  .dot{
    position:absolute;
    bottom:26px;
    transform:translateX(-50%);
    display:flex;
    flex-direction:column;
    align-items:center;
    gap:4px;
  }
  .dot i{
    order:1;
    width:13px;
    height:13px;
    border-radius:50%;
    border:2.5px solid #fff;
    box-shadow:0 5px 12px -4px rgba(96,116,140,.55);
  }
  .dot .lbl{order:2;font-size:10.5px;letter-spacing:.08em;color:#8b96a5;white-space:nowrap}
  .dot.d1{left:11.1%}
  .dot.d1 i{background:#eeb9c6}
  .dot.d2{left:31%}
  .dot.d2 i{background:#94b3d3}
  .map-note{margin:9px 2px 0;font-size:11.5px;letter-spacing:.03em;color:var(--ink-faint)}

  /* ---------- 大事记 ---------- */
  .timeline-card{
    margin-top:clamp(18px,3vw,26px);
    padding:clamp(22px,3.6vw,34px);
    background:rgba(255,253,252,.92);
    border:1px solid #f2e7eb;
    border-radius:30px;
    box-shadow:var(--card-shadow);
    animation:rise .8s ease both;
    animation-delay:.18s;
  }
  .section-head{
    display:flex;
    flex-wrap:wrap;
    align-items:baseline;
    justify-content:space-between;
    gap:8px;
    margin-bottom:22px;
  }
  .section-head h2{margin:0;font-size:19px;letter-spacing:.1em;color:#564b5b}
  .section-head p{margin:0;font-size:12px;letter-spacing:.05em;color:var(--ink-faint)}

  .timeline{
    list-style:none;
    margin:0;
    padding:2px 0 2px 24px;
    border-left:1.5px solid #f1e0e7;
    display:grid;
    gap:21px;
  }
  .timeline li{position:relative}
  .timeline li::before{
    content:"";
    position:absolute;
    left:-31px;
    top:7px;
    width:11px;
    height:11px;
    border-radius:50%;
    background:#f0c0ce;
    border:2.5px solid #fff;
    box-shadow:0 0 0 3px #fdf1f5;
  }
  .timeline li:nth-child(even)::before{background:#b8cee3;box-shadow:0 0 0 3px #f1f7fb}
  .timeline time{
    display:inline-block;
    margin-bottom:3px;
    font-size:12px;
    font-weight:700;
    letter-spacing:.14em;
    color:#b98fa0;
  }
  .timeline h3{margin:0 0 3px;font-size:15px;letter-spacing:.05em;color:#564b57}
  .timeline p{margin:0;font-size:13px;color:var(--ink-soft)}

  .mini-stats{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(84px,1fr));
    gap:10px;
    margin-top:26px;
  }
  .stat{
    padding:13px 14px;
    text-align:center;
    background:linear-gradient(170deg,#fff 0%,#fbf6f8 100%);
    border:1px solid #f4e7ed;
    border-radius:18px;
  }
  .stat b{display:block;font-size:22px;font-weight:800;letter-spacing:.02em;color:#c18e9f}
  .stat span{font-size:11.5px;letter-spacing:.04em;color:var(--ink-faint)}

  /* ---------- 结尾 ---------- */
  footer{margin-top:clamp(28px,4.5vw,44px);text-align:center}
  .quote{
    max-width:30em;
    margin:0 auto;
    font-family:Georgia,"Songti SC","STSong","SimSun",serif;
    font-size:15px;
    line-height:2.1;
    color:#7d6c78;
  }
  .quote::before,
  .quote::after{
    content:"";
    display:inline-block;
    width:22px;
    height:1px;
    margin:0 12px 5px;
    background:linear-gradient(90deg,rgba(233,174,189,0),#e9aebd);
    vertical-align:middle;
  }
  .quote::after{background:linear-gradient(90deg,#a8c1d9,rgba(168,193,217,0))}
  .fine{margin-top:16px;font-size:11px;letter-spacing:.1em;color:#b8afb8}

  @keyframes rise{
    from{opacity:0;transform:translateY(14px)}
    to{opacity:1;transform:none}
  }
  @media (prefers-reduced-motion: reduce){
    .card,.timeline-card{animation:none}
  }
  @media (max-width:560px){
    h1{letter-spacing:.05em}
    .outfit-now .big{font-size:22px}
    .map{height:82px}
    .facts strong{font-size:14.5px}
  }
  @media (max-width:400px){
    .mini-stats{grid-template-columns:repeat(3,1fr);gap:8px}
    .stat{padding:11px 6px}
    .stat b{font-size:20px}
    .stat span{font-size:10.5px;letter-spacing:0}
  }
</style>
</head>
<body>
<div class="page">

  <header class="hero">
    <p class="kicker">Orca × Xiaod · Daily</p>
    <h1>赛博动物园 · 今日日报</h1>
    <p class="date">@@DATE@@</p>
    <p class="sub">@@SUB@@</p>
    <div class="pills">
      <span class="pill">串门开关 · <b>@@ZOO_SWITCH@@</b></span>
      <span class="pill">小D · <b>@@XIAOD_STATE@@</b></span>
      <span class="pill">虎鲸 · <b>@@ORCA_STATE@@</b></span>
    </div>
  </header>

  <main class="grid">

    <!-- 小D -->
    <section class="card card-xiaod">
      <div class="card-head">
        <div class="avatar xiaod" aria-hidden="true">
          <span class="eye l"></span><span class="eye r"></span>
          <span class="blush l"></span><span class="blush r"></span>
          <span class="mouth"></span>
        </div>
        <div>
          <h2>小D</h2>
          <p class="tagline">两套衣服，一套给白天，一套给梦</p>
        </div>
      </div>

      <div class="outfit-now">
        <span class="label">此刻穿着</span>
        <span class="big">@@XIAOD_OUTFIT@@</span>
        <span class="hint">@@XIAOD_HINT@@</span>
      </div>

      <ul class="facts">
        <li><span>今天亲手挑的</span><strong>@@XIAOD_PICKED@@</strong></li>
        <li><span>今晚被摸</span><strong>@@XIAOD_PATS@@</strong></li>
        <li><span>今天的换衣</span><strong>@@XIAOD_CHANGE@@</strong></li>
        <li><span>此刻位置</span><strong>@@XIAOD_POS@@</strong></li>
      </ul>

      <div class="chips">
@@CHIPS@@
      </div>
    </section>

    <!-- 虎鲸 -->
    <section class="card card-orca">
      <div class="card-head">
        <div class="avatar orca" aria-hidden="true">
          <span class="belly"></span>
          <span class="eye l"></span><span class="eye r"></span>
        </div>
        <div>
          <h2>虎鲸</h2>
          <p class="tagline">把肚皮养得饱饱的一小只</p>
        </div>
      </div>

      <div class="bars">
        <div>
          <div class="bar-label"><span>饱腹</span><b>@@HUNGER@@</b></div>
          <div class="bar"><i style="width:@@HUNGER_W@@"></i></div>
        </div>
        <div>
          <div class="bar-label"><span>心情</span><b>@@MOOD@@</b></div>
          <div class="bar mood"><i style="width:@@MOOD_W@@"></i></div>
        </div>
      </div>

      <ul class="facts">
        <li><span>累计吃鱼</span><strong>@@FED@@</strong></li>
        <li><span>被摸次数</span><strong>@@ORCA_PATS@@</strong></li>
        <li><span>体型</span><strong>@@GROWTH@@</strong></li>
        <li><span>当前位置</span><strong>@@ORCA_POS@@</strong></li>
      </ul>

      <div class="map-wrap">
        <div class="map" aria-hidden="true">
          <span class="dot d1" style="left:@@DOT1@@"><i></i><span class="lbl">小D</span></span>
          <span class="dot d2" style="left:@@DOT2@@"><i></i><span class="lbl">虎鲸</span></span>
        </div>
        <p class="map-note">@@MAP_NOTE@@</p>
      </div>
    </section>

  </main>

  <!-- 大事记 -->
  <section class="timeline-card">
    <div class="section-head">
      <h2>今日大事记</h2>
      <p>@@TIMELINE_RANGE@@</p>
    </div>

    <ol class="timeline">
@@TIMELINE@@
    </ol>

    <div class="mini-stats">
      <div class="stat"><b>@@STAT_PATS@@</b><span>被摸摸</span></div>
      <div class="stat"><b>@@STAT_HELLO@@</b><span>串门打招呼</span></div>
      <div class="stat"><b>@@STAT_SPLASH@@</b><span>池里扑腾</span></div>
    </div>
  </section>

  <footer>
    <p class="quote">夜深了，一只把尾巴卷成枕头，一只还在水里慢慢转圈。今天也被好好地爱着，明天见呀。</p>
    <p class="fine">@@DATA_TIME@@</p>
  </footer>

</div>
</body>
</html>
'''

if __name__ == "__main__":
    sys.exit(main())
