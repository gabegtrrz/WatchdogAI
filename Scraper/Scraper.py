from bs4 import BeautifulSoup
import requests
import pandas as pd
import json

URL = "https://www.amazon.com/s?k=compound+microscope+1000x"

HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
webpage = requests.get(url, headers=HEADERS)
type(webpage.content)

soup = BeautifulSoup(webpage.content, "html.parser")
links = soup.find_all("a", class_="a-link-normal a-text-normal")

soup



