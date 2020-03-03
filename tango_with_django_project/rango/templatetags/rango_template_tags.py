from django import template
from rango.models import Category, Page

register = template.Library()


@register.inclusion_tag("rango/categories.html")
def get_category_list(current_category=None):
    return {"categories": Category.objects.all(), "current_category": current_category}


@register.inclusion_tag("rango/pages.html")
def get_page_list(category):
    return {"pages": Page.objects.filter(category=category)}