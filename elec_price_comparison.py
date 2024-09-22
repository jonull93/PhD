from my_utils import completion_sound, print_magenta, print_cyan, print_yellow, print_red, print_green, print_blue, select_pickle, shorten_year
import pickle
import os
import re
import time
import pandas as pd
import matplotlib.pyplot as plt

# In this file, we want to compare the regional (and demand-weighted total) average electricity prices for the years ’89-’90, ’91-’92 and ’92-’93 and ’94-’95 as well as the All years model-run
if __name__ == "__main__":
    print_magenta(f"Started {__file__} at {time.strftime('%H:%M:%S', time.localtime())}")
    print_magenta(f"Step 1: Select the pickle file to load electricity prices from ")
    pickle_file = select_pickle()
    data = pickle.load(open(pickle_file, "rb"))
    
    # select the model-runs to load from the pickle file
    # option 1: the individual years and all-years
    # option 2: all scenarios including the pattern "..[DIGIT]opt.." or "allopt.." in the name (use regex)
    print_magenta(f"Step 2: Select the model-runs to load from the pickle file")
    print_magenta(f"Option 1: ’89-’90, ’91-’92 and ’92-’93 and ’94-’95 and all-years")
    print_magenta(f"Option 2: all weather-year sets")
    model_runs = input("Enter 1 or 2: ")
    if model_runs == "1":
        years = ["1989-1990", "1991-1992", "1992-1993", "1994-1995"] #r"1989-1990|1989to1990|1991-1992|1991to1992|1992-1993|1992to1993|1994-1995|1994to1995|allyears"
        years = years + [i.replace("-", "to") for i in years] + ["allyears"]
        # search for scenarios that include any string from years
        model_runs = [key for key in data.keys() if any([re.search(year, key) for year in years])]
    elif model_runs == "2":
        model_runs = [key for key in data.keys() if re.search(r"opt\d", key) or re.search(r"allopt", key)] + ["allyears"]
    else:
        raise ValueError(f"Invalid input {model_runs}")
    print_magenta(f"Selected model-runs: {model_runs}")

    # data[model_run]["el_price"] is a df with multiindex (region, year) and columns timestep
    # we want to calculate the average price for each region and year, then combine the years using weights found in data[model_run]['stochastic_probability'] (a series of year: weight)

    # first, calculate the average price for each region and year
    regional_average_prices = {}
    average_prices = {}
    for model_run in model_runs:
        print_magenta(f"Calculating average price for {model_run}")
        regional_average_prices[model_run] = data[model_run]["el_price"].T.mean()
        weights = data[model_run]["stochastic_probability"]
        average_prices[model_run] = (regional_average_prices[model_run]*weights).groupby(level=0).sum()
        print(average_prices[model_run])
