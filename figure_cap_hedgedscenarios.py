import os
import pandas as pd
import matplotlib.pyplot as plt
import re
from my_utils import color_dict, tech_names, print_red, print_cyan, print_green, print_magenta, print_blue, print_yellow, select_pickle, load_from_file, save_to_file
from order_cap import wind, PV, baseload, peak, CCS, CHP, midload, hydro, PtH, order_cap, order_cap2, order_cap3
from datetime import datetime
from figure_bio_use import get_biogas_use

# Path to the pickle files and figures
pickle_folder = 'PickleJar/'
figures_folder = 'figures/capacity/'

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
    'Other thermals': CCS + CHP + ["W"]
}
tech_groups2 = {
    "Battery": ["bat"], # "bat_cap"
    "Hydrogen": ["H2store", "electrolyser","FC"],
    "VRE": PV + wind,
    "Thermals": CCS + CHP + midload + ["W", "U", "Other thermals"] + peak,
    #"Peak": peak,
}
techs_to_exclude = PtH + ["Electrolyser", "electrolyser", "H", "b", "H_CHP", "B_CHP"]
storage_techs = ["bat", "H2store"]
storage_techs = storage_techs + [tech_names[t] for t in storage_techs if t in tech_names]


def shorten_year(scenario):
    # define a function to be used in re.sub
    def replacer(match):
        return "'" + match.group()[-2:]

    # use re.sub to replace all occurrences of 4-digit years
    return re.sub(r'(19|20)\d{2}', replacer, scenario).removeprefix("singleyear_")


