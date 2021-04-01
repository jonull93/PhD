import pickle
import time
import numpy as np
import pandas as pd
import xlsxwriter

starttime = time.time()
foo = open(r"C:\git\multinode\Include\load_profile_ref.INC", "r")
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
print(daily_max["Ireland"][:4],hourly_daily_max["Ireland"][:55])
daily_demand_peak = pd.DataFrame({i: hourly_daily_max[i] for i in countries},
                                 index=["h" + str(i).zfill(4) for i in range(1, 8785)])
with pd.ExcelWriter(r"C:\git\multinode\Add-ons\PS\include\daily_demand_peak.xlsx") as writer:
    daily_demand_peak.to_excel(writer)

exit()
# ------------

# ramp = wind_ramp.copy()
# ramp["PV_cSiOPT"]=solar_ramp["SE2"]
demand_ramp_dict = {c: [] for c in countries}
for c in countries:
    for ind, load in enumerate(profile[c]):
        if ind == 0:
            first = 0
        else:
            first = abs(profile[c][ind - 1] - profile[c][ind])
        try:
            second = abs(profile[c][ind] - profile[c][ind + 1])
        except:
            second = 0
        demand_ramp_dict[c].append(max(first, second))

demand_ramp = pd.DataFrame({country_code[i]: demand_ramp_dict[i] for i in country_code},
                           index=["h" + str(i).zfill(4) for i in range(1, 8785)])
for c in demand_ramp:
    demand_ramp[c] = demand_ramp[c].clip(lower=np.median(demand_ramp[c]))

print("== Finished making the demand ramp profiles after " + str(round(time.time() - starttime)) + " s ==")

# ----------
if False:
    """wind_ramp={}
    #for c in i_reg: 
    #    wind_ramp[c] = pd.read_excel(r'Z:\models\Include\wind_profile_'+c+'.xlsx', sheet_name="profile_2012", usecols="A,Z:AK")
    #    wind_ramp[c] = wind_ramp[c].fillna(0) 
    foo = open("Z:\\models\\Include\\class_profiles_h_2012.inc","r")
    wind_profile = {i:{} for i in i_reg}
    for i in foo.readlines(): 
        reg,_,tech,_,h,val = i.split() #due to formatting in .inc, the order will be [I_reg, ., tech, ., timestep, value]
        if reg in i_reg:
            if tech in wind_profile[reg]:
                wind_profile[reg][tech].append(val)
            else:
                wind_profile[reg][tech] = [val]

    foo.close()
    wind_ramp = {}
    for i in i_reg: 
        wind_ramp[i] = pd.DataFrame(data = wind_profile[i], index=["h"+str(i).zfill(4) for i in range(1,8785)])

    #pickle.dump(wind_ramp,open("wind_ramp.pickle","wb"))"""
    wind_ramp = pickle.load(open("wind_ramp.pickle", "rb"))

    wind_copy = {i: wind_ramp[i].copy() for i in wind_ramp}
    for c in wind_ramp:
        # wind_ramp[c].columns = ["WON"+str(i) for i in range(1,13)]
        for col in wind_ramp[c].columns:
            for row in range(8784):
                try:
                    a = abs(wind_copy[c].ix[row, col] - wind_copy[c].ix[row + 1, col])
                except:
                    a = 0
                if row > 0:
                    b = abs(float(wind_copy[c].ix[row - 1, col]) - float(wind_copy[c].ix[row, col]))
                else:
                    b = 0
                wind_ramp[c].ix[row, col] = max(a, b)

    for c in wind_ramp:
        for i in range(1, len(wind_ramp[c].columns)):
            if wind_ramp[c].iloc[1, len(wind_ramp[c].columns) - i] > 0:
                wind_ramp[c]["WOFF"] = wind_ramp[c].iloc[:, len(wind_ramp[c].columns) - i]
                break

    # wb = Workbook()
    # ws = wb.active
    wb = xlsxwriter.Workbook(r"Z:\models\Include\wind_ramp.xlsx")
    ws = wb.add_worksheet()
    r = 0
    for idx1, c in enumerate(i_reg):
        # noinspection PyUnreachableCode
        for idx2, tech in enumerate([i for i in wind_ramp[c] if sum(wind_ramp[c][i]) > 0]):
            for idx3, val in enumerate(wind_ramp[c][tech]):
                ws.write(r, 0, c)
                ws.write(r, 1, ".")
                ws.write(r, 2, tech)
                ws.write(r, 3, ".")
                ws.write(r, 4, wind_ramp[c][tech].index[idx3])
                ws.write(r, 5, val)
                r += 1
            # print(idx1,idx2,r)

    # wb.save("wind_ramp.xlsx")
    wb.close()
    print("== Finished making the wind ramp profiles after " + str(round(time.time() - starttime)) + " s ==")
# -----------
# solar_ramp = {region:pd.read_excel(r'C:\Users\jonull\Box\python\profiles.xlsx', sheet_name=region).transpose() for region in i_reg}
# for region in solar_ramp:
#    solar_ramp[region].drop(columns=[i for i in solar_ramp[region] if "PV_" not in i], inplace=True)
#    #solar_ramp[c] = solar_ramp[c]["PV_cSiOPT"]
#    solar_ramp[region] = solar_ramp[region].fillna(0)

# pickle.dump(solar_ramp,open("solar_profiles.pickle","wb"))

solar_ramp = pickle.load(open("solar_profiles.pickle", "rb"))
solar_copy = {region: solar_ramp[region].copy() for region in solar_ramp}

for region in solar_copy.keys():
    for idx1, tech in enumerate(solar_copy[region]):
        for idx2, val in enumerate(solar_copy[region][tech]):
            try:
                a = abs(solar_copy[region][tech][idx2] - solar_copy[region][tech][idx2 - 1])
            except Exception as e:
                a = 0
                print(e)
            try:
                b = abs(solar_copy[region][tech][idx2] - solar_copy[region][tech][idx2 + 1])
            except:
                b = 0
            solar_ramp[region][tech][idx2] = max(a, b, solar_copy[region][tech][idx2] * 0.3)

wb = xlsxwriter.Workbook(r"Z:\models\Include\solar_ramp.xlsx")
ws = wb.add_worksheet()
r = 0
for idx1, c in enumerate(i_reg):
    for idx2, tech in enumerate(solar_ramp[c]):
        for idx3, val in enumerate(solar_ramp[c][tech]):
            ws.write(r, 0, c)
            ws.write(r, 1, ".")
            ws.write(r, 2, tech)
            ws.write(r, 3, ".")
            ws.write(r, 4, solar_ramp[c][tech].index[idx3])
            ws.write(r, 5, val)
            r += 1
        # print(idx1,idx2,r)

wb.close()
print("== Finished making the solar ramp profiles after " + str(round(time.time() - starttime)) + " s ==")

ramp = {"wind": wind_ramp, "solar": solar_ramp, "demand": demand_ramp}
pickle.dump(ramp, open("data_ramp2.pickle", "wb"))

with pd.ExcelWriter(r"Z:\models\Include\demand_ramp.xlsx") as writer:
    # for c in wind
    # wind_ramp.to_excel(writer, sheet_name='wind_ramp')
    # for idx,c in enumerate(i_reg):
    #    solar_ramp[c].to_excel(writer, sheet_name='solar_ramp_'+c)
    demand_ramp.to_excel(writer)
# ramp.to_excel(r"Z:\models\Include\ramp.xlsx")
