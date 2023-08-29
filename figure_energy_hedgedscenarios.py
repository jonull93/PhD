import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import glob
import re
from my_utils import color_dict, tech_names, print_red, print_cyan, print_green, print_magenta, print_blue, print_yellow, select_pickle
from order_cap import wind, PV, baseload, peak, CCS, CHP, midload, hydro, PtH, order_cap, order_cap2, order_cap3
from datetime import datetime

# Path to the figures
figures_folder = 'figures/gen/'

# Hardcoded scenario selection
scenario_selection = ['scenario_1', 'scenario_2']  # Modify with your actual scenario names
exclude_scenarios = ['scenario_3', 'scenario_4']   # Modify with the scenarios you want to exclude

# Groups of technologies 
tech_groups = {
    'Hydro': hydro,
    'PtH': PtH,
    'Wind': wind,
    'PV': PV,
    'Peak': peak,
    'Other thermals': CCS + CHP + midload + ["W"]
}
techs_to_exclude = PtH + ["Electrolyser", "electrolyser", "H", "b", "H_CHP", "B_CHP"]
storage_techs = ["bat", "H2store"]
storage_techs = storage_techs + [tech_names[t] for t in storage_techs if t in tech_names]

def shorten_year(scenario):
    # define a function to be used in re.sub
    def replacer(match):
        return "'" + match.group()[-2:]

    # use re.sub to replace all occurrences of 4-digit years
    return re.sub(r'(19|20)\d{2}', replacer, scenario)


