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

    def try_sum(df, level="FR_period", FR_cost=False):
        if type(FR_cost) != bool:
            try:
                foo = (df * FR_cost).sum().sum()
            except:
                foo = 0
        else:
            try:
                foo = df.sum(axis=1).sum(level=level)
            except ValueError:
                foo = 0
            except Exception as e:
                foo = 0
                print("! Failed to sum, ", type(e), e)
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
    year = k.split("_")[3]
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
        gen_per_eltech = gdx(f, "o_generation_el")
        el_price = gdx(f, "o_el_cost")
        load_profile = gdx(f, "demandprofile_average")
        net_load = gdx(f, "o_net_load")
        gams_timestep = gdx(f, "timestep")  # "h0001" or "d001a"
        iter_t = range(len(gams_timestep))
        timestep = [i + 1 for i in iter_t]  # 1
        TT = 8760 / len(gams_timestep)
        allwind = gdx(f, "timestep")
        cost_tot = gdx(f, "o_cost_total_oldinv", silent=False)
        if True:  # this whole thing should become redundant as new runs are made and the line above returns the actual value
            cost_tot2 = gdx(f, "v_totcost").level
            previous_investments = gdx(f, "previous_investments_yearly")
            annuity = gdx(f, "annuity")
            inv_cost = gdx(f, "inv_cost")
            techprop = gdx(f, "techprop")
            OM_fix = techprop[:, "OM_fix"]
            try:
                for ind, preInv in previous_investments.items():
                    _tech = ind[0]
                    _region = ind[1]
                    _year = ind[2]
                    cost_tot2 += preInv*annuity[_tech]*inv_cost[(_tech, _year)]/1000
                    try: cost_tot2 += preInv * OM_fix[_tech] / 1000
                    except KeyError:
                        if _tech not in ["EB", "bat"]: print("Unexpectedly failed to add OM_fix for", _tech)
            except Exception as e:
                print(f"!! failed because {e}")
                print(previous_investments)
                raise Exception

        cost_tot_onlynew = gdx(f, "v_totcost").level
        if round(cost_tot, 3) != round(cost_tot2, 3):
            print(f"- Discrepancy when adding previousInvestments in {scen_name}: from {round(cost_tot_onlynew, 5)} to {round(cost_tot, 5)} (or {round(cost_tot2,5)})")
            if cost_tot > cost_tot2+1 and "fullFC" in scen_name:
                cost_tot = cost_tot2
                print("Replacing value - cost_tot is now",cost_tot)
        cost_partload = gdx(f, "o_cost_partload")
        cost_flexlim = gdx(f, "o_cost_flexlim")
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
            FR_demand_VRE = gdx(f, "o_PS_FR_demand_VRE")
            FR_demand_other = gdx(f, "PS_FR_min")
            FR_available = gdx(f, "o_PS_FR_available")
            try: FR_deficiency = gdx(f, "v_PS_FR_deficiency").level
            except AttributeError: FR_deficiency = gdx(f, "v_PS_OR_deficiency").level
            try: FR_cost = gdx(f, "EQU_PS_FR_loadbalance").marginal.clip(upper=0)*-1e6/TT
            except AttributeError: FR_cost = gdx(f, "EQU_PS_FR_supply").marginal.clip(upper=0) * -1e6 / TT
            try:
                if FR_cost.sum().sum() > 0: print("FR cost in ", k, "=", round(FR_cost.sum().sum()))
                elif "lowFlex" in k and "fullFC" in k:
                    print("!! Missing non-zero FR_cost in", k)
            except:
                if "lowFlex" in k and "fullFC" in k:
                    print("!! Missing non-zero FR_cost in",k)
            FR_period_cost = gdx(f, "o_PS_FR_cost_perPeriod")
            FR_FFR_cost_share = gdx(f, "o_PS_FR_cost_FFRshare")
            FR_available_thermal = gdx(f, "o_PS_FR_available_thermal")
            FR_summed_thermal = try_sum(FR_available_thermal)
            FR_available_ESS = gdx(f, "o_PS_FR_available_ESS")
            FR_summed_ESS = try_sum(FR_available_ESS)
            FR_available_BEV = gdx(f, "o_PS_FR_available_BEV")
            FR_summed_BEV = try_sum(FR_available_BEV)
            FR_available_VRE = gdx(f, "o_PS_FR_available_VRE")
            FR_summed_VRE = try_sum(FR_available_VRE)
            FR_available_hydro = gdx(f, "o_PS_FR_available_hydro")
            FR_summed_hydro = try_sum(FR_available_hydro)
            FR_value_share_thermal = gdx(f, "o_PS_FR_thermal_value_share", silent=True)
            FR_value_share_VRE = gdx(f, "o_PS_FR_VRE_value_share", silent=True)
            FR_value_share_ESS = gdx(f, "o_PS_FR_ESS_value_share", silent=True, error_return=0)
            FR_value_share_BEV = gdx(f, "o_PS_FR_BEV_value_share", silent=True)
            FR_value_share_PtH = gdx(f, "o_PS_FR_PtH_value_share", silent=True)
            FR_value_share_hydro = gdx(f, "o_PS_FR_hydro_value_share", silent=True)
            FR_share_thermal = gdx(f, "o_PS_FR_thermal_share", silent=True)
            FR_share_VRE = gdx(f, "o_PS_FR_VRE_share", silent=True)
            FR_share_ESS = gdx(f, "o_PS_FR_ESS_share", silent=True)
            FR_share_BEV = gdx(f, "o_PS_FR_BEV_share", silent=True)
            FR_share_PtH = gdx(f, "o_PS_FR_PtH_share", silent=True)
            FR_share_hydro = gdx(f, "o_PS_FR_hydro_share", silent=True)
            FR_net_import = gdx(f, "o_PS_FR_net_import")
            FR_demand = {"wind": FR_demand_VRE.filter(like="WO", axis=0).groupby(level=[1]).sum(),
                         "PV": FR_demand_VRE.filter(like="PV", axis=0).groupby(level=[1]).sum(),
                         "other": FR_demand_other,
                         "total": FR_demand_VRE.groupby(level=[1]).sum() + FR_demand_other.fillna(0)
                         }
            PS = True
        except Exception as e:
            PS = False
            FR_value_share_thermal = False
            FR_value_share_VRE = False
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
    to_save = [i for i in after if i not in before and "_" != i[0]]  # skip variables that start with _
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
    stripped_scen = "_".join(scen.split("_")[:4])  # stripping unnecessary name components, like "6h"
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
    for i, scen_part in enumerate(stripped_scen.split('_')):  # split up the scenario name on _
        print_num(writer, [scen_part], "Indicators", row + 1, i, 0)  # print the (split) scenario name in Indicators
    c = i+1

    for indicator in indicators:
        # print(data[k][i])
        print_num(writer, [indicator], "Indicators", 0, c, 0)
        try: thing = data[indicator]
        except KeyError: thing = None
        ind_type = type(thing)
        if isinstance([], ind_type):
            print_num(writer, thing, "Indicators", row + 1, c, 0)
        elif ind_type in [type(1.), type(3), type(''), type(True), np.float64]:
            print_num(writer, [thing], "Indicators", row + 1, c, 0)
        elif isinstance(None, ind_type):
            print_num(writer, ["-"], "Indicators", row + 1, c, 0)
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
    cappy.groupby(level=[1]).sum().to_excel(writer, sheet_name=stripped_scen, startcol=1, startrow=1)
    for i, reg in enumerate(cappy.index.get_level_values(0).unique()):
        cappy.filter(like=reg,axis=0).to_excel(writer, sheet_name=stripped_scen, startcol=7+6*i, startrow=1)
    scen_row += cap_len+2
    print_df(writer, data["curtailment_profile_total"].round(decimals=3), "Curtailment", stripped_scen)
    print_df(writer, data["el_price"].round(decimals=3), "Elec. price", stripped_scen, row_inc=2)
    if data["PS"]: print_df(writer, data["FR_period_cost"].round(decimals=3), "FR period cost", stripped_scen, row_inc=2)

    print_gen(writer, stripped_scen, gen, data["gamsTimestep"])

    if data["PS"]:
        try: print_df(writer, data["FR_cost"].round(decimals=3), "FR: Cost", stripped_scen, row_inc=2)
        except IndexError:
            if "lowFlex" in stripped_scen and "fullFC" in stripped_scen: print(stripped_scen, data["FR_cost"])
        print_df(writer, data["FR_available"].round(decimals=3), "FR: Available", stripped_scen, header=False)
        print_df(writer, data["FR_deficiency"].round(decimals=2), "FR: Deficiency", stripped_scen, header=False)
        print_df(writer, data["FR_net_import"].round(decimals=3), "FR: Net-import", stripped_scen, header=False)
        print_df(writer, data["FR_demand"]["wind"].round(decimals=3), "FR demand: Wind", stripped_scen, header=True)
        print_df(writer, data["FR_demand"]["PV"].round(decimals=3), "FR demand: PV", stripped_scen, header=True)
        print_df(writer, data["FR_demand"]["other"].round(decimals=3), "FR demand: Other", stripped_scen, header=True)
        print_df(writer, data["FR_demand"]["total"].round(decimals=3), "FR demand: Total", stripped_scen, header=True, row_inc=2)
        print_df(writer, data["inertia_available"].round(decimals=3), "Inertia: Available", stripped_scen, header=True)
        print_df(writer, data["inertia_available_thermals"].round(decimals=3), "Inertia: Thermals", stripped_scen, header=True, row_inc=2)
    else:
        print("PS variables were not available for", scen)
