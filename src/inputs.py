# --------------------------------------------------------------------------------------------------
# This file contains all the functions for handling user input in the visualise_wildfires.ipynb file
# --------------------------------------------------------------------------------------------------

# imports
from IPython.display import display

params = {}

def _ask(key, prompt):
    value = input(prompt)
    if value.lower() == 'x':
        if key in params and params[key] != "":
            print(f"{key} kept as: {params[key]}")
        else:
            raise ValueError(f"No value for {key} yet, nothing to keep.")
    else:
        params[key] = value
        if value == '':
            print(f"{key} set to: default value")
        else:
            print(f"{key} set to: {params[key]}")

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
    _ask("browser", "Open in Browser: Enter 'True' or 'False':")
    if params["browser"] == "":
        params["browser"] = False
    elif type(params["browser"]) == bool:
        params["browser"] = params["browser"]
    elif params["browser"].lower() == 'true':
        params["browser"] = True
    elif params["browser"].lower() == 'false':
        params["browser"] = False
    else:
        raise ValueError("Invalid input for 'open in browser'. Must be 'True' or 'False' or left empty.")
    
def ask_save():
    _ask("save", "Save map: Enter 'True' or 'False':")
    if params["save"] == "":
        params["save"] = True
    elif type(params["save"]) == bool:
        params["save"] = params["save"]
    elif params["save"].lower() == 'true':
        params["save"] = True
    elif params["save"].lower() == 'false':
        params["save"] = False
    else:
        raise ValueError("Invalid input for 'save map'. Must be 'True' or 'False' or left empty.")
    
def ask_max_rows():
    _ask("max_rows", "Enter number of data points to render:")
    if params["max_rows"] == "":
        params["max_rows"] = 5000
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
    if params.get("browser") == True:
        params["save"] = True
    del cleaned["browser"]
    del cleaned["max_rows"]
    del cleaned["save"]
    return cleaned

def generate_mapping_parameters(WF):
    include = ["save", "browser", "max_rows"]
    result = {}
    for key in include:
        result[key] = params[key]
    result["wf"] = WF
    return result

def check_params(PARAMS: dict):
    if "sensor" in PARAMS:
        return
    else:
        raise ValueError("Sensor/Dataset not specified.")
    
def get_params():
    return params

