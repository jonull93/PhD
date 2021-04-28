# Written by Jonathan Ullmark, please let me know if you found this useful
import datetime as dt
import os, sys
import random
import threading
import time as tm
from itertools import product
from queue import Queue
import psutil
import gams
from glob import glob
import previousInvestments
from traceback import format_exc
from my_utils import append_to_file

print("Script started at", dt.datetime.now().strftime('%H:%M:%S'))

if "C18" in os.environ['COMPUTERNAME']:  # This allows you to change path depending on which computer you run script from
    path = "C:\\models\\multinode\\"  # where your main-file is located
elif "PLIA" in os.environ['COMPUTERNAME']:
    path = "C:\\git\\multinode\\"
elif "QGTORT8" in os.environ['COMPUTERNAME']:  # .22
    path = "C:\\Users\\Jonathan\\git\\multinode\\"
else:
    path = "D:\\Jonathan\\multinode\\"  # where your main-file is located
ws = gams.GamsWorkspace(path)
gmsfile = "MN_main.gms"  # name of your main-file [NEEDS TO BE EDITED WHEN SETTING SCRIPT UP]


def combinations(parameters):  # Create list of parameter combinations
    return [p for p in product(*parameters)]


followUp_run = True  # if True and len(years)<1, will look for previous years for the given year
years = [2030, 2040, 2050]
# set followUp_run to False if we are running first year and forgot to change followUp_run to false manually
if followUp_run: followUp_run = 2030 not in years
regions = ["nordic", "brit", "iberia"]  # ["SE2","HU","ES3","IE"]
systemFlex = ["lowFlex", "highFlex"]
modes = ["noFC", "fullFC", "inertia", "OR"]#, "FCnoPTH", "FCnoH2", "FCnoWind", "FCnoBat", "FCnoSynth"]
timeResolution = 3
HBresolutions = [26]
cores_per_scenario = 3  # the 'cores' in gams refers to logical cores, not physical
core_count = psutil.cpu_count()  # add logical=False to get physical cores

scenarios = {}
# looping through regions and modes in this way means that it will first run all "pre",
# then all "OR" and so on, instead of first solving all modes for each region.
# I create my scenario-code by using what is called an fstring.
# This allows me to put variables and if-statements in my text using {}. Very convenient :)

for flex in systemFlex:
    for mode in modes:
        if "low" in flex.lower() and "noH2" in mode:
            continue  # lowFlex means no H2storage, so FC from electrolysers seems less reasonable
        for region in regions:
            for HBres in HBresolutions:
                for year in years:
                    scenarioname = f"{region}_{flex}_{mode}_{year}" \
                                   f"{'' if timeResolution == 1 else '_' + str(timeResolution) + 'h'}"
                    scenarios[scenarioname] = \
                        f"""
*--  Scenario settings
$setglobal scenario "{scenarioname}"
$setglobal current_year {year}
$setglobal region {region}
$setglobal OR {"yes" if "OR" in mode or "fullFC" in mode else "no"}
$setglobal inertia {"yes" if "inertia" in mode.lower() or "fullFC" in mode else "no"}
$setglobal systemFlex {'yes' if "highflex" in scenarioname.lower() or "fullflex" in scenarioname.lower() else 'no'}
$setglobal synthetic_inertia {"no" if "FCnoSyn" in mode else "yes"}
$setglobal PtH_FC {"no" if "FCnoPTH" in mode else "yes"}
$setglobal electrolyser_FR {"no" if "FCnoH2" in mode else "yes"}
$setglobal wind_FC {"no" if "FCnoWind" in mode else "yes"}
$setglobal bat_FC {"no" if "FCnoBat" in mode else "yes"}

*--  Sensitivity analysis settings
$setglobal OR_energyReservation {"yes" if "energyRes" in mode else "no"} 
$setglobal OR_energyDepletion {"yes" if "energyDep" in mode else "no"}
$setglobal inertia_scaling {"2" if "2xInertia" in mode else "1"}
$setglobal forecast_scaling 1
$setglobal flywheel_price_scaling 1
$setglobal sync_cond_price_scaling 1
$setglobal onshore_storage "no"
$setglobal H2demand 0.2

*--  Other model settings
$setglobal ancillary_services yes
$setglobal flexlim {'no' if 'noflex' in mode.lower() else 'yes'}
$setglobal startup no //start-up time equations are not updated!
$setglobal first_iteration {'yes' if year == years[0] and not followUp_run else 'no'}
$setglobal cores {cores_per_scenario}
$setglobal double_use {"no" if "noDoubleUse" in mode else "yes"}
$setglobal SNSP no
$setglobal EV_AGG {'no' if 'noEV' in scenarioname else 'yes'}
$setglobal heatBalance {'no' if 'noHB' in scenarioname else 'yes'}
$setglobal hour_resolution {timeResolution}
$setglobal heatBalancePeriods {HBres}
$setglobal toExcel no
$setglobal update_scenario no"""  # [NEEDS TO BE EDITED WHEN SETTING SCRIPT UP]

num_threads = int(min(core_count/(cores_per_scenario-0.5), len(scenarios)/len(years)))
# The "optimal" number of threads depends on your hardware and model
# but nr of cores /2 seems good unless you hit RAM limit

print("Number of scenarios:", len(scenarios))
multipleYears = len(years) > 1
if multipleYears: print(" Multiple years detected, will run previousInvestments.py in-between runs")

# create .inc file for each scenario
for scen in scenarios:
    File = open(path + "Include\\pythonScenarios\\" + scen + ".inc",
                "w")  # here you can choose where the scenario-files should be placed (OBS: folder must already exist)
    File.write(scenarios[scen])
    File.close()

