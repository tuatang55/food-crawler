# example/urls.py
from django.urls import path

#from example.views import index
from example.destinations import get_countries_by_continent
from example.foods import get_foods_by_selected_countries

from django.urls import path
from example.views import FoodDataView

from . import views
from asgiref.sync import async_to_sync

urlpatterns = [
    # path('', index),
    # path('countries/', get_countries_by_continent, name='countries_by_continent'),
    # path('foods/', get_foods_by_selected_countries, name='get_foods'),
    path('fetch-food-data/', async_to_sync(views.FoodDataView.as_view()), name='fetch_food_data'),
]