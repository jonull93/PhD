import gams
import numpy
import pandas
from my_utils import tech_names, EPODs

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
    import string
    for i, set in enumerate([['ES_N','ES_S','SE_S','DE_N',]+[i for i in EPODs if i not in tech_names],
                             list(tech_names.keys()),
                             [f"d{d:03}{h}" for d in range(1,366) for h in string.ascii_lowercase[:24]],  # d001a etc
                             [str(i) for i in range(1, 9)],
                             ['2020', '2025', '2030', '2035', '2040', '2045', '2050'],
                             ['sy1_'+str(year) for year in range(2010,2020)]+[f"{y}-{y+1}" for y in range(1980,2020)],
                             ['OHAC', 'SCDC'],
                             ['life', 'heat_type', 'd-cost', 'OM_var', 'OM_fix', 'LF', 'd', 'fuel']
                             ]):
        # print("checking set",set)
        for item in set:
            # print("checking item", item)
            if item in iterable:
                return ["I_reg", "tech", "timestep", "FR_period", "model_year", "stochastic_scenarios", "tech_con", "tech_prop"][i]
    if len(iterable) > 0: print("found no match for", iterable)
    return ''


def gdx(f, symbol_name, silent=False, error_return=None, keep_na=False, dud_df_return=False, rounding=5):
    expected_a_df = type(dud_df_return) != bool
    try: symbol = f[symbol_name]
    except KeyError:
        if not silent: print(f"Unable to get {symbol_name} from gdx")
        if expected_a_df:
            return dud_df_return
        else:
            return error_return

    symbol_type = type(symbol)
    if symbol_type == pandas.core.series.Series and len(symbol) == 0 and expected_a_df:
        return dud_df_return

    def betterIndex(symbol):
        index_names = [which_set(symbol.index.get_level_values(i).astype(str)) for i in range(symbol.index.nlevels)]
        levels = [symbol.index.get_level_values(i).astype(str) for i in range(symbol.index.nlevels)]
        symbol.index = pandas.MultiIndex.from_arrays(levels, names=index_names)
        if "timestep" in index_names:
            symbol = symbol.unstack(level="timestep", fill_value=0)
        return symbol

    if symbol_type == numpy.ndarray:
        return symbol.astype(str)
    elif symbol_type == pandas.core.frame.DataFrame:
        if type(symbol.index) == pandas.core.indexes.multi.MultiIndex:
            symbol = betterIndex(symbol)
        else:
            symbol.index = symbol.index.astype(str)
        if not keep_na: symbol.fillna(0, inplace=True)
        if expected_a_df:
            symbol = symbol.reindex(index=dud_df_return.index, columns=dud_df_return.columns, fill_value=0)
        symbol = symbol.round(rounding)
    elif symbol_type == pandas.core.series.Series:
        if type(symbol.index) == pandas.core.indexes.multi.MultiIndex:
            symbol = betterIndex(symbol)
        else:
            symbol.index = symbol.index.astype(str)
        if not keep_na: symbol.fillna(0, inplace=True)
        try:
            if expected_a_df: symbol = symbol.reindex(index=dud_df_return.index, columns=dud_df_return.columns, fill_value=0)
        except TypeError:
            print("Failed to reindex:",symbol, "will now try to unstack and reindex again")
            print(symbol.columns)
            symbol = symbol.unstack(level="", fill_value=0)
            symbol = symbol.reindex(index=dud_df_return.index, columns=dud_df_return.columns, fill_value=0)
            print(symbol)
        try:
            symbol = symbol.round(rounding)
        except:
            print(f"Failed to round {symbol_name}")
    return symbol
