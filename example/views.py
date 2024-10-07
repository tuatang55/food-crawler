import asyncio
import aiohttp
import re
import json
from django.http import JsonResponse
from django.views import View
import time

import html

headers = {
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:32.0) Gecko/20100101 Firefox/32.0'
}
base_url = "https://globaltableadventure.com/"

# Compile regex patterns
continent_map_pattern = re.compile(r'<map name="m_regions">(.*?)</map>', re.DOTALL)
area_tag_pattern = re.compile(r'<area .*?href="(.*?)".*?>')
food_item_pattern = re.compile(r'<article.*?class="results-post.*?<img.*?src="(.*?)".*?<h2 class="entry-title"><a href="(.*?)" rel="bookmark">(.*?)</a></h2>.*?</article>', re.DOTALL)
region_name_pattern = re.compile(r'fwp_region=([^&]+)')
food_description_pattern = re.compile(r'<span class="wpurp-recipe-description".*?>(.*?)</span>', re.DOTALL)

food_id_counter = 1

async def fetch_url(session, url):
    async with session.get(url) as response:
        return await response.text()

async def get_regions(html_content):
    continent_map_match = continent_map_pattern.search(html_content)
    if continent_map_match:
        continent_map = continent_map_match.group(1)
        area_tags = area_tag_pattern.findall(continent_map)

        return [base_url + tag if tag.startswith('?') else tag for tag in area_tags]
    else:
        print("Continent map not found.")
        return []

async def get_food_description(session, food_url):
    """Fetches the food description from the given food_url."""
    html_content = await fetch_url(session, food_url)
    if html_content is None:
        return ""

    description_match = food_description_pattern.search(html_content)
    if description_match:
        return description_match.group(1).strip()
    else:
        return ""

async def get_foods_for_region(session, region_url):
    global food_id_counter
    all_food_items = []
    page = 1
    max_pages = 5

    while page <= max_pages:
        paginated_url = f"{region_url}&fwp_paged={page}"
        html_content = await fetch_url(session, paginated_url)
        food_items = food_item_pattern.findall(html_content)

        if not food_items:
            break

        tasks = [get_food_description(session, url) for _, url, _ in food_items]
        descriptions = await asyncio.gather(*tasks)

        for (img_url, url, name), description in zip(food_items, descriptions):
            all_food_items.append({
                "FoodId": food_id_counter,
                "FoodImageUrl": img_url,
                "FoodUrl": url,
                "FoodName": html.unescape(name),
                "FoodDescription": description
            })
            food_id_counter += 1

        page += 1

    region_name_match = region_name_pattern.search(region_url)
    region_name = region_name_match.group(1) if region_name_match else "Unknown"

    return {
        "Region": region_name,
        "Count": len(all_food_items),
        "Foods": all_food_items
    }

class FoodDataView(View):
    async def get(self, request):
        start_time = time.monotonic()
        connector = aiohttp.TCPConnector(limit=7)

        try:
            async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
                main_page = await fetch_url(session, base_url)
                region_urls = await get_regions(main_page)

                tasks = [get_foods_for_region(session, url) for url in region_urls]
                region_food_data = await asyncio.gather(*tasks)

            region_food_dict = {data["Region"]: data for data in region_food_data}

            response_data = {
                "data": region_food_dict,
                "message": "Data fetched successfully"
            }

            end_time = time.monotonic()
            elapsed_time = end_time - start_time
            print(f"Data fetched in {elapsed_time:.2f} seconds")

            response = JsonResponse(response_data)
            response["Access-Control-Allow-Origin"] = "*"
            return response

        except aiohttp.ClientError as e:
            print(f"Aiohttp Client Error: {e}") 
            return JsonResponse({"error": f"Error fetching URL: {e}"}, status=500)
        except AttributeError as e:
            print(f"AttributeError: {e}")
            return JsonResponse({"error": f"Error extracting data: {e}"}, status=500)
        except Exception as e:
            print(f"An error occurred: {e}")
            return JsonResponse({"error": "Failed to fetch data"}, status=500)