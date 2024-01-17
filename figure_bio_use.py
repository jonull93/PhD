from my_utils import completion_sound, print_magenta, print_cyan, print_yellow, print_red, print_green, print_blue, select_pickle, shorten_year
import pickle
import os
import time
import pandas as pd
import matplotlib.pyplot as plt

if __name__ == "__main__":
    print_magenta(f"Started {__file__} at {time.strftime('%H:%M:%S', time.localtime())}")
    print_magenta(f"Step 1: Select the pickle file to load biomass use from")
    pickle_file = select_pickle()
    # step 2: select model_run/scenario
    data = pickle.load(open(pickle_file, "rb"))
    if "allyears" in data.keys():
        print_yellow(f"  allyears is available, selecting that one")
        model_run = "allyears"
    else:
        print_magenta(f"Step 2: Select the model_run/scenario to load biomass use from")
        model_runs = list(data.keys())
        for i, model_run in enumerate(model_runs):
            print_yellow(f"  {i+1}: {model_run}")
        choice = input("  Enter the number of the model_run/scenario to load biomass use from: ")
        model_run = model_runs[int(choice)-1]
        print_yellow(f"  Selected {model_run}")
        # step 3: select year (defaults are 1: 1996-1997 and 2002-2003, 2: 2016-2017, 3: all years, 4: pick from list)
        # or, if allyears is available, pick that one and continue
    
    print_magenta(f"Step 3: Select the years to load biomass use from")
    print_yellow(f"  1: 1996-1997 and 2002-2003")
    print_yellow(f"  2: 2016-2017")
    print_yellow(f"  3: all years")
    print_yellow(f"  4: pick from list")
    choice = input("  Pick your choice: ")
    allyears = False
    if choice == "1":
        years = ["1996-1997", "2002-2003"]
    elif choice == "2":
        years = ["2016-2017"]
    elif choice == "3":
        years = list(data[model_run]["bio_use"].keys())
        allyears = True
    elif choice == "4":
        years = []
        for i, year in enumerate(data[model_run].keys()):
            print_yellow(f"  {i+1}: {year}")
        choice = input("  Enter the number of the year to load biomass use from: ")
        years.append(list(data[model_run].keys())[int(choice)-1])
    else:
        print_red(f"  Invalid choice: {choice}")
        exit()
    print_yellow(f"  Selected {years}")
    figure_path = f"figures/bio use/{model_run}"
    # make the figure_path silently
    os.makedirs(figure_path, exist_ok=True)
    # two plots should be made: one with biomass use aggregated over every 24 hours and plotted as a line, and one with biomass use aggregated over every 168 hours and plotted as bars
    # bio use is taken from data[model_run]["gen"] which is a df with three indices: tech, I_reg, stochastic_scenarios
    # the techs to read from are "WG", "WG_peak" and "WG_CHP"
    # the I_regs should be combined
    # the "stochastic_scenarios" is the year
    # each tech has a different efficiency which we must divide that generation by: CHP=0.492604, peak=0.420606, WG=0.610606
    efficiency = {"WG": 0.610606, "WG_peak": 0.420606, "WG_CHP": 0.492604}
    time_resolution_modifier = data[model_run]["TT"]
    print_magenta(f"  Time resolution modifier: {time_resolution_modifier}")
    # the biomass use is calculated as generation divided by efficiency
    df = data[model_run]["gen"].loc[["WG", "WG_peak", "WG_CHP"]]
    #print(df)
    #sum over regions and filter out the correct years
    dfs_per_year = {y: df.xs(y, level="stochastic_scenarios").fillna(0).groupby(level="tech").sum().div(efficiency,axis=0).mul(time_resolution_modifier) for y in years}
    #print(yearly_dfs[years[0]].sum().sum())
    hourly_bio_use = {y: dfs_per_year[y].sum() for y in years}
    def plot_bio_use():
        # hourlt_bio_use is now a series with index "d001a", "d001b", etc. and values in GWh
        # we want to aggregate over every 24 hours and plot as a line
        daily_bio_use = {y: hourly_bio_use[y].groupby(hourly_bio_use[y].index.str[:4]).sum() for y in years}
        # for the weekly data, we want to aggregate over every 168 hours and plot as bars
        weekly_bio_use = {y: pd.Series(dtype=float) for y in years}
        for week in range(1, 53):
            for y in years:
                weekly_bio_use[y][f"w{week}"] = daily_bio_use[y].iloc[week*7-7:week*7].sum()
        print(weekly_bio_use[years[0]][:5])
        #make a copy of the weekly data with labels that are plottable on the same axis as the daily data, i.e. "w1" becomes 3.5 (halfway between 1 and 7) and "w2" becomes 10.5 (halfway between 7 and 14)
        weekly_bio_use_plottable = {y: weekly_bio_use[y].copy() for y in years}
        for y in years:
            weekly_bio_use_plottable[y].index = weekly_bio_use_plottable[y].index.str[1:].astype(int)*7-3.5
        print(weekly_bio_use_plottable[years[0]][:25])
        monthly_bio_use = {y: pd.Series(dtype=float) for y in years}
        for month in range(1, 13):
            for y in years:
                monthly_bio_use[y][f"m{month}"] = daily_bio_use[y].iloc[month*30-30:month*30].sum()
        print(monthly_bio_use[years[0]])
        monthly_bio_use_plottable = {y: monthly_bio_use[y].copy() for y in years}
        for y in years:
            monthly_bio_use_plottable[y].index = monthly_bio_use_plottable[y].index.str[1:].astype(int)*30-15

        # make a fig, ax pair to plot on. the ax is shared between the two plots and the years are plotted on the same ax
        fig, ax = plt.subplots()
        # plot the daily bio use as a line
        x_daily = [i for i in range(len(daily_bio_use[years[0]]))]
        for y in years:
            ax.plot(x_daily, daily_bio_use[y], label=f"{y} daily")
            #ax.bar(weekly_bio_use_plottable[y].index, weekly_bio_use_plottable[y], width=6, label=f"{y} weekly", alpha=0.5)
            #ax.bar(monthly_bio_use_plottable[y].index, monthly_bio_use_plottable[y], width=28, label=f"{y} monthly", alpha=0.5)
            ax.plot(monthly_bio_use_plottable[y].index, monthly_bio_use_plottable[y], label=f"{y} monthly")
        # add labels and legend
        ax.set_xlabel("Date")
        ax.xaxis.set_major_locator(plt.FixedLocator([0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]))
        ax.xaxis.set_major_formatter(plt.FixedFormatter(["Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun"]))
        ax.set_ylabel("Biogas use [GWh]")
        ax.legend()
        plt.show()
    #if years is allyears, make a new series with all years in consecutive order
    #else, run plot_bio_use()
    if allyears:
        # make a new series with the hourly bio use for all years in consecutive order
        bio_use_allyears = pd.Series(dtype=float)
        bio_use_allyears = pd.concat([hourly_bio_use[y]/1000 for y in hourly_bio_use.keys()])
        bio_use_allyears.index = pd.MultiIndex.from_product([years, hourly_bio_use[years[0]].index]) # 2920 timesteps, but correct total yearly value
        #make a new series representing a storage level, starting at 0 and being filled each hour by the total hourly bio use divided by total number of hours
        storage_level = pd.Series(dtype=float, index=bio_use_allyears.index)
        total_bio_use = bio_use_allyears.sum() # this one is correct
        print_red(f"Total bio use: {total_bio_use:.1f} TWh")
        hourly_bio_refill = total_bio_use / len(years) / 8760 # this one is the correct hourly value, but may need to be adjusted to make the storage level work
        print_red(f"Yearly bio refill: {hourly_bio_refill*8760:.1f} TWh")
        #storage_level[0] = 0
        #for i in range(1,len(bio_use_allyears)):
        #    storage_level[i] = storage_level[i-1] - bio_use_allyears[i-1] + hourly_bio_refill
        #vectorize the above
        storage_level = (hourly_bio_refill*time_resolution_modifier - bio_use_allyears).cumsum()
        #print_red(storage_level[:5])
        storage_level = storage_level.shift(1).fillna(0)
        #print_red(storage_level[:5])
        #adjust the storage series so that no values are below 0
        storage_level -= storage_level.min()
        #print_red(storage_level[:5])
        #plot the storage_level
        print(f"Max storage level: {storage_level.max():.1f} TWh")
        print(f"Biogas refilled per year: {hourly_bio_refill*8760:.1f} TWh")
        #identify the year with the lowest and highest consumption
        min_year = bio_use_allyears.groupby(level=0).sum().idxmin()
        max_year = bio_use_allyears.groupby(level=0).sum().idxmax()
        yearly_bio_use = bio_use_allyears.groupby(level=0).sum().round(1)
        # for each year, print the min and max storage level
        print("Consumption per year in AllYears:")
        for y in years:
            print(f"{y}: min={storage_level.loc[y].min():.0f} TWh, max={storage_level.loc[y].max():.0f} TWh, consumed={bio_use_allyears.loc[y].sum():.1f} TWh")
        print(f"Min year: {min_year}, max year: {max_year}")
        # plot the allyears data
        fig, ax = plt.subplots()
        #ax.plot(bio_use_allyears, label="Biogas use")
        ax.plot(storage_level.values, label="Storage level")
        #set the x-axis to indicate each year with a small tick, and label every tenth tick with the year
        start_of_new_year = [i*8760/3+8760/3/2 for i in range(len(years))]
        shortened_years = [shorten_year(y.split("-")[1]) for y in years]
        ax.xaxis.set_major_locator(plt.FixedLocator([i*8760/3*5+8760/3/2 for i in range(len(years))]))
        ax.xaxis.set_major_formatter(plt.FixedFormatter([shortened_years[i] for i,y in enumerate(start_of_new_year) if i%5==0]))
        #add minor ticks to indicate each year
        ax.xaxis.set_minor_locator(plt.FixedLocator(start_of_new_year))
        ax.set_xlim(-1 * 8760/3, (len(years)+1) * 8760/3)
        # add minor ticks to indicate each 10 TWh on the y-axis
        ax.yaxis.set_minor_locator(plt.MultipleLocator(10))
        #add a grid which includes the minor ticks (with alpha 0.2 for minor ticks and 0.5 for major ticks)
        ax.grid(which="both", alpha=0.2)
        ax.grid(which="major", alpha=0.67)
        
        ax.set_xlabel("Year")
        ax.set_ylabel("Biogas [TWh]")
        ax.legend()
        ax.set_title("Biogas storage level")
        plt.tight_layout()
        #if there already is a figure, save it with a number at the end
        i = 1
        while os.path.exists(f"{figure_path}/biogas_storage_level_{i}.png"):
            i += 1
        plt.savefig(f"{figure_path}/biogas_storage_level_{i}.png", dpi=400)
        plt.savefig(f"{figure_path}/biogas_storage_level_{i}.svg")
        #plt.show()

        #plot the distribution of values in yearly_bio_use
        fig, ax = plt.subplots()
        ax.hist(yearly_bio_use, bins=20)
        ax.set_xlabel("Yearly bio use [TWh]")
        ax.set_ylabel("Frequency")
        ax.set_title("Distribution of yearly bio use")
        plt.tight_layout()
        #if there already is a figure, save it with a number at the end
        i = 1
        while os.path.exists(f"{figure_path}/biogas_yearly_distribution_{i}.png"):
            i += 1
        plt.savefig(f"{figure_path}/biogas_yearly_distribution_{i}.png", dpi=400)
        plt.savefig(f"{figure_path}/biogas_yearly_distribution_{i}.svg")


        print("All individual years: ")
        biogas_individual_years = []
        sorted_keys = sorted(data.keys())
        for year in sorted_keys:
            if "singleyear" not in year: continue # skip allyears and sets
            #print the biogas use for each year
            if "WG_CHP" in data[year]["gen"].index.get_level_values("tech").unique():
                df = data[year]["gen"].loc[["WG", "WG_peak", "WG_CHP"]]
                efficiency = {"WG": 0.610606, "WG_peak": 0.420606, "WG_CHP": 0.492604}
            else:
                df = data[year]["gen"].loc[["WG", "WG_peak"]]
                efficiency = {"WG": 0.610606, "WG_peak": 0.420606}
            df = df.fillna(0).groupby(level="tech").sum()
            df = df.div(efficiency, axis="index").sum(axis=1)
            year = year.replace("singleyear_", "").replace("1h_", "").replace("flexlim","").replace("_gurobi","").replace("to", "-")
            print(f"{year}: {df.sum()/1000:.1f} TWh \t {(df.sum()/10/68.2-100):.0f}")
            biogas_individual_years.append(df.sum())
            #df = df.div(efficiency, axis="index")
            #print(df)
        if len(biogas_individual_years) > 0:
            print(f"Total biogas use: {sum(biogas_individual_years)/1000:.1f} TWh")
            print(f"Average biogas use: {sum(biogas_individual_years)/len(biogas_individual_years)/1000:.1f} TWh")

    else:
        plot_bio_use()