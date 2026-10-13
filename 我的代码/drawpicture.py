import turtle

screen = turtle.Screen()
pen = turtle.Turtle()
pen.speed(3)
pen.color("blue")
pen.fillcolor("blue")

pen.begin_fill()
side_length = 80
radius = 20

for _ in range(4):   # 只需要4次，每边：直线 + 两个1/4圆
    pen.forward(side_length)
    pen.circle(radius, 90)
    pen.forward(side_length)
    pen.circle(radius, 90)

pen.end_fill()
pen.hideturtle()
turtle.done()

