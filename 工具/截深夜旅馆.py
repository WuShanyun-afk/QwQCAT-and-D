# -*- coding: utf-8 -*-
r"""给《深夜旅馆》网页截验收图（Edge 无头）

用法：
  python 工具\截深夜旅馆.py --scene arrive
  python 工具\截深夜旅馆.py --all                     # 所有场景，1440x900
  python 工具\截深夜旅馆.py --all --size 390x844      # 手机竖屏
  python 工具\截深夜旅馆.py --ending s9_end_warm      # 结局卡

参数说明：
  --instant=1 会关掉打字机，截图里文字是完整的；正式玩的时候不传这个参数。
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(BASE, "小D", "网页", "深夜旅馆.html")
STORY = os.path.join(BASE, "备份", "旅馆-剧情.json")
EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
USERDIR = os.path.join(tempfile.gettempdir(), "edge-inn-shot")


def find_edge():
    for p in EDGE_CANDIDATES:
        if os.path.exists(p):
            return p
    sys.exit("找不到 msedge.exe，请确认 Edge 装在哪")


def shot(edge, scene, size, out, auto=0):
    w, h = size
    url = "file:///" + HTML.replace("\\", "/").replace(" ", "%20") + "?instant=1"
    if auto:
        url += "&auto=%d" % auto
    if scene:
        url += "&scene=" + scene
    args = [
        edge, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--force-prefers-reduced-motion",
        "--window-size=%d,%d" % (w, h),
        "--screenshot=" + out,
        "--virtual-time-budget=8000",
        "--user-data-dir=" + USERDIR,
        url,
    ]
    proc = subprocess.run(args, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=90)
    ok = os.path.exists(out) and os.path.getsize(out) > 4000
    return ok, proc.returncode, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default=None, help="场景 id（默认起点）")
    ap.add_argument("--all", action="store_true", help="所有场景都截一遍")
    ap.add_argument("--ending", default=None, help="只截某个结局")
    ap.add_argument("--size", default="1440x900", help="宽x高，例如 390x844")
    ap.add_argument("--out", default=None, help="输出文件（单张时用）")
    ap.add_argument("--auto", type=int, default=0, help="自测：自动点 N 次第一个选项")
    ap.add_argument("--dir", default=os.path.join(tempfile.gettempdir(), "inn-shots"))
    args = ap.parse_args()

    edge = find_edge()
    w, h = (int(x) for x in args.size.lower().split("x"))
    os.makedirs(args.dir, exist_ok=True)

    if args.all:
        with open(STORY, "r", encoding="utf-8") as f:
            scenes = list(json.load(f)["scenes"].keys())
    elif args.ending:
        scenes = [args.ending]
    else:
        scenes = [args.scene or ""]

    bad = []
    for sid in scenes:
        name = sid or "start"
        out = args.out if (args.out and len(scenes) == 1) else os.path.join(
            args.dir, "%s_%dx%d.png" % (name, w, h))
        ok, code, path = shot(edge, sid, (w, h), out, auto=args.auto)
        print("%-22s %s  %s" % (name, "ok " if ok else "FAIL(%d)" % code, path))
        if not ok:
            bad.append(name)
    print("\n共 %d 张，失败 %d 张" % (len(scenes), len(bad)))
    if bad:
        print("失败：", ", ".join(bad))


if __name__ == "__main__":
    main()
