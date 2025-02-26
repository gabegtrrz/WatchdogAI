
### This is where data configuration is stored for clean and maintainable code
### Scenario is procurement of Educational Materials for Grade 10 Science Class

import pandas as pd


METHODS_DATA = {
    "Competitive Bidding": {
        "frequency": 0.5,
        "items": {
            "Compound Microscope (1000x)": 121409.38,
            "Refracting Telescope (70mm)": 5207.81,
            "Beaker (50ml)": 161.00, "Beaker (100ml)": 182.00,
            "Beaker (250ml)": 238.00, "Beaker (500ml)": 375.00,
            "Test Tube (10ml)": 19.00, "Test Tube (20ml)": 25.00,
            "Bunsen Burner": 334.62, "Triple Beam Balance": 2989.00,
            "Microscope Slides (box of 50)": 489.01,
            "Microscope Coverslips (box of 100)": 7520.34,
            "Dissecting Kit (basic)": 630.79,
            "Sodium Chloride (NaCl) - Solid (1kg)": 2700,
            "Hydrochloric Acid (HCl) - 1M (1L)": 1475.13,
            "Lab Manual - Grade 10 Science": 333.30
        }
    },
    "Limited Source Bidding": {
        "frequency": 0.2,
        "items": {
            "Reflecting Telescope (150mm)": 20255.87,
            "Digital Spectrophotometer": 18519.60,
            "High-Precision Balance": 15915
        }
    },
    "Negotiated Procurement": {
        "frequency": 0.2,
        "items": {
            "Potassium Iodide (KI) - Solid (500g)": 1661,
            "AmScope M150B-LED Replacement LED Bulb": 693.93,
            "Beaker (1000ml)": 2044
        }
    },
    "Direct Contracting": {
        "frequency": 0.1,
        "items": {
            "Replacement Xenon Flash Lamp for Do PerkinElmer": 2893.78,
            "Sulfuric Acid (H2SO4) - 1M (1L)": 1302
        }
    }
}

# Converting this into a DataFrame for manageable data handling
rows = []
for method, values in METHODS_DATA.items():
    frequency = values['frequency']
    items = values['items']

    for item, base_price in items.items():

        row = {
            "Method": method,
            "Frequency": frequency,
            "Item": item,
            "Base_Price": base_price
        }
        rows.append(row)

PROCUREMENT_DATA = pd.DataFrame(rows)

print(PROCUREMENT_DATA.head())



### VOLATILITY VARIABLES (adjust for overall price fluctuation)
VOLATILITY_LOW = 0.05
VOLATILITY_MEDIUM = 0.10
VOLATILITY_HIGH = 0.15


BASE_PRICES = {
        "Compound Microscope (1000x)": 121409.38,
        "Refracting Telescope (70mm)": 5207.81,
        "Beaker (50ml)": 161.00,
        "Beaker (100ml)": 182.00,
        "Beaker (250ml)": 238.00,
        "Beaker (500ml)": 375.00,
        "Test Tube (10ml)": 19.00,
        "Test Tube (20ml)": 25.00,
        "Bunsen Burner": 334.62,
        "Triple Beam Balance": 2989.00,
        "Microscope Slides (box of 50)": 489.01,
        "Microscope Coverslips (box of 100)": 7520.34,
        "Dissecting Kit (basic)": 630.79,
        "Sodium Chloride (NaCl) - Solid (1kg)": 2700,
        "Hydrochloric Acid (HCl) - 1M (1L)": 1475.13,
        "Lab Manual - Grade 10 Science": 333.30,
        "Reflecting Telescope (150mm)": 20255.87,
        "Digital Spectrophotometer": 18519.60,
        "High-Precision Balance": 15915,
        "Potassium Iodide (KI) - Solid (500g)": 1661,
        "AmScope M150B-LED Replacement LED Bulb": 693.93,
        "Beaker (1000ml)": 2044,
        "Replacement Xenon Flash Lamp for Do PerkinElmer])": 2893.78,
        "Sulfuric Acid (H2SO4) - 1M (1L)": 1302
}

ITEMS = list(BASE_PRICES.keys())

''' WE NEED TO PUT THIS IN PROCUREMENT_DATA.PY
    procurement_methods = {
    "Competitive Bidding": {
        "items": ["Compound Microscope (1000x)", "Refracting Telescope (70mm)", "Beaker (50ml)", "Beaker (100ml)", "Beaker (250ml)", "Beaker (500ml)", "Test Tube (10ml)", "Test Tube (20ml)", "Bunsen Burner", "Triple Beam Balance", "Microscope Slides (box of 50)", "Microscope Coverslips (box of 100)", "Dissecting Kit (basic)", "Sodium Chloride (NaCl) - Solid (1kg)", "Hydrochloric Acid (HCl) - 1M (1L)", "Lab Manual - Grade 10 Science"],
        "frequency": 0.5
    },
    "Limited Source Bidding": {
        "items": ["Reflecting Telescope (150mm)", "Digital Spectrophotometer", "Data Analysis Software (Logger Pro)", "High-Precision Balance"],
        "frequency": 0.2
    },
    "Negotiated Procurement": {
        "items": ["Potassium Iodide (KI) - Solid (500g)", "AmScope M150B-LED Replacement LED Bulb", "Beaker (1000ml)"],
        "frequency": 0.2
    },
    "Direct Contracting": {
        "items": ['Calibration Service (for high-precision balance)', "Replacement Xenon Flash Lamp for Do PerkinElmer", "Sulfuric Acid (H2SO4) - 1M (1L)"], 
        "frequency": 0.1
    }
    }
'''