def load_data(pickle_file, use_defaults):
    # Load the pickle file
    data = pd.read_pickle(pickle_file)
    
    # Handle scenario selection
    all_scenarios = list(data.keys())
    print(f"All scenarios: {all_scenarios}")
    
    selected_scenarios = []
    if use_defaults:
        # Use all scenarios, but if there's a scenarioname with "1h", skip the one with "3h" if there is one
        selected_scenarios = [i for i in all_scenarios if "singleyear" not in i]
        # add the singleyear scenarios corresponding to 1996-1997, 2002-2003, 2003-2004, 2009-2010, 1995-1996, 1997-1998, 2004-2005, 2018-2019
        selected_scenarios = all_scenarios
        print_magenta(f"Included sets: {selected_scenarios}")
        for s in selected_scenarios:
            if "1h" in s:
                selected_scenarios = [s for s in selected_scenarios if s != s.replace("1h", "3h")]
                break
            # then do the same to skip the "tight" scenarios
            if "tight" not in s:
                selected_scenarios = [s for s in selected_scenarios if s != s + "tight"]
                break
    else:
        # Let the user exclude some scenarios
        excluded = input("Please enter the scenarios you want to exclude, separated by commas (or H for the hardcoded list): ").split(',')
        if excluded == ['H'] or excluded == ['h']:
            # Use the hardcoded list
            selected_scenarios = [] # Replace with the hardcoded list
        else:
            excluded = [s.strip() for s in excluded]  # Remove leading/trailing spaces
            selected_scenarios = [s for s in all_scenarios if s not in excluded]

    # Handle alternative scenarios
    for s in selected_scenarios:
        if s not in all_scenarios:
            # Check for alternative scenarios in all possible combinations
            alt_scenarios = [s.replace("1h", "3h"), s + "tight", s.replace("1h", "3h") + "tight",
                             s.replace("3h", "1h"), s.replace("3h", "1h") + "tight"]
            alt_scenario_found = False
            for alt_s in alt_scenarios:
                if alt_s in all_scenarios:
                    selected_scenarios.append(alt_s)
                    alt_scenario_found = True
                    print_yellow(f"Alternative scenario found for the missing {s}: {alt_s}")
                    break
            if not alt_scenario_found:
                print_red(f"No alternative scenarios found for {s}. Skipping that one...")
               
    # Extract 'gen_per_eltech' data for the selected scenarios and replace NaNs with 0
    selected_data = {scenario: data[scenario]['gen_per_eltech'].fillna(0) for scenario in selected_scenarios}

    # Remove "ref_cap" from scenario names 
    selected_data = {s.replace("ref_cap_", ""): selected_data[s] for s in selected_data.keys()}
    selected_data = {s.replace("singleyear_", ""): selected_data[s] for s in selected_data.keys()}
    selected_data = {s.replace("to", "-"): selected_data[s] for s in selected_data.keys()}
    #selected_data = {s.replace("iter", "base1extreme2_"): selected_data[s] for s in selected_data.keys()}
    for s in selected_data.copy().keys():
        if "base" in s and "extreme" in s:
            s_components = s.split("_")
            if "base4extreme2_5" in s:
                selected_data["_".join([s_components[0]+"_v2", s_components[-1]])] = selected_data[s]    
            else:
                selected_data["_".join([s_components[0], s_components[-1]])] = selected_data[s]
            selected_data.pop(s)
    combined_series = pd.concat(selected_data.values(), keys=selected_data.keys(), names=['scenario'], axis=0)
    combined_series = combined_series.reorder_levels(['stochastic_scenarios', 'scenario', 'tech'])
    combined_series = combined_series.sort_index()
    combined_series = combined_series.rename_axis(['year', 'scenario', 'tech'])
    #print_cyan(combined_series)
    # has_altscenarios should be True if there are any scenarios with "v2" in the name
    has_altscenarios = any("v2" in s for s in combined_series.index.get_level_values('scenario').unique())
    if has_altscenarios and not use_defaults:
        print_yellow("There are alternative scenarios in the data. What should be done with these?")
        print_yellow("1. Keep all scenarios")
        print_yellow("2. Keep only alternative scenarios for years with other scenarios too")
        print_yellow("3. Remove all alternative scenarios (default)")
        user_input = input("Please enter your choice (1, 2 or 3): \n")
        if user_input == "1":
            print_yellow("Keeping all scenarios")
            pass
        elif user_input == "2":
            print_yellow("Keeping only alternative scenarios for years with other scenarios too")
            # If a year only has data for a scenario with "v2" in the name, remove that year
            for year in combined_series.index.get_level_values('year').unique():
                if len(combined_series.loc[year].index.get_level_values('scenario').unique()) == 1 and "v2" in combined_series.loc[year].index.get_level_values('scenario').unique()[0]:
                    combined_series = combined_series.drop(year, level='year')
        else:
            if user_input != "3": print_red("Invalid input. Removing all alternative scenarios..")
            print_yellow("Removing all alternative scenarios")
            combined_series = combined_series.drop(combined_series.index[combined_series.index.get_level_values('scenario').str.contains("v2")])
    if has_altscenarios and use_defaults:
        print_yellow("There are alternative scenarios in the data. Removing all alternative scenarios..")
        combined_series = combined_series.drop(combined_series.index[combined_series.index.get_level_values('scenario').str.contains("v2")])
    return combined_series


def prettify_scenario_name(name,year):
    if "set1" in name:
        #print_yellow("Set 1 scenario detected")
        # turn set1_4opt into Set 1 (4 opt.)
        nr = name.split("_")[1].replace("opt", "")
        alt = " alt."*('alt' in name)
        even = ", eq. w."*('even' in name)
        if "even" in name: nr = 4
        return f"2 HP + {nr}{alt} opt." + even # 2 opt., 2 HP
    if "allopt" in name:
        # turn allopt2_final into All opt. (2 yr), and allopt2_final_a into All opt. (2 yr) a
        nr = name.split("_")[0].replace("allopt", "")
        if len(name.split("_")) == 3:
            abc = name.split("_")[2]
            abc = f" ({abc})"
        else:
            abc = ""
        return f"{nr} opt.{abc}"
    if "iter2" in name:
        return "Set (1 opt.)"
    elif "iter3" in name:
        return "Set (2 opt.)"
    if len(name.replace(year,'')) > 3:
        # change labels from "base#extreme#" (where # is a number) to "#b #e"
        temp_label = f"{name.replace(year,'').replace('_tight','').replace('_1h','')}"
        if "base" in temp_label and "extreme" in temp_label:
            # remove 'base' and 'extreme' and split into a list
            parts = name.replace('base', '').replace('extreme', ' ').split()
            #print_magenta(f"Renaming {name}")
            # join the parts with appropriate labels
            if "v2" in name:
                return f'Alt. set ({parts[0]} opt.)'
            elif "even" in name:
                return f'6 yr, eq. weights'
            return f'Set ({parts[0]} opt.)'
    else:
        return "Single year"

