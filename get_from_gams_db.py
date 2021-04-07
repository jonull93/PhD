import gams
import numpy
import pandas

class GamsSymbol(object):
    def __init__(self, symbol):
        self.dimensions = symbol.domains_as_strings
        self.symbol = symbol

    def __iter__(self):
        return self

    def __next__(self):
        record = self.symbol.next()
        return JD[type(self.symbol)](record)


class GamsVariable(object):
    def __init__(self, record):
        self.name = "hi"
        self.keys = record.keys
        self.level = record.level
        self.marginal = record.marginal
        self.lower = record.lower
        self.upper = record.upper
        self.scale = record.scale


class GamsParameter(object):
    def __init__(self, record):
        self.name = "hi"
        self.value = record.value


class GamsEquation(object):
    def __init__(self, record):
        self.name = "hi"
        self.level = record.level
        self.marginal = record.marginal
        self.lower = record.lower
        self.upper = record.upper
        self.scale = record.scale


class GamsSet(object):
    def __init__(self, record):
        self.name = "hi"
        self.keys = record.keys
        self.text = record.text


JD = {
    gams.database.GamsSet: GamsSet,
    gams.database.GamsEquation: GamsEquation,
    gams.database.GamsParameter: GamsParameter,
    gams.database.GamsVariable: GamsVariable,
      }


def get_from_db(db, symbol_name):
    try:
        symbol = db.get_symbol(symbol_name)
        return GamsSymbol(symbol)
    except gams.workspace.GamsException:
        print(f"Couldn't get {symbol_name} from db")
        return None


def which_set(iterable):
    for i, set in enumerate([['UK2','UK3','IE','ES3', 'ES_N','SE3','SE_S','PT','DE_N','FI'],
                             ['b','bat','W_CHP','WOFF','WONA4','PVA1','sync_cond','WONA2', 'WONA3', 'WONB5','H2store',],
                             ['d001a','d001','d060a','d005b', 'd006a', 'd006a', 'd007b', 'd008a','d360a','d043', 'd057', 'd078'],
                             ['1','2','5','6'],
                             ['2025', '2030', '2035', '2040', '2045', '2050'],
                             ['OHAC', 'SCDC']]):
        #print("checking set",set)
        for item in set:
            #print("checking item", item)
            if item in iterable:
                return ["I_reg","tech","timestep","OR_period","year","tech_con"][i]
    if len(iterable) > 0: ("found no match for",iterable)
    return ''


def gdx(f, symbol_name):
    symbol = f[symbol_name]
    symbol_type = type(symbol)

    def betterIndex(symbol):
        index_names = [which_set(symbol.index.get_level_values(i).astype(str)) for i in range(symbol.index.nlevels)]
        levels = [symbol.index.get_level_values(i).astype(str) for i in range(symbol.index.nlevels)]
        symbol.index = pandas.MultiIndex.from_arrays(levels, names=index_names)
        if "timestep" in index_names:
            symbol = symbol.unstack(level="timestep",fill_value=0)
        return symbol
    if symbol_type == numpy.ndarray:
        return symbol.astype(str)
    elif symbol_type == pandas.core.frame.DataFrame:
        if type(symbol.index) == pandas.core.indexes.multi.MultiIndex:
            symbol = betterIndex(symbol)
        else:
            symbol.index = symbol.index.astype(str)
    elif symbol_type == pandas.core.series.Series:
        if type(symbol.index) == pandas.core.indexes.multi.MultiIndex:
            symbol = betterIndex(symbol)
        else:
            symbol.index = symbol.index.astype(str)
    return symbol
