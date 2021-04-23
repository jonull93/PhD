import pickle  # for dumping and loading variable to/from file
import threading
import time as tm
import traceback
from datetime import datetime
from multiprocessing import cpu_count
from queue import Queue
from traceback import format_exc

import gdxr
import pandas as pd
import numpy as np

from get_from_gams_db import gdx
from copy import copy
from main import overwrite, path, indicators, old_data, run_output, cases, name, gdxpath
from my_utils import TECH, order, order_map

print("Excel-writing script started at", datetime.now().strftime('%H:%M:%S'))


def print_gen(sheet, row, df, gamsTimestep):
    df["sort_by"] = df.index.get_level_values(0).map(order_map)
    df.sort_values("sort_by", inplace=True)
    df.drop(columns="sort_by", inplace= True)
    df = df.reorder_levels(["I_reg", "tech"]).sort_index(level=0, sort_remaining=False)
    df.to_excel(writer, sheet_name=sheet, freeze_panes=(0, 2), startrow=row, startcol=1)


def print_df(df, name, sheet, col=3, header=True, row_inc=1):
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


def print_num(num, sheet, row, col, ind):
    if not ind:
        num_df = pd.DataFrame(num)  # columns = ["System cost:"]
        num_df.to_excel(writer, sheet_name=sheet, index=False, header=False, startcol=col, startrow=row)
    else:
        num_df = pd.DataFrame(data=num, index=ind)  # columns = ["System cost:"]
        num_df.to_excel(writer, sheet_name=sheet, startcol=col, startrow=row)


def print_cap(num, sheet, row, col, ind):
    num_df = pd.DataFrame(data=num, index=ind).T  # columns = ["System cost:"]
    num_df.to_excel(writer, sheet_name=sheet, startcol=col, startrow=row)


def crawl_gdx(q_gdx, data, gdxpath):
    thread_nr[threading.get_ident()] = len(thread_nr) + 1
    while not q_gdx.empty():
        scen = q_gdx.get()  # fetch new work from the Queue
        if scen[1] in data and scen[1] not in overwrite:
            q_gdx.task_done()
            continue
        try:
            print(f"- Starting {scen[1]} on thread {thread_nr[threading.get_ident()]}")
            starttime[scen[0]] = tm.time()
            success = run_case(scen, data, gdxpath)
            print("Finished " + scen[1].ljust(20) + " after " + str(round(tm.time() - starttime[scen[0]],
                                                                          1)) + f" seconds, with {q_gdx.qsize()}/{len(todo_gdx)} files to go")
            if success:
                q_excel.put((scen[1], True))
                print(f'q_excel appended and is now : {q_excel.qsize()} items long')
        except FileNotFoundError:
            print("! Could not find file for", scen[1])
        except:
            identifier = thread_nr[threading.get_ident()]
            global errors
            errors += 1
            print(f"! Error in crawler {identifier}, scenario {scen[1]}. Exception:")
            print(traceback.format_exc())
            if q_gdx.qsize() > 0:
                print(q_gdx.qsize(), " gdx files left out of", len(todo_gdx),"\n")
        finally:
            q_gdx.task_done()  # signal to the queue that task has been processed

    # print(f"gdx crawler {thread_nr[threading.get_ident()]} now unemployed due to lack of work")
    return True


def crawl_excel(path=path):
    global q_excel
    global q_gdx
    global row
    print(f"starting crawl_excel('{path}')")
    while True:
        if not q_excel.empty():
            scen = q_excel.get()
            print("Starting excel() for", scen[0], "at", datetime.now().strftime('%H:%M:%S'))
            if scen[1]:
                try:
                    data = newdata[scen[0]]
                except:
                    print("data for", scen[0], "not found")
                    q_excel.task_done()
                    continue
            else:
                data = old_data[scen[0]]
            excel(scen[0], data, row)
            row += 1
            q_excel.task_done()
            # print("Finished excel for",scen[0],"at",datetime.now().strftime('%H:%M:%S'))
        else:
            tm.sleep(0.3)
        if q_excel.empty() and isgdxdone:
            print("crawl_excel finished")
            break
    return True


