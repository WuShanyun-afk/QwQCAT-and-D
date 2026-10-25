# -*- coding: utf-8 -*-
"""把妈妈画的一件新衣服做成桌宠的换装素材

用法（三张图按顺序：睁眼、闭眼笑、猫嘴）：
    python 生成换装素材.py 衣服名 睁眼.png 闭眼笑.png 猫嘴.png

可选：某套衣服里有一张多画了点小装饰（比如只有睁眼版才有的星星），
逐张自动裁边会让眨眼时左右跳，这时给一个统一的裁切框：
    python 生成换装素材.py 衣服名 睁眼.png 闭眼笑.png 猫嘴.png --box 54,67,913,1234

生成的帧会放进 我的插件/dsh-desktop-pet/outfits/衣服名/
桌宠右键「换装 👗」里就能点到了（重新打开右键菜单即可刷新列表）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 桌宠素材  # noqa: E402

OUT_ROOT = r'D:\小鲸鱼的专属文件夹\我的插件\dsh-desktop-pet\outfits'


if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) < 4:
        print(__doc__)
        raise SystemExit(0)
    box = None
    if '--box' in args:
        i = args.index('--box')
        try:
            box = tuple(int(v) for v in args[i + 1].replace('，', ',').split(','))
            del args[i:i + 2]
        except Exception:
            print('--box 要写成 0,0,100,200 这样的四个整数')
            raise SystemExit(1)
    name = args[0]
    paths = args[1:]
    桌宠素材.write_outfit(name, paths, OUT_ROOT, box=box)
    print('done ->', os.path.join(OUT_ROOT, name))
