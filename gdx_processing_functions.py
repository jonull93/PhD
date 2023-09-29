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
from my_utils import TECH, order_map_cap, order_map_gen, print_green, print_cyan, print_red, print_blue, print_magenta, print_yellow
from order_cap import VRE

def print_gen(writer, sheet, df, gamsTimestep):
    global scen_row
    df["sort_by"] = df.index.get_level_values(0).map(order_map_gen)
    df.sort_values("sort_by", inplace=True)
    df.drop(columns="sort_by", inplace= True)
    df = df.reorder_levels(["I_reg", "tech", "stochastic_scenarios"]).sort_index(level=0, sort_remaining=False)
    df.to_excel(writer, sheet_name=sheet, freeze_panes=(0, 2), startrow=scen_row, startcol=1)
    scen_row += len(df.index)+1


def print_df(writer, df, name, sheet, col=3, header=True, row_inc=1):
    global scen_row
    merge = False
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
    if len(df.index) > 1 and merge: worksheet.merge_cells(f"A{scen_row+1}:A{scen_row + len(df.index)+header}")
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


def run_case(scen_name, gdxpath, indicators, FC=False, print_FR_summary=False):
    def get_from_cap(tech_name, round=False):
        # if tech_name is not a list, do the following
        if type(tech_name) != list:
            try:
                if round:
                    foo = tot_cap.loc[tech_name].sum().round(decimals=round)
                else:
                    foo = tot_cap.loc[tech_name].sum()
            except KeyError:
                foo = 0
            return foo
        else:
            foo = get_from_cap(tech_name[0])
            for tech in tech_name[1:]:
                foo += get_from_cap(tech)
            return foo
                

    def try_sum(df, level="FR_period", FR_cost=False):
        if type(FR_cost) != bool:
            try:
                foo = (df * FR_cost).values.sum()
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
    # region = k.split("_")[0]
    # year = k.split("_")[3]
    with gdxr.GdxFile(gdxpath + k + ".gdx") as f:
        before = [i for i in locals().keys()]  # variables defined before this line do not get pickled
        gamsTimestep = gdx(f, "timestep")
        I_reg = gdx(f, "I_reg")
        curtailment_profiles = gdx(f, "o_curtailment_hourly")
        curtailment_profiles.fillna(0, inplace=True)
        curtailment_profiles[curtailment_profiles < 0] = 0
        curtailment_profile_total = gdx(f, "o_curtailment_hourly_total")
        curtailment = gdx(f, "o_curtailment_share_total")
        curtailment_regional = gdx(f, "o_curtailment_regional")
        #curtailment_wind = gdx(f, "o_curtailment_wind")
        #curtailment_PV = gdx(f, "o_curtailment_PV")
        gen_share = gdx(f, "o_share_gen").rename("Share")
        VRE_share = gdx(f, "o_VRE_share")
        #VRE_share_total = gdx(f, "o_VRE_share_total")
        #wind_share = gdx(f, "o_VRE_share")
        PV_share = gdx(f, "o_VRE_share")
        U_share = gen_share["U"]
        tot_cap = gdx(f, "o_capacity")
        new_cap = gdx(f, "v_newcap")
        for reg in new_cap.index.unique(1):
            if reg not in I_reg:
                new_cap.drop(reg, level="I_reg", inplace=True)
        for index, vals in new_cap.iterrows():
            if (0 < vals.upper == vals.level) and index[0] not in VRE:
                print_magenta(f" !! Found capped investment ({vals.level}) at {index} for {scen_name}")
        gen = gdx(f, "o_generation")
        gen_per_eltech = gdx(f, "o_generation_el")
        el_price = gdx(f, "o_el_price")
        load_profile = gdx(f, "demandprofile_average")
        net_load = gdx(f, "o_net_load")
        gams_timestep = gdx(f, "timestep")  # "h0001" or "d001a"
        iter_t = range(len(gams_timestep))
        timestep = [i + 1 for i in iter_t]  # 1
        TT = 8760 / len(gams_timestep)
        stochastic_probability = gdx(f, "stochastic_year_probability")
        allwind = gdx(f, "timestep")
        cost_tot = gdx(f, "o_cost_total_oldinv", silent=False)
        cost_tot_onlynew = gdx(f, "v_totcost").level
        cost_partload = gdx(f, "o_cost_partload")
        cost_flexlim = gdx(f, "o_cost_flexlim")
        cost_OMvar = gdx(f, "o_cost_OMvar")
        cost_OMfix = gdx(f, "o_cost_OMfix")
        cost_fuel = gdx(f, "o_cost_fuel")
        cost_CO2 = gdx(f, "o_cost_CO2")
        cost_CCS = gdx(f, "o_cost_CCS")
        cost_newinv = gdx(f, "o_cost_newinv")
        #if cost_fuel has "stochastic_scenarios" as index, then sum over it, otherwise just take cost_fuel
        if "stochastic_scenarios" in cost_fuel.index.names:
            cost_variable = cost_fuel.groupby(level="stochastic_scenarios").sum()
            #cost_variable = pd.DataFrame(cost_fuel).groupby(level="stochastic_scenarios").sum()
        else:
            cost_variable = cost_fuel
            #cost_variable = pd.DataFrame(cost_fuel)

        for _df in [cost_flexlim, cost_OMvar, cost_CO2, cost_CCS]:
            if type(_df) not in [pd.Series]:
                print_red(f"! {type(_df)} in the cost_variable loop")
            if not _df.empty:
                if "stochastic_scenarios" in _df.index.names:
                    _df = _df.groupby(level="stochastic_scenarios").sum()
                # this will throw an error about fill_value not being implemented if series and dfs get mixed 
                cost_variable = cost_variable.add(_df, fill_value=0) 
        allthermal = gdx(f, "allthermal")
        thermal_share_total = gen_per_eltech[gen_per_eltech.index.isin(allthermal, level="tech")].sum()/gen_per_eltech.sum()
        print(f"thermal_share_total = {round(thermal_share_total,2)}   ({scen_name})")
        if np.isnan(thermal_share_total):
            print(scen_name,gen_per_eltech)
        allstorage = gdx(f, "allwind")
        withdrawal_rate = gdx(f, "withdrawal_rate")
        FLH = gdx(f, "o_full_load_hours").rename("FLH")
        FLH_regional = gdx(f, "o_full_load_hours_regional").rename("FLH_regional")
        PV_FLH = gdx(f, "o_full_load_PV")
        wind_FLH = gdx(f, "o_full_load_wind")
        heat_price = gdx(f, "o_heat_price")
        discharge = gdx(f, "v_discharge")
        charge = gdx(f, "v_charge")
        demand = gdx(f, "o_load")
        inv_cost = gdx(f, "inv_cost")
        tech_revenue = gdx(f, "o_tech_revenue")
        tech_revenue_el = gdx(f, "o_tech_revenue_el")
        tech_revenue_inertia = gdx(f, "o_tech_revenue_inertia")
        tech_revenue_FR = gdx(f, "o_tech_revenue_FR")
        tech_revenue_FR_lowercap = gdx(f, "o_tech_revenue_FR_lowercap")
        tech_variable_expenses = gdx(f, "o_tech_variable_expenses")
        bio_use = gdx(f, "o_biomass_use_total")
        if FC:
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
                _empty_FR_df = pd.DataFrame(columns=demand.columns, index=FR_demand_other.index, data=0)
                FR_available = gdx(f, "o_PS_FR_available")
                #FR_available_total = gdx(f, "o_PS_FR_available_total_actualESS")
                try: FR_deficiency = gdx(f, "v_PS_FR_deficiency").level
                except AttributeError: FR_deficiency = gdx(f, "v_PS_OR_deficiency").level
                try: FR_cost = gdx(f, "EQU_PS_FR_loadbalance").marginal.clip(upper=0)*-1e6/TT
                except AttributeError: FR_cost = gdx(f, "EQU_PS_FR_supply").marginal.clip(upper=0) * -1e6 / TT
                try:
                    FR_cost_per_tech = (FR_available*FR_cost).sum(axis=1).sum(level="tech")
                    FR_cost_series_per_tech = (FR_available * FR_cost).sum(axis=0, level="tech")
                    FR_cost_series_per_tech_lowercap = (FR_available * FR_cost.mask(FR_cost < 10, other=0)).sum(axis=0, level="tech")
                except ValueError:
                    FR_cost_per_tech = FR_available.sum(axis=1).sum(level="tech")*0
                    FR_cost_series_per_tech = FR_available.sum(axis=0, level="tech")*0
                    FR_cost_series_per_tech_lowercap = FR_available.sum(axis=0, level="tech")*0
                FR_period_cost = gdx(f, "o_PS_FR_cost_perPeriod")
                FR_FFR_cost_share = gdx(f, "o_PS_FR_cost_FFRshare")
                FR_available_thermal = gdx(f, "o_PS_FR_available_thermal", dud_df_return=_empty_FR_df)
                FR_summed_thermal = try_sum(FR_available_thermal)
                FR_available_ESS = gdx(f, "o_PS_FR_available_ESS", dud_df_return=_empty_FR_df)
                FR_summed_ESS = try_sum(FR_available_ESS)
                FR_available_BEV = gdx(f, "o_PS_FR_available_BEV", dud_df_return=_empty_FR_df)
                FR_summed_BEV = try_sum(FR_available_BEV)
                FR_available_VRE = pd.concat([curtailment_profile_total], keys=["1"], names=["FR_period"])
                for _i in range(5):
                    _new_line = pd.concat([curtailment_profile_total], keys=[str(_i+2)], names=["FR_period"])
                    FR_available_VRE = pd.concat([FR_available_VRE, _new_line])
                try: FR_available_VRE = FR_available_VRE.reorder_levels(["I_reg", "FR_period"]).sort_index().reindex(index=_empty_FR_df.index, columns=_empty_FR_df.columns, fill_value=0)
                except (AssertionError, KeyError):
                    FR_available_VRE = FR_available_VRE.unstack(level=2).fillna(0).reindex(index=_empty_FR_df.index, columns=_empty_FR_df.columns, fill_value=0)

                FR_summed_VRE = try_sum(FR_available_VRE)
                FR_available_hydro = gdx(f, "o_PS_FR_available_hydro", dud_df_return=_empty_FR_df)
                FR_summed_hydro = try_sum(FR_available_hydro)
                FR_available_PtH = gdx(f, "o_PS_FR_available_PtH", dud_df_return=_empty_FR_df)
                FR_summed_PtH = try_sum(FR_available_PtH)
                FR_available_total = FR_available_PtH+FR_available_hydro+FR_available_thermal+FR_available_ESS+\
                                     FR_available_BEV+FR_available_VRE
                if print_FR_summary:
                    print(f"{scen_name}: sum(FR_available_total) = {round(FR_available_total.values.sum())}")
                    try:
                        if FR_cost.values.sum() > 0: print(f"{scen_name}: sum(FR cost) = {round(FR_cost.values.sum())}")
                        elif "lowFlex" in k and "fullFC" in k:
                            print_red("!! sum(FR_cost) is zero in", k)
                    except AttributeError:
                        if "lowFlex" in k and "fullFC" in k:
                            print_red("!! sum(FR_cost) is zero in", k)
                FR_value_share_thermal = gdx(f, "o_PS_FR_thermal_value_share", silent=True)
                FR_value_share_VRE = gdx(f, "o_PS_FR_VRE_value_share", silent=True)
                FR_value_share_ESS = gdx(f, "o_PS_FR_ESS_value_share", silent=True, error_return=0)
                FR_value_share_BEV = gdx(f, "o_PS_FR_BEV_value_share", silent=True)
                FR_value_share_PtH = gdx(f, "o_PS_FR_PtH_value_share", silent=True)
                FR_value_share_hydro = gdx(f, "o_PS_FR_hydro_value_share", silent=True)
                #FR_share_thermal = gdx(f, "o_PS_FR_thermal_share", silent=True)
                #FR_share_VRE = gdx(f, "o_PS_FR_VRE_share", silent=True)
                #FR_share_ESS = gdx(f, "o_PS_FR_ESS_share", silent=True)
                #FR_share_BEV = gdx(f, "o_PS_FR_BEV_share", silent=True)
                #FR_share_PtH = gdx(f, "o_PS_FR_PtH_share", silent=True)
                #FR_share_hydro = gdx(f, "o_PS_FR_hydro_share", silent=True)
                try: FR_net_import = gdx(f, "o_PS_FR_net_import", dud_df_return=_empty_FR_df)
                except TypeError:
                    FR_net_import = gdx(f, "o_PS_FR_net_import")
                    if len(FR_net_import) == 0:
                        FR_net_import = pd.DataFrame(columns=demand.columns, index=FR_demand_other.index, data=0)
                    elif type(FR_net_import) == type(pd.Series()):
                        FR_net_import = FR_net_import.unstack("", fill_value=0).reindex(index=_empty_FR_df.index, columns=_empty_FR_df.columns, fill_value=0)
                FR_VRE_timetable = gdx(f, "PS_timetable_VREramping")
                FR_demand = {"wind": FR_demand_VRE.filter(like="WO", axis=0).groupby(level=[1]).sum().reindex(columns=_empty_FR_df.columns).fillna(0),
                             "PV": FR_demand_VRE.filter(like="PV", axis=0).groupby(level=[1]).sum().reindex(columns=_empty_FR_df.columns).fillna(0),
                             "other": FR_demand_other,
                             "total": gdx(f, "o_PS_FR_demand_total" ,dud_df_return=FR_demand_other*0)  # *0 to discard all values but get index and header
                             }
                #for index, val in FR_available_total.iterrows():
                #    if int(index[1]) > 2:
                #        _to_add = FR_demand_other.loc[index] + FR_demand_VRE.groupby(level=[1]).sum().loc[index[0]]
                #        FR_demand["total"].loc[index] = _to_add
                #    else:
                #        _to_add = FR_demand_other.loc[index]
                #        FR_demand["total"].loc[index] = _to_add
                if "noFC" not in scen_name:
                    try: FR_supply_excess = FR_available_total - FR_demand["total"] + FR_net_import
                    except:
                        print_cyan(scen_name, "excess = ", FR_available_total, FR_demand["total"], FR_net_import)
                    # no change if FR_demand==FR_available, a downscaling if FR_demand<FR_available
                    # this downscaling should also make the new FR_available==FR_demand
                    try: FR_available_ESS = (FR_available_ESS * FR_demand["total"] / FR_available_total).fillna(0)
                    except:
                        print_cyan(scen_name, "ESS = ", FR_available_ESS, FR_demand["total"], FR_available_total)

                    FR_available_BEV = (FR_available_BEV * (FR_demand["total"]-FR_net_import) / FR_available_total).fillna(0)
                    FR_available_hydro = (FR_available_hydro * (FR_demand["total"]-FR_net_import) / FR_available_total).fillna(0)
                    FR_available_thermal = (FR_available_thermal * (FR_demand["total"]-FR_net_import) / FR_available_total).fillna(0)
                    FR_available_VRE = (FR_available_VRE * (FR_demand["total"]-FR_net_import) / FR_available_total).fillna(0)
                    FR_available_PtH = (FR_available_PtH * (FR_demand["total"]-FR_net_import) / FR_available_total).fillna(0)
                else: FR_supply_excess = _empty_FR_df
                FR_available_total_cutoff = FR_available_VRE + FR_available_PtH + FR_available_hydro + FR_available_thermal + FR_available_ESS + FR_available_BEV
                FR_share_thermal = FR_available_thermal.values.sum() / FR_available_total_cutoff.values.sum()
                FR_share_VRE = FR_available_VRE.values.sum() / FR_available_total_cutoff.values.sum()
                FR_share_ESS = FR_available_ESS.values.sum() / FR_available_total_cutoff.values.sum()
                FR_share_BEV = FR_available_BEV.values.sum() / FR_available_total_cutoff.values.sum()
                FR_share_PtH = FR_available_PtH.values.sum() / FR_available_total_cutoff.values.sum()
                FR_share_hydro = FR_available_hydro.values.sum() / FR_available_total_cutoff.values.sum()
                if "noFC" not in scen_name:
                    print_cyan(f"Reserve share in {scen_name}:\nThermal: {round(FR_share_thermal*100,1)} %, VRE: {round(FR_share_VRE*100,1)} %, "
                                 f"ESS: {round(FR_share_ESS*100,1)} %, BEV: {round(FR_share_BEV*100,1)} %, "
                                 f"Hydro: {round(FR_share_hydro*100,1)} %, PtH: {round(FR_share_PtH*100,1)} %")
                PS = True
            except Exception as e:
                PS = False
                FR_value_share_thermal = False
                FR_value_share_VRE = False
                print("%ancillary_services% was not activated for", k, "because:")
                print(format_exc())
        else:
            PS = False
            FR_value_share_thermal = False
            FR_value_share_VRE = False
    #flywheel = get_from_cap(TECH.FLYWHEEL)
    sync_cond = get_from_cap(TECH.SYNCHRONOUS_CONDENSER)
    wind = get_from_cap([TECH.WIND_OFFSHORE_1,TECH.WIND_OFFSHORE_2,TECH.WIND_OFFSHORE_3,TECH.WIND_OFFSHORE_4,TECH.WIND_OFFSHORE_5,
                         TECH.WIND_ONSHORE_1, TECH.WIND_ONSHORE_2, TECH.WIND_ONSHORE_3, TECH.WIND_ONSHORE_4, TECH.WIND_ONSHORE_5])
    PV = get_from_cap([TECH.PV_A1, TECH.PV_A2, TECH.PV_A3, TECH.PV_A4, TECH.PV_A5, 
                       TECH.PV_R1, TECH.PV_R2, TECH.PV_R3, TECH.PV_R4, TECH.PV_R5])
    FC = get_from_cap(TECH.FUEL_CELL)
    H2store = get_from_cap(TECH.H2_STORAGE)
    EB = get_from_cap(TECH.ELECTRIC_BOILER)
    HP = get_from_cap(TECH.HEAT_PUMP)
    G = get_from_cap(TECH.GAS)
    WGCCS = get_from_cap(TECH.BIOGAS_CCS)
    WG = get_from_cap(TECH.BIOGAS)
    WG_peak = get_from_cap(TECH.BIOGAS_PEAK)
    U = get_from_cap(TECH.NUCLEAR)
    bat = get_from_cap(TECH.BATTERY)
    bat_cap = get_from_cap(TECH.BATTERY_CAP)
    try: battery = tot_cap.loc[TECH.BATTERY].sum().round(decimals=2).astype(str) + " / " \
          + tot_cap.loc[TECH.BATTERY_CAP].sum().round(decimals=2).astype(str)
    except KeyError: battery = 0

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

