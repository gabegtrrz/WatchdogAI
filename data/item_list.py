'''
This is where data configuration is stored for clean and maintainable code
'''

# Volatility factors (adjust for overall price fluctuation)
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