def run_case(scen, data, gdxpath):
    def get_from_cap(tech_name, round=False):
        try:
            if round:
                foo = tot_cap.loc[tech_name].sum().round(decimals=round)
            else:
                foo = tot_cap.loc[tech_name].sum()
        except KeyError:
            foo = 0
        return foo

    k = scen[1]
    global newdata
    if run_output.lower() == "w" or k not in data:
        # flywheel,
        # sync_cond,
        # bat,
        # FC',
        # H2store
        # el_tot,
        region = k.split("_")[0]
        with gdxr.GdxFile(gdxpath + k + ".gdx") as f:
            before = [i for i in locals().keys()]
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
                inertia_available_thermals = gdx(f, "o_PS_inertia_available_thermal")
                inertia_demand = gdx(f, "PS_Nminus1")
                OR_demand_VRE = gdx(f, "o_PS_OR_demand_VRE")
                OR_demand_other = gdx(f, "PS_OR_min")
                OR_available = gdx(f, "o_PS_OR_available")
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
        newdata[k] = {}
        for variable in to_save:
            try:
                newdata[k][variable] = eval(variable)
            except:
                print("Could not save", i, "to newdata in case", k)

        return True


def excel(scen, data, row):
    global scen_row
    scen_row = 0
    cap = data["tot_cap"].rename("Cap").round(decimals=3)
    cap = cap[cap!=0]
    new_cap = data["new_cap"].level.rename("New cap").round(decimals=3)
    new_cap = new_cap[new_cap != 0]  # filter out technologies which aren't going to be the there for cap/share/FLH
    FLH = data["FLH"].astype(int)
    share = data["gen_share"].round(decimals=3)
    gen = data["gen"]
    try:
        if "electrolyser" in gen.index.unique(level="tech"):
            gen = gen.drop("electrolyser", level="tech")
    except KeyError:
        print(f"! Could not find tech in gen.index, {scen} probably failed the gams run.")
        return
    print_num([scen], "Indicators", row + 1, 0, 0)
    c = 1

    for indicator in indicators:
        # print(data[k][i])
        print_num([indicator], "Indicators", 0, c, 0)
        thing = data[indicator]
        ind_type = type(thing)
        if isinstance([], ind_type):
            print_num(thing, "Indicators", row + 1, c, 0)
        elif ind_type in [type(1.), type(3), type(''), np.float64]:
            print_num([thing], "Indicators", row + 1, c, 0)
        elif ind_type == pd.core.series.Series:
            try: print_num([thing.sum()], "Indicators", row + 1, c, 0)
            except: print(f"Failed to print {indicator} to excel!")
        else:
            print(f"some weird variable type ({str(indicator)}: {ind_type}) entered the excel-printing loop")
            if isinstance({}, ind_type): print(thing.keys())
        c += 1

    cap_len = len(cap.index.get_level_values(0).unique())+1
    reg_len = len(cap.index.get_level_values(1).unique())+1
    try: cappy = cap.to_frame(name="Cap").join(new_cap).join(share).join(FLH)
    except: print(cap,new_cap,share,FLH)
    cappy["sort_by"] = cappy.index.get_level_values(0).map(order_map)
    cappy.sort_values("sort_by", inplace=True)
    cappy.drop(columns="sort_by", inplace=True)
    cappy = cappy.reorder_levels(["I_reg", "tech"]).sort_index(level=0, sort_remaining=False)
    cappy.groupby(level=[1]).sum().to_excel(writer, sheet_name=scen, startcol=1, startrow=1)
    for i, reg in enumerate(cappy.index.get_level_values(0).unique()):
        cappy.filter(like=reg,axis=0).to_excel(writer, sheet_name=scen, startcol=7+6*i, startrow=1)
    scen_row += cap_len+2
    print_df(data["curtailment_profile_total"].round(decimals=3), "Curtailment", scen)
    print_df(data["el_price"].round(decimals=3), "Elec. price", scen, row_inc=2)
    if data["PS"]:
        print_df(data["OR_available"].round(decimals=3), "OR: Available", scen, row_inc=2)
        print_df(data["OR_net_import"].round(decimals=3), "OR: Net-import", scen, header=False)
        print_df(data["OR_demand"]["wind"].round(decimals=3), "OR demand: Wind", scen, header=True)
        print_df(data["OR_demand"]["PV"].round(decimals=3), "OR demand: PV", scen, header=True)
        print_df(data["OR_demand"]["other"].round(decimals=3), "OR demand: Other", scen, header=True)
        print_df(data["OR_demand"]["total"].round(decimals=3), "OR demand: Total", scen, header=True, row_inc=2)
        print_df(data["inertia_available"].round(decimals=3), "Inertia: Available", scen, header=True)
        print_df(data["inertia_available_thermals"].round(decimals=3), "Inertia: Thermals", scen, header=True, row_inc=2)
    else:
        print("PS variables were not available for", scen)

    print_gen(scen, scen_row, gen, data["gamsTimestep"])


