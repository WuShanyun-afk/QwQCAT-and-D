# -*- coding: utf-8 -*-
r"""按 PID 找到 OrcaPet 窗口，截一块真实屏幕（透明桌宠只能这样验货）。

用法：
  python 工具\截虎鲸.py --pid 12345 --out 备份\orca-now.png
"""
import argparse
import ctypes
import time
from ctypes import wintypes

from PIL import ImageGrab

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

u = ctypes.windll.user32
ENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)


def windows_of(pid):
    hits = []

    def cb(hwnd, _):
        wp = wintypes.DWORD()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(wp))
        if wp.value != pid or not u.IsWindowVisible(hwnd):
            return True
        r = wintypes.RECT()
        u.GetWindowRect(hwnd, ctypes.byref(r))
        w, h = r.right - r.left, r.bottom - r.top
        if w > 40 and h > 40:
            hits.append((hwnd, r.left, r.top, w, h))
        return True

    u.EnumWindows(ENUMPROC(cb), 0)
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pid', type=int, required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--pad', type=int, default=24)
    ap.add_argument('--shots', type=int, default=1)
    ap.add_argument('--gap', type=float, default=1.2)
    a = ap.parse_args()

    wins = windows_of(a.pid)
    if not wins:
        print('no usable window for pid %d' % a.pid)
        return 1
    hwnd, x, y, w, h = max(wins, key=lambda t: t[3] * t[4])
    print('window %s at %d,%d %dx%d' % (hwnd, x, y, w, h))

    for i in range(a.shots):
        box = (x - a.pad, y - a.pad, x + w + a.pad, y + h + a.pad)
        img = ImageGrab.grab(bbox=box, all_screens=True)
        out = a.out if a.shots == 1 else a.out.replace('.png', '-%d.png' % i)
        img.save(out)
        print('saved', out, img.size)
        if i < a.shots - 1:
            time.sleep(a.gap)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