def load_data(pickle_file, use_defaults=False, data_key='tot_cap'):
    # Load the pickle file
    #aggregate the dictionaries if pickle_file is a list
    if isinstance(pickle_file, list):
        data = {}
        for p in pickle_file:
            data.update(load_from_file(p))
    else:
        data = load_from_file(pickle_file)
    
    # Handle scenario selection
    all_scenarios = list(data.keys())
    print_cyan(f"All scenarios: {all_scenarios}")
    
    selected_scenarios = []
    if use_defaults==True:
        # Use all scenarios, but if there's a scenarioname with "1h", skip the one with "3h" if there is one
        selected_scenarios = [i for i in all_scenarios if "singleyear" not in i]
        print_magenta(f"Included sets: {selected_scenarios}")
        # add the singleyear scenarios corresponding to 2012, 2016-2017, 1996-1997, 2002-2003, 2003-2004, 2009-2010
        years_to_add = [i for i in all_scenarios if "singleyear" in i and ("singleyear_1h_2012" in i or "singleyear_2016to2017_" in i or "singleyear_1996to1997_" in i or "singleyear_2002to2003_" in i or "singleyear_2003to2004_" in i or "singleyear_2009to2010_" in i)]
        selected_scenarios = selected_scenarios + years_to_add

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
        excluded = []
        if use_defaults==False: 
            excluded = input("Please enter the scenarios you want to exclude, separated by commas (or H for the hardcoded list): ").split(',')
        if excluded == ['H'] or excluded == ['h']:
            # Use the hardcoded list
            selected_scenarios = [
                "2HP_1opt", "2HP_2opt", "2HP_3opt_mean", "2HP_4opt", "2HP_5opt",
                #'singleyear_1989to1990_1h', 'singleyear_1995to1996_1h',
                'singleyear_1996to1997_1h', #'singleyear_1997to1998_1h',
                'singleyear_2002to2003_1h', 
                #'singleyear_2003to2004_1h', #'singleyear_2004to2005_1h',
                #'singleyear_2009to2010_1h', #'singleyear_2010to2011_1h', 'singleyear_2018to2019_1h', 'singleyear_2014to2015_1h',
                'singleyear_1h_2012', 'singleyear_2016to2017_1h',
                #'set1_1opt', 'set1_2opt', 'set1_3opt', 'set1_4opt',
                ] # Replace with the hardcoded list
        else:
            # the input is a string but if there is an , in the input it will be split into a list
            if ',' not in excluded:
                excluded = [e.strip().replace("'", "").replace('"', '') for e in excluded]
                excluded = excluded + [e.replace('-','to') for e in excluded if '-' in e]
            else:
                parts = excluded.split(',')
                print_red(f"parts: {parts}")
                excluded = [p.strip().replace("'", "").replace('"', '') for p in parts]
            print_red(f"Excluding scenarios: {excluded}")
            excluded = excluded + [e.replace('_1h','').replace('_3h','') for e in excluded]
            sets = [s for s in all_scenarios if "singleyear" not in s and s not in excluded]
            selected_scenarios = sets+[s for s in all_scenarios if s not in excluded+sets]
    #if "allyears" in selected scenarios, move it to the end
    if "allyears" in selected_scenarios:
        selected_scenarios = [s for s in selected_scenarios if s != "allyears"] + ["allyears"]

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
               
    # Extract 'tot_cap' data for the selected scenarios and replace NaNs with 0
    if data_key == 'biogas':
        selected_data = {}
        for scenario in selected_scenarios:
            weights = data[scenario]['stochastic_probability'] # a Series of float(s)
            hourly_use = get_biogas_use(data, scenario) #returns a dictionary of time-series for each year
            total_use = 0
            for year, df in hourly_use.items():
                total_use += df.sum().sum()*weights[year]
            selected_data[scenario] = pd.Series(total_use, index=['biogas'])
        
        #print_yellow(f"Selected data: \n{selected_data}")
        # probability needs to be considered, then years combined for each scenario and then repeated for all selected_scenarios
    elif data_key == 'grossexport':
        def weighted_average(group, weights):
            return (group * weights).sum() / weights.sum()

        selected_data = {}
        for scenario in selected_scenarios:
            weights = data[scenario]['stochastic_probability'] # a Series of float(s)
            time_resolution_modifier = data[scenario]["TT"] #float
            yearly_export = data[scenario]['yearly_elec_grossexport']*time_resolution_modifier
            # Assuming 'yearly_export' has a MultiIndex with levels ['exporter', 'importer', 'stochastic_scenarios']
            # and 'weights' is aligned with 'stochastic_scenarios'
            weighted_grossexport = yearly_export.groupby(level=['exporter', 'importer']).apply(weighted_average, weights=weights)
            # now find the gross export to and from continental Europe (DE_N)
            northern_regions = ['NO_S', 'SE_S', 'FI']
            southern_regions = ['DE_N','DE_S']
            southwards = weighted_grossexport.loc[northern_regions, southern_regions].sum()
            northwards = weighted_grossexport.loc[southern_regions, northern_regions].sum()
            # Create a new series
            gross_transfer = pd.Series([southwards, northwards], index=['Export south', 'Export north'])
            selected_data[scenario] = gross_transfer
    elif data_key in ['cost_tot','cost_tot_onlynew']:
        selected_data = {scenario: pd.Series([data[scenario][data_key]], index=['System cost']) for scenario in selected_scenarios}

    else:
        try: selected_data = {scenario: data[scenario][data_key].fillna(0) for scenario in selected_scenarios}
        except AttributeError: selected_data = {scenario: data[scenario][data_key] for scenario in selected_scenarios}

    # Remove "ref_cap" from scenario names 
    selected_data = {s.replace("ref_cap_", ""): selected_data[s] for s in selected_data.keys()}
    #selected_data = {s.replace("singleyear_", ""): selected_data[s] for s in selected_data.keys()}
    selected_data = {s.replace("to", "-").replace("_1h", "").replace("_tight", "").replace("_flexlim", "").replace("_gurobi", ""): selected_data[s] for s in selected_data.keys()}

    # has_altscenarios should be True if there are any scenarios with "v2" in the name
    has_altscenarios = any("v2" in s or "_5_" in s for s in selected_data.keys())
    if has_altscenarios and not use_defaults:
        print_yellow("There are alternative scenarios in the data. What should be done with these?")
        print_yellow("1. Keep all scenarios (default)")
        print_yellow("2. Remove alternative scenarios")
        user_input = input("Please enter your choice ( or 2): \n")
        if user_input == "1":
            print_yellow("Keeping all scenarios")
            pass
        elif user_input == "2":
            print_yellow("Removing all alternative scenarios")
            selected_data = {s: selected_data[s] for s in selected_data.keys() if "v2" not in s and "_5_" not in s}
        else:
            print_yellow("Invalid input. Keeping all scenarios")
    if has_altscenarios and use_defaults:
        print_yellow("There are alternative scenarios in the data.")
    # reorder the keys in alphabetical order, but in a way where "10" comes after "9"
    sorted_keys = sorted(selected_data.keys(), key=custom_sort)
    # movescenarios including "opt" first
    #sorted_keys = [s for s in sorted_keys.keys() if "opt" in s] + [s for s in sorted_keys.keys() if "opt" not in s]
    selected_data = {s: selected_data[s] for s in sorted_keys}
    selected_scenarios_to_print = "\n".join(selected_data.keys())
    print_blue(f"Selected scenarios: \n{selected_scenarios_to_print}")
    return selected_data

