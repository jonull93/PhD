import pickle
import time
import numpy as np
import pandas as pd
import xlsxwriter
from my_utils import write_inc

starttime = time.time()
foo = open(r"C:\git\multinode\Include\load_profile_ref.INC", "r")

PS_path = 'C:\\git\\multinode\\Add-ons\\PS\\include\\'
lines = foo.readlines()
for i in lines:
    if "Austr" in i:  # skip lines until we're actually at the data, which starts with countries and includes Austria
        countries = i.split()
        # print(len(countries))
        profile = {x: [] for x in countries}
        start = True
        continue
    if 'start' in locals() and "h" in i[0]:
        for idx, c in enumerate(countries):
            # print(idx)
            profile[c].append(float(i.split()[idx + 1]))

foo.close()

hourly_daily_max = {c: [] for c in countries}
daily_max = {c: [] for c in countries}
for c in countries:
    n = 0
    while n < len(profile[c]):
        daily_max[c].append(max([profile[c][n + i] for i in range(0, 24)]))
        # print([n+i for i in range(24)])
        n += 24
    for i in range(len(profile[c])):
        day = int(np.floor(i / 24))
        hourly_daily_max[c].append(daily_max[c][day])
#print(daily_max["Ireland"][:4],hourly_daily_max["Ireland"][:55])
daily_demand_peak = pd.DataFrame({i: hourly_daily_max[i] for i in countries},
                                 index=["h" + str(i).zfill(4) for i in range(1, 8785)])
with pd.ExcelWriter(PS_path+"daily_demand_peak.xlsx") as writer:
    daily_demand_peak.to_excel(writer)

write_inc(PS_path, "daily_demand_peak.inc", hourly_daily_max)
