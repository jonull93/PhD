# %%
# from gams import *
import pickle  # for dumping and loading variable to/from file
import os
from datetime import datetime
import time as tm
import pandas as pd
import numpy as np
from multiprocessing import cpu_count
from queue import Queue
import pickle  # for dumping and loading variable to/from file
import threading
import time
import traceback
from traceback import format_exc
import gdx_processing_functions as gpf

start_time_script = tm.time()
print("Excel-writing script started at", datetime.now().strftime('%H:%M:%S'))

excel = True  # will only make a .pickle if excel == False
run_output = "rw"  # 'w' to (over)write or 'rw' to only add missing scenarios
overwrite = []  # names of scenarios to overwrite regardless of existence in pickled data
#overwrite = [reg+"_inertia_0.1x" for reg in ["ES3", "HU", "IE", "SE2"]]+\
#            [reg+"_inertia" for reg in ["ES3", "HU", "IE", "SE2"]]+\
#            [reg+"_inertia_noSyn" for reg in ["ES3", "HU", "IE", "SE2"]]
h = 3  # time resolution
suffix = "testing"  # Optional suffix for the run, e.g. "test" or "highBioCost"
suffix = '_'+suffix if len(suffix) > 0 else ''
name = f"results_{h}h{suffix}"  # this will be the name of the output excel file

# indicators are shown in a summary first page to give an overview of all scenarios in one place
# the name of an indicator should preferably match the name of a variable from the gdx, requires extra code if not
indicators = ["cost_tot",
              "VRE_share_total",
              'curtailment',
              #              'flywheel',
              "G",
              'sync_cond',
              'bat',
              'FC',
              'H2store',
              'EB', 'HP',
              ]

cases = []
systemFlex = ["lowFlex", "highFlex"]
modes = ["noFC", "fullFC"]  # , "fullFC", "inertia", "OR"]#
for reg in ["iberia", "brit", "nordic"]:
    for flex in systemFlex:
        for mode in modes:
            for year in [2020,2030,2040]:
                cases.append(f"{reg}_{flex}_{mode}_{year}{'_'+str(h)+'h' if h>1 else ''}")


comp_name = os.environ['COMPUTERNAME']
if "PLIA" in comp_name:
    path = "C:\\Users\\Jonathan\\Box\\python\\output\\"
    gdxpath = "C:\\git\\multinode\\"  # where to find gdx files
elif "QGTORT8" in comp_name:
    path = "C:\\Users\\Jonathan\\git\\python\\output\\"
    gdxpath = "C:\\Users\\Jonathan\\git\\multinode\\"  # where to find gdx files
else:
    path = "D:\\Jonathan\\python\\output\\"
    gdxpath = "D:\\Jonathan\\multinode\\"


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

print("GDX files:", todo_gdx, "(" + str(len(todo_gdx)) + " items)")

errors = 0
isgdxdone = False
row = 0
scen_row = 1
q_gdx = Queue(maxsize=0)
q_excel = Queue(maxsize=0)
for i, scen in enumerate(todo_gdx):
    q_gdx.put((i, scen))  # put (index, {scenarioname}) at the end of the queue

for scen in [j for j in cases if j not in todo_gdx]:
    # the False below relates to
    q_excel.put((scen, False))  # if some data is ready to be sent to excel right away, fill the queue accordingly

new_data = {}
# io_lock = threading.Lock()
threads = {}
thread_nr = {}
num_threads = min(max(cpu_count() - 1, 6), len(todo_gdx))
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
        print("OBS: EXCEL FILE MAY BE OPEN - PLEASE CLOSE IT BEFORE SCRIPT FINISHES ", e)

# Unfortunately, global variables can only be used within the same file, so not all functions can be imported
def crawl_gdx(q_gdx, old_data, gdxpath, thread_nr, overwrite, todo_gdx_len):
    thread_nr[threading.get_ident()] = len(thread_nr) + 1
    while not q_gdx.empty():
        scen_i, scen_name = q_gdx.get()  # fetch new work from the Queue
        if run_output == "rw" and scen_name not in overwrite and scen_name in old_data:
            q_gdx.task_done()
            continue
        try:
            print(f"- Starting {scen_name} on thread {thread_nr[threading.get_ident()]}")
            start_time_thread = tm.time()
            success, new_data[scen_name] = gpf.run_case(scen_name, old_data, gdxpath, indicators)
            print("Finished " + scen_name.ljust(20) + " after " + str(round(tm.time() - start_time_thread,
                                                                          1)) + f" seconds, with {q_gdx.qsize()}/{len(todo_gdx)} files to go")
            if success:
                q_excel.put((scen_name, True))
                print(f'q_excel appended and is now : {q_excel.qsize()} items long')
        except FileNotFoundError:
            print("! Could not find file for", scen_name)
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
            print("Starting excel() for", scen_name, "at", datetime.now().strftime('%H:%M:%S'))
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
print('Starting excel thread(s)')
worker = threading.Thread(target=crawl_excel, args=(path, old_data))
worker.start()
for i in range(num_threads):
    print('Starting gdx thread', i + 1)
    worker = threading.Thread(target=crawl_gdx, args=(q_gdx, old_data, gdxpath, thread_nr, overwrite, len(todo_gdx)),
                              daemon=False)
    # setting threads as "daemon" allows main program to exit eventually even if these dont finish correctly
    worker.start()
    tm.sleep(3)  # staggering gdx threads shouldnt matter as long as the excel process has something to work on
# now we wait until the queue has been processed
q_gdx.join()  # first we make sure there are no gdx files waiting to get processed
isgdxdone = True
if opened_file: print(" ! REMINDER TO MAKE SURE EXCEL FILE IS CLOSED !")
print("GDX queue empty!")
q_excel.join()  # and then we make sure the excel queue is also empty

for scen in todo_gdx:
    try:
        old_data[scen] = new_data[scen]
    except KeyError:
        print("! Could not add", scen, "to the pickle jar because",scen,"was not found in newdata")
    except Exception as e:
        print("! Could not add", scen, "to the pickle jar because",)

pickle.dump(old_data, open("PickleJar\\data_" + name + ".pickle", "wb"))
# for scen in file_list: run_case([0,scen], data, path, io_lock, True)

print("Finished the queue after ", str(round((tm.time() - start_time_script) / 60, 2)),
      "minutes - now saving excel file!")
try:
    f = open(excel_name, "r+")
    f.close()
except PermissionError:
    opened_file = True
    print("OBS: EXCEL FILE IS OPEN - PLEASE CLOSE IT TO RESUME SCRIPT")
    while opened_file:
        try:
            f = open(excel_name, "r+")
            f.close()
            opened_file = False
        except PermissionError:
            time.sleep(5)
except Exception as e:
    print("!! Unknown error when opening Excel file:",str(e))

worksheet = writer.sheets["Indicators"]
worksheet.column_dimensions["A"].width = 20
worksheet.column_dimensions["B"].width = 10
worksheet.column_dimensions["C"].width = 10
worksheet.column_dimensions["D"].width = 10
worksheet.column_dimensions["E"].width = 10
writer.save()
print('Script finished completed after', str(round((tm.time() - start_time_script) / 60, 2)), 'minutes with',
      str(errors), "errors.")
