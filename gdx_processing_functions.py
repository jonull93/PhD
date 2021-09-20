import pickle  # for dumping and loading variable to/from file
import threading
import time as tm
import traceback
from traceback import format_exc
from datetime import datetime
import gdxr
import pandas as pd
import numpy as np

from get_from_gams_db import gdx
from copy import copy
from my_utils import TECH, order_map_cap, order_map_gen


def print_gen(writer, sheet, df, gamsTimestep):
    global scen_row
    df["sort_by"] = df.index.get_level_values(0).map(order_map_gen)
    df.sort_values("sort_by", inplace=True)
    df.drop(columns="sort_by", inplace= True)
    df = df.reorder_levels(["I_reg", "tech"]).sort_index(level=0, sort_remaining=False)
    df.to_excel(writer, sheet_name=sheet, freeze_panes=(0, 2), startrow=scen_row, startcol=1)
    scen_row += len(df.index)+1


def print_df(writer, df, name, sheet, col=3, header=True, row_inc=1):
    global scen_row
    length = 0
    if type(df.index) == pd.core.indexes.base.Index:
        length = 1
    elif type(df.index) == pd.core.indexes.multi.MultiIndex:
        length = min(len(df.index.levels), 2)
    worksheet = writer.sheets[sheet]
    worksheet.column_dimensions["A"].width = 14
    df.to_excel(writer, sheet_name=sheet, header=header, startrow=scen_row, startcol=col-length)
    cell = worksheet.cell(scen_row+1, 1, name)
    alignment = copy(cell.alignment)
    alignment.wrapText = True
    cell.alignment = alignment
    if len(df.index) > 1: worksheet.merge_cells(f"A{scen_row+1}:A{scen_row + len(df.index)+header}")
    scen_row += len(df.index)+row_inc


def print_num(writer, num, sheet, row, col, ind):
    if not ind:
        num_df = pd.DataFrame(num)  # columns = ["System cost:"]
        num_df.to_excel(writer, sheet_name=sheet, index=False, header=False, startcol=col, startrow=row)
    else:
        num_df = pd.DataFrame(data=num, index=ind)  # columns = ["System cost:"]
        num_df.to_excel(writer, sheet_name=sheet, startcol=col, startrow=row)


def print_cap(writer, num, sheet, row, col, ind):
    num_df = pd.DataFrame(data=num, index=ind).T  # columns = ["System cost:"]
    num_df.to_excel(writer, sheet_name=sheet, startcol=col, startrow=row)


