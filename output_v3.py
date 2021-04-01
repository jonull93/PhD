import pickle  # for dumping and loading variable to/from file
import threading
import time as tm
import traceback
from datetime import datetime
from multiprocessing import cpu_count
from queue import Queue
import pandas as pd
from my_utils import TECH, order
from get_from_gams_db import gdx
from main import overwrite, path, indicators, old_data, run_output, cases, name, gdxpath
import gdxr

try:
    _ = path  # this will work if file was run from main since path is defined there
except:
    exec(open("./main.py").read())  # if not, then run main first
    exit()  # then do NOT run code again since main.py already executes this file once

print("Excel-writing script started at", datetime.now().strftime('%H:%M:%S'))


def print_gen(sheet, row, entry, data):
    gen_df = pd.DataFrame(entry)
    gen_df.transpose().to_excel(writer, sheet_name=sheet, freeze_panes=(0, 2), header=data["gamsTimestep"],
                                startrow=row,
                                startcol=1)


def print_gen2(sheet, row, col, data):
    gen_df = pd.DataFrame(data)
    gen_df.transpose().to_excel(writer, sheet_name=sheet, freeze_panes=(0, 2), header=False, startrow=row, startcol=col)


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
            print(f"Starting {scen[1]} on thread {thread_nr[threading.get_ident()]}")
            starttime[scen[0]] = tm.time()
            success = run_case(scen, data, gdxpath)
            print("Finished " + scen[1].ljust(20) + " after " + str(round(tm.time() - starttime[scen[0]],
                                                                          1)) + f" seconds, with {q_gdx.qsize()}/{len(todo_gdx)} files to go")
            if success:
                q_excel.put((scen[1], True))
                print(f'q_excel appended and is now : {q_excel.qsize()} items long')
        except:
            identifier = thread_nr[threading.get_ident()]
            global errors
            errors += 1
            print(f"Error in crawler {identifier}, scenario {scen[1]}. Exception:")
            print(traceback.format_exc())
            if q_gdx.qsize() > 0:
                print(q_gdx.qsize(), " gdx files left out of", len(todo_gdx))
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
            before = locals().keys()
            curtailment_profiles = gdx(f, "o_curtailment")
            curtailment_wind = gdx(f, "o_curtailment_wind")
            curtailment_PV = gdx(f, "o_curtailment_PV")
            gen_share = gdx(f, "o_new_share_gen")
            cap = gdx(f, "v_newcap")
            gen = gdx(f, "o_generation")
            el_price = gdx(f, "o_el_cost")
            load_profile = gdx(f, "demandprofile_average")
            net_load = gdx(f, "o_net_load")
            I_reg = gdx(f, "i_reg")
            gams_timestep = gdx(f, "timestep")  # "h0001" or "d001a"
            iter_t = range(len(gams_timestep))
            timestep = [i + 1 for i in iter_t]  # 1
            TT = 8760 / len(gams_timestep)
            allwind = gdx(f, "timestep")
            cost_tot = gdx(f, "cost_tot")
            allthermal = gdx(f, "allthermal")
            allstorage = gdx(f, "allwind")
            withdrawal_rate = gdx(f, "withdrawal_rate")
            FLH = gdx(f, "o_full_load_hours")
            PV_FLH = gdx(f, "o_full_load_PV")
            wind_FLH = gdx(f, "o_full_load_wind")
            el_price = gdx(f, "o_el_cost")
            discharge = gdx(f, "v_discharge")
            charge = gdx(f, "v_charge")
            gen.loc[TECH.BATTERY_CAP] = discharge.loc[TECH.BATTERY_CAP].level \
                                        - charge.loc[TECH.BATTERY_CAP].level
            demand = gdx(f, "o_load")
            inv_cost = gdx(f, "inv_cost")
            try:
                inertia_available = gdx(f, "o_PS_inertia_available")
                inertia_demand = gdx(f, "PS_Nminus1")
                OR_demand_VRE = gdx(f, "o_PS_OR_demand_VRE")
                OR_demand_other = gdx(f, "PS_OR_min")
                OR_available = gdx(f, "o_PS_OR_available")
                OR_cost = gdx(f, "o_PS_OR_cost")
                OR_demand = {"wind": OR_demand_VRE,
                             "solar": "",
                             "other": ""
                             }
            except:
                None

        flywheel = cap.loc[TECH.FLYWHEEL].level
        sync_cond = cap.loc[TECH.SYNCHRONOUS_CONDENSER].level
        FC = cap.loc[TECH.FUEL_CELL].level
        H2store = cap.loc[TECH.H2_STORAGE].level
        bat = cap.loc[TECH.BATTERY].level.astype(str) + " / " + cap.loc[TECH.BATTERY_CAP].level.astype(str)
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
    gen = data["gen"]
    cap = data["cap"]
    el_tot = data["el_tot"]
    OR_up = data["OR_up"]
    vPS_ESS_up = data["vPS_ESS_up"]
    inertia = data["inertia"]
    try:
        real_FLH = {i: sum(gen[i]) / cap[i] for i in cap if cap[i] > 0}
    except:
        print("RAN INTO THE WEIRD FLH ERROR IN", scen)
        print("DATA keys:", data.keys())
        print("gen keys:", gen.keys())
        print("cap keys:", data["cap"])
        real_FLH = {i: 0 for i in cap if cap[i] > 0}

    print_num([scen], "Indicators", row + 1, 0, 0)
    c = 1

    for i in indicators:
        # print(data[k][i])
        print_num([i], "Indicators", 0, c, 0)
        ind_type = type(data[i])
        thing = data[i]
        if isinstance([],
                      ind_type):  # this if-statement makes sure that the print_num always gets a list and not a float or int
            print_num(thing, "Indicators", row + 1, c, 0)
        elif isinstance(1., ind_type):
            print_num([thing], "Indicators", row + 1, c, 0)
        elif i == "curtailment":
            print_num([thing["tot"]], "Indicators", row + 1, c, 0)
        else:
            print(f"some weird variable type ({str(i)}: {ind_type}) entered the excel-printing loop")
            if isinstance({}, ind_type): print(thing.keys())
        c += 1

    length = len(data["gen"])
    print_gen(scen, 0, data["gen"], data)
    print_gen2(scen, +2, 1, {"Curtailment": data["OR_up"][1]["curtailment"]})
    print_gen2(scen, length + 3, 0, {("Marginal cost", "Elec."): data["el_price"]})
    print_gen2(scen, length + 4, 0, {
        ("OR", "Cost_up"): [sum([data["PS_OR_cost_up"][j + 1][i] for j in range(7)]) for i in
                            range(len(data["PS_OR_cost_up"][1]))]})
    print_gen2(scen, length + 5, 0, {("OR", "Tot"): data["OR_up_min"]})
    print_gen2(scen, length + 6, 0, {("Forecast error", "wind"): data["LF_profile"]["wind"]})
    print_gen2(scen, length + 7, 0, {("Forecast error", "solar"): data["LF_profile"]["solar"]})
    print_gen2(scen, length + 8, 0, {("Loadfollowing", "demand"): data["LF_profile"]["demand"]})
    print_gen2(scen, length + 10, 0, {("Inertia", tech): inertia[tech] for tech in inertia})
    print_gen2(scen, length + 10 + len(inertia), 0, {("OR 10-60s", i): data["OR_up"][0][i] for i in data["OR_up"][0]})
    print_gen2(scen, length + 11 + len(inertia) + len(data["OR_up"]), 0,
               {("OR_cost", i): data["PS_OR_cost_up"][i] for i in data["PS_OR_cost_up"]})

    print_cap({x: y for x, y in cap.items() if y > 0}, scen,
              len(gen) + len(OR_up) + len(inertia) + len(data["vPS_ESS_up"]) + 15,
              1, ["Cap"])
    c = 0
    print_num(["share"], scen, len(gen) + len(OR_up) + len(inertia) + len(data["vPS_ESS_up"]) + 15, 3, 0)
    for i in cap:
        if cap[i] > 0:
            c += 1
            num = sum(gen[i]) / el_tot
            print_num([num], scen, len(gen) + len(OR_up) + len(inertia) + len(data["vPS_ESS_up"]) + 15 + c, 3, 0)

    c = 0
    print_num(["FLH"], scen, len(gen) + len(OR_up) + len(inertia) + len(data["vPS_ESS_up"]) + 15, 4, 0)
    for i in cap:
        if cap[i] > 0:
            c += 1
            num = real_FLH[i]
            print_num([num], scen, len(gen) + len(OR_up) + len(inertia) + len(data["vPS_ESS_up"]) + 15 + c, 4, 0)


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
writer = pd.ExcelWriter(path + "output_" + name + ".xlsx", engine="openpyxl")
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
