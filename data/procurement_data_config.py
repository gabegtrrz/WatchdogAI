### This is where data configuration is stored for clean and maintainable code
### Scenario is procurement of Educational Materials for Grade 10 Science Class

import pandas as pd
from Scraper.scraper import read_csv_and_calculate_average

CSV_FILE_PATH = r'data/Scraper/item price1.csv'

average_prices = read_csv_and_calculate_average(CSV_FILE_PATH)

### PROCUREMENT_METHODS HERE ###
METHODS_DATA = {
    "Competitive Bidding": {
        "frequency": 0.5,
        "items": {
            "Compound Microscope": average_prices.get("Compound Microscope", 0.0) if average_prices else 0.0,
            "Beaker 50ml": average_prices.get("Beaker 50ml", 0.0) if average_prices else 0.0,
            "Beaker 100ml": average_prices.get("Beaker 100ml", 0.0) if average_prices else 0.0,
            "Beaker 250ml": average_prices.get("Beaker 250ml", 0.0) if average_prices else 0.0, 
            "Test Tube 15ml": average_prices.get("Test Tube 15ml", 0.0) if average_prices else 0.0, 
            "Bunsen Burner": average_prices.get("Bunsen Burner", 0.0) if average_prices else 0.0,
            "Thermometer (-10 to 110C)": average_prices.get("Thermometer (-10 to 110C)", 0.0) if average_prices else 0.0, 
            "Microscope Slides": average_prices.get("Microscope Slides", 0.0) if average_prices else 0.0,
            "Lab Manual - Grade 10 Science": average_prices.get("Lab Manual - Grade 10 Science", 0.0) if average_prices else 0.0,
            "Erlenmeyer Flask 250ml": average_prices.get("Erlenmeyer Flask 250ml", 0.0) if average_prices else 0.0,
            "Test Tube Rack": average_prices.get("Test Tube Rack", 0.0) if average_prices else 0.0,
            "Filter Paper pack of 100": average_prices.get("Filter Paper pack of 100", 0.0) if average_prices else 0.0,
        }
    },
    "Limited Source Bidding": {
        "frequency": 0.2,
        "items": {
            "Refracting Telescope 70mm": average_prices.get("Refracting Telescope 70mm", 0.0) if average_prices else 0.0,
            "Triple Beam Balance": average_prices.get("Triple Beam Balance", 0.0) if average_prices else 0.0,
            "pH Meter basic": average_prices.get("pH Meter basic", 0.0) if average_prices else 0.0,
            "Graduated Cylinder 100ml": average_prices.get("Graduated Cylinder 100ml", 0.0) if average_prices else 0.0,
            "Hot Plate basic": average_prices.get("Hot Plate basic", 0.0) if average_prices else 0.0,
            "Stopwatch digital": average_prices.get("Stopwatch digital", 0.0) if average_prices else 0.0,
            "Prism glass": average_prices.get("Prism glass", 0.0) if average_prices else 0.0,
            "Spring Scale 500g": average_prices.get("Spring Scale 500g", 0.0) if average_prices else 0.0,
            "Bar Magnet pair": average_prices.get("Bar Magnet pair", 0.0) if average_prices else 0.0,
            "Tuning Fork 256 Hz": average_prices.get("Tuning Fork 256 Hz", 0.0) if average_prices else 0.0,
            "Lens Set convex concave": average_prices.get("Lens Set convex concave", 0.0) if average_prices else 0.0,
            "Ammeter basic": average_prices.get("Ammeter basic", 0.0) if average_prices else 0.0,
        }
    },
    "Negotiated Procurement": {
        "frequency": 0.2,
        "items": {
            "Voltmeter basic": average_prices.get("Voltmeter basic", 0.0) if average_prices else 0.0,
            "Hydrochloric Acid": average_prices.get("Hydrochloric Acid", 0.0) if average_prices else 0.0,
            "Dissecting Kit": average_prices.get("Dissecting Kit", 0.0) if average_prices else 0.0,
            "Petri Dishes pack of 20": average_prices.get("Petri Dishes pack of 20", 0.0) if average_prices else 0.0,
            "Universal Indicator Solution 100ml": average_prices.get("Universal Indicator Solution 100ml", 0.0) if average_prices else 0.0,
            "Copper Sulfate": average_prices.get("Copper Sulfate", 0.0) if average_prices else 0.0,
            "Rubber Stoppers": average_prices.get("Rubber Stoppers", 0.0) if average_prices else 0.0,
            "Dropper Bottle 50ml": average_prices.get("Dropper Bottle 50ml", 0.0) if average_prices else 0.0,
            "Agar Powder 100g": average_prices.get("Agar Powder 100g", 0.0) if average_prices else 0.0,
            "Iron Filings 250g": average_prices.get("Iron Filings 250g", 0.0) if average_prices else 0.0,
        }
    },
    "Direct Contracting": {
        "frequency": 0.1,
        "items": {
            "Safety Goggles": average_prices.get("Safety Goggles", 0.0) if average_prices else 0.0,
            "Litmus Paper": average_prices.get("Litmus Paper", 0.0) if average_prices else 0.0,
            "Pipette 10ml": average_prices.get("Pipette 10ml", 0.0) if average_prices else 0.0,
            "Gloves nitrile box of 100": average_prices.get("Gloves nitrile box of 100", 0.0) if average_prices else 0.0,
            "Lab Aprons pack of 10": average_prices.get("Lab Aprons pack of 10", 0.0) if average_prices else 0.0,
            "Funnel plastic 100mm": average_prices.get("Funnel plastic 100mm", 0.0) if average_prices else 0.0,
            "Alcohol Burner": average_prices.get("Alcohol Burner", 0.0) if average_prices else 0.0,
            "Fire Blanket": average_prices.get("Fire Blanket", 0.0) if average_prices else 0.0,
            "Test Tube Brush": average_prices.get("Test Tube Brush", 0.0) if average_prices else 0.0,
            "Microscope Coverslips box of 100": average_prices.get("Microscope Coverslips box of 100", 0.0) if average_prices else 0.0,
            "Spatula stainless steel": average_prices.get("Spatula stainless steel", 0.0) if average_prices else 0.0,
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