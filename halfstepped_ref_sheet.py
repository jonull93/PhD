import pandas as pd
from my_utils import print_green, print_red

def load_data(ref1, ref2=False, ref3=False, filename = r'input\cap_ref.xlsx'):
    # Load data from the Excel file
    if ref2==False:
        id = int(ref1[3:])
        ref2 = f"ref{id-1}"
    sheet1 = pd.read_excel(filename, sheet_name=ref1)
    sheet2 = pd.read_excel(filename, sheet_name=ref2)
    if ref3:
        sheet3 = pd.read_excel(filename, sheet_name=ref3)
        sheet2 = pd.concat([sheet2, sheet3])
    # Combine both sheets
    combined = pd.concat([sheet1, sheet2])
    return combined


def calculate_mean_cap(data):
    # Convert the data into a multi-indexed series and compute the average
    #avg_capacity = data.groupby(['tech', 'I_reg'])['capacity'].mean()
    # to know how much to divide by, count the maximum number of rows in a groupby
    max_rows = data.groupby(['tech', 'I_reg']).size().max()
    print_green(f"Max number of rows in a groupby is {max_rows}")
    avg_capacity = data.groupby(['tech', 'I_reg'])['capacity'].sum() / max_rows
    # Prepare the DataFrame to be written back to Excel
    result = avg_capacity.sort_values(ascending=False).reset_index()
    return result


def append_to_capref(data, my_sheetname, filename = r'input\cap_ref.xlsx'):
    # First, check if the Excel file exists and is not already open
    try:
        with open(filename, 'a') as f:
            pass
    except IOError:
        print_red(f"!! The file {filename} does not exist. Please doublecheck the path.")
        return
    except PermissionError:
        print_red(f"!! The file {filename} is already open. Please close it and then type something below:")
        input("Press Enter to continue...")
    # Check if my_sheetname already exists in the Excel file and whether it is empty
    sheets = pd.ExcelFile(filename).sheet_names
    if my_sheetname in sheets:
        # if it is empty, delete it and continue
        if pd.read_excel(filename, sheet_name=my_sheetname).empty:
            print_green(f"Sheet {my_sheetname} already exists but is empty, so it will be deleted.")
            with pd.ExcelWriter(filename, engine='openpyxl', mode='a') as writer:
                writer.book.remove(writer.book[my_sheetname])
        # if it is not empty, leave it be and exit
        else:
            print_red(f"!! Sheet {my_sheetname} already exists and is not empty, so it will not be modified.")
            return
    # Load the entire Excel file
    with pd.ExcelWriter(filename, engine='openpyxl', mode='a') as writer:
        # Write the result DataFrame
        data.to_excel(writer, sheet_name=my_sheetname, index=False)
        # Position 'averaged_data' in the third place
        workbook = writer.book
        sheet = workbook[my_sheetname]
        idx = workbook._sheets.index(sheet)
        workbook._sheets.insert(2, workbook._sheets.pop(idx))
    print_green(f"Added sheet {my_sheetname} to the sheet!")


def ask_for_refname():
    # Ask the user for the ref to use
    ref1 = input("Enter the ref to use (separated by , if multiple): ")
    if "," in ref1:
        refs = ref1.split(",")
        ref1 = refs[0].strip()
        ref2 = refs[1].strip()
        if len(refs) == 3:
            ref3 = refs[2].strip()
        else: ref3 = False
    else:
        ref2 = False
        ref3 = False
    # new ref name will be the digits of ref except the FIRST DIGIT (not whole number) will be incremented by 2
    # e.g. ref134 -> ref334
    #extract the digits from ref1
    refdigits = [char for char in ref1 if char.isdigit()]
    if len(refdigits) >= 3:
        nr_of_opt_years_id = ref1[4]
        iteration_id = ref1[5:]
        algorithm_mode_id = int(ref1[3])
        if algorithm_mode_id == 1:
            algorithm_mode_id = 3
        elif algorithm_mode_id == 3:
            if "_out" in iteration_id:
                iteration_id = int(iteration_id.replace("_out", ""))
            iteration_id = int(iteration_id) + 1

        my_sheetname = f"ref{algorithm_mode_id}{nr_of_opt_years_id}{iteration_id}"
    elif len(refdigits) < 3:
        # increment the digit of ref1 until it is a sheet name that does not exist yet
        refnum = int("".join(refdigits))
        while True:
            refnum += 1
            my_sheetname = f"ref{refnum}"
            if my_sheetname not in pd.ExcelFile("input\\cap_ref.xlsx").sheet_names:
                break
    return ref1, ref2, ref3, my_sheetname


if __name__ == "__main__":
    # Ask the user for the ref to use
    ref1, ref2, ref3, my_sheetname = ask_for_refname()
    # Load the data
    data = load_data(ref1, ref2, ref3)
    # Calculate the average capacity
    averaged_data = calculate_mean_cap(data)
    # Append the result to the Excel file
    append_to_capref(averaged_data, my_sheetname)