import tkinter as tk
from tkinter import ttk
import csv
from collections import defaultdict
import os

def load_and_calculate(csv_file):
    category_prices = defaultdict(list)
    with open(csv_file, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            category = row['web-scraper-start-url']  # Use this as category
            try:
                price = float(row['price'])  # Price is already numeric, just convert
                category_prices[category].append(price)
            except (ValueError, KeyError):
                continue
    averages = {cat: sum(prices) / len(prices) for cat, prices in category_prices.items()}
    return averages

root = tk.Tk()
root.title("Table UI")
root.geometry("400x200")

columns = ("Date", "Item", "Etc")
tree = ttk.Treeview(root, columns=columns, show="headings")
tree.heading("Date", text="Date")
tree.heading("Item", text="Category")  # Rename to reflect web-scraper-start-url
tree.heading("Etc", text="Average Price")
tree.column("Date", width=100, anchor="center")
tree.column("Item", width=150, anchor="center")
tree.column("Etc", width=100, anchor="center")
tree.pack(fill="both", expand=True)

# CSV file path
csv_file = r"C:\Users\Christopher\OneDrive\Desktop\MY FILES\3RD YR 2ND SEM\Capstone 1\thesis\WatchdogAI\UI\amazon.csv"

# Debug
print(f"Looking for: {os.path.abspath(csv_file)}")
if os.path.exists(csv_file):
    print("File found!")
else:
    print("File not found!")

# Load CSV and populate Treeview
try:
    averages = load_and_calculate(csv_file)
    current_date = "2025-03-22"  # Today’s date
    for category, avg_price in averages.items():
        tree.insert("", "end", values=(current_date, category, f"${avg_price:.2f}"))
except FileNotFoundError:
    print(f"Could not find {csv_file}. Please ensure it exists.")

root.mainloop()