import os
import pandas as pd
import matplotlib.pyplot as plt
import glob
from my_utils import color_dict, tech_names, print_red, print_cyan, print_green, print_magenta, print_blue, print_yellow
from order_cap import wind, PV, baseload, peak, CCS, CHP, midload, hydro, PtH, order_cap, order_cap2
from datetime import datetime

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
    'Other thermals': CCS + CHP + midload + ["W"]
}
techs_to_exclude = PtH + ["Electrolyser", "electrolyser", "H", "b", "H_CHP", "B_CHP"]
storage_techs = ["bat", "H2store"]
storage_techs = storage_techs + [tech_names[t] for t in storage_techs if t in tech_names]

def select_pickle(use_defaults):
    pickle_files = glob.glob(os.path.join(pickle_folder, "data_results_*.pickle"))
    if not pickle_files:
        print_red("No data_results_*.pickle file found in PickleJar folder.")
        return None
    
    pickle_files.sort(key=os.path.getmtime, reverse=True)
    print_blue(f"Found {len(pickle_files)} data_results_*.pickle files.")
    print_blue(f"Most recent file: {pickle_files[0]}")

    if use_defaults or len(pickle_files) == 1:
        # Either use defaults or no appropriate pickle files were found, so just use the most recent file
        #most_recent_file = max(pickle_files, key=lambda x: os.path.getctime(pickle_folder + x))
        return pickle_files[0]

    print_yellow("Select the pickle file to load:")
    print_yellow("1. Most recent file")
    print_yellow("2. Largest file")
    print_yellow("3. Hardcoded filename")

    user_input = input("Please enter the option number: ")
    if user_input == '1':
        # Most recent file
        return pickle_files[0]  # The list is already sorted by modification time
    elif user_input == '2':
        # Largest file
        pickle_files.sort(key=os.path.getsize, reverse=True)
        return pickle_files[0]
    elif user_input == '3':
        # Hardcoded filename
        hardcoded_filename = pickle_folder + 'data_results_20230529_162027.pickle'  # Replace with the filename you want
        if hardcoded_filename in pickle_files:
            return hardcoded_filename
        else:
            print_red("The hardcoded file was not found in the directory. Falling back to the most recent file.")
            return pickle_files[0] # The list is already sorted by modification time


def load_data(pickle_file, use_defaults):
    # Load the pickle file
    data = pd.read_pickle(pickle_file)
    
    # Handle scenario selection
    all_scenarios = list(data.keys())
    print_cyan(f"All scenarios: {all_scenarios}")
    
    selected_scenarios = []
    if use_defaults:
        # Use all scenarios, but if there's a scenarioname with "1h", skip the one with "3h" if there is one
        selected_scenarios = all_scenarios 
        for s in all_scenarios:
            if "1h" in s:
                selected_scenarios = [s for s in all_scenarios if s != s.replace("1h", "3h")]
                break
            # then do the same to skip the "tight" scenarios
            if "tight" not in s:
                selected_scenarios = [s for s in all_scenarios if s != s + "tight"]
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
               
    # Extract 'tot_cap' data for the selected scenarios and replace NaNs with 0
    selected_data = {scenario: data[scenario]['tot_cap'].fillna(0) for scenario in selected_scenarios}

    # Remove "ref_cap" from scenario names 
    selected_data = {s.replace("ref_cap_", ""): selected_data[s] for s in selected_data.keys()}
    selected_data = {s.replace("singleyear_", ""): selected_data[s] for s in selected_data.keys()}
    selected_data = {s.replace("to", "-"): selected_data[s] for s in selected_data.keys()}
    return selected_data


def group_technologies(data):
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



def create_figure(grouped_data, pickle_timestamp, use_defaults):
    # Create a directory for the figures if it doesn't already exist
    if not os.path.exists('figures/capacity'):
        os.makedirs('figures/capacity')

    # Create a figure and axis
    fig, ax1 = plt.subplots()

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
    width = 0.35

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
            return f'{height:.1f}'
        else:
            return ''

    # Apply this function to each bar
    for container in bars1.containers:
        labels1 = [conditional_label(bar, 40) for bar in container]
        ax1.bar_label(container, labels=labels1, label_type='center', fontsize=9)

    for container in bars2.containers:
        labels2 = [conditional_label(bar, 40) for bar in container]
        ax2.bar_label(container, labels=labels2, label_type='center', fontsize=9)
    
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
    grouped_data = group_technologies(data)
    print_green(f"Technologies grouped successfully")
    print_yellow(f"Grouped data: \n{grouped_data}")
    create_figure(grouped_data, pickle_timestamp, use_defaults)
    print_magenta(f"Figures created and saved in {figures_folder}")
    
    print_red(f"Script finished at: {datetime.now()}")

if __name__ == "__main__":
    main()