def custom_sort(item):
    # "allyears" goes last
    if "allyears" in item:
        return (2, item)
    
    # "2HP.."
    if "2HP" in item:
        if "opt" in item:
            opt_num = int(item.split("opt")[0].split("_")[-1])  # Extract the number before "opt"
            return (0, opt_num, item)
        return (0, 0, item)
    
    # "singleyear.."
    if "singleyear" in item:
        return (1, item)
    
    # Default: alphabetical order
    return (0, 0, item)

def group_technologies(data):
    """Group technologies according to the tech_groups dictionary"""
    # Create a dictionary of Series to hold the grouped data
    grouped_data = {s:pd.Series(dtype=float) for s in data.keys()}

    for scenario in data.keys():
        # Sum over regions and replace technologies that belong to a group in tech_groups with the group
        data_region_sum = data[scenario].groupby(level=0).sum()

        # Iterate over each item in the Series
        for idx, value in data_region_sum.items():
            tech = idx
            if tech in techs_to_exclude:
                continue
            grouped = False
            
            # Check each group to see if the technology is in that group
            for group, tech_list in tech_groups.items():
                if tech in tech_list:
                    # Add the value to the group
                    if group not in grouped_data[scenario]:
                        grouped_data[scenario][group] = value
                    else:
                        grouped_data[scenario][group] += value
                    grouped = True
                    break

            # If the technology was not grouped, add it to the grouped data as is
            if not grouped:
                grouped_data[scenario][idx] = value

    return grouped_data


def prettify_scenario_name(name):
    #print_yellow(f"Prettifying scenario name: {name}")
    if "set1" in name:
        #print_yellow("Set 1 scenario detected")
        # turn set1_4opt into Set 1 (4 opt.)
        nr = name.split("_")[1].replace("opt", "")
        alt = " alt."*('alt' in name)
        even = ", eq. w."*('even' in name)
        if "even" in name: nr = 4
        return f"2 HP + {nr}{alt} opt." + even # 2 opt., 2 HP
    if "HP" in name and "opt" in name:
        parts = name.split("_")
        opt = parts[1].replace("opt", "")
        extra = f" ({parts[-1]})" if len(parts) == 3 and parts[-1]!="mean" else "" 
        if "trueref" in extra: extra = "" #" *"
        if "2012" in extra:
            return f"{name[0]} HP + {opt} opt. (2012)" 
        elif "evenweights" in extra:
            extra = ", eq. w."
        return f"{name[0]} HP + {opt} opt.{extra}" 
    if "allyears" in name:
        return "All years"
    if "allopt" in name:
        # turn allopt2_final into All opt. (2 yr), and allopt2_final_a into All opt. (2 yr) a
        nr = name.split("_")[0].replace("allopt", "")
        extra = f" ({name.split('_')[-1]})" if len(name.split('_'))>1 else ""
        if "trueref" in extra: extra = ""#" *"
        #if len(name.split("_")) == 3:
        #    abc = name.split("_")[2]
        #    abc = f" ({abc})"
        #else:
        #    abc = ""
        
        return f"{nr} opt.{extra}"
    if "iter2_3" in name:
        return "Set (1 opt.)"
    elif "iter3_16start" in name:
        return "Set (2 opt.)"
    if "singleyear" in name:
        # turn 'singleyear_1989to1990_1h' into "'89-'90" using regex
        return shorten_year(name)
    # remove 'base' and 'extreme' and split into a list
    parts = name.replace('base', '').replace('extreme', ' ').split()
    if "v2" in name or "_5_" in name:
        return f'Alt. set ({parts[0]} opt.)'
    elif "even" in name:
        return f'6 yr, eq. weights'
    # join the parts with appropriate labels
    return f'Set ({parts[0]} opt.)'


