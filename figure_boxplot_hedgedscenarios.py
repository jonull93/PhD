import os
import pickle
import pandas as pd
import matplotlib.pyplot as plt
import re
from my_utils import color_dict, tech_names, print_red, print_cyan, print_green, print_magenta, print_blue, print_yellow, select_pickle, save_to_file
from order_cap import wind, PV, baseload, peak, CCS, CHP, midload, hydro, PtH, order_cap, order_cap2, order_cap3
from datetime import datetime

from figure_cap_hedgedscenarios import load_data, custom_sort, group_technologies, prettify_scenario_name

def create_whisker_plots(grouped_data, pickle_timestamp, techs_to_plot=None, separate_by_number_stochastic_years=None):
    if techs_to_plot is None:
        techs_to_plot = ["PV", "Wind", "U", "WG", "Peak", "H2store", "bat"]  # Default technologies
    tech_labels = [tech_names.get(tech, tech) for tech in techs_to_plot]
    grouped_data_df = pd.DataFrame(grouped_data)
    
    extras = [i for i in grouped_data_df.index if i in ["biogas", 'Export south', 'Export north', 'System cost']]
    
    if "System cost" in extras:#move system cost to the end
        extras.remove("System cost")
        extras.append("System cost")
        
    extra_labels = [tech_names.get(tech, tech) for tech in extras]
    contains_extras = len(extras) > 0
    contains_HP_sets = any("HP" in s.split("_")[0] for s in grouped_data)
    contains_nonHP_sets = any("opt" in s.split("_")[0] for s in grouped_data)
    
    # Extract the reference levels for 'allyears'
    reference_levels = grouped_data.get("allyears", pd.Series(dtype=float))

    # Normalize the data such that the reference levels become 1
    normalized_grouped_data = grouped_data_df.div(reference_levels, axis=0)
    reference_levels = reference_levels.filter(items=techs_to_plot, axis=0).div(reference_levels, axis=0)  # Should be all ones now

    # Create a directory for the whisker plots if it doesn't already exist
    if not os.path.exists('figures/whisker_plots'):
        os.makedirs('figures/whisker_plots')

    # Split the normalized data into individual years and sets of years
    individual_years_data = normalized_grouped_data.filter(items=[s for s in normalized_grouped_data.columns if 'singleyear' in s], axis=1)
    #{key: data for key, data in normalized_grouped_data.items() if 'singleyear' in key}
    HPsets_of_years_data = normalized_grouped_data.filter(items=[s for s in normalized_grouped_data.columns if 'singleyear' not in s and "HP" in s.split("_")[0]], axis=1)
    #{key: data for key, data in normalized_grouped_data.items() if 'singleyear' not in key and "HP" in key.split("_")[0]}
    nonHPsets_of_years_data = normalized_grouped_data.filter(items=[s for s in normalized_grouped_data.columns if 'singleyear' not in s and "opt" in s.split("_")[0]], axis=1)
    #{key: data for key, data in normalized_grouped_data.items() if 'singleyear' not in key and "opt" in key.split("_")[0]}
    random_sets_of_years_data = normalized_grouped_data.filter(items=[s for s in normalized_grouped_data.columns if "random" in s.split("_")[0]], axis=1)

    save_to_file(random_sets_of_years_data, "PickleJar/random_sets_of_years_data")

    # Filter for selected technologies
    individual_years_df = pd.DataFrame(individual_years_data)
    HPsets_of_years_df = pd.DataFrame(HPsets_of_years_data)
    nonHPsets_of_years_df = pd.DataFrame(nonHPsets_of_years_data)
    #random_sets_of_years_data = pd.DataFrame(random_sets_of_years_data) #already a dataframe

    # Print a summary of the dataframes (sizes and min, mean and max for each row)
    print(f"Individual years: {individual_years_df.shape[1]} \n{individual_years_df.T.describe().loc[['min', 'mean', 'max','std']]}")
    print(f"HP sets of years df rows/cols: {HPsets_of_years_df.shape} \n{HPsets_of_years_df.T.describe().loc[['min', 'mean', 'max','std']]}")
    print(f"Non-HP sets of years df rows/cols: {nonHPsets_of_years_df.shape} \n{nonHPsets_of_years_df.T.describe().loc[['min', 'mean', 'max','std']]}")
    print(f"Random sets of years df rows/cols: {random_sets_of_years_data.shape} \n{random_sets_of_years_data.T.describe().loc[['min', 'mean', 'max','std']]}")
    #print_yellow(f"Individual years data: \n{individual_years_df}")
    #print_yellow(f"Sets of years data: \n{HPsets_of_years_df}")
    #print_yellow(f"\nSets of random years data: \n{random_sets_of_years_data}")
    #print_yellow(f"Reference levels: \n{reference_levels}")

    secondary_axes = []
    def plot_boxplot(ax, data, labels, ylabel, yside, whisker_props, width=0.5):
        if yside.lower() in ['right', 'r']:
            ax2 = ax.twinx()  # Create a new y-axis that shares the same x-axis
            secondary_axes.append(ax2)
        else:
            ax2 = ax
        ax2.boxplot(data.T, widths=width, labels=labels, vert=True, patch_artist=True, **whisker_props, )
        ax.set_xticklabels(labels, rotation=15, ha='right', rotation_mode="anchor") #must be applied to the original axis, not the twin
        ax2.set_ylabel(ylabel, color='black')
        ax2.axhline(y=1, color='black', linestyle='-', linewidth=0.7)

    def center_title(ax_left, ax_right, title, y_position=1.06):
        if ax_right:  # If the right axis exists
            # Calculate the center x-position between the left and right axes
            left_pos = ax_left.get_position()
            right_pos = ax_right.get_position()
            center_x = (left_pos.x0 + right_pos.x1) / 2
        else:
            # Center over the left axis only
            left_pos = ax_left.get_position()
            center_x = (left_pos.x0 + left_pos.x1) / 2
        y_pos = ax_left.get_position().y0 + y_position * (ax_left.get_position().y1 - ax_left.get_position().y0)
        fig.text(center_x, y_pos, title, ha='center', va='center', fontsize=13)
      
    # Figure and Axes setup
    nr_of_rows = 1 + contains_HP_sets + contains_nonHP_sets
    if separate_by_number_stochastic_years: 
        # Add one row for each unique number of stochastic years
        unique_numbers = set(separate_by_number_stochastic_years.values())
        print(f"unique_numbers: {unique_numbers}")
        nr_of_rows = 1 + len(unique_numbers)

    nr_of_cols = 1 + contains_extras
    gridspec = {'width_ratios': [7, len(extras)] if contains_extras else [1], }
    fig, axs = plt.subplots(nrows=nr_of_rows, ncols=nr_of_cols, figsize=(8, 2 + 2 * nr_of_rows), gridspec_kw=gridspec)
    axs = axs.flatten()

    # Whisker settings
    whisker_props = dict(whis=1.5, showfliers=True, sym="o")

    ## Plotting
    plot_idx = 0
    extra_ylabel = 'Normalized values' if 'System cost'  in extra_labels else 'Normalized energy'
    titles = [f'{len(individual_years_df.columns)} individual weather-years']
    
    # Plot boxplots for individual years
    plot_boxplot(axs[plot_idx], individual_years_df.loc[techs_to_plot], tech_labels, 
                'Normalized capacity', 'left', whisker_props)
    plot_idx += 1
    if contains_extras:
        # Plot boxplots for the extra technologies
        plot_boxplot(axs[plot_idx], individual_years_df.loc[extras], extra_labels, 
                    extra_ylabel, 'right', whisker_props)
        plot_idx += 1

    # Prepare data for each row in the figure
    if separate_by_number_stochastic_years:
        datasets = []
        for number in unique_numbers:
            datasets.append(
                (True, 
                 random_sets_of_years_data.filter(
                     items=[s for s in random_sets_of_years_data.columns if separate_by_number_stochastic_years[s] == number], axis=1)))
            titles.append(f'Random sets of {number} weather-years')
    else:
        datasets = [(contains_HP_sets, HPsets_of_years_df),
                    (contains_nonHP_sets, nonHPsets_of_years_df)]
        titles += [ f'{len(HPsets_of_years_df.columns)} sets of weather-years (with hand-picking)',
                    f'{len(nonHPsets_of_years_df.columns)} sets of weather-years (without hand-picking)']
    
    print(f"datasets: {datasets}")
    
    for contains_set, df in datasets:
        if contains_set:
            # If there are HP or non-HP sets of years, plot them
            plot_boxplot(axs[plot_idx], df.loc[techs_to_plot], tech_labels, 
                        'Normalized capacity', 'left', whisker_props)
            plot_idx += 1
            if contains_extras:
                plot_boxplot(axs[plot_idx], df.loc[extras], extra_labels, 
                            extra_ylabel, 'right', whisker_props)
                plot_idx += 1
    """
    # Plot red 'X' markers for 'singleyear_1989-1990'
    # Extract the values for the scenario 'singleyear_1989-1990'
    scenario_1989_1990_values = individual_years_df['singleyear_1989-1990']
    for idx, tech in enumerate(techs_to_plot):
        if tech in scenario_1989_1990_values:
            axs[0].plot(idx + 1, scenario_1989_1990_values[tech], 'rx')  # 'rx' is red 'X' marker
    for idx, tech in enumerate(extras):
        if tech in scenario_1989_1990_values:
            axs[1].plot(idx + 1, scenario_1989_1990_values[tech], 'rx')  # 'rx' is red 'X' marker
    """

    # Set the same y-limits for both axes
    all_axes = list(axs)+secondary_axes
    y_lims = [min(ax.get_ylim()[0] for ax in all_axes), max(ax.get_ylim()[1] for ax in all_axes)]
    #only apply if has children
    def is_axis_empty(ax):
        return not (ax.lines or ax.patches or ax.texts)
    for ax in all_axes:
        if not is_axis_empty(ax):
            ax.set_ylim(y_lims)
        else: #remove the yticks
            ax.set_yticks([])

    # Add overall title and adjust layout
    #fig.suptitle('Box plots of installed capacity (normalized to All years)')
    #fig.tight_layout(rect=[0, 0.03, 1, 0.95])
    fig.tight_layout()
    fig.subplots_adjust(hspace=0.43, top=0.96, wspace=0.04)
    if contains_extras:
        for ax_idx in range(nr_of_rows):
            left = axs[ax_idx * 2]
            right = axs[ax_idx * 2 + 1]
            center_title(left, right, titles[ax_idx])
    else:
        for ax_idx in range(nr_of_rows):
            center_title(axs[ax_idx], None, titles[ax_idx])

    # Save the figure
    fig_name_base = f"figures/capacity/boxplots/{pickle_timestamp}"
    os.makedirs(os.path.dirname(fig_name_base), exist_ok=True)
    fig_num = 1
    while os.path.exists(f"{fig_name_base}_{fig_num}.png"):
        fig_num += 1
    fig.savefig(f"{fig_name_base}_{fig_num}.png", dpi=300)
    fig.savefig(f"{fig_name_base}_{fig_num}.svg")  # or .eps for EPS format
    plt.close(fig)

    # Log the success message
    print(f"Normalized whisker plots saved as '{fig_name_base}_{fig_num}.png'.")


