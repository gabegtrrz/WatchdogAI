import tkinter as tk
from tkinter import ttk
import csv
from collections import defaultdict
import os

# Conversion rate (USD to PHP)
USD_TO_PHP = 56.0  # Adjust as needed

def load_and_calculate(csv_file):
    category_prices = defaultdict(list)
    with open(csv_file, 'r') as file:
        reader = csv.DictReader(file)
        # Print headers to debug
        print("CSV Headers:", reader.fieldnames)
        for row in reader:
            # Replace with actual column names after checking headers
            category = row['web-scraper-start-url']  # Update this
            price_str = row['price'].strip()  # Update this
            if price_str:  # Skip empty prices
                try:
                    price_usd = float(price_str.replace('$', ''))
                    category_prices[category].append(price_usd)
                except ValueError:
                    continue
    averages_usd = {cat: sum(prices) / len(prices) for cat, prices in category_prices.items()}
    averages_php = {cat: usd * USD_TO_PHP for cat, usd in averages_usd.items()}
    return averages_php

root = tk.Tk()
root.title("Table UI")
root.geometry("400x200")

columns = ("Date", "Item", "Etc")
tree = ttk.Treeview(root, columns=columns, show="headings")
tree.heading("Date", text="Date")
tree.heading("Item", text="Category")
tree.heading("Etc", text="Average Price (PHP)")
tree.column("Date", width=100, anchor="center")
tree.column("Item", width=150, anchor="center")
tree.column("Etc", width=100, anchor="center")
tree.pack(fill="both", expand=True)

# CSV file path
csv_file = r"C:\Users\Christopher\OneDrive\Desktop\MY FILES\3RD YR 2ND SEM\Capstone 1\thesis\WatchdogAI\UI\MethodData.csv"

# Debug file
print(f"Looking for: {os.path.abspath(csv_file)}")
if os.path.exists(csv_file):
    print("File found!")
else:
    print("File not found!")
    exit()

# Load CSV and populate Treeview
try:
    averages = load_and_calculate(csv_file)
    current_date = "2025-03-22"
    for category, avg_price_php in averages.items():
        tree.insert("", "end", values=(current_date, category, f"₱{avg_price_php:.2f}"))
except FileNotFoundError:
    print(f"Could not find {csv_file}. Please ensure it exists.")

root.mainloop()