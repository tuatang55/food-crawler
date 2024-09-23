from django.urls import path
from .destinations import get_countries_by_continent
from .foods import get_foods_by_selected_countries

urlpatterns = [
    path('countries/', get_countries_by_continent, name='countries_by_continent'),
    path('foods/', get_foods_by_selected_countries, name='get_foods')
]