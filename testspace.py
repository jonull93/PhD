import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from time import sleep
from my_utils import print_red, print_cyan, print_green, fast_rolling_average

# load data to data_s from "C:\Users\jonathan\git\python\PickleJar\netload_components_small_1980-2019.pickle"
# load data to data_l from "C:\Users\jonathan\git\python\PickleJar\netload_components_large_1980-2019.pickle"
data_s = pd.read_pickle("C:\\Users\\jonathan\\git\\python\\PickleJar\\netload_components_small_1980-2019.pickle")
data_l = pd.read_pickle("C:\\Users\\jonathan\\git\\python\\PickleJar\\netload_components_large_1980-2019.pickle")

netload = data_s['net_load']
VRE_gen = data_s['VRE_gen']
load = pd.concat(data_s['total_hourly_load'])
#print(total_load.values.mean())
traditional_load = data_l['traditional_load']
yearly_nontraditional_load = data_l['yearly_nontraditional_load']
hourly_nontraditional_load = data_l['hourly_nontraditional_load']
print_green(hourly_nontraditional_load)
load = pd.concat(traditional_load).sum(axis=1) + yearly_nontraditional_load.sum() / 8766 + hourly_nontraditional_load.sum(axis=1)
print(load-VRE_gen)
#print(load.values.mean())

netload_constructed = load - VRE_gen

print_cyan(netload)
print_red(netload_constructed)

# print max, mean, min of the two netloads
print_cyan(f"max of netload: {netload.values.max()}")
print_cyan(f"mean of netload: {netload.values.mean()}")
print_cyan(f"min of netload: {netload.values.min()}")

print_red(f"max of netload_constructed: {netload_constructed.max()}")
print_red(f"mean of netload_constructed: {netload_constructed.mean()}")
print_red(f"min of netload_constructed: {netload_constructed.min()}")

amps = range(-20,0,6)
netload_RA12 = fast_rolling_average(netload, 12)
netload_RA24 = fast_rolling_average(netload, 24)
for amp in amps:
    # find the longest period of time where netload is less than amp
    counter = 0
    highest_counter = 0
    for val in netload.values:
        if val < amp:
            counter += 1
            if counter > highest_counter:
                highest_counter = counter
        else:
            counter = 0
    print(f"No RA, amp = {amp}, longest event is {highest_counter / 24:.1f} days")
    counter = 0
    highest_counter = 0
    for val in netload_RA12.values:
        if val < amp:
            counter += 1
            if counter > highest_counter:
                highest_counter = counter
        else:
            counter = 0
    print(f"RA 12, amp = {amp}, longest event is {highest_counter / 24:.1f} days")
    counter = 0
    highest_counter = 0
    for val in netload_RA24.values:
        if val < amp:
            counter += 1
            if counter > highest_counter:
                highest_counter = counter
        else:
            counter = 0
    print(f"RA 24, amp = {amp}, longest event is {highest_counter / 24:.1f} days")
exit()
# plot the two netloads for .loc[year]
year = 1983
fig, ax = plt.subplots(figsize=(10, 5))
netload.loc[year].plot(ax=ax, label="netload", linewidth=0.5, color="blue")
ax.axhline(y=netload.loc[year].values.mean(), color="blue", linestyle="--", linewidth=2, label=f"{netload.loc[year].values.mean():.2f}")
ax.axhline(y=0, color="black", linestyle="-", linewidth=0.5)
netload_RA.loc[year].plot(ax=ax, label="netload_RA", linewidth=2, color="orange")
#ax.axhline(y=netload_constructed.loc[year].values.mean(), color="orange", linestyle="--", linewidth=0.5, label=f"{netload_constructed.loc[year].values.mean():.2f}")
plt.legend()
plt.show()

for year in range(1980,2020):
    fig, ax = plt.subplots(figsize=(10, 5))
    netload.loc[year].plot(ax=ax, label="netload", linewidth=0.5, color="blue")
    ax.axhline(y=netload.loc[year].values.mean(), color="blue", linestyle="--", linewidth=0.5, label=f"{netload.loc[year].values.mean():.2f}")
    netload_RA.loc[year].plot(ax=ax, label="netload_RA", linewidth=0.5, color="orange")
    #ax.axhline(y=netload_constructed.loc[year].values.mean(), color="orange", linestyle="--", linewidth=0.5, label=f"{netload_constructed.loc[year].values.mean():.2f}")
    plt.legend()
    plt.show()
    sleep(1)
