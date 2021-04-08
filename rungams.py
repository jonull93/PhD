# Written by Jonathan Ullmark, please let me know if you found this useful
import datetime as dt
import os
import random
import threading
import time as tm
from itertools import product
from queue import Queue
import psutil
from gams import *
from glob import glob
import previousInvestments
from traceback import format_exc

print("Script started at", dt.datetime.now().strftime('%H:%M:%S'))

if "C18" in os.environ['COMPUTERNAME']:  # This allows you to change path depending on which computer you run script from
    path = "C:\\models\\multinode\\"  # where your main-file is located
elif "PLIA" in os.environ['COMPUTERNAME']:
    path = "C:\\git\\multinode\\"
else:
    path = "D:\\Jonathan\\multinode\\"  # where your main-file is located
ws = GamsWorkspace(path)
gmsfile = "MN_main.gms"  # name of your main-file [NEEDS TO BE EDITED WHEN SETTING SCRIPT UP]
starttime = {0: 0.}
errors = 0


def combinations(parameters):  # Create list of parameter combinations
    return [p for p in product(*parameters)]


years = [2030, 2040, 2050]
regions = ["brit", "brit", "iberia"]  # ["SE2","HU","ES3","IE"]
modes = ["base"]
timeResolution = 12
HBresolutions = [52]
cores_per_scenario = 3  # the 'cores' in gams refers to logical cores, not physical
core_count = psutil.cpu_count()  # add logical=False to get physical cores

# ["pre", "OR","OR_inertia", "inertia","inertia_noSyn"]
# ["leanOR", "OR","OR+inertia","leanOR+inertia", "inertia","inertia_noSyn","inertia_2x","OR+inertia_noDoubleUse"]

scenarios = {}
# looping through regions and modes in this way means that it will first run all "pre",
# then all "OR" and so on, instead of first solving all modes for each region.
# I create my scenario-code by using what is called an fstring.
# This allows me to put variables and if-statements in my text using {}. Very convenient :)

for mode in modes:
    for region in regions:
        for HBres in HBresolutions:
            for year in years:
                scenarioname = f"{region}_{mode}{HBres if 'HB' in mode else ''}_{year}" \
                               f"{'' if timeResolution == 1 else '_' + str(timeResolution) + 'h'}"
                scenarios[scenarioname] = \
                    f"""
$setglobal scenario "{scenarioname}"
$setglobal region {region}
$setglobal heatBalance {'no' if 'noHB' in mode else 'yes'}
$setglobal flexlim {'no' if 'noflex' in mode.lower() else 'yes'}
$setglobal startup no
$setglobal current_year {year}
$setglobal first_iteration {'yes' if year == years[0] else 'no'} //if no -> will try to read previousInvestments.gdx
$setglobal cores {cores_per_scenario}

$setglobal ancillary_services yes
$setglobal OR {"yes" if "OR" in mode else "no"}
$setglobal lean {"yes" if "lean" in mode.lower() else "no"}
$setglobal inertia {"yes" if "inertia" in mode.lower() else "no"}
$setglobal synthetic_inertia {"no" if "noSyn" in mode else "yes"}
$setglobal double_use {"no" if "noDoubleUse" in mode else "yes"}
$setglobal SNSP no

$setglobal inertia_scaling {"2" if "2xInertia" in mode else "1"}
$setglobal forecast_scaling 1
$setglobal flywheel_price_scaling 1
$setglobal sync_cond_price_scaling 1
$setglobal onshore_storage "no"
$setglobal H2demand 0.2
$setglobal EV_AGG {'no' if 'noEV' in scenarioname else 'yes'}

$setglobal savepoint no
$setglobal profiling yes
* Temporal resolution 1, 3 or 6 h
$setglobal hour_resolution {timeResolution}
$setglobal heatBalancePeriods {HBres}
$setglobal toExcel no
$setglobal update_scenario no"""  # [NEEDS TO BE EDITED WHEN SETTING SCRIPT UP]

num_threads = int(min(core_count/cores_per_scenario+1, len(scenarios)/len(years)))
# The "optimal" number of threads depends on your hardware and model
# but nr of cores /2 seems good unless you hit RAM limit

print("Number of scenarios:", len(scenarios))
multipleYears = len(years) > 1
if multipleYears: print("  Multiple years detected, will run previousInvestments.py in-between runs")

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
    while True:  # this loop halts new scenarios from being run while the computer is at near-max load
        if psutil.cpu_percent(2) < 90:  # if more than 90% cpu is used, wait 
            break  # it's not a guarantee, but it may prevent complete catastrophe
        tm.wait(5)
    while not q.empty():
        scen = q.get()  # fetch new work from the Queue
        try:
            run_scenario(ws, io_lock, scen)
        except Exception as e:
            identifier = thread_nr[threading.get_ident()]
            global errors
            errors += 1
            print("! Error in crawler", identifier, "- scenario", scen[0], "exception:", e, "\n")
        q.task_done()  # signal to the queue that task has been processed
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
    if q.empty(): print("--- Queue is now empty ---")
    return True


# Function which gets called to actually run the model
def run_scenario(workspace, io_lock, scen):
    year = int([i for i in scen[1].replace('.', '_').split('_') if "20" in i][0])
    if multipleYears and year > years[0]:
        previousRunIsRan = False
        while not previousRunIsRan:
            files = []
            for file in glob(path+"\\*.gdx"):
                files.append(file.split("\\")[-1])  # building list of existing .gdx files
            if scen[1].replace(str(year),str(years[years.index(year)-1]))+".gdx" in files:
                previousRunIsRan = True
            else:
                print(f"? Did not find {scen[1].replace(str(year),str(years[years.index(year)-1]))}.gdx")
                tm.sleep(random.randrange(8, 32))  # to avoid several threads searching and starting at the same time
        try:
            previousInvestments.doItAll(path, scen[1])  # create previousInvestments.gdx
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
    try:  # these things require job.run to have create_out_db=True (which creates duplicate gdx files)
        if int(job.out_db["ms"][()].value) <= 2 and int(job.out_db["ss"][()].value) <= 2:
            print("  Model- and solvestatus OK!")
        else:
            print(" ! OBS BAD STATUS! Modelstatus: " + str(job.out_db["ms"][()].value) + " and Solvestatus: " + str(
                job.out_db["ss"][()].value), "(1s and 2s are good)")
        print("  Obj: " + str(job.out_db["v_totcost"][()].level))
    except:
        None
    print("-- Time to solve: ", str(round((tm.time() - starttime[scen[0]]) / 60, 1)), "min")
    io_lock.release()


# cp = ws.add_checkpoint()
cp = ""
io_lock = threading.Lock()
threads = {}
thread_nr = {}
# Starting worker threads on queue processing
for i in range(num_threads):
    print('- Starting thread', i + 1)
    worker = threading.Thread(target=crawl, args=(q, ws, io_lock))
    worker.setDaemon(True)  # setting threads as "daemon" allows main program to
    # exit eventually even if these dont finish
    # correctly.
    worker.start()
# now we wait until the queue has been processed
q.join()
print('- All tasks completed after', str(round((tm.time() - starttime[0]) / 60, 2)), 'minutes and with', str(errors), "errors.")