def create_figure(grouped_data, pickle_timestamp, use_defaults):
    # Create a directory for the figures if it doesn't already exist
    if not os.path.exists('figures/capacity'):
        os.makedirs('figures/capacity')

    # Create a figure and axis
    fig, ax1 = plt.subplots(figsize=(8,5))

    # Combine all scenarios into a single DataFrame
    combined_data = pd.DataFrame({scenario: data for scenario, data in grouped_data.items()})
    print_cyan(combined_data)
    # Order the bars according to order_cap
    combined_data = combined_data.reindex(order_cap2).dropna(how='all')

    # If the technology exists as a key in tech_names, replace the index with the value
    combined_data = combined_data.rename(index=tech_names, errors='ignore')
    print_magenta(combined_data)
    # Move "electrolyser" index to the top of the df and make it negative
    #combined_data = combined_data.reindex(['electrolyser'] + [idx for idx in combined_data.index if idx != 'electrolyser'])
    #combined_data.loc["electrolyser"] *= -1
    
    # Split the data into two groups: normal tech and storage tech
    normal_tech = combined_data.drop(index=storage_techs, errors='ignore')
    storage_tech = combined_data.loc[combined_data.index.intersection(storage_techs)].dropna(how='all')
    # Create second axis that shares the same x-axis
    ax2 = ax1.twinx()

    # Width of the bars
    width = 0.39

    # Plot normal tech and storage tech side by side
    bars1 = normal_tech.T.plot(kind='bar', stacked=True, ax=ax1, width=width, color=[color_dict.get(tech, 'gray') for tech in normal_tech.index], position=1.05, rot=11)
    bars2 = storage_tech.T.plot(kind='bar', stacked=True, ax=ax2, width=width, color=[color_dict.get(tech, 'gray') for tech in storage_tech.index], position=-0.05)

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

    # Apply this function to each bar
    for container in bars1.containers:
        labels1 = [conditional_label(bar, 40) for bar in container]
        ax1.bar_label(container, labels=labels1, label_type='center', fontsize=8)

    for container in bars2.containers:
        labels2 = [conditional_label(bar, 40) for bar in container]
        ax2.bar_label(container, labels=labels2, label_type='center', fontsize=7)
    
    # Adjust the xlim
    ax1.set_xlim(-0.5, len(combined_data.columns) - 0.5)

    # Get the legend labels and handles from both axes
    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()

    # Remove the old legends
    ax1.get_legend().remove()
    ax2.get_legend().remove()

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
            legend_ncol = 4
        elif legend_position == '3':
            legend_loc = 'center left'
            legend_bbox_to_anchor = (1.1, 0.5)
            legend_ncol = 1
        else:
            legend_loc = 'lower center'
            legend_bbox_to_anchor = (0.5, 1.12)
            legend_ncol = 4
    else:
        legend_loc = 'lower center'
        legend_bbox_to_anchor = (0.5, 1.12)
        legend_ncol = 4

    # Create a combined legend above the figure title
    ax1.legend(handles1 + handles2, labels1 + labels2, loc=legend_loc, ncol=legend_ncol, bbox_to_anchor=legend_bbox_to_anchor)

    # Change the x-labels to be right-aligned
    x_ticks = ax1.get_xticklabels()
    new_labels = []#[f"{f'{scenario}, '*(len(scenario.replace(year,''))>3)}" + f"{year}" for scenario, year in zip(all_scenarios, all_years)]
    for scenario in x_ticks:
        scenario = scenario.get_text()
        if len(scenario) > 10 or "_" in scenario:
            # change labels from "base#extreme#" (where # is a number) to "#b #e"
            temp_label = f"{scenario.replace('_tight','').replace('_1h','')}"
            temp_label = prettify_scenario_name(temp_label)
            new_labels.append(temp_label)
        else:
            new_labels.append(scenario)
    ax1.set_xticklabels(new_labels, rotation=20, ha='right', fontsize=10)

    # Add title and labels
    ax1.set_title('Technology capacity in each scenario')
    ax1.set_xlabel('Scenario')
    ax1.set_ylabel('Installed power capacity [GW]')
    ax2.set_ylabel('Installed storage capacity [GWh]')
    plt.tight_layout(pad=0.5)
    
    # Save the figure as PNG and SVG (or EPS)
    fig_name_base = f"figures/capacity/{pickle_timestamp}"
    fig_num = 1
    while os.path.exists(f"{fig_name_base}_{fig_num}.png"):
        fig_num += 1
    fig.savefig(f"{fig_name_base}_{fig_num}.png", dpi=300)
    fig.savefig(f"{fig_name_base}_{fig_num}.svg")  # or .eps for EPS format

    # Close the figure to free memory
    plt.close(fig)

    print_green(f"Figure saved as '{fig_name_base}_{fig_num}.png'.")

