import matplotlib.pyplot as plt
import random
from my_utils import print_red, print_cyan, print_green

def gen_one_stat():
    rolls = [random.randint(1, 6) for i in range(4)]
    return sum(rolls)-min(rolls)


x = []
for i in range(10000):
    stat = gen_one_stat()
    x.append(stat)
print(f"average is {sum(x)/len(x)}")
print(f"expected total for 6 stats is {sum(x)/len(x)*6}")
plt.hist(x)
plt.show()

i = 0
while True:
    i += 1
    print_cyan("Try nr",i)
    stats = [gen_one_stat() for i in range(6)]
    summed_rolls = sum(stats)
    viable_stats = summed_rolls>=80
    if viable_stats:
        print(stats)
        print(summed_rolls)
        break
    else:
        print_red(summed_rolls)
