#Written by Jonathan Ullmark, please let me know if you found this useful
from gams import *
import time as tm
import datetime as dt
import os
import sys
import threading
from queue import Queue
import random

print("Script started at",dt.datetime.now().strftime('%H:%M:%S'))
path = "Z:\\models\\" #where your main-file is located
ws = GamsWorkspace(path)
gmsfile = "total_optimum.gms" #name of your main-file
starttime = {}
errors=0

#Create dictionary of scenario-code
regions = ["ES3"]#, "HU", "IE", "SE2"]
modes = ["leanOR"]#,"inertia","leanOR+inertia"]
i=0
scenarios = {}
for mode in modes:
    for region in regions: #looping through regions and modes in this way means that it will first run all "pre", then all "OR" and so on, instead of first solving all modes for each region
        #I create my scenario-code by using what is called an fstring. This allows me to put variables and if-statements in my string-text. Very convenient :)
        scenarios[region+"_"+mode+"_test"] =  \
        f"""
$setglobal tot_opt "{region}_{mode}" 
$setglobal ireg {region}
$setglobal flexlim yes
$setglobal which_year 2050
$setglobal cores 4
$setglobal OR {"yes" if "OR" in mode else "no"}
$setglobal lean {"yes" if "lean" in mode else "no"}
$setglobal inertia {"yes" if "inertia" in mode else "no"}
$setglobal inertia_scaling {"2" if "2x" in mode else "1"}
$setglobal forecast_scaling 1

$setglobal synthetic_inertia {"no" if "noSyn" in mode else "yes"}
$setglobal double_use {"no" if "noDoubleUse" in mode else "yes"}

$setglobal SNSP no
* Temporal resolution 1, 3 or 6 h
$setglobal hour_resolution 100"""
        i+=1

#create .inc file for each scenario
for scen in scenarios:
    File = open(path+"Include\\scenarios\\"+scen+".inc","w") #here you can choose where the scenario-files should be placed (OBS: folder must already exist)
    File.write(scenarios[scen])
    File.close()

#set up the queue to hold all the urls
q = Queue(maxsize=0) #infinite max-size
# Use many threads (4 max, or one for each scenario)
num_theads = min(5, len(scenarios))

#Populating Queue with tasks
for i,scen in enumerate(scenarios):
    #need the index and the scenarioname in each queue item.
    q.put((i,scen)) #put (i, {scenarioname}) at the end of the queue

# Threaded function for queue processing.
def crawl(q,ws, cp, io_lock):
    antistuck = 0 #I don't like uncontrolled while-loops so this is just a comfort-of-mind thing
    thread_nr[threading.get_ident()]=len(thread_nr)+1
    while not q.empty() or antistuck < len(scenarios)*2:
        scen = q.get()  #fetch new work from the Queue
        try:
            #print("Requested scenario # " + str(scen[0]))
            run_scenario(ws, cp, io_lock, scen)
        except Exception as e:
            identifier = "Error in crawler"
            global errors
            errors += 1
            print(identifier, "scenario",scen[0],"exception:",e)
        q.task_done()   #signal to the queue that task has been processed
        antistuck += 1
    if antistuck > len(scenarios)*2-2: print("OBS: the crawl function hit its antistuck limit!")
    return True

#Function which does gets called to actually run the model
def run_scenario(workspace, checkpoint, io_lock, scen):
    starttime[scen[0]] = tm.time()
    job = workspace.add_job_from_file(gmsfile)
    randint = random.randrange(99999999999) #we create a scenario-specific options file with this identifier (to avoid reading the wrong options file)
    f = open(path+"options_"+str(randint)+".txt","w")
    f.write("LogOption 2\nLogFile "+scen[1]+".log")
    f.close()
    opt = workspace.add_options(opt_file=path+"options_"+str(randint)+".txt")
    os.remove(path+"options_"+str(randint)+".txt") #then remove the scenario-specific options file since its not interesting
    opt.defines["scenariofile"] = scen[1] #give gams the variable 'scenarioname' with value scen[1]
    print(" --- Starting scenario", scen[0], "in thread",thread_nr[threading.get_ident()],"---")
    job.run(opt, create_out_db=False)
    io_lock.acquire() # we need to make the ouput a critical section to avoid messed up report informations
    print("Thread", thread_nr[threading.get_ident()], "finished scenario",scen[1],"(#"+str(scen[0])+") at", dt.datetime.now().strftime('%H:%M:%S'), "...")
    try: #these things require job.run to NOT have create_out_db=False
        if job.out_db["ms"][()].value <= 2 and job.out_db["ss"][()].value <= 2:
            print("  Model- and solvestatus OK!")
        else:
            print("  OBS BAD STATUS! Modelstatus: " + str(job.out_db["ms"][()].value) + " and Solvestatus: " + str(job.out_db["ss"][()].value),"(1s and 2s are good)")
        print("  Obj: " + str(job.out_db["vtotcost"][()].level))
    except:
        None
    print("  Time to solve: ",str(round((tm.time()-starttime[scen[0]])/60,1)),"min")
    io_lock.release()

#cp = ws.add_checkpoint()
cp = ""
io_lock = threading.Lock()
threads = {}
thread_nr={}
#Starting worker threads on queue processing
for i in range(num_theads):
    print('Starting thread', i+1)
    worker = threading.Thread(target=crawl, args=(q, ws, cp, io_lock))
    worker.setDaemon(True)    #setting threads as "daemon" allows main program to 
                              #exit eventually even if these dont finish 
                              #correctly.
    worker.start()
#now we wait until the queue has been processed
q.join()
print('All tasks completed after',str(round((tm.time()-starttime[0])/60,2)),'minutes and with',str(errors),"errors.")