import pickle
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import to_rgb
from matplotlib.patches import Patch
import matplotlib.gridspec as gridspec
import os
os.chdir(r"C:\Users\Jonathan\Box\python")  # not needed unless running line-by-line in a console

from my_utils import color_dict, order_cap, add_in_dict, tech_names, scen_names

pickleJar = ""
data = pickle.load(open(r"C:\Users\Jonathan\Box\python\PickleJar\data_results_6h.pickle", "rb"))