# set up the queue to hold all the urls
q = Queue(maxsize=0)  # infinite max-size

# Populating Queue with tasks
for i, scen in enumerate(scenarios):
    if not multipleYears:
        q.put((i, scen))  # put (i, {scenarioname}) at the end of the queue
    else:
        if str(years[0]) in scen:
            q.put((i, scen))


# Threaded function for queue processing.
def crawl(q, ws, io_lock):
    thread_nr[threading.get_ident()] = len(thread_nr) + 1
    tm.sleep(thread_nr[threading.get_ident()] / 5)
    identifier = thread_nr[threading.get_ident()]
    while not q.empty():
        while True:  # this loop halts new scenarios from being run while the computer is at near-max load
            if psutil.cpu_percent(2) < 85 and psutil.virtual_memory().percent < 80 - 80 / (num_threads + 1):
                break  # it's not a guarantee, but it may prevent complete catastrophe
            print(f"Thread {identifier} waiting for resources")
            tm.sleep(random.randrange(1, 7) * 60)
        scen = q.get()  # fetch new work from the Queue
        global in_progress
        try:
            in_progress.append(scen[1])
            run_scenario(ws, io_lock, scen)
        except gams.workspace.GamsExceptionExecution as e:
            print("!GAMS is complaining! If the error code is 3, it may just be a /0 problem in the output stuff:", repr(e))
        except Exception as e:
            global errors
            errors += 1
            print("! Error in crawler", identifier, "- scenario", scen[0], "exception:", e, "\n")
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            print(format_exc(e))
        finally:
            in_progress.remove(scen[1])
        # since a 2040 run has to come after a 2030 run, lets only add 2040 to the queue after finishing 2030
        # this makes it so that threads don't just sit and wait for some specific scenario to finish before being useful
        if multipleYears:
            year = [s for s in scen[1].split("_") if s.isdigit()][0]
            if int(year) < years[-1]:
                nextyear = years[years.index(int(year))+1]
                nextscenario = scen[1].replace(year, str(nextyear))
                if nextscenario in scenarios:
                    print(f"Putting ({scen[0]+1}, {nextscenario}) in the queue")
                    q.put((scen[0]+1, nextscenario))
                else:
                    print(f"! Did not find {nextscenario} in scenarios")
        q.task_done()  # signal to the queue that task has been processed
    if q.empty():
        print(f"- Queue is now empty -\nIn progress: {', '.join(in_progress)}")
    return True


# Function which gets called to actually run the model
def run_scenario(workspace, io_lock, scen):
    year = int([i for i in scen[1].replace('.', '_').split('_') if "20" in i][0])
    if followUp_run or (multipleYears and year > years[0]):
        files = []
        for file in glob(path+"\\*.gdx"):
            files.append(file.split("\\")[-1])  # building list of existing .gdx files
        if scen[1].replace(f"_{year}",f"_{years[years.index(year)-1]}")+".gdx" not in files:
            print(f"! Did not find {scen[1].replace(str(year),str(years[years.index(year)-1]))}.gdx")
            print(f"! Skipping {scen[1]}")
            return
        try:
            print(f"- Running previousInvestments for {scen[1]}")
            previousInvestments.doItAll(path, scen[1])  # create previousInvestments_***.inc
        except Exception as e:
            print(f"! Failed to run previousInvestments.py for {scen[1]}: \n {format_exc(e)}")

    starttime[scen[0]] = tm.time()
    job = workspace.add_job_from_file(gmsfile)
    # we create a scenario-specific options file to avoid reading the wrong options file
    randint = random.randrange(99999999999)
    f = open(path + "options_" + str(randint) + ".txt", "w")
    f.write("LogOption 2\nLogFile " + scen[1] + ".log\nparallelmode -1")
    f.close()
    opt = workspace.add_options(opt_file=path + "options_" + str(randint) + ".txt")
    # then remove the scenario-specific options file since its not interesting
    os.remove(path + "options_" + str(randint) + ".txt")
    # give gams the variable 'scenarioname' with value scen[1] which is the string
    opt.defines["scenariofile"] = scen[1]
    opt.output = scen[1]  # listing file name (files are called _gams_py_gjo#.lst without this)

    print(f"-- Starting scenario {scen[0]}: {scen[1]} in thread", thread_nr[threading.get_ident()], "at",
          dt.datetime.now().strftime('%H:%M:%S'), "---")
    job.run(opt, create_out_db=False)
    io_lock.acquire()  # we need to make the ouput a critical section to avoid messed up report information
    print("-- Thread", thread_nr[threading.get_ident()], "finished", scen[1], "(#" + str(scen[0]) + ") at",
          dt.datetime.now().strftime('%H:%M:%S'))
    append_to_file("time_to_solve", scen[1], round((tm.time() - starttime[scen[0]]) / 60, 1))
    print("-- Time to solve: ", str(round((tm.time() - starttime[scen[0]]) / 60, 1)), "min")
    io_lock.release()


# cp = ws.add_checkpoint()
starttime = {0: 0.}
in_progress = []
errors = 0

cp = ""
io_lock = threading.Lock()
threads = {}
thread_nr = {}
# Starting worker threads on queue processing
for i in range(num_threads):
    worker = threading.Thread(target=crawl, args=(q, ws, io_lock))
    worker.setDaemon(True)  # setting threads as "daemon" allows main program to
    # exit eventually even if these dont finish correctly.
    worker.start()
print(f'- {num_threads} threads started')
# now we wait until the queue has been processed
q.join()
print('- All tasks completed after', str(round((tm.time() - starttime[0]) / 60, 2)), 'minutes and with', str(errors), "errors.")
