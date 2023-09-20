import pandas as pd

# Load data from the Excel file
filename = r'input\cap_ref.xlsx'
sheet1 = pd.read_excel(filename, sheet_name='ref134')
sheet2 = pd.read_excel(filename, sheet_name='ref133')

# Combine both sheets
combined = pd.concat([sheet1, sheet2])

# Convert the data into a multi-indexed series and compute the average
avg_capacity = combined.groupby(['tech', 'I_reg'])['capacity'].mean()

# Prepare the DataFrame to be written back to Excel
result = avg_capacity.reset_index()

# Load the entire Excel file
with pd.ExcelWriter(filename, engine='openpyxl', mode='a') as writer:
    # Check if "info" and "cap_comp" sheets exist
    if 'info' in writer.sheets:
        info_position = writer.sheets.index('info')
    else:
        info_position = 0
    
    if 'cap_comp' in writer.sheets:
        cap_comp_position = writer.sheets.index('cap_comp')
    else:
        cap_comp_position = 1
    
    # Define the desired position for the new sheet
    start_position = max(info_position, cap_comp_position) + 1
    
    # Write the result DataFrame in the desired position
    result.to_excel(writer, sheet_name='averaged_data', index=False, startrow=start_position)

print("Done!")
