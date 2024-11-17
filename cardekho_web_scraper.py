import json
import time
import random
import re
import requests
from bs4 import BeautifulSoup
import os

# the Base URL and Brand Links
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

def process_text(text):
    cleaned_data = []
    lines = text.splitlines()
    for line in lines:
        if not re.search(r"Unknown Section|latest updates|Save \d+%-\d+%|featured in", line, re.IGNORECASE):
            cleaned_data.append(line)
    return "\n".join(cleaned_data)

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
    model_links = [get_full_url(link.get('href')) for link in soup.select("div.gsc_col-sm-12.gsc_col-xs-12.gsc_col-md-8.listView.holder.posS > a")]
    return model_links

def get_variant_links(model_url):
    response = requests.get(model_url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Failed to fetch model page with URL {model_url}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    variant_links = [get_full_url(row.find("a", class_="pricecolor")['href']) for row in soup.select("tr[data-variant]") if row.find("a", class_="pricecolor")]
    return variant_links

def get_variant_specs(variant_url):
    response = requests.get(variant_url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Failed to fetch variant page with URL {variant_url}")
        return None, None, {}

    soup = BeautifulSoup(response.text, 'html.parser')
    variant_name_tag = soup.select_one("h1.displayInlineBlock")
    variant_name = variant_name_tag.get_text(strip=True) if variant_name_tag else "Unknown Variant"

    price_tag = soup.select_one("div.price")
    price = price_tag.get_text(strip=True) if price_tag else "Price not available"
    price = re.sub(r"(\d+(\.\d+)?\s*(Lakh|Lakhs|Crore|Crores|Cr|₹)[^A-Za-z0-9]+).*", r"\1", price)

    specs_data = {}
    
    # Keywords for sections to exclude
    irrelevant_sections = [
        "Save", "featured in", "latest updates", "buying a used", "Questions & answers",
        "user reviews", "Trending", "Top Sedan Cars", "comparison with similar cars",
        "alternatives to consider", "Must read articles", "images", "videos", "news",
        "Similar electric cars", "Unknown Section", "Compare variants"
    ]

    sections = soup.select("section, div[data-track-component='specificationList']")
    
    for section in sections:
        section_title_tag = section.select_one("h3, h2")
        section_title = section_title_tag.get_text(strip=True) if section_title_tag else "Unknown Section"
        
        if any(keyword.lower() in section_title.lower() for keyword in irrelevant_sections):
            continue
        
        section_specs = {}
        rows = section.select("tr")
        
        for row in rows:
            cells = row.select("td")
            if len(cells) == 2:
                key = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True) if cells[1].get_text(strip=True) else "No" if cells[1].find('i', {'class': 'icon-deletearrow'}) else "Yes"
                section_specs[key] = value
        
        if section_specs:
            specs_data[section_title] = section_specs

    return variant_name, price, specs_data

def save_to_json(data, filename="car_data.json"):
    # Save to a temporary file first to prevent corruption during writes
    temp_filename = f"{filename}.tmp"
    with open(temp_filename, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, indent=4, ensure_ascii=False)
    os.replace(temp_filename, filename)

def main():
    all_data = {}

    for brand, pattern in BRANDS.items():
        all_data[brand] = []
        model_links = get_model_links(brand, pattern)

        for model_index, model_url in enumerate(model_links):
            model_data = {"model_url": model_url, "variants": []}
            variant_links = get_variant_links(model_url)
            
            for variant_index, variant_url in enumerate(variant_links):
                variant_name, price, specs_data = get_variant_specs(variant_url)
                if specs_data:
                    variant_data = {
                        "variant_name": variant_name,
                        "price": price,
                        "specifications": specs_data
                    }
                    model_data["variants"].append(variant_data)
                    save_to_json(all_data)
                time.sleep(random.uniform(2, 5))
            all_data[brand].append(model_data)

    save_to_json(all_data)
    print("Data collection complete and saved to car_data.json")

if __name__ == "__main__":
    main()