def create_figure_separated_techs(grouped_data, pickle_timestamp, use_defaults):
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

    # Create a directory for the figures if it doesn't already exist
    if not os.path.exists('figures/capacity'):
        os.makedirs('figures/capacity')

    # Create a figure and axes
    fig, axs = plt.subplots((len(tech_groups2)-1)//2+1, 2, figsize=(7,3*len(tech_groups2)//2)) 
    axes = axs.flatten()

    # Combine all scenarios into a single DataFrame
    combined_data = pd.DataFrame({scenario: data for scenario, data in grouped_data.items()})
    print_magenta(combined_data)
    
    # Loop over each group and create a subplot
    for ax, (group_name, tech_list) in zip(axes, tech_groups2.items()):
        # Filter data for the current technology group
        group_data = combined_data.loc[combined_data.index.intersection(tech_list)].dropna(how='all')
        # Reorder the bars according to order_cap
        group_data = group_data.reindex(order_cap3).dropna(how='all')

        if group_name == 'Battery' and 'bat_cap' in group_data.index:
            width = 0.4
            x_values_storage = [x - width / 2 for x in range(len(group_data.columns))]
            x_values_power = [x + width / 2 for x in range(len(group_data.columns))]

            print(group_data)
            ax2 = ax.twinx()  # instantiate a second axes that shares the same x-axis

            ax.bar(x_values_storage, group_data.loc["bat"].values, color=color_dict.get('storage', 'gray'), width=width)
            ax.set_ylabel('Installed storage capacity [GWh]')

            ax2.bar(x_values_power, group_data.loc["bat_cap"].values, color=color_dict.get('power', 'gray'), alpha=0.5, width=width)
            ax2.set_ylabel('Installed power capacity [GW]')
        else:
            # Plot the data for this group
            group_data.T.plot(kind='bar', stacked=True, ax=ax, color=[color_dict.get(tech, 'gray') for tech in group_data.index], width=0.8)

        # Set the title for this subplot
        ax.set_title(group_name)

        # After plotting, iterate over the bars and add labels


        # get the max y-value for this subplot
        max_y = ax.get_ylim()[1]
        for bars in ax.containers:
            # Apply this function to each bar
            for bar in bars:
                #if in the Battery or Hydrogen group, make the label text white
                if group_name in ['Battery', 'Hydrogen']:
                    textcolor = 'white'
                    textsize = 5+1*(len(group_data.columns)<11)
                else:
                    textcolor = 'black'
                    textsize = 6
                label = conditional_label(bar, 10)
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_y() + bar.get_height()-max_y*0.04, label, ha='center', va='center', fontsize=textsize, color=textcolor)

    # Add overall title, labels, legend etc. to your liking
    # Change the x-labels to be right-aligned
    for i_a, ax in enumerate(axes):
        x_ticks = ax.get_xticklabels()
        new_labels = []#[f"{f'{scenario}, '*(len(scenario.replace(year,''))>3)}" + f"{year}" for scenario, year in zip(all_scenarios, all_years)]
        for scenario in x_ticks:
            scenario = scenario.get_text()
            if len(scenario) > 7 or "_" in scenario:
                # change labels from "base#extreme#" (where # is a number) to "#b #e"
                temp_label = f"{scenario.replace('_tight','').replace('_1h','')}"
                temp_label = prettify_scenario_name(temp_label)
                new_labels.append(temp_label)
            else:
                # change all years from 19## or 20## to '## (e.g. 1990 to '90)
                scenario = shorten_year(scenario).replace('_tight','').replace('1h_','')
                new_labels.append(scenario)

        ax.set_xticklabels(new_labels, rotation=35, ha='right', fontsize=10, rotation_mode='anchor')
        # for each label in the legend see if there is a better name in tech_names and replace it
        handles, labels = ax.get_legend_handles_labels()
        new_labels = []
        for label in labels:
            if label in tech_names:
                new_labels.append(tech_names[label])
            else:
                new_labels.append(label)
        ncols = 1+(len(new_labels)>2)
        ax.legend(handles[::-1], new_labels[::-1], loc='lower center', framealpha=0.65, ncols=2, fontsize="small") # [::-1] to reverse the order of the legend entries
        if i_a==0:
            ax.set_ylabel('Installed storage capacity [GWh]')
        elif i_a == 1:
            ax.set_ylabel('Installed storage capacity [GWh]')
        else:
            ax.set_ylabel('Installed power capacity [GW]')
    fig.tight_layout(pad=0.5, rect=(0,0,1,0.98))
    plt.subplots_adjust(wspace=0.3)
    # Save and close the figure as in your original function
    # Save the figure as PNG and SVG (or EPS)
    fig_name_base = f"figures/capacity/{pickle_timestamp}"
    fig_num = 1
    while os.path.exists(f"{fig_name_base}_{fig_num}.png"):
        fig_num += 1
    fig.savefig(f"{fig_name_base}_{fig_num}.png", dpi=300)
    fig.savefig(f"{fig_name_base}_{fig_num}.svg")  # or .eps for EPS format
    print_green(f"Figure saved as '{fig_name_base}_{fig_num}.png'.")

    # Close the figure to free memory
    plt.close(fig)

