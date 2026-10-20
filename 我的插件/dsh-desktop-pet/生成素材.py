r"""从妈妈画的透明底成品帧 + 分层件，生成桌宠的「耳朵抖 / 尾巴摇」动画帧。

输入：
  ..\..\小D\拆分图\成品-透明底\成品-{睁眼,单眼眨,笑眼闭眼}-透明.png   （完整图，带装饰）
  ..\..\小D\拆分图\分层\04-猫耳-右.png / 15-尾巴.png                  （妈妈画的耳朵/尾巴本体）
输出：
  assets\{state}_{tail}_{ear}.png  —— 3 状态 × 4 尾巴角 × 2 耳朵角 = 24 张
  assets\squeak.wav                —— 点击时的「吱吱」声

做法（只动耳朵和尾巴，全身不晃；不"切"身体）：
  1) 尾巴/耳朵直接用妈妈画的**分层件本身**当精灵，绕根部旋转（不是从成品图上切一块下来）；
  2) 身体 = 成品图，**只把「露在身体轮廓外面」的尾巴、耳朵抠掉**（尾巴底下本来就是天空，保持透明）；
     耳朵根部压在头发上的那一小块，用周围头发的中位色补上，避免转动时露洞；
  3) 合成：尾巴精灵（最底层，根部自然被身体挡住）→ 身体 → 耳朵精灵；
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

# 「身体轮廓」用的图层（不含耳朵、尾巴）
BODY_LAYERS = ["01-后发", "02-辫子", "03-脸", "05-刘海", "09-眉毛",
               "11-腿", "12-身体", "13-光球效果", "14-手", "16-布条"]
HEAD_LAYERS = ["01-后发", "02-辫子", "03-脸", "05-刘海", "09-眉毛"]


def load_layer(name):
    return Image.open(os.path.join(LAYER, name + ".png")).convert("RGBA")


def layer_alpha(name):
    return np.array(load_layer(name))[:, :, 3]


def grow(mask, px):
    if px <= 0:
        return mask
    m = Image.fromarray((mask * 255).astype(np.uint8), "L")
    m = m.filter(ImageFilter.MaxFilter(px * 2 + 1))
    return np.array(m) > 128


def silhouette(names, grow_px=2):
    m = np.zeros((1280, 1280), dtype=bool)
    for n in names:
        m |= layer_alpha(n) > 24
    return grow(m, grow_px)


def ring_color(arr, mask, grow_px=10):
    """遮罩外一圈不透明像素的中位色（补耳朵底下的头发）"""
    ring = grow(mask, grow_px) & ~mask & (arr[:, :, 3] > 200)
    if ring.sum() == 0:
        return (38, 55, 81, 255)
    px = arr[ring][:, :3]
    return tuple(int(v) for v in np.median(px, axis=0)) + (255,)


def build_frame(fin_arr, tail_img, ear_img, tail_vis, ear_vis, ear_hide,
                ear_fill, ear_angle, tail_angle):
    body = fin_arr.copy()
    body[tail_vis, 3] = 0                # 露在外面的尾巴 → 透明（底下是天空）
    body[ear_vis, 3] = 0                 # 露在外面的耳朵 → 透明
    body[ear_hide] = ear_fill            # 压在头发上的耳根 → 补头发色
    body = Image.fromarray(body, "RGBA")

    tail_rot = tail_img.rotate(tail_angle, resample=Image.BICUBIC,
                               center=TAIL_PIVOT, fillcolor=(0, 0, 0, 0))
    ear_rot = ear_img.rotate(ear_angle, resample=Image.BICUBIC,
                             center=EAR_PIVOT, fillcolor=(0, 0, 0, 0))
    frame = Image.new("RGBA", (1280, 1280), (0, 0, 0, 0))
    frame.alpha_composite(tail_rot)   # 尾巴在最底：根部被身体自然挡住
    frame.alpha_composite(ear_rot)    # 耳朵也在身体后面：耳根被头发/补色盖住，转动不会露缝
    frame.alpha_composite(body)
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
    tail_img = load_layer("15-尾巴")
    ear_img = load_layer("04-猫耳-右")
    tail_mask = grow(layer_alpha("15-尾巴") > 24, 1)
    ear_mask = grow(layer_alpha("04-猫耳-右") > 24, 8)   # 多切一点，防成品图上残留的耳边
    body_sil = silhouette(BODY_LAYERS, 2)
    head_sil = silhouette(HEAD_LAYERS, 2)
    tail_vis = tail_mask & ~body_sil                 # 尾巴露在身体外的部分
    ear_vis = ear_mask & ~head_sil                   # 耳朵露在头发外的部分
    ear_hide = ear_mask & head_sil                   # 耳根压在头发上的一小块
    print("tail vis %d | ear vis %d  hide %d" % (
        tail_vis.sum(), ear_vis.sum(), ear_hide.sum()))

    for st, fname in STATES.items():
        fin = Image.open(os.path.join(SRC, fname)).convert("RGBA")
        fin_arr = np.array(fin)
        fill = ring_color(fin_arr, ear_hide, 10)
        for ti, ta in enumerate(TAIL_ANGLES):
            for ei, ea in enumerate(EAR_ANGLES):
                frame = build_frame(fin_arr, tail_img, ear_img, tail_vis, ear_vis,
                                    ear_hide, fill, ea, ta)
                frame = frame.crop(CROP)
                w = max(1, round(frame.width * BODY_H / frame.height))
                frame = frame.resize((w, BODY_H), Image.LANCZOS)
                frame = fade_bottom(frame)
                frame.save(os.path.join(OUT, "%s_%d_%d.png" % (st, ti, ei)))
        print("state", st, "-> 4x2 frames")
    make_squeak(os.path.join(OUT, "squeak.wav"))


if __name__ == "__main__":
    main()
