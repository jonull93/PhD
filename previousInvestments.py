import gams
import gdxpds
import pandas as pd


def doItAll(gdxpath, scenario):
    data, transInv, life = readResults(gdxpath, scenario)  # search for, and read, previously modelled years of the scenario
    writeGdx(data, transInv, life, gdxpath, scenario)      # sum the capacities and write gdx-file for the next
    # model-iteration
    return data     # in case we want to pickle the data or something


def readResults(gdxpath, scenario):  # search for, and read, previously modelled years of the scenario
    ws = gams.GamsWorkspace(gdxpath)
    # assume that the year part of the scenario name is surrounded by __ (or _.)
    year = [i for i in scenario.replace('.', '_').split('_') if "20" in i][0]  # so that this returns an int
    inv = {}  # investments
    eta = {}  # fuel-to-elec efficiency
    transInv = {}  # transmission capacity investments
    data = {}  # combined inv, eta and transInv
    for y in range(year-1, 2019, -1):  # looping through possibly modelled previous years
        # assume that the old scenario name was X_2030 if the new one is X_2040
        possible_scen = scenario.replace(str(year), str(y))
        try:  # if the file exists, save investment
            db = ws.add_database_from_gdx(possible_scen + ".gdx")
            tech = [i for i in db["tech"]]
            life = {rec.keys[0]: rec.value for rec in db["techprop"] if rec.keys[1] == "life"}
            I_reg = [i for i in db["I_reg"]]
            inv[y] = dict((tuple(rec.keys), rec.level) for rec in db["vnewcap"])  # (tech,region):level
            eta[y] = dict((tuple(rec.keys), rec.level) for rec in db["eta_el"])  # (tech,region):level
            transInv[y] = dict((tuple(rec.keys), rec.level) for rec in db["vnewcon"])  # (tech,region,region):level
            data[y] = dict((key, {"inv": inv[y][key],
                                  "eta": eta[y][key]}) for key in inv[y])  # (tech, region):{'inv' & 'eta'}
        except:
            continue
    if life in locals():
        return data, transInv, life
    else:
        raise ValueError("Jonathan says no previous years were found, in which case you shouldn't call this function")


def addEntry(entry, key, dictionary):  # why is there no built-in way to do this
    try: dictionary[key] += entry
    except KeyError: dictionary[key] = entry


def addToMean(entry, key, dictionary, addedWeight, oldWeight):
    try: dictionary[key] = (dictionary[key]*oldWeight + entry*addedWeight)/(oldWeight + addedWeight)
    except KeyError: dictionary[key] = entry


def writeGdx(data, transInv, life, gdxpath, scenario):  # sum the capacities and write gdx-file for the next model-iteration
    invToSave = {}
    etaToSave = {}
    transInvToSave = {}
    year = [i for i in scenario.split('_') if "20" in i]
    for investmentYear, pair in data.items():
        inv = pair["inv"]
        eta = pair["eta"]
        for key in inv.keys():
            tech, region = key
            if investmentYear + life[tech] >= year:
                addToMean(eta[key], key, etaToSave, inv[key], invToSave[key])
                addEntry(inv[key], key, invToSave)
        for key in transInv[investmentYear].keys():
            if investmentYear + 40 >= year:  # 40 years lifetime for both types of tech_con
                addEntry(transInv[investmentYear], key, transInvToSave)

    df_inv = pd.Series(invToSave).reset_index()
    df_inv.columns = ["tech", "region", "value"]
    df_eta = pd.Series(etaToSave).reset_index()
    df_eta.columns = ["tech", "region", "value"]
    df_trans = pd.Series(etaToSave).reset_index()
    df_trans.columns = ["tech_con", "I_reg", "I_reg2", "value"]
    gdxpds.to_excel({"previousInvestments": df_inv,
                     "previousInvestments_eta": df_eta,
                     "previousTransmissionInvestments": df_eta},
                    path=gdxpath + f"previousInvestments_{scenario}.gdx")
