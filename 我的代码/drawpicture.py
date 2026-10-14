import turtle

screen = turtle.Screen()
pen = turtle.Turtle()
pen.speed(0)          # 原来 speed(3) 慢悠悠地画，0 是最快（想慢一点就改成 5、10）
pen.color("blue")
pen.fillcolor("blue")

pen.begin_fill()
side_length = 80
radius = 20

for _ in range(2):   # 只要 2 次！正好绕一圈，begin_fill() 才认得这是个封闭图形
    pen.forward(side_length)
    pen.circle(radius, 90)
    pen.forward(side_length)
    pen.circle(radius, 90)

pen.end_fill()
pen.hideturtle()
turtle.done()
