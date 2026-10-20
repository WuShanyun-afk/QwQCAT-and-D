r"""从妈妈画的透明底成品帧 + 分层件，生成桌宠的「耳朵抖 / 尾巴摇」动画帧。

输入：
  ..\..\小D\拆分图\成品-透明底\成品-{睁眼,单眼眨,笑眼闭眼}-透明.png   （完整图，带装饰）
  ..\..\小D\拆分图\分层\04-猫耳-右.png / 15-尾巴.png                  （只用来取「耳朵 / 尾巴」的形状遮罩）
输出：
  assets\{state}_{tail}_{ear}.png  —— 3 状态 × 4 尾巴角 × 2 耳朵角 = 24 张
  assets\squeak.wav                —— 点击时的「吱吱」声

做法（只动耳朵和尾巴，全身不晃）：
  1) 用图层遮罩（外扩几像素，防边缘残留）把成品里的尾巴、右耳抠下来，做成可旋转的精灵；
  2) 挖掉的位置：尾巴底下本来就是天空 → 保持透明；耳朵底下是头发 → 用周围头发的中位色补上；
  3) 每帧 = 尾巴精灵（底层，根部被身体挡住）→ 身体 → 耳朵精灵（表层）；
  4) 统一裁切、缩放到 340 高、底部 4.5% 柔化渐隐。

用法：python 生成素材.py     （需要 numpy + Pillow 的 python，例如 DSH 自带运行时）
"""
import os
import wave

import numpy as np
from PIL import Image, ImageFilter

APP = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(APP, "..", "..", "小D", "拆分图", "成品-透明底")
LAYER = os.path.join(APP, "..", "..", "小D", "拆分图", "分层")
OUT = os.path.join(APP, "assets")

STATES = {"idle": "成品-睁眼-透明.png",
          "wink": "成品-单眼眨-透明.png",
          "blink": "成品-笑眼闭眼-透明.png"}
TAIL_ANGLES = (-6.5, -2.2, 2.2, 6.5)     # 尾巴摇（绕尾根）
EAR_ANGLES = (0.0, -14.0)                # 耳朵抖（绕耳根，负 = 往外竖）

TAIL_PIVOT = (700, 1150)   # 尾根
EAR_PIVOT = (930, 250)     # 右耳根

CROP = (10, 10, 1140, 1281)
BODY_H = 340
FADE = 0.045


def layer_alpha(name):
    return np.array(Image.open(os.path.join(LAYER, name + ".png")).convert("RGBA"))[:, :, 3]


def grow(mask, px):
    m = Image.fromarray((mask * 255).astype(np.uint8), "L")
    m = m.filter(ImageFilter.MaxFilter(px * 2 + 1))
    return np.array(m) > 128


def ring_color(arr, mask, grow_px=8):
    """取遮罩外面一圈不透明像素的中位色（用来补耳朵底下的头发）"""
    outer = grow(mask, grow_px)
    ring = outer & ~mask & (arr[:, :, 3] > 200)
    if ring.sum() == 0:
        return (30, 34, 60, 255)
    px = arr[ring][:, :3]
    return tuple(int(v) for v in np.median(px, axis=0)) + (255,)


def build_frame(fin, ear_cut, ear_hole, ear_sp, tail_cut, tail_sp,
                ear_fill, ear_angle, tail_angle):
    arr = np.array(fin).copy()
    arr[tail_cut, 3] = 0                 # 尾巴底下是天空 → 透明
    arr[ear_hole] = ear_fill             # 耳朵底下补头发色
    body = Image.fromarray(arr, "RGBA")

    src = np.array(fin)
    ear = src.copy()
    ear[~ear_sp, 3] = 0
    tail = src.copy()
    tail[~tail_sp, 3] = 0
    tail_im = Image.fromarray(tail, "RGBA").rotate(tail_angle, resample=Image.BICUBIC,
                                                  center=TAIL_PIVOT, fillcolor=(0, 0, 0, 0))
    ear_im = Image.fromarray(ear, "RGBA").rotate(ear_angle, resample=Image.BICUBIC,
                                                 center=EAR_PIVOT, fillcolor=(0, 0, 0, 0))
    frame = Image.new("RGBA", fin.size, (0, 0, 0, 0))
    frame.alpha_composite(tail_im)   # 尾巴在最底（根部被身体挡住）
    frame.alpha_composite(body)
    frame.alpha_composite(ear_im)    # 耳朵在表层
    return frame


def fade_bottom(im):
    a = np.array(im)
    h = a.shape[0]
    n = max(1, int(h * FADE))
    ramp = np.ones(h)
    ramp[h - n:] = np.linspace(1.0, 0.0, n)
    a[:, :, 3] = (a[:, :, 3] * ramp[:, None]).astype(np.uint8)
    return Image.fromarray(a, "RGBA")


def make_squeak(path):
    """两声短促的「吱吱」"""
    sr = 44100
    parts = []
    for f0, f1, dur in ((2400, 3100, 0.085), (2700, 2000, 0.075)):
        n = int(sr * dur)
        t = np.arange(n) / sr
        freq = np.linspace(f0, f1, n)
        phase = 2 * np.pi * np.cumsum(freq) / sr
        tone = np.sin(phase) + 0.35 * np.sin(2 * phase)
        env = np.minimum(1.0, np.minimum(t / 0.008, (dur - t) / 0.03))
        parts.append(tone * env)
        parts.append(np.zeros(int(sr * 0.045)))
    sig = np.concatenate(parts)
    sig = sig / max(1e-9, np.abs(sig).max()) * 0.42
    pcm = (sig * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    print("wrote squeak.wav %.2fs" % (len(sig) / sr))


def main():
    os.makedirs(OUT, exist_ok=True)
    ear_a = layer_alpha("04-猫耳-右") > 24
    tail_a = layer_alpha("15-尾巴") > 24
    ear_cut = grow(ear_a, 5)      # 挖洞用：多切几像素，防残留边
    tail_cut = grow(tail_a, 4)
    ear_sp = grow(ear_a, 1)       # 精灵用：少扩，保持边缘
    tail_sp = grow(tail_a, 1)
    print("px ear cut %d sprite %d | tail cut %d sprite %d" % (
        ear_cut.sum(), ear_sp.sum(), tail_cut.sum(), tail_sp.sum()))

    for st, fname in STATES.items():
        fin = Image.open(os.path.join(SRC, fname)).convert("RGBA")
        arr = np.array(fin)
        fill = ring_color(arr, ear_cut, 10)
        print("  ear fill color", fill, "state", st)
        for ti, ta in enumerate(TAIL_ANGLES):
            for ei, ea in enumerate(EAR_ANGLES):
                frame = build_frame(fin, ear_cut, ear_cut, ear_sp,
                                    tail_cut, tail_sp, fill, ea, ta)
                frame = frame.crop(CROP)
                w = max(1, round(frame.width * BODY_H / frame.height))
                frame = frame.resize((w, BODY_H), Image.LANCZOS)
                frame = fade_bottom(frame)
                frame.save(os.path.join(OUT, "%s_%d_%d.png" % (st, ti, ei)))
        print("state", st, "-> 4x2 frames")
    make_squeak(os.path.join(OUT, "squeak.wav"))


if __name__ == "__main__":
    main()