def run_case(scen_name, data, gdxpath, indicators):
    def get_from_cap(tech_name, round=False):
        try:
            if round:
                foo = tot_cap.loc[tech_name].sum().round(decimals=round)
            else:
                foo = tot_cap.loc[tech_name].sum()
        except KeyError:
            foo = 0
        return foo

    k = scen_name
    global newdata
    # flywheel,
    # sync_cond,
    # bat,
    # FC',
    # H2store
    # el_tot,
    region = k.split("_")[0]
    with gdxr.GdxFile(gdxpath + k + ".gdx") as f:
        before = [i for i in locals().keys()]  # variables defined before this line do not get pickled
        gamsTimestep = gdx(f, "timestep")
        I_reg = gdx(f, "i_reg")
        curtailment_profiles = gdx(f, "o_curtailment_hourly")
        curtailment_profiles.fillna(0, inplace=True)
        curtailment_profiles[curtailment_profiles < 0] = 0
        curtailment_profile_total = gdx(f, "o_curtailment_hourly_total")
        curtailment = gdx(f, "o_curtailment_total")
        curtailment_regional = gdx(f, "o_curtailment_regional")
        curtailment_wind = gdx(f, "o_curtailment_wind")
        curtailment_PV = gdx(f, "o_curtailment_PV")
        gen_share = gdx(f, "o_new_share_gen").rename("Share")
        VRE_share = gdx(f, "o_VRE_share")
        VRE_share_total = gdx(f, "o_VRE_share_total")
        wind_share = gdx(f, "o_VRE_share")
        PV_share = gdx(f, "o_VRE_share")
        tot_cap = gdx(f, "o_capacity")
        new_cap = gdx(f, "v_newcap")
        for reg in new_cap.index.unique(1):
            if reg not in I_reg:
                new_cap.drop(reg, level="I_reg", inplace=True)
        for index, vals in new_cap.iterrows():
            if 0 < vals.upper == vals.level:
                print(" ! ! Found capped investment at",index)
        gen = gdx(f, "o_generation")
        el_price = gdx(f, "o_el_cost")
        load_profile = gdx(f, "demandprofile_average")
        net_load = gdx(f, "o_net_load")
        gams_timestep = gdx(f, "timestep")  # "h0001" or "d001a"
        iter_t = range(len(gams_timestep))
        timestep = [i + 1 for i in iter_t]  # 1
        TT = 8760 / len(gams_timestep)
        allwind = gdx(f, "timestep")
        cost_tot = gdx(f, "v_totcost").level
        allthermal = gdx(f, "allthermal")
        allstorage = gdx(f, "allwind")
        withdrawal_rate = gdx(f, "withdrawal_rate")
        FLH = gdx(f, "o_full_load_hours").rename("FLH")
        FLH_regional = gdx(f, "o_full_load_hours_regional").rename("FLH_regional")
        PV_FLH = gdx(f, "o_full_load_PV")
        wind_FLH = gdx(f, "o_full_load_wind")
        el_price = gdx(f, "o_el_cost")
        discharge = gdx(f, "v_discharge")
        charge = gdx(f, "v_charge")
        demand = gdx(f, "o_load")
        inv_cost = gdx(f, "inv_cost")
        try:
            ESS_available = gdx(f, "o_PS_ESS_available")
            inertia_available = gdx(f, "o_PS_inertia_available")
            inertia_available_thermals = gdx(f, "o_PS_inertia_thermal")
            inertia_available_wind = gdx(f, "o_PS_inertia_wind")
            inertia_available_PTH = gdx(f, "o_PS_inertia_PTH")
            inertia_available_BEV = gdx(f, "o_PS_inertia_BEV")
            inertia_demand = gdx(f, "PS_Nminus1")
            OR_demand_VRE = gdx(f, "o_PS_OR_demand_VRE")
            OR_demand_other = gdx(f, "PS_OR_min")
            OR_available = gdx(f, "o_PS_OR_available")
            OR_deficiency = gdx(f, "v_PS_OR_deficiency").level
            OR_available_thermal = gdx(f, "o_PS_OR_available_thermal")
            OR_net_import = gdx(f, "o_PS_OR_net_import")
            OR_cost = gdx(f, "o_PS_OR_cost")
            OR_demand = {"wind": OR_demand_VRE.filter(like="WO", axis=0).groupby(level=[1]).sum(),
                         "PV": OR_demand_VRE.filter(like="PV", axis=0).groupby(level=[1]).sum(),
                         "other": OR_demand_other,
                         "total": OR_demand_VRE.groupby(level=[1]).sum() + OR_demand_other.fillna(0)
                         }
            PS = True
        except Exception as e:
            PS = False
            print("%ancillary_services% was not activated for", k, "because:")
            print(format_exc())

    flywheel = get_from_cap(TECH.FLYWHEEL)
    sync_cond = get_from_cap(TECH.SYNCHRONOUS_CONDENSER)
    FC = get_from_cap(TECH.FUEL_CELL)
    H2store = get_from_cap(TECH.H2_STORAGE)
    EB = get_from_cap(TECH.ELECTRIC_BOILER)
    HP = get_from_cap(TECH.HEAT_PUMP)
    G = get_from_cap(TECH.GAS)
    try: bat = tot_cap.loc[TECH.BATTERY].sum().round(decimals=2).astype(str) + " / " \
          + tot_cap.loc[TECH.BATTERY_CAP].sum().round(decimals=2).astype(str)
    except KeyError: bat = 0

    after = locals().keys()
    to_save = [i for i in after if i not in before]
    for i in indicators:
        if i not in to_save:
            print(i, "from Indicators is not currently captured! ~~")
    new_data = {}
    for variable in to_save:
        try:
            new_data[variable] = eval(variable)
        except:
            print("Could not save", i, "to new_data in case", k)

    return True, new_data


