# -*- coding: utf-8 -*-
"""把妈妈画的睡衣版小D 做成桌宠的「睡衣」这一套（调用公共素材处理）"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 桌宠素材  # noqa: E402

SRC = r'D:\小鲸鱼的专属文件夹\小D\拆分图\新形象-睡衣-2026-10-24'
OUT_ROOT = r'D:\小鲸鱼的专属文件夹\我的插件\dsh-desktop-pet\outfits'

FACES = [
    os.path.join(SRC, '睡衣-睁眼张嘴.png'),      # idle
    os.path.join(SRC, '睡衣-闭眼笑张嘴.png'),    # blink（被摸头/笑）
    os.path.join(SRC, '睡衣-闭眼猫嘴.png'),      # wink（猫嘴）
]

if __name__ == '__main__':
    桌宠素材.write_outfit('睡衣', FACES, OUT_ROOT)
    print('done')