def group_technologies(data):
    result_list = []
    
    # Iterate over each item in the Series
    for idx, value in data.items():
        scenario, year, tech = idx
        if tech in techs_to_exclude:
            continue
        grouped = False
        
        # Check each group to see if the technology is in that group
        for group, tech_list in tech_groups.items():
            if tech in tech_list:
                # Create new index with the group
                grouped_idx = (year, scenario, group)
                # Add the value to the group
                found_idx = [i for i, x in enumerate(result_list) if x[:3] == grouped_idx]
                if found_idx:
                    result_list[found_idx[0]] = (grouped_idx[0], grouped_idx[1], grouped_idx[2], result_list[found_idx[0]][3] + value)
                else:
                    result_list.append((grouped_idx[0], grouped_idx[1], grouped_idx[2], value))
                grouped = True
                break

        # If the technology was not grouped, add it to the grouped data as is
        if not grouped:
            grouped_idx = (year, scenario, tech)
            result_list.append((grouped_idx[0], grouped_idx[1], grouped_idx[2], value))

    # Swap the levels of the index to match the desired output structure and create series
    result_list = [(year, prettify_scenario_name(scenario,year), tech, value) for scenario, year, tech, value in result_list]
    grouped_data = pd.Series((x[3] for x in result_list), index=pd.MultiIndex.from_tuples((x[0], x[1], x[2]) for x in result_list))

    return grouped_data

def plot_cluster(data, position, ax, stack_width=0.8, stack_spacing=0.02, cluster_spacing=0.35):
    # Sum values at the scenario level
    scenario_sums = data.groupby(level=0).sum()

    # Filter scenarios that have non-zero sums
    non_zero_scenarios = scenario_sums[scenario_sums != 0].index

    # Filter data to include only non-zero scenarios
    data = data[data.index.get_level_values(0).isin(non_zero_scenarios)]
    
    # Get the number of unique scenarios in the data
    n_scenarios = len(data.index.get_level_values(0).unique())

    # Initialize the start position for the bars
    pos = position

    # For each unique scenario in data, create a stacked bar
    bars = []
    scenarios = []  # List to collect scenario names
    positions = []  # List to collect bar positions
    for scenario in data.index.get_level_values(0).unique():
        scenario_data = data.loc[scenario]
        bottom = 0
        # skip if all values are zero
        if scenario_data.sum() == 0:
            continue
        for tech in scenario_data.index:
            value = scenario_data.loc[tech]
            bars.append(ax.bar(pos, value, bottom=bottom, width=stack_width, label=tech, color=color_dict.get(tech, 'gray')))
            bottom += value
        scenarios.append(scenario)
        positions.append(pos)
        
        # Update the start position for the next stack
        pos += stack_width + stack_spacing

    # Compute the position for the next cluster
    next_cluster_pos = pos + cluster_spacing - stack_spacing

    return bars, positions, scenarios, next_cluster_pos


