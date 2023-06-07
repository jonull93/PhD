# %%
import pickle  # for dumping and loading variable to/from file
import os
from datetime import datetime
import time as tm
import pandas as pd
from multiprocessing import cpu_count
from queue import Queue
import pickle  # for dumping and loading variable to/from file
import threading
import time
import traceback
from traceback import format_exc
import gdx_processing_functions as gpf
from my_utils import print_red, print_cyan, print_green
from termcolor import colored
from glob import glob

start_time_script = tm.time()
print("Excel-writing script started at", datetime.now().strftime('%H:%M:%S'))

excel = True  # will only make a .pickle if excel == False
run_output = "rw"  # 'w' to (over)write or 'rw' to only add missing scenarios
overwrite = []  # names of scenarios to overwrite regardless of existence in pickled data
#overwrite = [reg+"_inertia_0.1x" for reg in ["ES3", "HU", "IE", "SE2"]]+\
#            [reg+"_inertia" for reg in ["ES3", "HU", "IE", "SE2"]]+\
#            [reg+"_inertia_noSyn" for reg in ["ES3", "HU", "IE", "SE2"]]

# indicators are shown in a summary first page to give an overview of all scenarios in one place
# the name of an indicator should preferably match the name of a variable from the gdx, requires extra code if not
indicators = ["cost_tot",
              "U_share",
              "VRE_share",
              "bio_use",
              'curtailment',
              "wind",
              "PV",
              "U",
              "WG",
              "WG_peak",
#              'sync_cond',
              'bat',
              'bat_cap',
              'H2store',
#              'EB', 'HP',
              ]

scenario_prefix = "ref_cap" # prefix of scenario names in gdx files
cases = []
systemFlex = ["highFlex"]
modes = [""]   # , "fullFC", "inertia", "OR"]# "noFC",
regions = ["nordic_L"]
hedging_scenarios = ['iter1_2', 'iter2_2', 'iter3_2', '2base2extreme']
years = [2050] #[2020,2025,2030,2040]
timesteps = [1,3]  # time resolution
replace_with_alternative_solver_if_missing = True
alternative_solutions = ["tight"]  # to replace with if replace_with_alternative_solver_if_missing
suffix = ""  # Optional suffix for the run, e.g. "test" or "highBioCost"
suffix = '_'+suffix if len(suffix) > 0 else ''
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
name = f"results_{timestamp}{suffix}"  # this will be the name of the output excel and pickle files
for reg in regions:
    for flex in systemFlex:
        for mode in modes:
            for year in years:
                for timestep in timesteps:
                    for hedging_scenario in hedging_scenarios:
                        #if f"{reg}_{flex}_{mode}_{year}{suffix}{'_'+str(h)+'h' if h>1 else ''}" != "iberia_lowFlex_fullFC_2030_noGpeak_6h": continue
                        cases.append(f"{scenario_prefix}{'_'+str(timestep)+'h'}{'_'+hedging_scenario if hedging_scenario else ''}{suffix}")

# Or overwrite the cases list manually
# iter2_3 = "2002-2003", "1996-1997", "2014-2015"
cases = ["singleyear_1h_2002to2003", "singleyear_1h_1996to1997", "singleyear_1h_2014to2015", "iter2_3_1h"]
cases = ["singleyear_"+str(year)+"to"+str(year+1)+"_1h" for year in range(1980, 2018)]

comp_name = os.environ['COMPUTERNAME']
if "PLIA" in comp_name:
    path = "C:\\git\\quality-of-life-scripts\\output\\"
    gdxpath = "C:\\git\\multinode\\results\\"  # where to find gdx files
elif "QGTORT8" in comp_name:
    path = "C:\\Users\\Jonathan\\git\\python\\output\\"
    gdxpath = "C:\\Users\\Jonathan\\git\\multinode\\results\\"  # where to find gdx files
elif "DESKTOP-ATM4RVA" in comp_name: #.22
    path = "C:\\Users\\Jonathan\\git\\python\\output\\"
    gdxpath = "C:\\Users\\Jonathan\\git\\multinode\\results\\"  # where to find gdx files
