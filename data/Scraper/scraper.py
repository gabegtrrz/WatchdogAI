import csv
from collections import defaultdict

# Exchange rate: 1 USD to PHP
USD_TO_PHP = 56.0

def read_csv_and_calculate_average(file_path):
    # Dictionary to store total price and count per category
    category_totals = defaultdict(float)
    category_counts = defaultdict(int)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:  # Hardcode UTF-8 encoding
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
    except UnicodeDecodeError:
        print(f"Error: The file {file_path} could not be decoded as UTF-8. Please check the file's encoding.")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    # Calculate averages and convert to PHP
    print("-" * 40)
    for category in category_totals:
        avg_usd = category_totals[category] / category_counts[category]
        avg_php = avg_usd * USD_TO_PHP

if __name__ == "__main__":
    # Use a relative path for GitHub environment
    file_path = 'data/Scraper/item price1.csv'  # If running from data/Scraper/ directory
    # file_path = 'data/Scraper/item price1.csv'  # If running from the root of the repository
    read_csv_and_calculate_average(file_path)