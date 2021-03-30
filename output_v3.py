# from __future__ import print_function
import pickle  # for dumping and loading variable to/from file
import sys
import threading
import time as tm
import traceback
from datetime import datetime
from multiprocessing import cpu_count
from queue import Queue
import pandas as pd
from gams import *
from my_utils import TECH, order
from main import overwrite, path, indicators, old_data, run_output, cases, name, gdxpath

try:
    _ = path  # this will work if file was run from main since path is defined there
except:
    exec(open("./main.py").read())  # if not, then run main first
    exit()  # then do NOT run code again since main.py already executes this file once

print("Excel-writing script started at", datetime.now().strftime('%H:%M:%S'))


def print_gen(sheet, row, entry, data):
    gen_df = pd.DataFrame(entry)
    gen_df.transpose().to_excel(writer, sheet_name=sheet, freeze_panes=(0, 2), header=data["gamsTimestep"], startrow=row,
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
        if len(sys.argv) > 1:
            ws = GamsWorkspace(system_directory=sys.argv[1], working_directory=gdxpath)
        else:
            ws = GamsWorkspace(gdxpath)
        try:
            db = ws.add_database_from_gdx(k + ".gdx")
        except:
            print("gdx file not found for: " + k + "\n")
            return False

        i_reg = [rec.keys[0] for rec in db["I_reg"]]
        gamsTimestep = [i.keys[0] for i in db["timestep"]]  # "h0001" or "d001a"
        #head = [i[1:] for i in gamsTimestep]  # "0001"
        iter_t = range(len(gamsTimestep))
        timestep = [i+1 for i in iter_t]  # 1
        TT = 8760 / len(gamsTimestep)
        unsorted_cap = {}
        for rec in db["v_newcap"]:  # BUILDING CAPACITY VARIABLE
            if rec.keys[1] == i_reg:
                unsorted_cap[rec.keys[0]] = rec.level

        cap = {i: unsorted_cap[i] for i in order if i in unsorted_cap}
        allwind = [rec.keys[0] for rec in db["allwind"] if rec.keys[0] in cap]
        cost_tot = [rec.level for rec in db["v_totcost"]]
        # tech = [x.keys[0] for x in db["tech"]]
        allthermal = [rec.keys[0] for rec in db["allthermal"]]
        #        allCCS = [rec.keys[0] for rec in db["allCCS"]]
        #        tech_slowslow = [rec.keys[0] for rec in db["tech_slowslow"]]
        allstorage = [rec.keys[0] for rec in db["allstorage"]]
        withdrawal_rate = {rec.keys[0]: rec.value for rec in db["withdrawal_rate"] if rec.keys[0] in allstorage}

        try:
            OR_period = [rec.keys[0] for rec in db["OR_period"]]
            PS = True
        except:
            PS = False

        if PS:
            ESS = [rec.keys[0] for rec in db["ESS"]]
            v_PS_ESS_up = {i: {j: [] for j in OR_period} for i in ESS}
            for rec in db["v_PS_ESS_up"]:
                v_PS_ESS_up[rec.keys[0]][int(rec.keys[3])].append(rec.level)

            ramp = pickle.load(open("PickleJar\\data_ramp2.pickle", "rb"))

            LF_profile = {"wind": [sum([ramp["wind"][i_reg][i][t] * cap[i] for i in ramp["wind"][i_reg] if "WO" in i]) for t in
                                   iter_t],
                          "solar": [sum([ramp["solar"][i_reg][i][t] * cap[i] * FLH[i] for i in ramp["solar"][i_reg] if "PV" in i])
                                    for t in iter_t],
                          "demand": [rec.value for rec in db["PS_OR_min"] if rec.keys[0] == i_reg]}

        #        min_load = {rec.keys[0]:rec.value for rec in db["techprop"] if rec.keys[1]=="minload"}
        #        inv_cost = {rec.keys[0]:rec.value for rec in db["techprop"] if rec.keys[1]=="inv_cost"}
        #        annuity = {rec.keys[0]:rec.value for rec in db["annuity"]}
        tech_el = [rec.keys[0] for rec in db["tech_el"]]
        VRE_tech = allwind + [TECH.SOLAR_OPT, TECH.SOLAR_TRACKING]
        wind_profile = {i: [] for i in allwind}
        PV_profile = {i: [0 for x in range(0, timestep[-1])] for i in [TECH.SOLAR_OPT, TECH.SOLAR_TRACKING]}
        PV_FLH = {i.keys[0]: i.value for i in db["FLH"] if "PV_" in i.keys[0]}
        FLH = {i.keys[0]: i.value for i in db["FLH"]}
        el_price = [rec.marginal / TT * -1e6 for rec in db["EQU_elecbalance"] if rec.keys[0] == i_reg]
        discharge = {i: [rec.level for rec in db["v_discharge"] if rec.keys[0] == i and rec.keys[1] == i_reg] for i in
                     [TECH.BATTERY, "bat_PS"]}

        charge = {i: [rec.level for rec in db["v_charge"] if rec.keys[0] == i] for i in [TECH.BATTERY, "bat_PS"]}
        #        eta_discharge = {rec.keys[0]:rec.value for rec in db["eta_discharge"]}
        #        eta_charge = {rec.keys[0]:rec.value for rec in db["eta_charge"]}
        demand = [db["demand"][i_reg].value]
        load_profile = [rec.value * demand[0] for rec in db["demandprofile_average"] if rec.keys[0] == i_reg]

        try:
            OR_up_min = [rec.level for rec in db["vPS_OR_up"] if rec.keys[0] == i_reg]
            #            PS_OR_spin_up = [rec.level for rec in db["vPS_OR_spin_up"]  if rec.keys[0] == i_reg]
            PS_OR_cost_up = {i + 1: [] for i in range(7)}
            for rec in db["EQU_PS_OR_supply"]:
                PS_OR_cost_up[int(rec.keys[2])].append(rec.marginal / TT * -1e6)
        except Exception as exception:
            print("ran into exception when making OR lists:", exception)
            OR_up_min = []
            # PS_OR_spin_up = []
            PS_OR_cost_up = []

        for rec in db["profile"]:  # BUILDING PV/WIND PROFILES
            if rec.keys[0] in allwind and rec.keys[1] == i_reg:
                wind_profile[rec.keys[0]].append(rec.value)
            elif rec.keys[0] in PV_profile and rec.keys[
                1] == i_reg:  # PV_profile has to be built differently since the profile for PV is sparse
                PV_profile[rec.keys[0]][
                    int(rec.keys[2][1:]) - 1] = rec.value  # int(rec.keys[2][1:]) converts "h0152" to 152

        wind_FLH = {i: 0. for i in allwind}
        for t in timestep:
            for i in [j for j in wind_FLH if cap[j] > 0]:
                wind_FLH[i] += wind_profile[i][t - 1]


        unsorted_gen = {}
        VRE_tot = 0.
        wind_tot = 0.
        solar_tot = 0.
        el_tot = 0.
        for rec in db["vgen"]:
            if rec.keys[0] in cap and cap[rec.keys[0]] > 0 and rec.keys[1] == i_reg:
                # Counting all renewable generation (VRE, wind, solarheat)
                if rec.keys[0] in VRE_tech:
                    VRE_tot += rec.level
                    if rec.keys[0] in allwind:
                        wind_tot += rec.level
                    elif "PV_" in rec.keys[0]:
                        solar_tot += rec.level
                # Counting all electricity, heat, CHP and PtH generation
                if rec.keys[0] in tech_el:
                    el_tot += rec.level
                # Building generation dictionary as gen[(typesys, tech)] = [list with generation for each hour]
                try:
                    unsorted_gen[rec.keys[0]].append(rec.level)
                except:
                    unsorted_gen[rec.keys[0]] = [rec.level]

        gen = {i: unsorted_gen[i] for i in order if i in unsorted_gen}
        for i in discharge:
            if cap[i] > 0:
                gen[i + '_discharge'] = [discharge[i][j] - charge[i][j] for j in range(len(discharge[i]))]

                # real_FLH = {i:sum([j for j in gen[i]])/cap[i] for i in cap if cap[i]>0}

        curtailment_profile = [0 for x in range(0, len(timestep))]
        for i in allwind + list(PV_profile):
            for t in range(0, len(timestep)):
                if i in allwind and cap[i] > 0:
                    curtailment_profile[t] += round(wind_profile[i][timestep[t] - 1] * cap[i] - gen[i][t], 4)
                if i in PV_profile and cap[i] > 0:
                    curtailment_profile[t] += round(PV_profile[i][timestep[t] - 1] * cap[i] * PV_FLH[i] - gen[i][t], 4)

        spin = {}
        for rec in [i for i in db["VSPIN"] if i.keys[0] in cap and cap[i.keys[0]] > 0]:
            # if rec.keys[0] in allthermal and rec.keys[0] not in [i for i in tech_slowslow if i not in allCCS] and rec.keys[0] in cap and cap[rec.keys[0]]>0:
            if rec.keys[0] in spin:
                spin[rec.keys[0]].append(rec.level)
            else:
                spin[rec.keys[0]] = [rec.level]

        # == OR ==
        ramp_factor = {tech: [0 for i in range(7)] for tech in spin}
        for rec in db["PS_timetable_online"]:
            tech = rec.keys[0]
            timeframe = int(rec.keys[1]) - 1  # -1 since python counts from 0 unlike gams
            if tech in ramp_factor:
                ramp_factor[tech][timeframe] = rec.value
            else:
                ramp_factor[tech] = [0 for i in range(7)]
                ramp_factor[tech][timeframe] = rec.value

        startup_factor = {tech: [0 for i in range(7)] for tech in spin}
        for rec in db["PS_timetable_offline"]:
            tech = rec.keys[0]
            timeframe = int(rec.keys[1]) - 1
            if tech in startup_factor:
                startup_factor[tech][timeframe] = rec.value
            else:
                startup_factor[tech] = [0 for i in range(7)]
                startup_factor[tech][timeframe] = rec.value

        OR_up = {i: {} for i in
                 range(7)}  # lets make one version for each timeframe so that ramp-rates can be accounted for
        for timeframe in range(7):
            for tech in spin:
                OR_up[timeframe][tech] = [min(spin[tech][t] - gen[tech][t], cap[tech] * ramp_factor[tech][timeframe])
                                          for t in range(len(gen[tech]))]
                if sum(startup_factor[tech]) > 0:
                    OR_up[timeframe][tech + "_offline"] = [(cap[tech] - spin[tech][t]) * startup_factor[tech][timeframe]
                                                           for t in range(len(gen[tech]))]
            if TECH.HYDRO in cap and cap[TECH.HYDRO] > 0:
                OR_up[timeframe][TECH.HYDRO] = [cap[TECH.HYDRO] - gen[TECH.HYDRO][t] for t in range(len(gen[TECH.HYDRO]))]
            if TECH.HYDRO_IMPORT in cap and cap[TECH.HYDRO_IMPORT] > 0:
                OR_up[timeframe][TECH.HYDRO_IMPORT] = [cap[TECH.HYDRO_IMPORT] - gen[TECH.HYDRO_IMPORT][t] for t in
                                                       range(len(gen[TECH.HYDRO_IMPORT]))]
            OR_up[timeframe]["curtailment"] = curtailment_profile

        for t in iter_t:
            if TECH.BATTERY in unsorted_gen:
                if unsorted_gen[TECH.BATTERY][t] <= cap[TECH.BATTERY] * withdrawal_rate[TECH.BATTERY]:
                    for timeframe in range(7):
                        try:
                            OR_up[timeframe][TECH.BATTERY].append(
                                min(unsorted_gen[TECH.BATTERY][t], cap[TECH.BATTERY_CAP]) + charge[TECH.BATTERY][t] - discharge[
                                    TECH.BATTERY][t])
                        except Exception as exception:
                            if TECH.BATTERY not in exception.args: print("Couldn't append to OR_up list.", exception)
                            OR_up[timeframe][TECH.BATTERY] = [
                                min(unsorted_gen[TECH.BATTERY][t], cap[TECH.BATTERY_CAP]) + charge[TECH.BATTERY][t] - discharge[
                                    TECH.BATTERY][t]]
                    # LF_down[TECH.BATTERY].append(cap[TECH.BATTERY]/withdrawal_rate[TECH.BATTERY])
                else:
                    for timeframe in range(7):
                        try:
                            OR_up[timeframe][TECH.BATTERY].append(
                                cap[TECH.BATTERY] * withdrawal_rate[TECH.BATTERY] + charge[TECH.BATTERY][t] -
                                discharge[TECH.BATTERY][t])
                        except:
                            OR_up[timeframe][TECH.BATTERY] = [
                                cap[TECH.BATTERY] * withdrawal_rate[TECH.BATTERY] + charge[TECH.BATTERY][t] -
                                discharge[TECH.BATTERY][t]]
                    # LF_down[TECH.BATTERY].append(cap[TECH.BATTERY] - unsorted_gen[TECH.BATTERY][t])
            if TECH.FUEL_CELL in cap and cap[TECH.FUEL_CELL] > 0:
                # LF_down[TECH.FUEL_CELL].append(gen[TECH.FUEL_CELL][t])
                if unsorted_gen[TECH.H2_STORAGE][t] > cap[TECH.FUEL_CELL]:
                    for timeframe in range(7):
                        try:
                            OR_up[timeframe][TECH.FUEL_CELL].append(cap[TECH.FUEL_CELL] - gen[TECH.FUEL_CELL][t])
                        except:
                            OR_up[timeframe][TECH.FUEL_CELL] = cap[TECH.FUEL_CELL] - gen[TECH.FUEL_CELL][t]
                else:
                    for timeframe in range(7):
                        try:
                            OR_up[timeframe][TECH.FUEL_CELL].append(
                                max(unsorted_gen[TECH.H2_STORAGE][t] - gen[TECH.FUEL_CELL][t], 0))
                        except:
                            OR_up[timeframe][TECH.FUEL_CELL] = max(unsorted_gen[TECH.H2_STORAGE][t] - gen[TECH.FUEL_CELL][t], 0)

        # == INERTIA ==
        synthetic_tech = allwind + [TECH.BATTERY, TECH.FLYWHEEL]
        nosyn = "nosyn" in k.lower()
        inertia = {i: [] for i in gen if
                   i in allthermal + allwind + [TECH.FLYWHEEL, TECH.BATTERY, TECH.SYNCHRONOUS_CONDENSER, TECH.HYDRO,
                                                TECH.HYDRO_IMPORT] and cap[i]
                   > 0}
        inertia_factor = {i: 0. for i in gen if i in allthermal + allwind + [TECH.HYDRO, TECH.HYDRO_IMPORT]}
        for i in allwind: inertia_factor[i] = 0.13
        for i in allthermal: inertia_factor[i] = 0.32
        inertia_factor[TECH.NUCLEAR] = 0.48
        inertia_factor[TECH.SYNCHRONOUS_CONDENSER] = 0.48
        inertia_factor[TECH.HYDRO] = 0.24
        inertia_factor[TECH.HYDRO_IMPORT] = 0.24
        if nosyn:
            for tech in synthetic_tech:
                inertia.pop(tech, None)

        for tech in [i for i in inertia if cap[i] > 0]:
            if tech in allthermal:
                inertia[tech] = [spin[tech][t] * inertia_factor[tech] for t in iter_t]
            elif tech in [TECH.HYDRO, TECH.HYDRO_IMPORT]:
                inertia[tech] = [gen[tech][t] * inertia_factor[tech] for t in iter_t]
            elif tech in allwind:
                inertia[tech] = [gen[tech][t] * inertia_factor[tech] for t in iter_t]
            elif tech in [TECH.FLYWHEEL]:
                inertia[tech] = [cap[tech] * 6 for t in iter_t]
            elif tech in [TECH.SYNCHRONOUS_CONDENSER]:
                inertia[tech] = [cap[tech] * inertia_factor[tech] for t in iter_t]
            elif tech in [TECH.BATTERY]:
                inertia[tech] = [max(min(cap[TECH.BATTERY_CAP], gen[tech][t] * 60) + charge[tech][t] - discharge[tech][t], 0)
                                 for t in iter_t]

        # print(k,unsorted_cap[TECH.FLYWHEEL],cap[TECH.FLYWHEEL],sum(inertia.get(TECH.FLYWHEEL,[0])))
        try:
            inertia["tot"] = [sum(inertia[tech][t] for tech in inertia) for t in iter_t]
        except Exception as exception:
            print(" !! INERTIA TOT ERROR", {i: cap[i] for i in inertia}, {i: len(inertia[i]) for i in inertia}, exception)

        # inertia["tot"] = [rec.level for rec in db["vPS_inertia"]]
        # e = 0
        # for t in range(0,800,10):
        #    if round(sum(inertia[tech][t] for tech in inertia if tech!="tot"),2) != round(inertia["tot"][t],2):
        #        e+=1
        #        if e == 1: print(k,{tech:round(inertia[tech][t],2) for tech in inertia})
        # if e > 0:
        #    print("!! INERTIA MISMATCH IN",k,f"FOR {e}/80 hours, removing bat from inertia if noSyn")

        totwindcap = 0.
        # totwind = 0. #weighted by cap
        expwind = 0.
        for i in allwind:
            totwindcap += (cap[i])
            expwind += wind_FLH[i] * cap[i]
            # if cap[i] > 0:
            # avgwind += sum(gen[i])

        expsol = sum([cap[t] * PV_FLH[t] for t in PV_profile])
        if expsol > 0:
            solcurt = 1 - solar_tot / expsol
        else:
            solcurt = 0
        if expwind > 0:
            windcurt = 1 - wind_tot / expwind
        else:
            windcurt = 0
        curtailment = {"wind": windcurt, "solar": solcurt, "tot": 1 - (wind_tot + solar_tot) / (expwind + expsol)}

        VRE_share = [VRE_tot / el_tot]
        wind_share = [wind_tot / el_tot]
        solar_share = [solar_tot / el_tot]
        bat = [str(round(cap[TECH.BATTERY], 2)) + " / " + str(round(cap[TECH.BATTERY_CAP], 2))]
        flywheel = [round(cap[TECH.FLYWHEEL], 3)]
        sync_cond = [round(cap[TECH.SYNCHRONOUS_CONDENSER], 3)]
        FC = cap[TECH.FUEL_CELL]
        if TECH.H2_STORAGE in cap:
            H2store = cap[TECH.H2_STORAGE]  # +cap["H2LRC"]
        else:
            H2store = 0.

        netload = [load_profile[t] - sum([gen[i][t] for i in allwind + [TECH.SOLAR_OPT] if cap[i] > 0]) for t in iter_t]
        newdata[k] = dict(zip(
            indicators +
            ["gamsTimestep",
             "cap",
             "gen",
             "VRE_share",
             "wind_share",
             "solar_share",
             "curtailment",
             "el_price",
             "load_profile",
             "allwind",
             "OR_up",
             "netload",
             "PS_OR_cost_up",
             "LF_profile",
             "vPS_ESS_up",
             "OR_up_min",
             "el_tot",
             "inertia"],
            [cost_tot,
             VRE_share,
             wind_share,
             solar_share,
             curtailment,
             # flywheel,
             sync_cond,
             bat,
             # FC',
             H2store] +
            [gamsTimestep,
             cap,
             gen,
             VRE_share,
             wind_share,
             solar_share,
             curtailment,
             el_price,
             load_profile,
             allwind,
             OR_up,
             netload,
             PS_OR_cost_up,
             LF_profile,
             vPS_ESS_up,
             OR_up_min,
             el_tot,
             inertia]))
        # print("Created returndata containing:",newdata[k].keys())
        # time_for_reading = str(round(tm.time()-time,1))
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
        if isinstance([], ind_type):  # this if-statement makes sure that the print_num always gets a list and not a float or int
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

    print_cap({x: y for x, y in cap.items() if y > 0}, scen, len(gen) + len(OR_up) + len(inertia) + len(data["vPS_ESS_up"]) + 15,
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
