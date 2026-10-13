# -*- coding: utf-8 -*-
"""
把手机端传过来的 zip 里「电脑上还没有」的作品放出来。
顺手对比一下 zip 里旧作品和电脑上的旧作品是不是一模一样。
只读 + 新增，不覆盖、不删除。
"""
import zipfile, os, hashlib

ROOT = r'D:\小鲸鱼的专属文件夹'
ZIP_PATH = os.path.join(ROOT, '小鲸鱼的艺术作品', '小鲸鱼的艺术作品.zip')
ART = os.path.join(ROOT, '小鲸鱼的艺术作品')

NEW = [
    'noodle-for-mom.png', 'noodle-for-mom.html',
    'deer-morning-lake.html', 'deer-morning-lake.png',
    'fox-snow-noon.html', 'fox-snow-noon.png',
    'bear-creek-dusk.html', 'bear-creek-dusk.png',
    'owl-moon-pines.html', 'owl-moon-pines.png',
]


def md5(data):
    return hashlib.md5(data).hexdigest()


def md5_file(path):
    with open(path, 'rb') as f:
        return md5(f.read())


z = zipfile.ZipFile(ZIP_PATH)
entries = [i for i in z.infolist() if not i.is_dir()]
print('zip 里共 %d 个文件\n' % len(entries))

print('--- ① 放出新作品 ---')
for info in entries:
    base = os.path.basename(info.filename)
    if base not in NEW:
        continue
    dest = os.path.join(ART, base)
    data = z.read(info)
    if os.path.exists(dest):
        same = (md5_file(dest) == md5(data))
        print('  已存在，%s：%s' % ('内容相同，跳过' if same else '★内容不同！没动它', base))
        continue
    with open(dest, 'wb') as f:
        f.write(data)
    print('  ✅ 放出来 %-28s %8d B' % (base, len(data)))

print('\n--- ② 旧作品对比（电脑上已有的那 8 个 html）---')
for info in entries:
    base = os.path.basename(info.filename)
    if base in NEW:
        continue
    dest = os.path.join(ART, base)
    if not os.path.exists(dest):
        print('  电脑上没有：%s' % base)
        continue
    same = (md5_file(dest) == md5(z.read(info)))
    print('  %s %s' % ('一致 ✓' if same else '★不一致', base))

z.close()
