import re
import requests
import json
import threading
import os
from django.http import JsonResponse

renderer_port = 3000
renderer_url = f"https://rendertron-436513.appspot.com/render/"
url = "https://artoftravel.tips/list-of-countries-by-continents/"
req_url = renderer_url + url

response = requests.get(req_url)
html_content = response.text

# Regular expression patterns
continent_pattern = r'<h[23]>(?![A-Z]</h[23]>)(?!Recent Posts</h[23]>)(?!Blog Topics</h[23]>)[A-Z][a-z]*(?:\s[A-Z][a-z]*)*</h[23]>'
list_element_pattern = r"<ul>(.*?)</ul>"
country_pattern = r'<li><span style="font-size: 20px;">([^<(]+)</span></li>'

# Country mapping for special cases
expt_country_mapping = {
    "Gambia": "the-gambia",
    "Swaziland": "eswatini",
    "South Korea": "korea",
    "Turkey": "turkiye",
    "United Arab Emirates": "uae",
    "Bosnia and Herzegovina": "bih",
    "Republic of Ireland": "ireland",
    "United States of America": "usa",
    "Bahamas": "the-bahamas",
}

continent_country_map = {}
countries_endpoint_map = {}

# Function to format the country name for TasteAtlas
def format_country_name(country_name):
    return expt_country_mapping.get(country_name, re.sub(r"[^\w\s-]", "", country_name.lower()).replace(" ", "-"))

# Function to check if the country is available on TasteAtlas
def is_country_available(country_name, results, lock):
    formatted_name = format_country_name(country_name)
    countries_endpoint_map[country_name] = formatted_name
    print(countries_endpoint_map)
    url = f"https://www.tasteatlas.com/{formatted_name}?ref=main-menu"
    response = requests.head(url)
    with lock:
        results[country_name] = response.status_code == 200

def get_countries_by_continent(request):
    # Find all continent headers without the <h2> or <h3> tags
    matches_continent = re.findall(continent_pattern, html_content)
    matches_continent = [re.sub(r'</?h[23]>', '', continent).strip() for continent in matches_continent]
    matches_continent = matches_continent[1:]  # Remove Antarctica

    # Extract lists of countries
    _extracted_list_element = re.findall(list_element_pattern, html_content)
    

    max_threads = os.cpu_count() or 1  # Ensure at least one thread

    # Iterate through continents and their corresponding lists
    for idx, continent in enumerate(matches_continent):
        country_list = re.findall(country_pattern, _extracted_list_element[idx])
        valid_countries = []
        results = {}
        threads = []
        lock = threading.Lock()  # Lock for thread-safe operations

        # Create and start threads
        for country in country_list:
            thread = threading.Thread(target=is_country_available, args=(country, results, lock))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Collect valid countries based on the results
        for country in country_list:
            if results.get(country, False):
                valid_countries.append(country)
            else:
                print(f"{country} does NOT exist on TasteAtlas.")

        # Add the continent and its valid countries to the dictionary
        if valid_countries:
            continent_country_map[continent] = valid_countries

    # Return JSON response
    return JsonResponse({
        "continent_country_map": continent_country_map,
        "countries_endpoint_map": countries_endpoint_map
    })
