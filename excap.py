import pickle
import time
import gdxpds
#gdxpds.load_gdxcc('C:\\GAMS\\win64\\31.1\\')
import numpy as np
import pandas as pd
from openpyxl import load_workbook

# NOTE: gdxpds.to_gdx() seems finicky and does not seem to work on all python-gams setups
# That particular issue results in "RuntimeError: Unable to locate your GAMS directory"
# regardless of the gams_dir parameter


starttime = time.time()
ratio_OCGT_over_CCGT = 26550/165417  # from a spreadsheet sent to Jonathan by Jan on 8/feb/21

excap_path = r"excap.xlsx"
new_file = r"excap_slim.xlsx"
modelpath = r"C:\models\multinode\Include\regional\excap.gdx"

nuts_df = pd.read_excel(excap_path,
                        sheet_name="nuts",
                        header=0,  # column name
                        index_col=None  # simple numeric index
                        )
nuts2 = nuts_df.transpose().values.tolist()[0]
numbers = nuts_df.transpose().values.tolist()[1]
nuts2_to_EPOD = pickle.load(open("PickleJar/nuts2_to_EPOD.pickle", "rb"))
number_to_nuts = {}
nuts_to_numbers = {}
for i in range(len(nuts2)):
    number_to_nuts[numbers[i]] = nuts2[i]
    nuts_to_numbers[nuts2[i]] = numbers[i]
EPOD_to_numbers = {
    EPOD: [num for num in numbers if
           number_to_nuts[num] in nuts2_to_EPOD and nuts2_to_EPOD[number_to_nuts[num]] == EPOD] for EPOD
    in np.unique(list(nuts2_to_EPOD.values()))}
units_df = pd.read_excel(excap_path,
                         sheet_name="units",
                         header=[0],  # column name
                         index_col=[0]  # simple numeric index
                         )
# first, lets clean up the data a bit
units_df["nuts2"] = units_df["nutsnumber"].map(number_to_nuts)
units_df.fillna(0)  # make missing values into 0
units_df.drop(units_df[units_df.capacity_el == 0].index, inplace=True)  # remove units with no elec cap
# if there is no "real" decommission date, use the one based on normal lifespans:
units_df["decom_db"] = np.where(units_df["decom_db"] == 0, units_df["decommission"], units_df["decom_db"])

foo = {1: "b", 2: "H", 3: "G", 4: "O", 5: "P", 6: "W", 7: "WA", 8: "U", 17: "HW", 18: "BW", 19: "GWG", 30: "WG"}
fuel_no = {i: j for i, j in foo.items()}
for i, j in foo.items():
    fuel_no[j] = i
fuel_no["G_peak"] = 3
fuel_no["WG_peak"] = 30
plant_types = list(foo.values()) + [foo[i] + "_CHP" for i in range(1, 8)] + ["G_peak", "WG_peak"]
nuts2agg = pd.DataFrame(index=pd.MultiIndex.from_tuples([(i, j) for i in nuts2 for j in plant_types]),
                        columns=["capacity_el", "capacity_heat", "eta_el", "eta_tot"])
EPODagg = pd.DataFrame(
    index=pd.MultiIndex.from_tuples([(i, j) for i in np.unique(list(nuts2_to_EPOD.values())) for j in plant_types]),
    columns=["capacity_el", "capacity_heat", "eta_el", "eta_tot"])

y1 = 2015
y2 = 2050
dy = 1  # can be set to 1 for hard cutoffs instead of smoothed end-of-life capacities
# if smoothed, each year will represent an interval
# e.g. 2030 = (2028 -> 2032), 2035 = (2033 -> 2037)
# and plants which expire inside an interval get averaged out according to time spent in the interval
# e.g. a plant expiring 2029 would count for 2 out of 5 years in the 2030 example above and thus give 0.4 of its capacity
years = [i for i in
         range(y1, y2 + 1, 5)]  # this can be set independently of dy, but dy should not be larger than y(i)-y(i-1)
agg = {i: EPODagg.copy() for i in years}


def punish_fun(df, y1, y2):  #
    foo = np.where(df["decom_db"] < y1, df["capacity_el"], 0)
    foo = np.where((df["decom_db"] <= y2) & (df["decom_db"] >= y1),
                   df["capacity_el"] * (y2 - df[(df["decom_db"] <= y2) & (df["decom_db"] >= y1)]["decom_db"]) / (
                               y2 - y1), foo)
    return foo


