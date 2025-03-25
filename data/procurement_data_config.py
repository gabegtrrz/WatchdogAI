
### This is where data configuration is stored for clean and maintainable code
### Scenario is procurement of Educational Materials for Grade 10 Science Class

import pandas as pd

### PROCUREMENT_METHODS HERE ###

METHODS_DATA = {
    "Competitive Bidding": {
        "frequency": 0.5,
        "items": {
            "Compound Microscope": average_prices_here,
            "Beaker 50ml": average_prices_here,
            "Beaker 100ml": average_prices_here,
            "Beaker 250ml": average_prices_here, 
            "Test Tube 15ml": average_prices_here, 
            "Bunsen Burner": average_prices_here,
            "Thermometer (-10 to 110C)": average_prices_here, 
            "Microscope Slides": average_prices_here,
            "Lab Manual - Grade 10 Science": average_prices_here,
            "Erlenmeyer Flask 250ml": average_prices_here,
            "Test Tube Rack": average_prices_here,
            "Filter Paper pack of 100": average_prices_here,
        }
    },
    "Limited Source Bidding": {
        "frequency": 0.2,
        "items": {
            "Refracting Telescope 70mm": average_prices_here,
            "Triple Beam Balance":  average_prices_here,
            "pH Meter basic":  average_prices_here,
            "Graduated Cylinder 100ml": average_prices_here,
            "Hot Plate basic": average_prices_here,
            "Stopwatch digital":  average_prices_here,
            "Prism glass":  average_prices_here,
            "Spring Scale 500g": average_prices_here,
            "Bar Magnet pair":  average_prices_here,
            "Tuning Fork 256 Hz":  average_prices_here,
            "Lens Set convex concave":  average_prices_here,
            "Ammeter basic": average_prices_here,
        }
    },
    "Negotiated Procurement": {
        "frequency": 0.2,
        "items": {
            "Voltmeter basic": average_prices_here,
            "Hydrochloric Acid": average_prices_here,
            "Dissecting Kit": average_prices_here,
            "Petri Dishes pack of 20": average_prices_here,
            "Universal Indicator Solution 100ml": average_prices_here,
            "Copper Sulfate": average_prices_here,
            "Rubber Stoppers": average_prices_here,
            "Dropper Bottle 50ml": average_prices_here,
            "Agar Powder 100g": average_prices_here,
            "Iron Filings 250g": average_prices_here,
        }
    },
    "Direct Contracting": {
        "frequency": 0.1,
        "items": {
            "Safety Goggles":  average_prices_here,
            "Litmus Paper": average_prices_here,
            "Pipette 10ml": average_prices_here,
            "Gloves nitrile box of 100": average_prices_here,
            "Lab Aprons pack of 10": average_prices_here,
            "Funnel plastic 100mm": average_prices_here,
            "Alcohol Burner": average_prices_here,
            "Fire Blanket": average_prices_here,
            "Test Tube Brush": average_prices_here,
            "Microscope Coverslips box of 100": average_prices_here,
            "Spatula stainless steel": average_prices_here,
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
            "Item_Name": item,
            "Base_Price": base_price
        }
        rows.append(row)

### Final Procurement Data HERE

PROCUREMENT_DATA = pd.DataFrame(rows)

PROCUREMENT_OFFICERS = [
        'Casey Hernandez',
        'Alex Rivera',
        'James Patrick Mendoza',
        'Morgan Cruz',
        'Angela Ramirez',
        'Taylor Martinez',
        'Sophia Christine Navarro',
        'Angela Renee Mendoza',
        'Luke Andrew Navarro',
        'Jamie Thompson',
        'Christine Bautista',
        ]

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