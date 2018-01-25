from django.shortcuts import render
from django.views.generic import ListView

from shop.models import Item

index = ListView.as_view(model=Item)