else:
    path = "C:\\Users\\jonathan\\git\\python\\output\\"
    gdxpath = "C:\\Users\\jonathan\\git\\multinode\\results\\"


if run_output.lower() == "w" or run_output.lower() == "write":
    old_data = {}
elif run_output.lower() == "rw":
    try: old_data = pickle.load(open("PickleJar\\data_" + name + ".pickle", "rb"))
    except FileNotFoundError:
        old_data = {}
else:
    raise ValueError

todo_gdx = []
for j in cases:
    if j not in old_data or j in overwrite:
        todo_gdx.append(j)

print("To do:", todo_gdx, "(" + str(len(todo_gdx)) + " items)")
files = []
for file in glob(gdxpath + "*.gdx"):
    files.append(file.split("\\")[-1].replace(".gdx", ""))
alt_files = []
for file in files:
    for alt in alternative_solutions:
        if alt in file: alt_files.append(file)
print("Alternative files found:",alt_files)

errors = 0
isgdxdone = False
row = 0
scen_row = 1
indicators_column = 0
q_gdx = Queue(maxsize=0)
q_excel = Queue(maxsize=0)
for i, scen in enumerate(todo_gdx):
    q_gdx.put((i, scen))  # put (index, {scenarioname}) at the end of the queue

if excel:
    for scen in [j for j in cases if j not in todo_gdx]:
        # the False below relates to
        q_excel.put((scen, False))  # if some data is ready to be sent to excel right away, fill the queue accordingly

new_data = {}
# io_lock = threading.Lock()
threads = {}
thread_nr = {}
num_threads = min(max(cpu_count() - 5, 4), len(todo_gdx))
excel_name = path + name + ".xlsx"
writer = pd.ExcelWriter(excel_name, engine="openpyxl")
opened_file = False
try:
    f = open(excel_name, "r+")
    f.close()
except Exception as e:
    if "No such" in str(e):
        None
    elif "one sheet" not in str(e):
        opened_file = True
        print_red("OBS: EXCEL FILE MAY BE OPEN - PLEASE CLOSE IT BEFORE SCRIPT FINISHES ", e)

# Unfortunately, global variables can only be used within the same file, so not all functions can be imported
def crawl_gdx(q_gdx, old_data, gdxpath, thread_nr, overwrite, todo_gdx_len, files = files):
    thread_nr[threading.get_ident()] = len(thread_nr) + 1
    while not q_gdx.empty():
        scen_i, scen_name = q_gdx.get()  # fetch new work from the Queue
        if run_output == "rw" and scen_name not in overwrite and scen_name in old_data:
            q_gdx.task_done()
            continue
        try:
            print(f"- Starting {scen_name} on thread {thread_nr[threading.get_ident()]}")
            if scen_name not in files:
                raise FileNotFoundError
            start_time_thread = tm.time()
            success, new_data[scen_name] = gpf.run_case(scen_name, gdxpath, indicators)
            print_green("Finished " + scen_name.ljust(20) + " after " + str(round(tm.time() - start_time_thread,
                                                                          1)) + f" seconds")
            if success and excel:
                q_excel.put((scen_name, True))
                print(f' (q_excel appended and is now : {q_excel.qsize()} items long)')
        except FileNotFoundError:
            print_cyan("! Could not find file for", scen_name)
            if replace_with_alternative_solver_if_missing:
                for replacer in alternative_solutions:
                    alternative = scen_name.split("_")
                    alternative.insert(-1, replacer)
                    alternative = "_".join(alternative)
                    print_cyan("Looking for", alternative)
                    if alternative in files:
                        print_cyan("Found and added to the queue an alternative file:",alternative)
                        q_gdx.put((scen_i, alternative))
                if "1h" in scen_name:
                    if scen_name.replace("1h", "3h") in files:
                        print_cyan("Found and added to the queue an alternative file:", scen_name.replace("1h", "3h"))
                        q_gdx.put((scen_i, scen_name.replace("1h", "3h")))
        except:
            identifier = thread_nr[threading.get_ident()]
            global errors
            errors += 1
            print(f"! Error in crawler {identifier}, scenario {scen_name}. Exception:")
            print(traceback.format_exc())
            if q_gdx.qsize() > 0:
                print(q_gdx.qsize(), " gdx files left out of", todo_gdx_len,"\n")
        finally:
            q_gdx.task_done()  # signal to the queue that task has been processed

    # print(f"gdx crawler {thread_nr[threading.get_ident()]} now unemployed due to lack of work")
    return True

