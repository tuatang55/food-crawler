import asyncio
import aiohttp
import re
import json
from django.http import JsonResponse
from django.views import View
import time

headers = {
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:32.0) Gecko/20100101 Firefox/32.0'
}
base_url = "https://globaltableadventure.com/"

# Compile regex patterns
continent_map_pattern = re.compile(r'<map name="m_regions">(.*?)</map>', re.DOTALL)
area_tag_pattern = re.compile(r'<area .*?href="(.*?)".*?>')
food_item_pattern = re.compile(r'<article.*?class="results-post.*?<img.*?src="(.*?)".*?<h2 class="entry-title"><a href="(.*?)" rel="bookmark">(.*?)</a></h2>.*?</article>', re.DOTALL)
region_name_pattern = re.compile(r'fwp_region=([^&]+)')

async def fetch_url(session, url):
    async with session.get(url) as response:
        return await response.text()

async def get_regions(html_content):
    continent_map_match = continent_map_pattern.search(html_content)
    if continent_map_match:
        continent_map = continent_map_match.group(1)
        area_tags = area_tag_pattern.findall(continent_map)
        
        # Construct absolute URLs manually
        return [base_url + tag if tag.startswith('?') else tag for tag in area_tags]
    else:
        print("Continent map not found.")
        return []

async def get_foods_for_region(session, region_url):
    all_food_items = []
    page = 1
    max_pages = 5  # Limit to 5 pages per region to balance speed and data completeness

    while page <= max_pages:
        paginated_url = f"{region_url}&fwp_paged={page}"
        html_content = await fetch_url(session, paginated_url)
        food_items = food_item_pattern.findall(html_content)
        
        if not food_items:
            break  # No more food items found, exit the loop
        
        all_food_items.extend(food_items)
        page += 1

    region_name_match = region_name_pattern.search(region_url)
    region_name = region_name_match.group(1) if region_name_match else "Unknown"

    return {
        "Region": region_name,
        "Count": len(all_food_items),
        "Foods": [{"FoodImageUrl": img_url, "FoodUrl": url, "FoodName": name} for img_url, url, name in all_food_items]
    }

class FoodDataView(View):
    async def get(self, request):
        start_time = time.monotonic()
        connector = aiohttp.TCPConnector(limit=7)  # Limit concurrent connections
        
        async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
            main_page = await fetch_url(session, base_url)
            region_urls = await get_regions(main_page)

            tasks = [get_foods_for_region(session, url) for url in region_urls]
            region_food_data = await asyncio.gather(*tasks)

        region_food_dict = {data["Region"]: data for data in region_food_data}

        # Prepare the JSON response
        response_data = {
            "data": region_food_dict,
            "message": "Data fetched successfully"
        }

        end_time = time.monotonic()
        elapsed_time = end_time - start_time
        print(f"Data fetched in {elapsed_time:.2f} seconds")

        return JsonResponse(response_data)