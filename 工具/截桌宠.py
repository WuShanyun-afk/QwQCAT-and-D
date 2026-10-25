# -*- coding: utf-8 -*-
r"""截桌宠「真实像素」并用数字体检有没有白边。

为什么要有这个工具：
  桌宠是 340×430 的物理像素窗口，画布也是 340×430，图 1:1 贴上去、不缩放。
  但**不带 DPI 感知**的截图/测量工具在 125% 缩放的屏幕上会把窗口量成 272×344，
  看起来就像「桌宠被缩小成 0.8 倍」—— 那是工具的假象，不是桌宠的问题。
  这个脚本先 SetProcessDpiAwareness(2)，再用 PrintWindow 抓窗口内容，
  顺便量一圈「贴着透明背景的边缘像素」有多亮：有白边就会量出来。

用法（系统 Python 自带 Pillow 就够，不用 numpy）：
  python 工具\截桌宠.py                  # 体检 + 存图到 %TEMP%
  python 工具\截桌宠.py --out D:\x.png   # 指定输出
  python 工具\截桌宠.py --zoom 6         # 额外存边缘 6 倍放大图
"""
import argparse
import ctypes
import os
import tempfile
import time
from ctypes import wintypes

from PIL import Image

APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "我的插件", "dsh-desktop-pet")
LOCK = os.path.join(APP, "pet.lock")

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

u = ctypes.windll.user32
gdi = ctypes.windll.gdi32


def pet_pid():
    try:
        txt = open(LOCK, "r", encoding="utf-8").read().strip()
        return int(txt) if txt.isdigit() else None
    except Exception:
        return None


def find_window(pid):
    """找桌宠的 Tk 顶层窗口（overrideredirect 窗口没有标题，靠进程 + 类名认）"""
    ENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    hits = []

    def cb(hwnd, _):
        cls = ctypes.create_unicode_buffer(256)
        u.GetClassNameW(hwnd, cls, 256)
        wp = wintypes.DWORD()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(wp))
        if cls.value == "TkTopLevel" and (pid is None or wp.value == pid):
            r = wintypes.RECT()
            u.GetWindowRect(hwnd, ctypes.byref(r))
            hits.append((hwnd, wp.value, r.left, r.top, r.right - r.left, r.bottom - r.top))
        return True

    u.EnumWindows(ENUMPROC(cb), 0)
    return hits[0] if hits else None


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


def grab_window(hwnd, w, h):
    """PrintWindow(PW_RENDERFULLCONTENT) 抓窗口自己的内容，透明处会是黑色"""
    hdc_win = u.GetWindowDC(hwnd)
    hdc_mem = gdi.CreateCompatibleDC(hdc_win)
    bmp = gdi.CreateCompatibleBitmap(hdc_win, w, h)
    gdi.SelectObject(hdc_mem, bmp)
    ok = u.PrintWindow(hwnd, hdc_mem, 2)
    bi = BITMAPINFO()
    bi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bi.bmiHeader.biWidth = w
    bi.bmiHeader.biHeight = -h
    bi.bmiHeader.biPlanes = 1
    bi.bmiHeader.biBitCount = 32
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi.GetDIBits(hdc_mem, bmp, 0, h, buf, ctypes.byref(bi), 0)
    gdi.DeleteObject(bmp)
    gdi.DeleteDC(hdc_mem)
    u.ReleaseDC(hwnd, hdc_win)
    return ok, Image.frombuffer("RGB", (w, h), buf.raw, "raw", "BGRX", 0, 1)


def edge_report(im):
    """非透明(=非纯黑) 且 四邻域有透明的像素 = 轮廓边缘，量它们「白不白」

    白边 = 又亮又没颜色（接近灰/白）。所以只看「亮度 > 200 且 RGB 三通道差 ≤ 25」的
    像素 —— 这样金色的天线灯、黄色的星星挂饰（很亮但很黄）不会被误判成白边。

    另外桌宠正在说话时，白色气泡也会被算成「边缘」，所以额外统计这些偏白像素
    是不是都挤在上半部分（气泡区），用来自动区分。
    """
    px = im.load()
    w, h = im.size
    total = bright = bright_top = 0
    worst = 0.0
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            if lum <= 8:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    rr, gg, bb = px[nx, ny]
                    if 0.299 * rr + 0.587 * gg + 0.114 * bb <= 8:
                        total += 1
                        if lum > 200 and (max(r, g, b) - min(r, g, b)) <= 25:
                            bright += 1
                            if y < 110:       # 气泡基本只出现在窗口最上面这一带
                                bright_top += 1
                            worst = max(worst, lum)
                        break
    return total, bright, bright_top, worst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--zoom", type=int, default=0)
    args = ap.parse_args()

    pid = pet_pid()
    hit = find_window(pid)
    if not hit:
        raise SystemExit("没找到桌宠窗口（桌宠没开？或者 pet.lock 里的 PID 不对）")
    hwnd, wpid, x, y, w, h = hit
    print("窗口: hwnd=%s pid=%s 位置=(%d,%d) 大小=%dx%d (物理像素)" % (hwnd, wpid, x, y, w, h))
    try:
        dpi = u.GetDpiForWindow(hwnd)
        print("窗口 DPI: %d  (96=100%%, 120=125%%, 144=150%%) → 缩放 %.2f×" % (dpi, dpi / 96.0))
    except Exception:
        pass

    ok, im = grab_window(hwnd, w, h)
    total, bright, bright_top, worst = edge_report(im)
    print("PrintWindow: %s" % ("ok" if ok else "失败"))
    print("轮廓边缘像素: %d 个；最亮的偏白像素 %.0f/255；偏白像素: %d 个（其中 %d 个在上方气泡区）"
          % (total, worst, bright, bright_top))
    if bright < 20:
        verdict = "没有白边（边缘是深色描边；个别偏白像素是珍珠/高光之类的装饰，只有几十个以上才可能是白边）"
    elif bright_top >= bright * 0.8:
        verdict = "检测到的是正在说话的白色气泡，不是白边（等气泡消失再跑一次就干净了）"
    else:
        verdict = "有一圈白边，要查素材"
    print("白边结论: %s" % verdict)

    out = args.out or os.path.join(tempfile.gettempdir(),
                                   "桌宠-1比1-%s.png" % time.strftime("%Y%m%d-%H%M%S"))
    im.save(out)
    print("截图:", out, im.size)

    if args.zoom > 0:
        # 只放大有内容的左上角一块，方便肉眼看边缘
        bbox = im.getbbox() or (0, 0, w, h)
        box = (max(0, bbox[0] - 4), max(0, bbox[1] - 4),
               min(w, bbox[0] + 90), min(h, bbox[1] + 90))
        crop = im.crop(box)
        z = crop.resize((crop.width * args.zoom, crop.height * args.zoom), Image.NEAREST)
        p = os.path.splitext(out)[0] + "-zoom.png"
        z.save(p)
        print("放大图:", p, z.size)


if __name__ == "__main__":
    main()
