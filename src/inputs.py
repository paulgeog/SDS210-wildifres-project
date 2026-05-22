# --------------------------------------------------------------------------------------------------
# This file contains all the functions for handling user input in the visualise_wildfires.ipynb file
# --------------------------------------------------------------------------------------------------

# imports
import ipywidgets as widgets
from IPython.display import display

params = {}

def _ask(key, prompt):
    params[key] = input(prompt)
    print(f"{key} input: {params[key]}")

def ask_area():
    _ask("area", "Enter area:")

def ask_date():
    _ask("date", "Enter date:")

def ask_sensor():
    _ask("sensor", "Enter sensor/dataset:")

def ask_n_days():
    _ask("n_days", "Enter time range:")
    if params["n_days"] == "":
        return
    try:
        params["n_days"] = int(params["n_days"])
    except ValueError:
        raise ValueError("Invalid input for number of days. Must be an integer between 1 and 5 or left empty.")
    
def ask_browser():
    _ask("browser", "Enter 'True' or 'False':")
    if params["browser"] == "":
        return
    if params["browser"].lower() == 'true':
        params["browser"] = True
    elif params["browser"].lower() == 'false':
        params["browser"] = False
    else:
        raise ValueError("Invalid input for 'open in browser'. Must be 'True' or 'False' or left empty.")
    
def ask_max_rows():
    _ask("max_rows", "Enter number of data points to render:")
    if params["max_rows"] == "":
        return 5000
    try:
        params["max_rows"] = int(params["max_rows"])
    except ValueError:
        raise ValueError("Maximum number of rows must be an INTEGER.")
    return params["max_rows"]
    
def generate_map():
    params["enter"] = input("Press 'Enter' to generate the map")
    del params["enter"]

def generate_query_parameters():
    cleaned = {k: v for k, v in params.items() if v != ""}
    del cleaned["browser"]
    del cleaned["max_rows"]
    return cleaned