def adjusted_cap(df, y1, y2, col):
    foo = np.where(df["decom_db"] > y2, df[col], 0)
    if y2 > y1:  # to avoid dividing by zero (or: The Story of the Missing Data - June 2021)
        bar = np.where((df["decom_db"] <= y2) & (df["decom_db"] >= y1),
                   df[col] * (df[(df["decom_db"] <= y2) & (df["decom_db"] >= y1)]["decom_db"] - y1) / (y2 - y1), foo)
    else:
        bar = foo
    # out = sum(bar)
    # print(df,"\n",out,f"{y1}->{y2}")
    return bar


def adjusted_eta(df, y1, y2, col, bar):
    foo = np.average(df[df["eta_el"] != 0]["eta_el"], weights=df[df["eta_el"] != 0]["capacity_el"])
    bar = np.where((df["decom_db"] <= y2) & (df["decom_db"] >= y1),
                   df[col] * (df[(df["decom_db"] <= y2) & (df["decom_db"] >= y1)]["decom_db"] - y1) / (y2 - y1), foo)
    out = sum(bar)
    # print(df,"\n",out,f"{y1}->{y2}")
    return out


def combined_agg_data(df, y1, y2, CHP):
    el = adjusted_cap(df, y1, y2, "capacity_el")
    if len(el) > 0:
        try:
            eta_el = np.average(df[df["eta_el"] > 0]["eta_el"], weights=el[df["eta_el"] > 0])
        except:
            eta_el = 0
        # if eta_el == 0 and sum(el) > 0: print("== OBS: CAPACITY WITHOUT ELEC EFFICIENCY in ==\n",df[["fuel_no", "nuts2", "capacity_el"]])
        try:
            eta_tot = np.average(df[df["eta_tot"] != 0]["eta_tot"], weights=el[df["eta_tot"] != 0])
        except:
            # if sum(el) > 0: print("== OBS: CAPACITY WITHOUT TOTAL EFFICIENCY in ==\n", df[["fuel_no", "nuts2"]])
            eta_tot = 0
    else:
        eta_el = 0
        eta_tot = 0
    if not CHP:
        heat = [0]
    else:
        heat = adjusted_cap(df, y1, y2, "capacity_heat")
    el = np.where(np.isnan(el), 0, el)
    heat = np.where(np.isnan(heat), 0, heat)
    return sum(el), sum(heat), eta_el, eta_tot


punish = {i: punish_fun(units_df, np.ceil(i - (dy - 1) / 2), np.ceil(i + (dy - 1) / 2)) for i in years}
for row in EPODagg.itertuples():
    EPOD, plant = row[0]
    if "CHP" in plant:
        plant_type = [2]
    else:
        plant_type = [1, 3]
    correct_nut = units_df["nutsnumber"].isin(EPOD_to_numbers[EPOD])

    df = units_df[(correct_nut) & (units_df["plant_type_db"].isin(plant_type)) & (
            units_df["fuel_no"] == fuel_no[plant.replace("_CHP", "")]) & (
                          units_df["capacity_heat"] / units_df["capacity_el"] < 4) & (
                          ((0 < units_df["eta_tot"]) & (units_df["eta_tot"] < 0.41)) == ("peak" in plant or "U" in plant)
                  )]
    if "UK1" in EPOD and "G" in plant:
        print(f"Here's the df of {plant} in UK1:\n", df[["commission","capacity_el","eta_el"]])
        print(f"its summed capacity is {df['capacity_el'].sum()} ")
    for i in years:
        y1 = np.ceil(i - (dy - 1) / 2)
        y2 = np.ceil(i + (dy - 1) / 2)
        el, heat, eta_el, eta_tot = combined_agg_data(df, y1, y2, "CHP" in plant)
        if EPOD == "UK1" and "G" in plant and df['capacity_el'].sum()>0: print(f"! year {i}: {el}, {eta_el}")

        #try: int(el)
        #except ValueError: print("found nan in i",EPOD,plant,i)
        if plant == "G_peak":
            agg[i].at[(EPOD, plant), "capacity_el"] = agg[i].at[(EPOD, "G"), "capacity_el"] * ratio_OCGT_over_CCGT
            agg[i].at[(EPOD, plant), "capacity_heat"] = 0
            agg[i].at[(EPOD, plant), "eta_el"] = 0.4
            agg[i].at[(EPOD, plant), "eta_tot"] = 0.4
        else:
            agg[i].at[(EPOD, plant), "capacity_el"] = el / 1000 * (1 - ratio_OCGT_over_CCGT*(plant == "G"))
            agg[i].at[(EPOD, plant), "capacity_heat"] = heat / 1000
            agg[i].at[(EPOD, plant), "eta_el"] = eta_el
            agg[i].at[(EPOD, plant), "eta_tot"] = eta_tot
        # agg[i].at[(EPOD, plant),"capacity_el"] = adjusted_cap(df,y1,y2,"capacity_el")
        # print(EPOD,plant,i,f"({y1}-{y2})", agg[i].loc[EPOD, plant]["capacity_el"])
        # if "CHP" in plant: agg[i].at[(EPOD, plant),"capacity_heat"] = adjusted_cap(df,y1,y2,"capacity_heat")

    if df[df["eta_el"] != 0]["capacity_el"].sum() > 0:
        EPODagg.loc[EPOD, plant]["eta_el"] = np.average(df[df["eta_el"] != 0]["eta_el"],
                                                        weights=df[df["eta_el"] != 0]["capacity_el"])
    else:
        EPODagg.loc[EPOD, plant]["eta_el"] = np.NaN

    if df[df["eta_tot"] != 0]["capacity_el"].sum() > 0:
        EPODagg.loc[EPOD, plant]["eta_tot"] = np.average(df[df["eta_tot"] != 0]["eta_tot"],
                                                         weights=df[df["eta_tot"] != 0]["capacity_el"] +
                                                                 df[df["eta_tot"] != 0][
                                                                     "capacity_heat"])
    else:
        EPODagg.loc[EPOD, plant]["eta_tot"] = np.NaN

