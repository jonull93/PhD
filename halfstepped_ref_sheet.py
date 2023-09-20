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
    avg_capacity = data.groupby(['tech', 'I_reg'])['capacity'].mean()
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
        ref1 = refs[0]
        ref2 = refs[1]
        if len(refs) > 2:
            ref3 = refs[2]
    else:
        ref2 = False
        ref3 = False
    # new ref name will be the digits of ref except the FIRST DIGIT (not whole number) will be incremented by 2
    # e.g. ref134 -> ref334
    id_to_keep = int(ref1[4:])
    id_to_increment = int(ref1[3]) + 2
    my_sheetname = f"ref{id_to_increment}{id_to_keep}"
    
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