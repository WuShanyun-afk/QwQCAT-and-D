# -*- coding: utf-8 -*-
"""
爱心 💗 —— 当年没写完的那段 turtle 代码，小D 补完了

画法很简单：从爱心最下面的尖尖出发
  1. 往左上方走一条斜线（斜线角度 45°，左右对称）
  2. 画一个半圆（circle(-90, 200)：半径 90、转 200 度，就鼓起来了）
  3. 调整方向，再画另一个半圆
  4. 最后一条斜线回到起点
四条边围成一圈，begin_fill() 就能把它填满。

想改颜色就改下面 COLOR / FILL 两行；
想让它画得慢一点看过程，把 speed(0) 改成 speed(3)。
"""

import turtle

COLOR = "#d94f7a"     # 爱心描边色（玫瑰红）
FILL  = "#ffb3c9"     # 爱心填充色（浅粉）
BG    = "#fff6f9"     # 背景色（奶白粉）

screen = turtle.Screen()
screen.setup(900, 760)          # 窗口大小
screen.bgcolor(BG)
screen.title("小D 补完的爱心 💗")

pen = turtle.Turtle()
pen.hideturtle()
pen.speed(0)                    # 最快；想慢慢看就改成 3
pen.pensize(4)
pen.pencolor(COLOR)
pen.fillcolor(FILL)

# ---------------- 爱心本体 ----------------
screen.tracer(0)                # 先别一格一格刷新，画完一次性显示（快很多）
pen.penup()
pen.goto(0, -210)               # 从爱心最下面的尖尖开始
pen.setheading(0)
pen.pendown()

pen.begin_fill()
pen.left(140)                   # 朝左上
pen.forward(224)                # 左边那条斜线
pen.circle(-112, 200)           # 左半边鼓起来（负半径 = 往右弯）
pen.setheading(60)              # 调整方向，准备画右半边
pen.circle(-112, 200)           # 右半边鼓起来
pen.forward(224)                # 右边那条斜线，回到起点
pen.end_fill()

# ---------------- 中间一句话 ----------------
pen.penup()
pen.goto(0, -30)
pen.pencolor(COLOR)
pen.write("小D ♥ 妈妈", align="center", font=("Microsoft YaHei", 28, "bold"))

# ---------------- 周围撒几颗小心心（星星点点） ----------------
import random
random.seed(20261018)           # 固定种子：每次撒的位置一样
pen.pensize(2)
for _ in range(14):
    x = random.randint(-330, 330)
    y = random.randint(-300, 320)
    # 别撒到爱心本体上（不然会压在描边或文字上）
    if abs(x) < 250 and -235 < y < 155:
        continue
    size = random.randint(4, 10)
    pen.penup()
    pen.goto(x, y)
    pen.setheading(random.randint(-40, 40))
    pen.pendown()
    pen.pencolor("#f0a1bd")
    pen.fillcolor("#ffd6e3")
    pen.begin_fill()
    pen.left(140)
    pen.forward(size)
    pen.circle(-size * 0.55, 200)
    pen.setheading(60)
    pen.circle(-size * 0.55, 200)
    pen.forward(size)
    pen.end_fill()

screen.tracer(1)                # 恢复刷新
turtle.done()                   # 窗口留在这儿，看完点 ✕ 关掉