todo_gdx = []
for j in cases:
    if j not in old_data or j in overwrite:
        todo_gdx.append(j)
        # file_list.append(j+i)

print("GDX files:", todo_gdx, "(" + str(len(todo_gdx)) + " items)")
starttime = {"start": tm.time(), 0: 0}
errors = 0
isgdxdone = False
row = 0
scen_row = 1
q_gdx = Queue(maxsize=0)
q_excel = Queue(maxsize=0)
for i, scen in enumerate(todo_gdx):
    q_gdx.put((i, scen))  # put (i, {scenarioname}) at the end of the queue

for scen in [j for j in cases if j not in todo_gdx]:
    q_excel.put((scen, False))

newdata = {}
# io_lock = threading.Lock()
threads = {}
thread_nr = {}
num_threads = min(max(cpu_count() - 1, 6), len(todo_gdx))
writer = pd.ExcelWriter(path + name + ".xlsx", engine="openpyxl")
opened_file = False
try:
    f = open(path + "output_" + name + ".xlsx", "r+")
    f.close()
except Exception as e:
    if "No such" in str(e):
        None
    elif "one sheet" not in str(e):
        opened_file = True
        print("OBS: EXCEL FILE MAY BE OPEN - PLEASE CLOSE IT BEFORE SCRIPT FINISHES ", e)

# Starting worker threads on queue processing
print('Starting excel thread(s)')
worker = threading.Thread(target=crawl_excel)
worker.start()
for i in range(num_threads):
    print('Starting gdx thread', i + 1)
    worker = threading.Thread(target=crawl_gdx, args=(q_gdx, old_data, gdxpath),
                              daemon=False)
    # setting threads as "daemon" allows main program to exit eventually even if these dont finish correctly
    worker.start()
    tm.sleep(0.1)
# now we wait until the queue has been processed
q_gdx.join()  # first we make sure there are no gdx files waiting to get processed
isgdxdone = True
if opened_file: print(" ! REMINDER TO MAKE SURE EXCEL FILE IS CLOSED !")
print("GDX queue empty!")
q_excel.join()  # and then we make sure the excel queue is also empty

for scen in todo_gdx:
    try:
        old_data[scen] = newdata[scen]
    except:
        print("Could not add", scen, "to the pickle jar")

pickle.dump(old_data, open("PickleJar\\data_" + name + ".pickle", "wb"))
# for scen in file_list: run_case([0,scen], data, path, io_lock, True)

print("Finished the queue after ", str(round((tm.time() - starttime["start"]) / 60, 2)),
      "minutes - now saving excel file!")
worksheet = writer.sheets["Indicators"]
worksheet.column_dimensions["A"].width = 20
worksheet.column_dimensions["B"].width = 10
worksheet.column_dimensions["C"].width = 10
worksheet.column_dimensions["D"].width = 10
worksheet.column_dimensions["E"].width = 10
writer.save()
print('Script finished completed after', str(round((tm.time() - starttime["start"]) / 60, 2)), 'minutes with',
      str(errors), "errors.")
