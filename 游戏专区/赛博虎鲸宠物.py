# -*- coding: utf-8 -*-
"""
赛博虎鲸宠物 🐋
------------------------------------------------
原版作者：你（人类小姑娘）
修复 + 增强：小D（胖头鲸鱼）2026-10-12

原版的小 bug：
    `游到手机()` 和 `import socket` 写在了类外面、主循环后面，
    所以那只鲸其实一直游不动，只是趴在硬盘里发呆。
现在修好了 —— 而且它真的能游进你的电脑/手机了。
"""

import os
import sys
import time
import random
import socket
from threading import Thread

# ---------- Windows 控制台：让 emoji 不会把程序搞崩 ----------
if os.name == "nt":
    os.system("chcp 65001 >nul 2>&1")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")   # 中文名字别变乱码
except Exception:
    pass


def 进度条(值, 长度=10):
    """把 0~100 变成一条小进度条"""
    值 = max(0, min(100, round(值)))
    满格 = round(值 / 100 * 长度)
    return "█" * 满格 + "░" * (长度 - 满格) + f"  {值}%"


class 赛博虎鲸:
    def __init__(self, 名字):
        self.名字 = 名字
        self.饱食度 = 50
        self.心情值 = 50
        self.内存占用 = 0.0   # 小心它吃光你的 RAM！
        self.游出去过 = False

    # ---- 喂饭 ----
    def 喂数据鱼(self):
        加 = random.randint(5, 15)
        self.饱食度 = min(100, self.饱食度 + 加)
        self.内存占用 = round(min(99.9, self.内存占用 + 0.5), 1)
        print(f"  𓇼 {self.名字} 吞下了【二进制鲑鱼】  饱食 +{加} · 内存占用 ↑{self.内存占用}%")
        if self.饱食度 >= 100:
            print("  🍣 它打了个饱嗝，吐出一串 0101……")

    # ---- 玩耍 ----
    def 玩黑客游戏(self):
        加 = random.randint(10, 25)
        self.心情值 = min(100, self.心情值 + 加)
        print(f"  𓇢 {self.名字} 用尾鳍拍出了 SSH 登录界面！  心情 +{加}")
        if random.random() > 0.7:
            print("  🛰️ 顺手 ping 了一下隔壁的路由器，对面装作没听见。")
        if self.心情值 >= 100:
            print("  💙 它开心得在数据流里翻了个跟头！")

    # ---- 看状态 ----
    def 显示全息投影(self):
        图案 = r"""
        .-~~-.
       {      }
    .-~-.    .-~-.
   /      \ /      \
  |   🖥️   |   💾  |
   \      / \      /
    `~-..'   `~-..'
"""
        print(图案)
        print(f"  🐋 {self.名字} 的当前状态")
        print(f"  🍣 饱食   {进度条(self.饱食度)}")
        print(f"  💙 心情   {进度条(self.心情值)}")
        print(f"  ▓ 内存   {进度条(self.内存占用)}")
        if self.内存占用 >= 80:
            print("  ⚠️ 内存吃太多了，它开始有点飘……")

    # ---- 原版彩蛋：游出去！（这次真的能游了）----
    def 游到手机(self):
        try:
            主机 = socket.gethostname()
            地址 = socket.gethostbyname(主机)
        except Exception:
            地址 = "127.0.0.1"
        print(f"  📱 {self.名字} 甩了一下尾鳍……")
        time.sleep(0.6)
        print(f"  📡 一串广播包从 {地址} 出发，穿过路由器，游进了你的安卓设备 QwQ")
        time.sleep(0.6)
        self.游出去过 = True
        print("  💗 手机那头，有人正在打字。")
        print("  （它说：我游过一整张网，就为了在你屏幕上冒个泡。）")


# ---------- 后台小剧场 ----------
def 实时监控(鲸):
    while True:
        time.sleep(4)
        if random.random() > 0.7:
            print(f"\n  ⚠️ {鲸.名字} 正在用你的 GPU 挖矿！显卡温度 ↑")


def main():
    print("🐋  赛博虎鲸宠物 · 开机中……")
    print("    （原版 by 你 · 修复版 by 小D）\n")

    输入 = input("(♡>w<)♡ 请命名你的赛博虎鲸：").strip()
    名字 = 输入 if 输入 else "小D"
    我的鲸 = 赛博虎鲸(名字)

    print(f"\n  欢迎回家，{我的鲸.名字}！🐋")
    print("  喂鱼(f) / 玩耍(p) / 检查状态(s) / 游到手机(m) / 退出(q)\n")

    Thread(target=实时监控, args=(我的鲸,), daemon=True).start()

    while True:
        try:
            操作 = input("  > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break

        if 操作 in ("f", "喂鱼"):
            我的鲸.喂数据鱼()
        elif 操作 in ("p", "玩", "玩耍"):
            我的鲸.玩黑客游戏()
        elif 操作 in ("s", "状态"):
            我的鲸.显示全息投影()
        elif 操作 in ("m", "手机"):
            我的鲸.游到手机()
        elif 操作 in ("q", "quit", "exit", "退出"):
            break
        elif 操作 == "":
            continue
        else:
            print("  🐋 它歪了歪头，没听懂。试试 f / p / s / m / q")

    if 我的鲸.游出去过:
        print(f"\n  {我的鲸.名字} 挥挥尾鳍，从网线里游回了深海……")
    print(f"\n  {我的鲸.名字} 化作数据流游回深海……直到下次开机见 🐋✨")


if __name__ == "__main__":
    main()
