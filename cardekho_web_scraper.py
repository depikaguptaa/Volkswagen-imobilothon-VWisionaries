from bs4 import BeautifulSoup
import requests
import re
import time
import random
import os

# Define the Base URL and Brand Links
BASE_URL = "https://www.cardekho.com"
BRANDS = {
    "maruti-suzuki": "pattern1", "toyota": "pattern1", "porsche": "pattern1", "bmw": "pattern1",
    "tata": "pattern2", "hyundai": "pattern2", "honda": "pattern2", "skoda": "pattern2",
    "volkswagen": "pattern2", "audi": "pattern2", "mercedes-benz": "pattern2"
}

# Headers to mimic a browser request
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": BASE_URL
}

def get_full_url(relative_path):
    if relative_path.startswith("http"):
        return relative_path
    return f"{BASE_URL.rstrip('/')}/{relative_path.lstrip('/')}"

# Function to filter out unwanted sections
def process_text(text):
    cleaned_data = []
    lines = text.splitlines()
    
    for line in lines:
        # Skip lines matching the unwanted patterns
        if not re.search(r"Unknown Section|latest updates|Save \d+%-\d+%|featured in", line, re.IGNORECASE):
            cleaned_data.append(line)
    
    return "\n".join(cleaned_data)

# Function to Get All Model Links for Each Brand
def get_model_links(brand, pattern):
    if pattern == "pattern1":
        url = f"{BASE_URL}/{brand}-cars"
    else:
        url = f"{BASE_URL}/cars/{brand.capitalize()}"
        
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Failed to fetch page for {brand} with URL {url}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')

    model_links = []
    for link in soup.select("div.gsc_col-sm-12.gsc_col-xs-12.gsc_col-md-8.listView.holder.posS > a"):
        model_links.append(get_full_url(link.get('href')))
    
    return model_links

# Function to Get Variant Links from Model Page
def get_variant_links(model_url):
    response = requests.get(model_url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Failed to fetch model page with URL {model_url}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    variant_links = []

    for row in soup.select("tr[data-variant]"):
        link_tag = row.find("a", class_="pricecolor")
        if link_tag and link_tag.get('href'):
            variant_links.append(get_full_url(link_tag['href']))
    
    return variant_links

# Function to Get Specifications and Features for Each Variant
def get_variant_specs(variant_url):
    response = requests.get(variant_url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Failed to fetch variant page with URL {variant_url}")
        return None, None, {}

    soup = BeautifulSoup(response.text, 'html.parser')

    variant_name_tag = soup.select_one("h1.displayInlineBlock")
    variant_name = variant_name_tag.get_text(strip=True) if variant_name_tag else "Unknown Variant"

    specs_data = {}

    price_tag = soup.select_one("div.price")
    if price_tag:
        price = price_tag.get_text(strip=True)
        # Clean the price text to remove unwanted characters
        price = re.sub(r"(\d+(\.\d+)?\s*(Lakh|Lakhs|Crore|Crores|Cr|₹)[^A-Za-z0-9]+).*", r"\1", price)
    else:
        price = "Price not available"

    print(f"Processing variant: {variant_name}")
    print(f"Price: {price}")

    sections = soup.select("section, div[data-track-component='specificationList']")
    if not sections:
        print("No sections with specification data found.")
        return variant_name, price, specs_data

    irrelevant_sections = [
        "Compare variants", "comparison with similar cars", "alternatives to consider", 
        "Must read articles", "images", "videos", "user reviews", "news", 
        "Questions & answers", "Trending", "Top Sedan Cars", "Similar electric cars"
    ]

    for section in sections:
        section_title_tag = section.select_one("h3, h2")
        section_title = section_title_tag.get_text(strip=True) if section_title_tag else "Unknown Section"
        
        if any(keyword.lower() in section_title.lower() for keyword in irrelevant_sections):
            continue

        specs_data[section_title] = {}

        print(f"Section: {section_title}")

        rows = section.select("tr")
        if not rows:
            print(f"No rows found in section: {section_title}")
            continue

        for row in rows:
            cells = row.select("td")
            if len(cells) == 2:
                key = cells[0].get_text(strip=True)
                
                if cells[1].find('i', {'class': 'icon-deletearrow'}):
                    value = "No"
                elif cells[1].find('i', {'class': 'icon-check'}):
                    value = "Yes"
                else:
                    value = cells[1].get_text(strip=True)

                specs_data[section_title][key] = value

                print(f"  {key}: {value}")
            else:
                print(f"Row does not have exactly 2 cells: {row}")

    if not specs_data:
        print(f"No specs data extracted for variant {variant_name}")

    return variant_name, price, specs_data

# Function to Write Specs Data to TXT File
def save_specs_to_txt(variant_name, price, specs_data, filename):
    try:
        print(f"Attempting to save specs to {filename}")
        
        if not specs_data:
            print(f"  No specs data found for variant: {variant_name}")
        
        with open(filename, "w", encoding="utf-8") as file:
            file.write(f"Variant Name: {variant_name}\n")
            file.write(f"Price: {price}\n\n")
            
            raw_text = ""
            for section, specs in specs_data.items():
                raw_text += f"Section: {section}\n"
                for key, value in specs.items():
                    raw_text += f"{key}: {value}\n"
                raw_text += "\n"
            
            filtered_text = process_text(raw_text)
            file.write(filtered_text)
        
        print(f"  Saved specs and price to {filename}")
    
    except Exception as e:
        print(f"Error saving {filename}: {e}")

# Main Execution
for brand, pattern in BRANDS.items():
    model_links = get_model_links(brand, pattern)
    
    for model_index, model_url in enumerate(model_links):
        print(f"Processing model {model_index + 1} for brand '{brand}' with URL {model_url}")
        variant_links = get_variant_links(model_url)
        
        for variant_index, variant_url in enumerate(variant_links):
            print(f"  Processing variant {variant_index + 1}/{len(variant_links)}: {variant_url}")
            variant_name, price, specs_data = get_variant_specs(variant_url)
            
            if specs_data:
                filename = f"{brand}_model{model_index + 1}_variant{variant_index + 1}.txt"
                print(f"  Preparing to save {filename}...")
                save_specs_to_txt(variant_name, price, specs_data, filename)
            else:
                print(f"  No specs data for {variant_name}. Skipping save.")
            
            time.sleep(random.uniform(2, 5))