def crawl_excel(path, old_data):
    global q_excel
    global q_gdx
    global row
    print(f"starting crawl_excel('{path}')")
    while True:
        if not q_excel.empty():
            scen_name, scen_new = q_excel.get()
            print("Starting excel() for", scen_name, "at", datetime.now().strftime('%H:%M:%S'), f' ({q_excel.qsize()} items in excel queue)')
            if scen_new:
                try:
                    data = new_data[scen_name]
                except:
                    print("data for", scen_name, "not found")
                    q_excel.task_done()
                    continue
            else:
                data = old_data[scen_name]
            gpf.excel(scen_name, data, row, writer, indicators)
            row += 1
            q_excel.task_done()
            # print("Finished excel for",scen[0],"at",datetime.now().strftime('%H:%M:%S'))
        else:
            tm.sleep(0.3)
        if q_excel.empty() and isgdxdone:
            print("crawl_excel finished")
            break
    return True


# Starting worker threads on queue processing
if excel:
    print('Starting excel thread(s)')
    worker = threading.Thread(target=crawl_excel, args=(path, old_data))
    worker.start()
for i in range(num_threads):
    print(colored(f'Starting gdx thread {i + 1}',"white"))
    worker = threading.Thread(target=crawl_gdx, args=(q_gdx, old_data, gdxpath, thread_nr, overwrite, len(todo_gdx)),
                              daemon=False)
    # setting threads as "daemon" allows main program to exit eventually even if these dont finish correctly
    worker.start()
    tm.sleep(0.1+1*excel)  # staggering gdx threads shouldnt matter as long as the excel process has something to work on
# now we wait until the queue has been processed
q_gdx.join()  # first we make sure there are no gdx files waiting to get processed
isgdxdone = True
if opened_file: print(" ! REMINDER TO MAKE SURE EXCEL FILE IS CLOSED !")

print("Finished the GDX queue after ", str(round((tm.time() - start_time_script) / 60, 2)),
      "minutes - now saving pickle at", datetime.now().strftime('%H:%M:%S'))

for scen in todo_gdx:
    try:
        old_data[scen] = new_data[scen]
    except KeyError:
        print("! Not saved (probably a missing gdx):", scen)
    except Exception as e:
        print("! Could not add", scen, "to the pickle jar because",str(e))

pickle.dump(old_data, open("PickleJar\\data_" + name + ".pickle", "wb"))
print("Successfully pickled")
# for scen in file_list: run_case([0,scen], data, path, io_lock, True)

q_excel.join()  # and then we make sure the excel queue is also empty
print("Finished excel queue after ", str(round((tm.time() - start_time_script) / 60, 2)),
      "minutes - now saving excel file at", datetime.now().strftime('%H:%M:%S'))
if excel:
    try:
        f = open(excel_name, "r+")
        f.close()
    except PermissionError:
        opened_file = True
        for i in range(3): print_red("OBS: EXCEL FILE IS OPEN - PLEASE CLOSE IT TO RESUME SCRIPT")
        while opened_file:
            try:
                f = open(excel_name, "r+")
                f.close()
                print("thank you for closing the file :)")
                opened_file = False
            except PermissionError:
                time.sleep(5)
    except FileNotFoundError:
        None
    except Exception as e:
        print("!! Unknown error when opening Excel file:", type(e), str(e))
    writer.save()
print('Script finished completed after', str(round((tm.time() - start_time_script) / 60, 2)), 'minutes with',
      str(errors), "errors, at", datetime.now().strftime('%H:%M:%S'))