def short_scen(scen):
    shortened_scen = scen.replace("iberia", "ib")
    shortened_scen = shortened_scen.replace("nordic", "no")
    shortened_scen = shortened_scen.replace("brit", "br")
    shortened_scen = shortened_scen.replace("Flex", "F")
    shortened_scen = shortened_scen.replace("fullFC", "FC")
    shortened_scen = shortened_scen.replace("noTransport", "noTrsp")
    shortened_scen = shortened_scen.replace("Flex", "Flx")
    shortened_scen = shortened_scen.replace("ref_cap", "refCap")
    shortened_scen = shortened_scen.replace("tight", "t")
    shortened_scen = shortened_scen.replace("base", "b")
    shortened_scen = shortened_scen.replace("extreme", "e")
    return shortened_scen

def excel(scen:str, data, row, writer, indicators):
    global scen_row
    global indicators_column
    try: type(indicators_column) == int
    except NameError: indicators_column = 5
    stripped_scen = "_".join(scen.split("_")[:5])  # stripping unnecessary name components, like "6h"
    shortened_scen = short_scen(stripped_scen)
    if len(shortened_scen)>30: print_red("scen name is too long!", shortened_scen)
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
        print(f"! Could not find tech in gen.index, {scen} probably failed the gams run. Here's gen:",gen)
        return
    for i, scen_part in enumerate(stripped_scen.split('_')):  # split up the scenario name on _
        print_num(writer, [scen_part], "Indicators", row.value + 1, i, 0)  # print the (split) scenario name in Indicators
        if i>indicators_column: indicators_column = i
    c = indicators_column+1

    for indicator in indicators:
        # print(data[k][i])
        print_num(writer, [indicator], "Indicators", 0, c, 0)
        try: thing = data[indicator]
        except KeyError: thing = None
        ind_type = type(thing)
        if isinstance([], ind_type):
            print_num(writer, thing, "Indicators", row.value + 1, c, 0)
        elif ind_type in [type(1.), type(3), np.float64]:
            print_num(writer, [round(thing,ndigits=2)], "Indicators", row.value + 1, c, 0)
        elif ind_type in [type(''), type(True)]:
            print_num(writer, [thing], "Indicators", row.value + 1, c, 0)
        elif isinstance(None, ind_type):
            print_num(writer, ["-"], "Indicators", row.value + 1, c, 0)
        elif ind_type == pd.core.series.Series:
            try: 
                print_num(writer, ["/".join(map(str, (thing*100).round(1)))], "Indicators", row.value + 1, c, 0)
                #if "share" in 
            except: print(f"Failed to print {indicator} to excel!")
        else:
            print(f"some weird variable type ({str(indicator)}: {ind_type}) entered the excel-printing loop")
            if isinstance({}, ind_type): print(thing.keys())
        c += 1

    cap_len = len(cap.index.get_level_values(0).unique())+1
    reg_len = len(cap.index.get_level_values(1).unique())+1
    try:
        cappy = cap.to_frame(name="Cap").join(new_cap).join(share).join(FLH_regional)
    except: print(cap,new_cap,share,FLH_regional)
    cappy["sort_by"] = cappy.index.get_level_values(0).map(order_map_cap)
    cappy.sort_values("sort_by", inplace=True)
    cappy.drop(columns="sort_by", inplace=True)
    #print(cappy)
    cappy = cappy.reorder_levels(["I_reg", "tech", "stochastic_scenarios"]).sort_index(level=0, sort_remaining=False)
    mask = cappy.duplicated(subset=["New cap","Cap"], keep='first')
    cappy2 = cappy[~mask]
    cappy2[["New cap","Cap"]].groupby(level=["tech"]).sum().to_excel(writer, sheet_name=shortened_scen, startcol=1, startrow=1)
    cappy_len = len(cappy2[["New cap","Cap"]].groupby(level=["tech"]).sum())
    for i, reg in enumerate(cappy.index.get_level_values(0).unique()):
        cappy.filter(like=reg,axis=0).to_excel(writer, sheet_name=shortened_scen, startcol=5+8*i, startrow=1)
        if len(cappy.filter(like=reg,axis=0)) > cappy_len: cappy_len = len(cappy.filter(like=reg,axis=0))
    # get the nr of rows in cappy.filter(like=reg,axis=0)
    #print_yellow(scen_row)
    scen_row += cappy_len+4
    #print_yellow(scen_row)
    try: print_df(writer, data["curtailment_profile_total"].round(decimals=3), "Curtailment", shortened_scen)
    except AttributeError: print_red(f"could not print curtailment for {shortened_scen}")
    try: print_df(writer, data["el_price"].round(decimals=3), "Elec. price", shortened_scen, row_inc=2)
    except AttributeError: print_red(f"could not print elec price for {shortened_scen}")

    if data["PS"]: print_df(writer, data["FR_period_cost"].round(decimals=3), "FR period cost", shortened_scen, row_inc=2)
    try: print_gen(writer, shortened_scen, gen, data["gamsTimestep"])
    except AttributeError: print_red(f"could not print gen for {shortened_scen}")

    if data["PS"]:
        try: print_df(writer, data["FR_cost"].round(decimals=3), "FR: Cost", shortened_scen, row_inc=2)
        except IndexError:
            if "lowFlex" in stripped_scen and "fullFC" in stripped_scen: print(shortened_scen, data["FR_cost"])
        print_df(writer, data["FR_available"].round(decimals=3), "FR: Available", shortened_scen, header=False)
        print_df(writer, data["FR_deficiency"].round(decimals=2), "FR: Deficiency", shortened_scen, header=False)
        print_df(writer, data["FR_net_import"].round(decimals=3), "FR: Net-import", shortened_scen, header=False)
        print_df(writer, data["FR_demand"]["wind"].round(decimals=3), "FR demand: Wind", shortened_scen, header=True)
        print_df(writer, data["FR_demand"]["PV"].round(decimals=3), "FR demand: PV", shortened_scen, header=True)
        print_df(writer, data["FR_demand"]["other"].round(decimals=3), "FR demand: Other", shortened_scen, header=True)
        print_df(writer, data["FR_demand"]["total"].round(decimals=3), "FR demand: Total", shortened_scen, header=True, row_inc=2)
        print_df(writer, data["inertia_available"].round(decimals=3), "Inertia: Available", shortened_scen, header=True)
        print_df(writer, data["inertia_available_thermals"].round(decimals=3), "Inertia: Thermals", shortened_scen, header=True, row_inc=2)
    else:
        #print("PS variables were not available for", scen)
        pass
