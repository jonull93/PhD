import os
from my_utils import print_red, print_cyan, print_green, print_magenta, print_blue, print_yellow

def extract_yearly_demand(filepath):
    """Reads the file and returns a dictionary with yearly demand for each country."""
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # Skip header lines
    data_lines = [i for i in lines if not i.startswith('*')]
    
    yearly_demand = {}
    
    for line in data_lines:
        parts = line.split('.')
        country = parts[0].strip()
        year_range = parts[1].strip()  # Year-range is preserved as it is
        demand = float(parts[-1].strip())
        
        if country not in yearly_demand:
            yearly_demand[country] = {}
        
        if year_range not in yearly_demand[country]:
            yearly_demand[country][year_range] = 0
        
        yearly_demand[country][year_range] += demand
    
    return yearly_demand

# Directory containing the data files
directory_path = r'C:\Users\jonull\git\multinode\Include\demand_data'

# Dictionary to hold yearly demand for all countries
all_year_demands = {}

# Loop through each file in the directory
for filename in os.listdir(directory_path):
    if not filename.startswith('.') and filename.startswith("hourly_heat_demand") and "-" in filename:  # To ignore hidden files like .DS_Store in MacOS
        filepath = os.path.join(directory_path, filename)
        yearly_demands = extract_yearly_demand(filepath)
        
        for country, year_range_data in yearly_demands.items():
            if country not in all_year_demands:
                all_year_demands[country] = {}
            all_year_demands[country].update(year_range_data)

# For each country, compute the average yearly demand
average_yearly_demands = {}
for country, year_ranges_data in all_year_demands.items():
    average_yearly_demands[country] = sum(year_ranges_data.values()) / len(year_ranges_data)

# Compute global percentage range to determine the largest outliers
percentages = []
for country, year_ranges_data in all_year_demands.items():
    average_demand = average_yearly_demands[country]
    for year_range, demand in year_ranges_data.items():
        percentage = (demand / average_demand) * 100
        percentages.append(percentage)

max_deviation = max([abs(p - 100) for p in percentages])
min_deviation = min([abs(p - 100) for p in percentages])

# Function to get the colored print function based on global percentage deviation
def get_colored_print_fn(percentage):
    deviation = abs(percentage - 100)
    
    # Determine thresholds for quintiles
    quintile_thresholds = [
        max_deviation * 0.2,
        max_deviation * 0.4,
        max_deviation * 0.6,
        max_deviation * 0.8,
        max_deviation
    ]

    if deviation > quintile_thresholds[3]:
        return print_red
    elif deviation > quintile_thresholds[2]:
        return print_magenta
    elif deviation > quintile_thresholds[1]:
        return print_yellow
    elif deviation > quintile_thresholds[0]:
        return print_blue
    else:
        return print_blue
    
# At this point, all_year_demands will have the yearly demand for each country across all year ranges

# To compare differences:
# Let's print the difference between consecutive year ranges for each country

# Print the yearly demand differences as percentages of the average load
for country, year_ranges_data in all_year_demands.items():
    average_demand = average_yearly_demands[country]
    print_green(f"Yearly demand differences for {country} (Average yearly demand: {average_demand/1000:.0f} TWh):")
    sorted_year_ranges = sorted(year_ranges_data.keys())
    for i in range(len(sorted_year_ranges)):
        year_range_demand = year_ranges_data[sorted_year_ranges[i]]
        percentage = (year_range_demand / average_demand) * 100
        colored_print = get_colored_print_fn(percentage)
        colored_print(f"{sorted_year_ranges[i]}: {percentage:.1f}%")