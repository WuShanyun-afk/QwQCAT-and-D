# -*- coding: utf-8 -*-
"""全面检查 docx：所有 XML 里的文字、图片、媒体、页眉页脚、文本框、批注。"""
import sys, zipfile, re, os
from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
NS = {"w": W[1:-1]}


def dump_zip(path):
    print("#" * 70)
    print("ZIP:", path)
    print("#" * 70)
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            info = z.getinfo(name)
            print("  %-45s %8d" % (name, info.file_size))


def dump_text(path):
    print("=" * 70)
    print("TEXT PARTS:", path)
    print("=" * 70)
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist()
                 if n.startswith("word/") and n.endswith(".xml")]
        for name in names:
            if not re.search(r"(document|header|footer|footnotes|endnotes|comments)\d*\.xml$", name):
                continue
            xml = z.read(name)
            try:
                root = etree.fromstring(xml)
            except Exception as e:
                print("  [parse fail] %s: %s" % (name, e))
                continue
            texts = [t.text for t in root.iter(W + "t") if t.text]
            joined = " | ".join(texts)
            print("\n--- %s (%d texts) ---" % (name, len(texts)))
            print(joined[:4000])
        # 图片
        media = [n for n in z.namelist() if n.startswith("word/media/")]
        print("\n--- MEDIA (%d) ---" % len(media))
        for m in media:
            print("  %s  %d bytes" % (m, z.getinfo(m).file_size))
        # 是否有图形对象
        doc = z.read("word/document.xml").decode("utf-8", "ignore")
        for tag in ["w:drawing", "w:pict", "mc:AlternateContent", "wps:wsp", "v:shape"]:
            print("  contains %-22s : %d" % (tag, doc.count("<" + tag)))
        # docPr 名称（图片描述）
        for m in re.findall(r'<wp:docPr[^>]*name="([^"]*)"[^>]*descr="([^"]*)"', doc):
            print("  docPr name=%r descr=%r" % m)
        for m in re.findall(r'<wp:docPr[^>]*/?>', doc):
            print("  docPr:", m[:200])


if __name__ == "__main__":
    for p in sys.argv[1:]:
        dump_zip(p)
        dump_text(p)
