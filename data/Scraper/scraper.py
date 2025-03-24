import csv
from collections import defaultdict
import chardet

# Exchange rate: 1 USD to PHP
USD_TO_PHP = 56.0

def detect_encoding(file_path):
    with open(file_path, 'r') as file:
        result = chardet.detect(file.read())
    return result['encoding']

def read_csv_and_calculate_average(file_path):
    # Dictionary to store total price and count per category
    category_totals = defaultdict(float)
    category_counts = defaultdict(int)
    
    # Detect file encoding
    encoding = detect_encoding(file_path)
    
    try:
        with open(file_path, 'r', encoding=encoding) as file:
            reader = csv.DictReader(file)
            
            if not {'Category', 'Title', 'Price'}.issubset(reader.fieldnames):
                raise ValueError("CSV file must contain 'Category', 'Title', and 'Price' columns")
            
            for row in reader:
                category = row['Category']
                try:
                    price_usd = float(row['Price'].replace('$', '').strip())
                except ValueError:
                    print(f"Skipping invalid price for {row['Title']}: {row['Price']}")
                    continue
                
                category_totals[category] += price_usd
                category_counts[category] += 1
    
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    # Calculate averages and convert to PHP
    print("-" * 40)
    for category in category_totals:
        avg_usd = category_totals[category] / category_counts[category]
        avg_php = avg_usd * USD_TO_PHP
        print(f"{category}: ₱{avg_php:.2f}")

if __name__ == "__main__":
    file_path = r'C:\Users\Christopher\OneDrive\Desktop\MY FILES\3RD YR 2ND SEM\Capstone 1\thesis\WatchdogAI\data\Scraper\item price1.csv'
    read_csv_and_calculate_average(file_path)