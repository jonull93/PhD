from random import randrange
import my_utils

print(my_utils.__file__,dir(my_utils))

def d6(mean=False): return randrange(1,7)*(1-mean)+(6/2+0.5)*mean
def d8(mean=False): return randrange(1,9)*(1-mean)+(8/2+0.5)*mean
def d10(mean=False): return randrange(1,11)*(1-mean)+(10/2+0.5)*mean
def d12(mean=False): return randrange(1,13)*(1-mean)+(12/2+0.5)*mean

chance_to_hit = 0.65
