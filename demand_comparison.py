import os

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

# At this point, all_year_demands will have the yearly demand for each country across all year ranges

# To compare differences:
# Let's print the difference between consecutive year ranges for each country

for country, year_ranges_data in all_year_demands.items():
    print(f"Yearly demand differences for {country}:")
    sorted_year_ranges = sorted(year_ranges_data.keys())
    for i in range(1, len(sorted_year_ranges)):
        prev_year_range = sorted_year_ranges[i - 1]
        current_year_range = sorted_year_ranges[i]
        difference = year_ranges_data[current_year_range] - year_ranges_data[prev_year_range]
        print(f"{current_year_range} - {prev_year_range} = {difference}")