def main():
    print_blue(f"Script started at: {datetime.now()}")
    
    #user_input = input("Press ENTER to go with default options or type anything to be prompted for choices along the way: ")
    #use_defaults = user_input.strip() == ""  # This will be True if the user just pressed enter

    print_blue(f"Script started at: {datetime.now()}")
    pickle_file = select_pickle(predetermined_choice="combine")
    if isinstance(pickle_file, list):
        # use the most recently modified pickle file to determine the timestamp
        pickle_file_for_timestamp = sorted(pickle_file, key=os.path.getmtime)[-1]
        pickle_timestamp = "agg"+os.path.basename(pickle_file_for_timestamp).replace(".pickle", "").replace(".blosc", "").replace("data_results_", "")
    else:
        pickle_timestamp = os.path.basename(pickle_file).replace(".pickle", "").replace(".blosc", "").replace("data_results_", "")
    print_cyan(f"Selected pickle file: {pickle_file}")
    
    cap_data = load_data(pickle_file, use_defaults="skip")
    bio_data = load_data(pickle_file, use_defaults="skip", data_key="biogas")
    export_data = load_data(pickle_file, use_defaults="skip", data_key="grossexport")
    cost_total = load_data(pickle_file, use_defaults="skip", data_key="cost_tot_onlynew")
    if isinstance(pickle_file, list) and any("random" in f for f in pickle_file):
        number_stochastic_years = load_data(pickle_file, use_defaults="skip", data_key="number_stochastic_years")
        number_stochastic_years = {k: v for k, v in number_stochastic_years.items() if v in [3,4,5,6]}
        #print_cyan(f"Number of stochastic years: {number_stochastic_years}")
        #input("Press ENTER to continue")
    else:
        number_stochastic_years = None

    print_yellow(f"Data loaded from pickle file")
    grouped_data = group_technologies(cap_data)
    for scenario, series in grouped_data.items():
        grouped_data[scenario] = pd.concat([series, bio_data[scenario], export_data[scenario], cost_total[scenario]])
    
    print_green(f"Technologies grouped successfully")
    print_yellow(f"Grouped data: \n{pd.DataFrame(grouped_data)}")
    create_whisker_plots(grouped_data, pickle_timestamp, separate_by_number_stochastic_years=number_stochastic_years)
    #print_magenta(f"Figures created and saved in {figures_folder}")
    
    print_red(f"Script finished at: {datetime.now()}")

if __name__ == "__main__":
    main()