def main():
    print_blue(f"Script started at: {datetime.now()}")
    
    user_input = input("Press ENTER to go with default options or type anything to be prompted for choices along the way: ")
    use_defaults = user_input.strip() == ""  # This will be True if the user just pressed enter

    print_blue(f"Script started at: {datetime.now()}")
    pickle_file = select_pickle(use_defaults)
    if isinstance(pickle_file, list):
        # use the most recently modified pickle file to determine the timestamp
        pickle_file_for_timestamp = sorted(pickle_file, key=os.path.getmtime)[-1]
        pickle_timestamp = "agg"+os.path.basename(pickle_file_for_timestamp).replace(".pickle", "").replace("data_results_", "")
    else:
        pickle_timestamp = os.path.basename(pickle_file).replace(".pickle", "").replace("data_results_", "")
    print_cyan(f"Selected pickle file: {pickle_file}")
    
    data = load_data(pickle_file, use_defaults)
    print_yellow(f"Data loaded from pickle file")
    grouped_data = group_technologies(data)
    print_green(f"Technologies grouped successfully")
    print_yellow(f"Grouped data: \n{grouped_data}")
    create_figure_separated_techs(grouped_data, pickle_timestamp, use_defaults)
    print_magenta(f"Figures created and saved in {figures_folder}")
    
    print_red(f"Script finished at: {datetime.now()}")

if __name__ == "__main__":
    main()
