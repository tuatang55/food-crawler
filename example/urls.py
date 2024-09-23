# example/urls.py
from django.urls import path

from example.views import index
from example.destinations import get_countries_by_continent
from example.foods import get_foods_by_selected_countries


urlpatterns = [
    path('', index),
    path('countries/', get_countries_by_continent, name='countries_by_continent'),
    path('foods/', get_foods_by_selected_countries, name='get_foods')
]