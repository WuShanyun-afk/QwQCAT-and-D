# -*- coding: utf-8 -*-
"""
预览图生成器 🖼️
规矩：只要「小鲸鱼的艺术作品」里有一张 PNG，就在「预览图」里生成一张
      宽 1280 的 preview-xxx.png（画廊页要用）。
判据：**原图没动就跳过，原图改过（时间更新）自动重做** —— 同一张画重画一遍、
      同名覆盖，预览图也会跟着换新，不会一直显示旧版。
只新增/更新预览图，绝不碰原图。
用法：双击我，或者 python 工具\生成预览图.py
      想强制全部重做：python 工具\生成预览图.py --force
"""
import os
import sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, '小鲸鱼的艺术作品')
PREV = os.path.join(ROOT, '预览图')
TARGET_W = 1280

FORCE = any(a in ('-f', '--force') for a in sys.argv[1:])

# Pillow 10 起 LANCZOS 搬进了 Image.Resampling，这里新老两代都兼容
LANCZOS = getattr(getattr(Image, 'Resampling', Image), 'LANCZOS', None) or Image.LANCZOS

os.makedirs(PREV, exist_ok=True)

made, updated, skipped = [], [], []

for name in sorted(os.listdir(ART)):
    if not name.lower().endswith('.png'):
        continue
    src = os.path.join(ART, name)
    dst = os.path.join(PREV, 'preview-' + name)
    exists = os.path.exists(dst)

    # 关键：不是「文件在就跳过」，而是「原图没动才跳过」
    if exists and not FORCE and os.path.getmtime(dst) >= os.path.getmtime(src):
        skipped.append(name)
        continue

    im = Image.open(src)
    w, h = im.size
    if w > TARGET_W:
        im = im.resize((TARGET_W, round(h * TARGET_W / w)), LANCZOS)
    if im.mode != 'RGB':
        im = im.convert('RGB')
    im.save(dst, 'PNG', optimize=True)

    line = '%-30s %s -> %s   %.0f KB' % (name, (w, h), im.size,
                                         os.path.getsize(dst) / 1024)
    (updated if exists else made).append(line)

if made:
    print('新增 %d 张预览图：' % len(made))
    for line in made:
        print('  ' + line)
if updated:
    print('原图改过，重做 %d 张：' % len(updated))
    for line in updated:
        print('  ' + line)
if skipped:
    print('原图没变，跳过 %d 张：%s' % (len(skipped), '、'.join(skipped)))
if not made and not updated and not skipped:
    print('  （艺术作品文件夹里还没有 PNG）')