for y in agg:
    df = agg[y]
    for row in df[(df["capacity_el"] > 0) & (df["eta_tot"] == 0)].itertuples():
        EPOD, plant = row[0]
        # print(EPOD,plant,row,row["eta_tot"])
        if "CHP" not in plant and row[3] != 0:
            df.loc[EPOD, plant]["eta_tot"] = row[3]
            print("Filled missing eta_tot with eta_el in", EPOD, plant)
        else:
            print(f"~~ Missing efficiency unaccounted for in {EPOD}: {plant}!! ~~")

pickle.dump({1:units_df, 2: EPODagg}, open("PickleJar\\exCap_unitsDF.pickle", "wb"))
writer = pd.ExcelWriter(new_file, engine='openpyxl')
try:
    writer.book = load_workbook(new_file)
    writer.sheets = dict((ws.title, ws) for ws in writer.book.worksheets)
except:
    None
# EPODagg.to_excel(writer,sheet_name="by_EPOD")
for y in agg:
    agg[y].fillna(0, inplace=True)
    agg[y].to_excel(writer, sheet_name=f"{y}_d{dy}")

# CHP_units.drop(columns=["location_no",'capacity_boiler','latitude', 'longitude', 'nutsnumber']).to_excel(writer,sheet_name="CHP")
# power_units.drop(columns=["location_no",'capacity_boiler','latitude', 'longitude', 'nutsnumber']).to_excel(writer,sheet_name="power")
writer.save()
# df1 = pd.DataFrame(data=agg[2030]["capacity_el"]).reset_index()
df_capEl = pd.DataFrame(columns=["tech", "EPODreg", "year", "value"])
df_capHeat = pd.DataFrame(columns=["tech", "EPODreg", "year", "value"])
df_etaEl = pd.DataFrame(columns=["tech", "EPODreg", "year", "value"])
df_etaTot = pd.DataFrame(columns=["tech", "EPODreg", "year", "value"])
for y in years:
    agg[y]["year"] = y
    df1 = pd.DataFrame(data=agg[y][["year", "capacity_el"]]).reset_index()
    df1.columns = ["EPODreg", "tech", "year", "value"]
    df1 = df1[["tech", "EPODreg", "year", "value"]]
    df_capEl = df_capEl.append(df1, ignore_index=True)

    df1 = pd.DataFrame(data=agg[y][["year", "capacity_heat"]]).reset_index()
    df1.columns = ["EPODreg", "tech", "year", "value"]
    df1 = df1[["tech", "EPODreg", "year", "value"]]
    df_capHeat = df_capHeat.append(df1, ignore_index=True)

    df1 = pd.DataFrame(data=agg[y][["year", "eta_el"]]).reset_index()
    df1.columns = ["EPODreg", "tech", "year", "value"]
    df1 = df1[["tech", "EPODreg", "year", "value"]]
    df_etaEl = df_etaEl.append(df1, ignore_index=True)

    df1 = pd.DataFrame(data=agg[y][["year", "eta_tot"]]).reset_index()
    df1.columns = ["EPODreg", "tech", "year", "value"]
    df1 = df1[["tech", "EPODreg", "year", "value"]]
    df_etaTot = df_etaTot.append(df1, ignore_index=True)

gdxpds.write_gdx.to_gdx({"realCap": df_capEl, "realCap_heat": df_capHeat, "realCap_etaEl": df_etaEl, "realCap_etaTot": df_etaTot},
              path=modelpath, gams_dir='C:\\GAMS\\win64\\30.1\\')

print("Finished running excap.py after", round(time.time() - starttime), "seconds.")
