# -*- coding: utf-8 -*-
"""把妈妈画的一件新衣服做成桌宠的换装素材

用法（三张图按顺序：睁眼、闭眼笑、猫嘴）：
    python 生成换装素材.py 衣服名 睁眼.png 闭眼笑.png 猫嘴.png

生成的帧会放进 我的插件/dsh-desktop-pet/outfits/衣服名/
桌宠右键「换装 👗」里就能点到了（重新打开右键菜单即可刷新列表）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 桌宠素材  # noqa: E402

OUT_ROOT = r'D:\小鲸鱼的专属文件夹\我的插件\dsh-desktop-pet\outfits'


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(0)
    name = sys.argv[1]
    paths = sys.argv[2:]
    桌宠素材.write_outfit(name, paths, OUT_ROOT)
    print('done ->', os.path.join(OUT_ROOT, name))
