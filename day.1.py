'''
f = open("家人", mode='w', encoding="utf-8")  # 写入之前会清除之前的
f.write("罗立平")
f.write("杨运焯")
f.flush()
f.close()
f = open("家人", mode="a", encoding="utf-8")  # a表示增加文本
f.write("老罗")
f.flush()
f.close()
f = open("家人", mode="rb")  # 读字节
base = f.read()
print(base.decode("utf-8"))
f.close()
f = open("家人", mode="wb")  # 写字节,追加ab，跟wb一样
f.write("小杨".encode("utf-8"))
f.close()
f = open("家人", mode="r+", encoding="utf-8")  # r+是先读后写，先写后读会替换掉
# f.write("周杰伦")
a = f.read()
f.write("周杰伦")
f.flush()
f.close()
print(a)

f=open("nijia",mode="w+",encoding="utf-8")
f.write("你好啊")
f.seek(0)  #seek是移动光标
s=f.read()
print(s)
f.flush()
f.close()

f = open("nijia", mode="r+", encoding="utf-8")  # r+模式下光标显示多少，你在写进去一直是在末尾添加
# s=f.read(3)                       可以先写再读，先写的时候一直是在前面，前提是在r+的情况下先写
# ss=f.read(4)
f.write("马虎他")
# print(s)
# print(ss)

f = open("nijia", mode="r+", encoding="utf-8")
f.read(3)
f.seek(3)  # seek(3)代表移动三个字节就是一个字，
# 移动到开头，f.seek(0)  移动到末尾，f.seek(0,2) 0,在开头 1，在当前， 2 在末尾
print(f.read())

import os
with open("nijia",mode="r",encoding="utf-8")as f1, open("nijia2",mode="w",encoding="utf-8")as f2:
    s=f1.read()
    ss=s.replace("肉","菜")
    f2.write(ss)
os.remove("nijia")
os.rename("nijia2","nijia")

f=open("nijia",mode="r",encoding="utf-8")
for line in f:
    print(line)
f.close()

def yue():
    print("wo")
    print("ni")
    return "dama", "woma"  # 执行到return的时候停止执行，后面的不执行了
    print("wi")
# ret=yue()
# print(ret)
a, b = yue()
print(a)
print(b)

def yue(app):#形参和实参是要一样数量的
    print("打开手机")
    print("打开"+app)
yue("探探")
yue("陌陌")



def information(id, name, sex="男"):
    print("录入学生信息：id是%s,名字是%s,性别是%s" % (id, name, sex))


information(1, "llp")
information(2, "ljp")
information(3, "lx", "女")
open("文件名", mode="w+")



# 1+2+3+4+5+6+7+8+9+10+。。。。。。。。。+100=5050
def sum(n):
    s = 0
    count = 1
    while count <= n:
        s = s + count
        count = count + 1
    return s


ret = sum(2)
print(ret)



def fn(n):
    if n % 2 == 0:
        print(str(n) + "为偶数")
    else:
        print(str(n) + "为奇数")
fn(8)
fn(111111111111111111111111111111111111989999)

def num(a, b, c, *args, d=5):  # 位置参数>*动态参数>默认参数
    print(a, b, c, d, args)
num(1, 2, 3, 4, 5, 6, 7)

def he(*n):
    sum = 0
    for i in n:
        sum += i
    return sum
print(he(1, 2, 3, 4, 5))

#动态接收关键字参数
#*位置参数
#**关键字参数
def func(**food):
    print(food)
func(good_food="面条",bad_food="辣条",drink="shui")

a=10
def num():
    a=20
    print(a)
    print(globals())  # globals()获取到全局作用域（内置+全局）中所有的名字
    print(locals())  # locals()查看当前作用域中的所有名字
num()
#print(globals())#globals()获取到全局作用域（内置+全局）中所有的名字
#print(locals())#locals()查看当前作用域中的所有名字

def func1():
    print("haha")
    def func2():
        print("呵呵")
    func2()
    print("hoho")
func1()

def func1():
    print("赵")
    def func2():
        print("钱")
        def func3():#没执行
            print("孙")
        print("李")
    def func4():#没执行
        print("哈哈哈")
        func2()
    print("周")
    func2()
func1()

a=10
def func():
    #a=20
    global a#把外面全局中的a引入
    #a+=10
    a=30#修改赋值
    print(a)
func()
print(a)

def func1():
    a=10
    def func2():
        nonlocal a
        a=20
        print(a)
    func2()
    print(a)
func1()

a = 1
def func1():
    a = 2
    def func2():
        nonlocal a
        a = 3
        def func3():
            a = 4
            print(a)
        print(a)
        func3()
        print(a)
    print(a)
    func2()
    print(a)
print(a)
func1()
print(a)

def f1():
    print("1")
def f2():
    print("2")
def f3():
    print("3")
def f4():
    print("4")
lst=[f1,f2,f3,f4]
for i in lst:
    i()



# 闭包：就是内层函数对外层函数（非全局）的变量的引用,可以让一个局部变量常驻内存
def func():
    a = "llp"    #闭包作用：常驻内存，防止其他程序改变这个变量
    def name():
        print(a)
    print(name.__closure__)#用__closure__判断是否闭包
    return name
c = func()
print(c)

from urllib.request import urlopen
def but():
    content = urlopen("https://www.xiaohua100.cn/index.html").read()
    def inner():
        return content
    return inner
a = but()
content = a()
print(content)
content2 = a()
print(content2)

#可迭代对象：dic,str,tuple,set,f,list(所有的以上都有一个函数__iter__())
#（所有包含了__iter__()的数据类型都是可迭代的数据类型 Iterable）
#dir()用来查看一个对象，数据类型中包含了哪些东西
lst=[1,2,3]
#print(dir(lst))
#获取迭代器
a=lst.__iter__()
#迭代器往外拿元素，__next__()
print(a.__next__())#迭代最后一个数量之后，再迭代就会报错
print(a.__next__())
print(a.__next__())
print(a.__next__())

lst=[1,2,3,4]
#模拟for循环
a=lst.__iter__()
while True:
    try:
        name=a.__next__()
        print(name)
    except StopIteration:
        break

lst = [1, 2, 3, 4]
from collections import Iterable  # 可迭代的
from collections import Iterator  # 迭代器
A=lst.__iter__()
print(isinstance(A, Iterable))#判断是否是可迭代的
print(isinstance(A, Iterator))#判断是不是迭代器
# print("__iter__" in dir(lst))#判断可不可以迭代的
# print("__next__" in dir(lst))#判断是不是一个迭代器

#迭代器特点：节省内存，惰性机制，不能反复，只能向下进行
from collections import Iterable  # 可迭代的
from collections import Iterator  # 迭代器

f=open("a3.txt",mode="r",encoding="utf-8")
print(isinstance(f,Iterable))
print(isinstance(f,Iterator))

#生成器和生成器函数
#（生成器的本质就是迭代器）生成器的三种生成办法:1.通过生成器函数2.通过生成器表达式创建生成器3.通过数据转换
def func():
    print("周杰伦")
    yield "昆凌"#函数中包含了yield就是生成器函数
#a=func()#通过函数func()来创建一个生成器
print(func().__next__())
#return 是直接返回结果，结束函数的调用 yield是返回结果让函数分段执行

def func():
    yield 11
    yield 22
    yield 33
    yield 44
a=func()#拿到的是生成器，生成器的本质是迭代器，迭代器可以被迭代，生成器可以for循环
for i in a:
    print(i)
b=a.__iter__()
while True:
    try:
        print(b.__next__())
    except StopIteration:
        break

def func():
    yield 1
    yield 2
    yield 3
    yield 4
a=func()
while True:
    try:
        print(a.__next__())
    except StopIteration:
        break

#__next__()可以让生成器向下执行一次
#send()也可以让生成器向下执行一次% 作用：给上一个yeild传一个值
def func():
    print("大碴子")
    a=yield "11"
    print(a)
    print("大碴子")
    b=yield "22"
    print("大碴子")
    c=yield "33"

d=func()
while True:
    try:
        print(d.__next__())
        print(d.send(1))
        print(d.send(2))
        print(d.send(3))
        # print(d.__next__())
    except StopIteration:
        break

def func():
    print("我吃什么啊")
    a=yield "馒头"
    print("a=", a)
    b=yield "大饼"
    print("b=", b)
    c=yield "韭菜盒子"
    print("c=", c)
    yield "OUT"
l=func()
print(l.__next__())
print(l.send("胡辣汤"))
print(l.send("狗粮"))
print(l.send("猫粮"))

#生成列表里面装1-14的数据（不用推导式）
a=[]
for i in range(1,15):
    a.append("python%s" % i)
print(a)

#列表推导式，最终给你的是列表
#语法【最终结果 for 变量 in 可迭代对象】
lst=["python%s" % i for i in range(1,15) ]
print(lst)

#获取1-100能被3整除的数
lst=[i for i in range(1,101) if i%3==0]
print(lst)

#获取100以内能被3整除的数的平方
lst=[i*i for i in range(1,101) if i%3==0]
print(lst)

#寻找名字中带有两个e的人的名字
names=[['Tom','Billy','Jefferson','Andrew','Wesley','Steven','Joe',],
['Alice','Jill','Ana','Wendy','Jennifer','Sherry','Eva']]
lst=[name for first in names for name in first if name.count("e")==2]
print(lst)

lst=["我喜欢%s" % i for i in range(1,1001)]
print(lst)

a=(i for i in range(10))
print(list(a))

def func():
    print(111)
    yield 222
a=func()
a1=(i for i in a)
a2=(i for i in a)
print(list(a))
print(list(a1))
print(list(a2))

dic={"a":"b","c":"d"}
#把字典中的key,value进行互换
new_dic={dic[key]:key for key in dic}
print(new_dic)

a=["llp","ljp","lhp","zxn"]
b=["1","2","3","4"]
dic={a[i]:b[i] for i in range(len(a))}
print(dic)
'''
