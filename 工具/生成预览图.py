# -*- coding: utf-8 -*-
"""
预览图生成器 🖼️
规矩：只要「小鲸鱼的艺术作品」里有一张 PNG，就在「预览图」里生成一张
      宽 1280 的 preview-xxx.png（画廊页要用）。
已经有的不重复生成。只新增，不删除、不覆盖原图。
用法：双击我，或者 python 工具\生成预览图.py
"""
import os
import sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, '小鲸鱼的艺术作品')
PREV = os.path.join(ROOT, '预览图')
TARGET_W = 1280

os.makedirs(PREV, exist_ok=True)

made, skipped = [], []
for name in sorted(os.listdir(ART)):
    if not name.lower().endswith('.png'):
        continue
    src = os.path.join(ART, name)
    dst = os.path.join(PREV, 'preview-' + name)
    if os.path.exists(dst):
        skipped.append(name)
        continue
    im = Image.open(src)
    w, h = im.size
    if w > TARGET_W:
        im = im.resize((TARGET_W, round(h * TARGET_W / w)), Image.LANCZOS)
    if im.mode != 'RGB':
        im = im.convert('RGB')
    im.save(dst, 'PNG', optimize=True)
    made.append('%-30s %s -> %s   %.0f KB' % (name, (w, h), im.size,
                                              os.path.getsize(dst) / 1024))

print('生成 %d 张预览图：' % len(made))
for line in made:
    print('  ' + line)
if skipped:
    print('已有，跳过 %d 张：%s' % (len(skipped), '、'.join(skipped)))
if not made and not skipped:
    print('  （艺术作品文件夹里还没有 PNG）')
