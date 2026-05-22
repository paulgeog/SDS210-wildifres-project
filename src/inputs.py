# --------------------------------------------------------------------------------------------------
# This file contains all the functions for handling user input in the visualise_wildfires.ipynb file
# --------------------------------------------------------------------------------------------------

# imports
import ipywidgets as widgets
from IPython.display import display

params = {}

def _ask(key, prompt):
    text_input = widgets.Text(description=prompt)

    def handle_submit(widget):
        params[key] = widget.value # passes user input to input dict

    text_input.on_submit(handle_submit)
    display(text_input)

def _ask(key, prompt):
    params[key] = input(prompt)
    print(f"{key} input: {params[key]}")

def ask_area():
    _ask("area", "Enter area:")

def ask_date():
    _ask("date", "Enter date:")