def create_figure(grouped_data, pickle_timestamp, use_defaults):
    # Create a directory for the figures if it doesn't already exist
    if not os.path.exists(figures_folder):
        os.makedirs(figures_folder)

    # Create a figure and axis
    fig, ax1 = plt.subplots(figsize=(7, 4))

    # Combine all scenarios into a single DataFrame
    combined_data = grouped_data.unstack(level=0).fillna(0)/1e3  # Move 'year' to column

    # Order the bars according to order_cap
    # First get the current order of the first level of the index
    scenarios = combined_data.index.get_level_values(0).unique().tolist()
    
    new_index = pd.MultiIndex.from_product([scenarios, order_cap3], names=['scenario', 'tech'])
    combined_data = combined_data.reindex(new_index)
    combined_data = combined_data.dropna(how='all')

    # Specify the scenario you want to move
    move_scenario = 'Single year'

    # Make sure the scenario to move is in the list of scenarios
    assert move_scenario in scenarios, "Specified scenario is not in the DataFrame"

    # Remove the scenario from its current position
    scenarios.remove(move_scenario)

    # Add the scenario back to the top of the list
    scenarios.insert(0, move_scenario)

    # Reindex the first level of the DataFrame's index based on the new scenario order
    combined_data = combined_data.reindex(scenarios, level=0)

    # Find all unique years
    unique_years = combined_data.columns.get_level_values(0).unique()
    years_to_add = ["1996-1997","2002-2003","2014-2015","2009-2010","2003-2004","1995-1996","1997-1998","2004-2005","2018-2019"]
    years_to_add = [i for i in years_to_add if i in unique_years]
                    #("1996-1997" in i or "2002-2003" in i or "2003-2004" in i or "2009-2010" in i or 
                    # "1995-1996" in i or "1997-1998" in i or "2004-2005" in i or "2018-2019" in i or 
                    # "2014-2015" in i)]

    # Variables to collect all scenarios and their positions
    all_positions = []
    all_scenarios = []
    all_years = []

    # For each unique year, create a cluster of stacked bars
    next_cluster_pos = 0
    for i, year in enumerate(years_to_add):
        print_yellow(f'Plotting {year}...')
        year_data = combined_data[year]  # Get the data for this year
        bars_cluster, positions, scenarios, next_cluster_pos = plot_cluster(year_data, next_cluster_pos, ax1)  # Create the cluster at position i

        # After plotting, iterate over the bars and add labels
        def conditional_label(bar, cutoff):
            # Get the height of the bar
            height = bar.get_height()
            # If height is greater than or equal to cutoff, return label
            if abs(height) >= 100:
                return f'{height:.0f}'
            # Otherwise, return an empty string
            elif abs(height) >= cutoff:
                return f'{height:.0f}'
            else:
                return ''
        
        for bars in bars_cluster:
            # Apply this function to each bar
            for bar in bars:
                label = conditional_label(bar, 20)
                ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_y() + bar.get_height()/2, label, ha='center', va='center', fontsize=6)
        
        # Collect the positions of the bars and the scenarios for this year
        all_positions.extend(positions)
        all_scenarios.extend(scenarios)
        all_years.extend([year]*len(scenarios))  # repeat the current year for all scenarios

    # Set new xticks and labels
    new_labels = []#[f"{f'{scenario}, '*(len(scenario.replace(year,''))>3)}" + f"{year}" for scenario, year in zip(all_scenarios, all_years)]
    for scenario, year in zip(all_scenarios, all_years):
        temp_label = prettify_scenario_name(scenario,year)
        print_blue(f"Renaming {scenario} {year} to {temp_label}")
        new_labels.append(temp_label)

    ax1.set_xticks(all_positions)
    ax1.set_xticklabels(all_scenarios, rotation=35, ha='right', fontsize=9)

    # Add lines to separate the clusters of labels
    change_indices = [i for i in range(1, len(all_years)) if all_years[i] != all_years[i-1]]
    for idx in change_indices:
        ax1.axvline(x=all_positions[idx] - 0.5 * (all_positions[idx] - all_positions[idx-1]), color='black', linestyle='--', linewidth=0.5)
    
    # Get maximum height of all bars
    max_height = max(bar.get_height() + bar.get_y() for bars in bars_cluster for bar in bars)

    # Set y limit with some additional space for the text
    ax1.set_ylim(top=max_height + 0.12*max_height) # change 0.2 to desired proportion

    # Set the x limit to tighten the plot
    ax1.set_xlim(left=-0.6, right=all_positions[-1]+0.6)

    # Compute positions for the year labels (center of each cluster)
    change_indices = np.array([0] + change_indices + [len(all_positions)])  # include start and end indices
    cluster_positions = [(np.array(all_positions)[change_indices[i-1]:change_indices[i]]).mean() for i in range(1, len(change_indices))]

    # Add a text label for each year
    for pos, year in zip(cluster_positions, years_to_add):
        ax1.text(pos, max_height + 0.06*max_height, shorten_year(year), ha='center', fontsize=7)  # change 0.1 to desired proportion

    # Get legend location from user
    if not use_defaults:
        print("Choose a position for the legend: ")
        print("1) Top")
        print("2) Bottom")
        print("3) Right")
        legend_position = input("Enter a number (default is 1): ")

        if legend_position == '2':
            legend_loc = 'upper center'
            legend_bbox_to_anchor = (0.5, -0.25)
            legend_ncol = 3
        elif legend_position == '3':
            legend_loc = 'center left'
            legend_bbox_to_anchor = (1.07, 0.5)
            legend_ncol = 1
        else:
            legend_loc = 'lower center'
            legend_bbox_to_anchor = (0.5, 1.12)
            legend_ncol = 3
    else:
        legend_loc = 'lower center'
        legend_bbox_to_anchor = (0.5, 1.12)
        legend_ncol = 4


    # Get the legend labels and handles from ax1
    handles, labels = ax1.get_legend_handles_labels()

    # Create a dictionary where the keys are the labels and the values are the handles
    # This effectively removes any duplicates because dictionaries cannot have duplicate keys
    legend_dict = dict(zip(labels, handles))

    # Get the labels and handles back from the dictionary
    labels = list(legend_dict.keys())
    handles = list(legend_dict.values())

    # Now use these unique labels and handles to create the legend
    ax1.legend(handles, labels, loc=legend_loc, ncol=legend_ncol, bbox_to_anchor=legend_bbox_to_anchor)

    # Add title and labels
    ax1.set_title('Electricity generation per scenario for each year')
    ax1.set_xlabel('Model-run')
    ax1.set_ylabel('Electricity generation [TWh]')
    plt.tight_layout(pad=0.5)
    
    # Save the figure as PNG and SVG (or EPS)
    fig_name_base = f"{figures_folder}/{pickle_timestamp}"
    fig_num = 1
    while os.path.exists(f"{fig_name_base}_{fig_num}.png"):
        fig_num += 1
    fig.savefig(f"{fig_name_base}_{fig_num}.png", dpi=300)
    fig.savefig(f"{fig_name_base}_{fig_num}.svg")  # or .eps for EPS format

    # Close the figure to free memory
    plt.close(fig)

    print_green(f"Figure saved as '{fig_name_base}_{fig_num}.png'.")


def main():
    print_blue(f"Script started at: {datetime.now()}")
    
    user_input = input("Press ENTER to go with default options or type anything to be prompted for choices along the way: ")
    use_defaults = user_input.strip() == ""  # This will be True if the user just pressed enter

    print_blue(f"Script started at: {datetime.now()}")
    pickle_file = select_pickle(use_defaults)
    pickle_timestamp = pickle_filename = os.path.basename(pickle_file).replace(".pickle", "").replace("data_results_", "")
    print_cyan(f"Selected pickle file: {pickle_file}")
    data = load_data(pickle_file, use_defaults)
    print_yellow(f"Data loaded from pickle file")
    print_yellow(f"Years in data: \n{data.index.get_level_values('year').unique()}")
    grouped_data = group_technologies(data)
    print_green(f"Technologies grouped successfully")
    print_yellow(f"Grouped data: \n{grouped_data}")
    create_figure(grouped_data, pickle_timestamp, use_defaults)
    print_magenta(f"Figures created and saved in {figures_folder}")
    
    print_red(f"Script finished at: {datetime.now()}")

if __name__ == "__main__":
    main()
