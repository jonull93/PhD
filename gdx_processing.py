# %%
import pickle  # for dumping and loading variable to/from file
import os
from datetime import datetime
import time as tm
import pandas as pd
from multiprocessing import cpu_count, Process, Manager, Queue
import multiprocessing
import pickle  # for dumping and loading variable to/from file
import threading
import time
import traceback
from traceback import format_exc
import gdx_processing_functions as gpf
from my_utils import print_red, print_cyan, print_green, print_magenta, save_to_file
from termcolor import colored
from glob import glob

if __name__ == "__main__":
    start_time_script = tm.time()
    print("Excel-writing script started at", datetime.now().strftime('%H:%M:%S'))

    #set path to the relative subfolder \output
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "output\\")
    #set gdxpath to ..\multinode\results\ where .. is the parent folder of the current folder
    gdxpath = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "multinode\\results\\")

    excel = True  # will only make a .pickle if excel == False
    individual_sheets = False # if True, each scenario will be written to a separate sheet in the excel file
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
                'EB', 'HP',
                'FC',
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
    cases1 = [#"singleyear_2002to2003_1h", "singleyear_1996to1997_1h", "singleyear_2014to2015_1h", "singleyear_1989to1990_1h", "singleyear_2010to2011_1h", "singleyear_2003to2004_1h",
            #"singleyear_1990to1991_1h", 
            # years to include: ['89', '95', '96', '97', '02', '03', '04', '09', '10', '18']
            #"singleyear_1989to1990_1h",
            "singleyear_1993to1994_1h",
            "singleyear_1995to1996_1h",
            "singleyear_1996to1997_1h", "singleyear_2002to2003_1h",
            #"singleyear_1997to1998_1h", "singleyear_2003to2004_1h",
            #"singleyear_2004to2005_1h", "singleyear_2009to2010_1h",
            #"singleyear_2010to2011_1h",
            #"singleyear_2018to2019_1h", "singleyear_2014to2015_1h",
            # also 2012 and 2016-2017
            "singleyear_1h_2012", "singleyear_2016to2017_1h",
            # 82-83 and 10-11
            "singleyear_1982to1983_1h", "singleyear_2010to2011_1h",
            #"set1_1opt", "set1_2opt", "set1_3opt", "set1_4opt" "2HP_3opt_a", "2HP_3opt_b", 
            "2HP_1opt", "2HP_2opt","2HP_3opt_mean", "2HP_4opt", "2HP_5opt", "2HP_6opt",
            "allyears",
            ]
    cases2 = [
        "2HP_1opt", "2HP_2opt", "2HP_3opt_mean", "2HP_4opt",# "2HP_5opt",
        "allopt2_final",
        #"allopt3_final_a", "allopt3_final_b", 
        "allopt3_final",
        #"allopt4_final_a", "allopt4_final_b", 
        "allopt4_final",
        "allyears",
        "singleyear_1995to1996_1h",
        "singleyear_1996to1997_1h", "singleyear_2002to2003_1h",
        "singleyear_1h_2012", "singleyear_2016to2017_1h", #start-points
    ]
    cases3 = [
        "2HP_1opt", "2HP_1opt_2012start",
        "2HP_2opt", "2HP_2opt_b", "2HP_2opt_evenweights",
        "2HP_3opt_a", "2HP_3opt_b",  "2HP_3opt_mean",

        #"set1_4opt_alt",
        #"set1_6even",
        #"2HP_4opt_alt", "2HP_4opt_even",

        "singleyear_1996to1997_1h", "singleyear_2002to2003_1h", #extremes
        "singleyear_1h_2012", "singleyear_2016to2017_1h", #start-points
        "allyears"
    ]
    cases_test = [
        "2HP_1opt_2012start", "2HP_1opt"
    ]
    cases_manyyears = [
        "singleyear_1995to1996_1h",
        "singleyear_1996to1997_1h", "singleyear_2002to2003_1h",
        "singleyear_1h_2012", "singleyear_2016to2017_1h", #start-points
        #‘93-’94	’99-’00	‘00-’01	‘03-’04	‘10-’11	‘11-’12
        "singleyear_1993to1994_1h", "singleyear_1999to2000_1h", "singleyear_2000to2001_1h", "singleyear_2003to2004_1h", "singleyear_2010to2011_1h", "singleyear_2011to2012_1h",
        #‘90-’91	‘94-’95	’08-’09	‘15-’16
        "singleyear_1990to1991_1h", "singleyear_1994to1995_1h", "singleyear_2008to2009_1h", "singleyear_2015to2016_1h",
        # ‘12-’13	‘13-’14
        "singleyear_2012to2013_1h", "singleyear_2013to2014_1h",
        #‘00-’01	‘16-’17
        "singleyear_2000to2001_1h",
        #‘01-’02
        "singleyear_2001to2002_1h",
        "allyears"
    ]
    cases_allyears = [
        "allyears",
        "singleyear_1980to1981_1h_flexlim_gurobi", "singleyear_1981to1982_1h_flexlim_gurobi","singleyear_1982to1983_1h_flexlim_gurobi",
        "singleyear_1983to1984_1h_flexlim_gurobi", "singleyear_1984to1985_1h_flexlim_gurobi","singleyear_1985to1986_1h_flexlim_gurobi",
        "singleyear_1986to1987_1h_flexlim_gurobi", "singleyear_1987to1988_1h_flexlim_gurobi","singleyear_1988to1989_1h_flexlim_gurobi",
        "singleyear_1989to1990_1h_flexlim_gurobi", "singleyear_1990to1991_1h_flexlim_gurobi","singleyear_1991to1992_1h_flexlim_gurobi",
        "singleyear_1992to1993_1h_flexlim_gurobi", "singleyear_1993to1994_1h_flexlim_gurobi","singleyear_1994to1995_1h_flexlim_gurobi",
        "singleyear_1995to1996_1h_flexlim_gurobi", "singleyear_1996to1997_1h_flexlim_gurobi","singleyear_1997to1998_1h_flexlim_gurobi",
        "singleyear_1998to1999_1h_flexlim_gurobi", "singleyear_1999to2000_1h_flexlim_gurobi","singleyear_2000to2001_1h_flexlim_gurobi",
        "singleyear_2001to2002_1h_flexlim_gurobi", "singleyear_2002to2003_1h_flexlim_gurobi","singleyear_2003to2004_1h_flexlim_gurobi",
        "singleyear_2004to2005_1h_flexlim_gurobi", "singleyear_2005to2006_1h_flexlim_gurobi","singleyear_2006to2007_1h_flexlim_gurobi",
        "singleyear_2007to2008_1h_flexlim_gurobi", "singleyear_2008to2009_1h_flexlim_gurobi","singleyear_2009to2010_1h_flexlim_gurobi",
        "singleyear_2010to2011_1h_flexlim_gurobi", "singleyear_2011to2012_1h_flexlim_gurobi","singleyear_2012to2013_1h_flexlim_gurobi",
        "singleyear_2012_1h_flexlim_gurobi",
        "singleyear_2013to2014_1h_flexlim_gurobi", "singleyear_2014to2015_1h_flexlim_gurobi","singleyear_2015to2016_1h_flexlim_gurobi",
        "singleyear_2016to2017_1h_flexlim_gurobi", "singleyear_2017to2018_1h_flexlim_gurobi","singleyear_2018to2019_1h_flexlim_gurobi",
    ]    
    cases_manyyears = [
        "allyears",
        #1992-1993, 2000-2001, 1989-1990, 1991-1992, 2015-2016, 1994-1995, 2008-2009, 2015-2016, 1996-1997, 2002-2003, 2012, 2016-2017
        "singleyear_1992to1993_1h_flexlim_gurobi", "singleyear_2000to2001_1h_flexlim_gurobi", "singleyear_1989to1990_1h_flexlim_gurobi",
        "singleyear_1991to1992_1h_flexlim_gurobi", "singleyear_2015to2016_1h_flexlim_gurobi", "singleyear_1994to1995_1h_flexlim_gurobi",
        "singleyear_2008to2009_1h_flexlim_gurobi", "singleyear_2015to2016_1h_flexlim_gurobi", "singleyear_1996to1997_1h_flexlim_gurobi",
        "singleyear_2002to2003_1h_flexlim_gurobi", "singleyear_2012_1h_flexlim_gurobi", "singleyear_2016to2017_1h_flexlim_gurobi",
    ]
    cases_truerefmixed = [
        "2HP_1opt_trueref", "2HP_2opt_trueref", "2HP_3opt_trueref", "2HP_4opt_trueref", "2HP_5opt_trueref", "2HP_6opt_trueref", "2HP_10opt_trueref",
        "singleyear_1996to1997_1h_flexlim_gurobi", "singleyear_2002to2003_1h_flexlim_gurobi", "singleyear_2001to2002_1h_flexlim_gurobi", "singleyear_2012_1h_flexlim_gurobi", "singleyear_2016to2017_1h_flexlim_gurobi",
        "allyears",
    ]
    cases_truerefall = [
        "2HP_1opt_trueref", "2HP_2opt_trueref", "2HP_3opt_trueref", "2HP_4opt_trueref", "2HP_5opt_trueref", "2HP_6opt_trueref", "2HP_10opt_trueref",
        "allopt2_trueref", "allopt3_trueref", "allopt4_trueref", "allopt5_trueref", "allopt6_trueref",
        "allyears",
    ]
    cases_random = [i.replace(".gdx","") for i in os.listdir(gdxpath) if "random" in i]

    #cases = cases1
    # instead of setting cases manually, prompt the user to select a set of cases
    print("Select a set of cases to run:")
    print("1: main (single years + 2HP + allyears)")
    print("2: allopt (2HP + allopt + allyears)")
    print("3: alt (2HP_alt + single years + allyears)")
    print('4: test ("2HP_1opt_2012start", "2HP_1opt")')
    print("5: manyyears (many single years+ allyears)")
    print("6: allyears (all years + allyears)")
    print("7: trueref_main (2HP_trueref + single years + allyears)")
    print("8: trueref_all (2HP_trueref + allopt_trueref + allyears)")
    print("9: random (all random cases)")
    cases = []
    while cases not in [cases1, cases2, cases3, cases_test, cases_manyyears, cases_allyears, cases_truerefmixed, cases_truerefall, cases_random]:
        cases = input("Enter a number: ")
        if cases == "1":
            cases = cases1
            suffix = "_main"
        elif cases == "2":
            cases = cases2
            suffix = "_allopt"
        elif cases == "3":
            cases = cases3
            suffix = "_alt"
        elif cases == "4":
            cases = cases_test
            suffix = "_test"
        elif cases == "5":
            cases = cases_manyyears
            suffix = "_manyyears"
        elif cases == "6":
            cases = cases_allyears
            suffix = "_allyears"
        elif cases == "7":
            cases = cases_truerefmixed
            suffix = "_trueref_main"
        elif cases == "8":
            cases = cases_truerefall
            suffix = "_trueref_all"
        elif cases == "9":
            cases = cases_random
            suffix = "_random"
        else:
            print("Invalid input")
    cases = list(set(cases))  # remove duplicates

    #cases = ["singleyear_"+str(year)+"to"+str(year+1)+"_1h" for year in range(1980, 2018)]

    """
    comp_name = os.environ['COMPUTERNAME']
    if "PLIA" in comp_name:
        path = "C:\\git\\quality-of-life-scripts\\output\\"
        gdxpath = "C:\\git\\multinode\\results\\"  # where to find gdx files
    elif "QGTORT8" in comp_name:
        path = "C:\\Users\\Jonathan\\git\\PhD\\output\\"
        gdxpath = "C:\\Users\\Jonathan\\git\\multinode\\results\\"  # where to find gdx files
    elif "DESKTOP-ATM4RVA" in comp_name: #.22
        path = "C:\\Users\\Jonathan\\git\\PhD\\output\\"
        gdxpath = "C:\\Users\\Jonathan\\git\\multinode\\results\\"  # where to find gdx files
    else:
        path = "C:\\Users\\jonathan\\git\\PhD\\output\\"
        gdxpath = "C:\\Users\\jonathan\\git\\multinode\\results\\"
    """

    if run_output.lower() == "w" or run_output.lower() == "write":
        old_data = {}
    elif run_output.lower() in ["rw", "add", "append"]:
        try:
            most_recent_cases_file = max([f for f in os.listdir("PickleJar") if f.startswith(f"data_") 
                                          and (f.endswith(f"{suffix}.pickle") or f.endswith(f"{suffix}.blosc"))])
            old_data = pickle.load(open(f"PickleJar\\{most_recent_cases_file}", "rb"))
        except FileNotFoundError:
            print_red("No pickle file found, starting from scratch")
            old_data = {}
    else:
        raise ValueError

    old_data_keys = list(old_data.keys())

    todo_gdx = []
    for j in cases:
        if j not in old_data_keys or j in overwrite:
            todo_gdx.append(j)

    todo_gdx_len = len(todo_gdx)
    print("To do:", todo_gdx, "(" + str(todo_gdx_len) + " items)")
    files = []
    for file in glob(gdxpath + "*.gdx"):
        files.append(file.split("\\")[-1].replace(".gdx", ""))
    alt_files = []
    for file in files:
        for alt in alternative_solutions:
            if alt in file: alt_files.append(file)
    #print("Alternative files found:",alt_files)

    #errors = 0
    #row = 0
    scen_row = 1
    indicators_column = 0
    #q_gdx = Queue(maxsize=0)
    #q_excel = Queue(maxsize=0)
    # Setting up multiprocessing
    manager = Manager()
    q_gdx = manager.Queue()
    q_excel = manager.Queue()
    row = manager.Value('i', 0)  # assuming 'row' is an integer. 'i' denotes integer.
    errors = manager.Value('i', 0)
    new_data = manager.dict()
    isgdxdone = manager.Value('b', False)
    thread_nr = manager.dict()

    for i, scen in enumerate(todo_gdx):
        q_gdx.put((i, scen))  # put (index, {scenarioname}) at the end of the queue

    if excel:
        for scen in [j for j in cases if j not in todo_gdx]:
            # the False below relates to
            q_excel.put((scen, False))  # if some data is ready to be sent to excel right away, fill the queue accordingly


    #new_data = {}
    # io_lock = threading.Lock()
    threads = {}
    num_threads = min(max(cpu_count() - 5, 4), len(todo_gdx), 10)
    excel_name = path + name + suffix + ".xlsx"
    #writer = pd.ExcelWriter(excel_name, engine="openpyxl")
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
def crawl_gdx(q_gdx, q_excel, old_data_keys, gdxpath, overwrite, todo_gdx_len, new_data, files, thread_nr, run_output, indicators, errors, excel, replace_with_alternative_solver_if_missing=False, alternative_solutions=[]):
    # Assign a unique identifier for the process
    pid = multiprocessing.current_process().pid

    # Set a thread_nr for the current process
    thread_nr[pid] = len(thread_nr) + 1

    while not q_gdx.empty():
        scen_i, scen_name = q_gdx.get()  # fetch new work from the Queue
        if run_output == "rw" and scen_name not in overwrite and scen_name in old_data_keys:
            q_gdx.task_done()
            continue
        try:
            print(f"- Starting {scen_name} on thread {thread_nr[pid]}")
            if scen_name not in files:
                raise FileNotFoundError
            start_time_thread = tm.time()
            success, new_data[scen_name] = gpf.run_case(scen_name, gdxpath, indicators)
            #print_green("Finished " + scen_name.ljust(20) + " after " + str(round(tm.time() - start_time_thread,
            #                                                              1)) + f" seconds")
            print_green(f"Finished {scen_name.ljust(20)} after {round((tm.time()-start_time_thread)/60, 1)} minutes. {q_gdx.qsize()} gdx files left out of {todo_gdx_len}")
            if success and excel:
                q_excel.put((scen_name, True))
                print(f' (q_excel appended and is now : {q_excel.qsize()} items long)')
        except FileNotFoundError:
            print_cyan("! Could not find file for", scen_name)
            found_alternative = False
            if replace_with_alternative_solver_if_missing:
                for replacer in alternative_solutions: # list of alternative suffixes
                    alternative = scen_name.split("_")
                    alternative.append(replacer)
                    alternative = "_".join(alternative)
                    print_cyan("Looking for", alternative)
                    if alternative in files:
                        print_green("Found and added to the queue an alternative file:",alternative)
                        q_gdx.put((scen_i, alternative))
                        todo_gdx.append(alternative)
                        found_alternative = True
                if "1h" in scen_name and not found_alternative:
                    if scen_name.replace("1h", "3h") in files:
                        print_green("Found and added to the queue an alternative file:", scen_name.replace("1h", "3h"))
                        q_gdx.put((scen_i, scen_name.replace("1h", "3h")))
                        todo_gdx.append(scen_name.replace("1h", "3h"))
        except:
            errors.value += 1
            print(f"! Error in crawler {thread_nr[pid]}, scenario {scen_name}. Exception:")
            print(traceback.format_exc())
            if q_gdx.qsize() > 0:
                print(q_gdx.qsize(), " gdx files left out of", todo_gdx_len,"\n")
        finally:
            q_gdx.task_done()  # signal to the queue that task has been processed
    return True

