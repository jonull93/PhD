import gdxr
from my_utils import write_inc_from_df_columns
import pandas as pd
from glob import glob
from get_from_gams_db import gdx


def doItAll(gdxpath, scenario):
    if gdxpath[-1] != "\\": gdxpath += "\\"
    data, transInv, life = readResults(gdxpath, scenario)  # search for, and read, previously modelled years of the scenario
    writePreviousInvestmentsInc(data, transInv, life, gdxpath, scenario)  # sum the capacities and write gdx-file for the next
    # model-iteration
    return data  # in case we want to pickle the data or something


def readResults(gdxpath, scenario):  # search for, and read, previously modelled years of the scenario
    # ws = gams.GamsWorkspace(gdxpath)
    # assume that the year part of the scenario name is surrounded by __ (or _.)
    year = [i for i in scenario.replace('.', '_').split('_') if "20" in i and len(i) is 4][0]  # so that this returns an int
    inv = {}  # investments
    eta = {}  # fuel-to-elec efficiency
    transInv = {}  # transmission capacity investments
    data = {}  # combined inv, eta and transInv
    files = []
    for file in glob(gdxpath + "*.gdx"):
        files.append(file.split("\\")[-1])
    for y in range(int(year) - 1, 2019, -1):  # looping through possibly modelled previous years
        possible_scen = scenario.replace(f"_{year}", f"_{y}")  # replace scenario year with previous possible year
        if possible_scen+".gdx" in files:
            with gdxr.GdxFile(gdxpath+possible_scen+".gdx") as f:
                life = gdx(f,"techprop").loc[:,"life"]
                I_reg = gdx(f,"I_reg")
                inv[y] = gdx(f,"v_newcap").level  # (tech,region):level
                inv[y] = inv[y][inv[y].index.isin(I_reg,level=1)]  # filter out regions not in I_reg
                inv[y] = inv[y][inv[y]!=0].to_dict()  # filter out entries with 0 capacity
                eta[y] = gdx(f,"eta_el").loc[:,:,str(y)].to_dict()  # (tech,region):value
                transInv[y] = gdx(f,"v_newcon").level.to_dict()  # (tech_con,region,region):level
                data[y] = {"inv": {key: inv[y][key] for key in inv[y]}, "eta": {key: eta[y][key] for key in inv[y]}}
                # (tech, region):{'inv' & 'eta'}
    if 'life' in locals():
        print(f"previousInvestments.py found {len(data.keys())} previous years for {scenario}")
        return data, transInv, life
    else:
        raise ValueError(f"Jonathan says no previous years were found, in which case you shouldn't call this function \n "
                         f"Looked for precursor to {scenario}.gdx in {files}")


def addEntry(entry, key, dictionary):  # why is there no built-in way to do this
    try:
        dictionary[key] += entry
    except KeyError:
        dictionary[key] = entry


def addToMean(entry, key, dictionary, addedWeight, oldWeight):
    try:
        dictionary[key] = (dictionary[key] * oldWeight[key] + entry * addedWeight) / (oldWeight[key] + addedWeight)
    except KeyError:
        dictionary[key] = entry


def writePreviousInvestmentsInc(data, transInv, life, gdxpath, scenario):  # sum the capacities and write gdx-file for the next model-iteration
    invToSave = {}
    etaToSave = {}
    transInvToSave = {}
    year = int([i for i in scenario.split('_') if "20" in i][0])
    for investmentYear, pair in data.items():
        inv = pair["inv"]
        eta = pair["eta"]
        for key in inv.keys():
            tech, region = key
            if investmentYear + life[tech] >= year:
                addToMean(eta[key], key, etaToSave, inv[key], invToSave)
                addEntry(inv[key], key, invToSave)
        for key in transInv[investmentYear].keys():
            if investmentYear + 40 >= year:  # 40 years lifetime for both types of tech_con
                addEntry(transInv[investmentYear][key], key, transInvToSave)

    df_inv = pd.Series(invToSave).reset_index()
    df_inv.columns = ["tech", "region", "value"]
    df_eta = pd.Series(etaToSave).reset_index()
    df_eta.columns = ["tech", "region", "value"]
    df_trans = pd.Series(transInvToSave).reset_index()
    df_trans.columns = ["tech_con", "I_reg", "I_reg2", "value"]
    write_inc_from_df_columns(gdxpath + "\\Include\\previousInvestments\\", f"{scenario}_inv.inc", df_inv)
    write_inc_from_df_columns(gdxpath + "\\Include\\previousInvestments\\", f"{scenario}_eta.inc", df_eta)
    write_inc_from_df_columns(gdxpath + "\\Include\\previousInvestments\\", f"{scenario}_trans.inc", df_trans)
    #gdxpds.to_gdx({"previousInvestments": df_inv,
    #                 "previousInvestments_eta": df_eta,
    #                 "previousTransmissionInvestments": df_trans},
    #                path=gdxpath + "\\Include\\previousInvestments\\" + f"previousInvestments_{scenario}.gdx")
    return invToSave, df_inv

#path = "C:\\models\\multinode\\"
#path = "C:\\Users\\Jonathan\\multinode\\"
#file = "brit_base_noEV_2040_24h"
#data, transInv, life = readResults(path,file)
#writeGdx(data,transInv,life,path,file)
#writeGdx(data,transInv,life,path,file)