import tkinter as tk
from tkinter import ttk
import csv
from collections import defaultdict

# Function to calculate average price per category
def load_and_calculate(csv_file):
    # Dictionary to store prices by category
    category_prices = defaultdict(list)
    
    # Read the CSV
    with open(csv_file, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            category = row['Item']  # Assuming 'Item' is the category
            try:
                price = float(row['Price'])  # Assuming 'Price' column exists
                category_prices[category].append(price)
            except (ValueError, KeyError):
                continue  # Skip invalid entries
    
    # Calculate averages
    averages = {cat: sum(prices) / len(prices) for cat, prices in category_prices.items()}
    return averages

# Create the main application window
root = tk.Tk()
root.title("Table UI")
root.geometry("400x200")

# Create a Treeview widget
columns = ("Date", "Item", "Etc")
tree = ttk.Treeview(root, columns=columns, show="headings")
tree.heading("Date", text="Date")
tree.heading("Item", text="Item")
tree.heading("Etc", text="Average Price")  # Repurpose 'Etc' for average
tree.column("Date", width=100, anchor="center")
tree.column("Item", width=150, anchor="center")
tree.column("Etc", width=100, anchor="center")
tree.pack(fill="both", expand=True)

# Load CSV and populate Treeview
csv_file = 'amazon.csv'  # Adjust to your file name
try:
    averages = load_and_calculate(csv_file)
    # Insert data into Treeview (using today's date as placeholder)
    current_date = "2025-03-22"  # Matches your current date
    for category, avg_price in averages.items():
        tree.insert("", "end", values=(current_date, category, f"${avg_price:.2f}"))
except FileNotFoundError:
    print(f"Could not find {csv_file}")

# Run the application
root.mainloop()