def crawl_excel(path, old_data, q_excel, new_data, row, indicators, isgdxdone, excel_name, individual_sheets):
    #print(f"starting crawl_excel('{path}')")
    writer = pd.ExcelWriter(excel_name, engine="openpyxl")
    start_time_excel = False
    while True:
        if not q_excel.empty():
            if not start_time_excel: start_time_excel = tm.time() #reset the timer when the first item is taken from the queue
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
            gpf.excel(scen_name, data, row, writer, indicators, individual_sheets=individual_sheets)
            row.value += 1
            q_excel.task_done()
        else:
            tm.sleep(0.3)
        if q_excel.empty() and isgdxdone.value == True:
            print("Finished excel queue after ", str(round((tm.time() - start_time_excel) / 60, 2)),
                "minutes - now saving excel file at", datetime.now().strftime('%H:%M:%S'))
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
            break
    return True

if __name__ == "__main__":
    print_magenta(f"Starting {num_threads} threads to work on {todo_gdx_len} gdx files")
    # Starting worker threads on queue processing
    processes = []
    for i in range(num_threads):
        print_cyan(f'Starting gdx thread {i + 1}')
        p = multiprocessing.Process(target=crawl_gdx, args=(q_gdx, q_excel, old_data_keys, gdxpath, overwrite, todo_gdx_len, 
                                                            new_data, files, thread_nr, run_output, indicators, errors, excel))
        tm.sleep(0.1*i+0.5)  # staggering gdx threads shouldnt matter as long as the excel process has something to work on
        p.start()
        processes.append(p)

    if excel:
        tm.sleep(1)
        print_magenta('Starting excel thread') # crawl_excel DOES NOT SUPPORT BEING RAN IN MULTIPLE INSTANCES
        p_excel = multiprocessing.Process(target=crawl_excel, args=(path, old_data, q_excel, new_data, row, indicators, 
                                                                    isgdxdone, excel_name, individual_sheets))
        p_excel.start()

    for p in processes:
        p.join()
    isgdxdone.value = True

    print_green("Finished the GDX queue after ", str(round((tm.time() - start_time_script) / 60, 1)),
        "minutes - now saving pickle at", datetime.now().strftime('%H:%M:%S'))

    for scen in todo_gdx:
        try:
            old_data[scen] = new_data[scen]
        except KeyError:
            print_red("! Not saved (probably a missing gdx):", scen)
        except Exception as e:
            print_red("! Could not add", scen, "to the pickle jar because",str(e))

    #pickle.dump(old_data, open(f"PickleJar\\data_{name}{suffix}.pickle", "wb"))
    save_to_file(old_data, f"PickleJar\\data_{name}{suffix}") #specifying the file extension is no longer necessary

    print_green("Successfully pickled")
    
    if opened_file: print_red(" ! REMINDER TO MAKE SURE EXCEL FILE IS CLOSED !")
    if excel: p_excel.join() # wait for the excel process to finish

    print_green('Script finished completed after', str(round((tm.time() - start_time_script) / 60, 2)), 'minutes with',
        str(errors.value), "errors, at", datetime.now().strftime('%H:%M:%S'))

    """
    for i in range(num_threads):
        print(colored(f'Starting gdx thread {i + 1}',"white"))
        worker = threading.Thread(target=crawl_gdx, args=(q_gdx, old_data, gdxpath, thread_nr, overwrite, len(todo_gdx)),
                                daemon=False)
        # setting threads as "daemon" allows main program to exit eventually even if these dont finish correctly
        worker.start()
        tm.sleep(0.1+1*excel)  # staggering gdx threads shouldnt matter as long as the excel process has something to work on
    # now we wait until the queue has been processed
    q_gdx.join()  # first we make sure there are no gdx files waiting to get processed
    q_excel.join()  # and then we make sure the excel queue is also empty
    """


    # for scen in file_list: run_case([0,scen], data, path, io_lock, True)