def excel(scen:str, data, row, writer, indicators):
    global scen_row
    scen_row = 0
    cap = data["tot_cap"].rename("Cap").round(decimals=3)
    cap = cap[cap!=0]
    new_cap = data["new_cap"].level.rename("New cap").round(decimals=3)
    new_cap = new_cap[new_cap != 0]  # filter out technologies which aren't going to be the there for cap/share/FLH
    FLH = data["FLH"].astype(int)
    FLH_regional = data["FLH_regional"].astype(int)
    share = data["gen_share"].round(decimals=3)
    gen = data["gen"]
    try:
        if "electrolyser" in gen.index.unique(level="tech"):
            gen = gen.drop("electrolyser", level="tech")
    except KeyError:
        print(f"! Could not find tech in gen.index, {scen} probably failed the gams run.")
        return
    for i, scen_part in enumerate(scen.split('_')):  # split up the scenario name on _s
        print_num(writer, [scen_part], "Indicators", row + 1, i, 0)
    c = i+1

    for indicator in indicators:
        # print(data[k][i])
        print_num(writer, [indicator], "Indicators", 0, c, 0)
        thing = data[indicator]
        ind_type = type(thing)
        if isinstance([], ind_type):
            print_num(writer, thing, "Indicators", row + 1, c, 0)
        elif ind_type in [type(1.), type(3), type(''), np.float64]:
            print_num(writer, [thing], "Indicators", row + 1, c, 0)
        elif ind_type == pd.core.series.Series:
            try: print_num(writer, [thing.sum()], "Indicators", row + 1, c, 0)
            except: print(f"Failed to print {indicator} to excel!")
        else:
            print(f"some weird variable type ({str(indicator)}: {ind_type}) entered the excel-printing loop")
            if isinstance({}, ind_type): print(thing.keys())
        c += 1

    cap_len = len(cap.index.get_level_values(0).unique())+1
    reg_len = len(cap.index.get_level_values(1).unique())+1
    try: cappy = cap.to_frame(name="Cap").join(new_cap).join(share).join(FLH_regional)
    except: print(cap,new_cap,share,FLH_regional)
    cappy["sort_by"] = cappy.index.get_level_values(0).map(order_map_cap)
    cappy.sort_values("sort_by", inplace=True)
    cappy.drop(columns="sort_by", inplace=True)
    cappy = cappy.reorder_levels(["I_reg", "tech"]).sort_index(level=0, sort_remaining=False)
    cappy.groupby(level=[1]).sum().to_excel(writer, sheet_name=scen, startcol=1, startrow=1)
    for i, reg in enumerate(cappy.index.get_level_values(0).unique()):
        cappy.filter(like=reg,axis=0).to_excel(writer, sheet_name=scen, startcol=7+6*i, startrow=1)
    scen_row += cap_len+2
    print_df(writer, data["curtailment_profile_total"].round(decimals=3), "Curtailment", scen)
    print_df(writer, data["el_price"].round(decimals=3), "Elec. price", scen, row_inc=2)

    print_gen(writer, scen, gen, data["gamsTimestep"])

    if data["PS"]:
        try: print_df(writer, data["OR_cost"].round(decimals=3), "OR: Cost", scen, row_inc=2)
        except IndexError: print(scen, data["OR_cost"])
        print_df(writer, data["OR_available"].round(decimals=3), "OR: Available", scen, header=False)
        print_df(writer, data["OR_deficiency"].round(decimals=2), "OR: Deficiency", scen, header=False)
        print_df(writer, data["OR_net_import"].round(decimals=3), "OR: Net-import", scen, header=False)
        print_df(writer, data["OR_demand"]["wind"].round(decimals=3), "OR demand: Wind", scen, header=True)
        print_df(writer, data["OR_demand"]["PV"].round(decimals=3), "OR demand: PV", scen, header=True)
        print_df(writer, data["OR_demand"]["other"].round(decimals=3), "OR demand: Other", scen, header=True)
        print_df(writer, data["OR_demand"]["total"].round(decimals=3), "OR demand: Total", scen, header=True, row_inc=2)
        print_df(writer, data["inertia_available"].round(decimals=3), "Inertia: Available", scen, header=True)
        print_df(writer, data["inertia_available_thermals"].round(decimals=3), "Inertia: Thermals", scen, header=True, row_inc=2)
    else:
        print("PS variables were not available for", scen)