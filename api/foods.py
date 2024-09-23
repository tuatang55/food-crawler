import requests
import re
import json
import threading
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json as js

renderer_port = 3000
renderer_url = f"http://localhost:{renderer_port}/render/"
base_url = "https://www.tasteatlas.com/"

# Extract food names from HTML
def extract_food_names(html_content):
    pattern = r'</div><h2 class="h2 h2--bold h2--lowercase"><a (.*?)</a></h2>'
    return re.findall(pattern, html_content)

# Get food names for a specific country
def get_foods_from_country(country_endpoint):
    url = f"https://www.tasteatlas.com/{country_endpoint}?ref=main-menu"
    req_url = renderer_url + url
    response = requests.get(req_url)
    return extract_food_names(response.text) if response.status_code == 200 else []

# Extract food metadata from HTML
def extract_food_metadata(html_content):
    food_name_pattern = r'<h1 class="h1 ng-binding ng-scope" ng-if="\$ctrl.preloadedDetails.Certificates.length === 0">(.*?)</h1>'
    categories_pattern = r'<a class="category-name-items[^"]*"[^>]*href="[^>]*">([^<]+)</a>'
    description_pattern = r'<div class="read-more--hidden ng-scope">(.*?)</div>'
    food_image_pattern = r'<div ng-if="photo.Image" class="swiper-slide ng-scope" ng-repeat="photo in \$ctrl.photos track by \$index"><img[^>]*src="([^"]*)"'
    country_name_pattern = r'<a ng-if="\$ctrl.preloadedDetails.Region.Current.Name" class="region-name ng-scope" href="[^"]*"><span class="ng-binding">(.*?)<!-- ngIf: !\$ctrl.preloadedDetails.Region.Parent.IsContinent --></span></a>'
    country_flag_pattern = r'<div class="emblem">.*?<img[^>]*src="([^"]+)"'

    food_name = re.search(food_name_pattern, html_content)
    categories = re.findall(categories_pattern, html_content)
    description = re.search(description_pattern, html_content)
    food_image = re.search(food_image_pattern, html_content)
    country_name = re.search(country_name_pattern, html_content)
    country_flag = re.search(country_flag_pattern, html_content)

    cleaned_description = description.group(1) if description else ""

    return {
        food_name.group(1) if food_name else "N/A": {
            "categories": categories,
            "country": {
                "name": country_name.group(1) if country_name else "N/A",
                "flag": base_url + country_flag.group(1) if country_flag else "N/A"
            },
            "description": cleaned_description,
            "image_url": base_url + food_image.group(1) if food_image else "N/A"
        }
    }

# Fetch metadata for a food item
def fetch_food_metadata(food_endpoint):
    url = f"https://www.tasteatlas.com/{food_endpoint}"
    req_url = renderer_url + url
    response = requests.get(req_url)
    return extract_food_metadata(response.text) if response.status_code == 200 else {}

@csrf_exempt  # Use this to bypass CSRF for testing purposes (not recommended for production)
def get_foods_by_selected_countries(request):
    if request.method == 'PUT':
        body = json.loads(request.body)
        select_countries = body.get('selected_countries', [])
        foods_json = {}

        def thread_function(country_endpoint):
            food_list = get_foods_from_country(country_endpoint)
            food_endpoint_pattern = r' href="([^"]+)"'
            country_foods = {}

            for food in food_list:
                food_metadata = fetch_food_metadata(re.search(food_endpoint_pattern, food).group(1))
                country_foods.update(food_metadata)

            foods_json[country_endpoint] = {"foods": country_foods}

        threads = []
        max_threads = 5

        for country in select_countries:
            thread = threading.Thread(target=thread_function, args=(country,))
            threads.append(thread)
            thread.start()

            if len(threads) >= max_threads:
                for t in threads:
                    t.join()
                threads.clear()

        for t in threads:
            t.join()

        return JsonResponse(foods_json)

    return JsonResponse({"error": "Invalid request method."}, status=400)

# In your urls.py, update the endpoint accordingly
# from .views import get_foods_by_selected_countries

# urlpatterns = [
#     path('api/foods/', get_foods_by_selected_countries, name='get_foods'),
# ]
