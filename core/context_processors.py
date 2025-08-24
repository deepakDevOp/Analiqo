from menu_generator.menu import generate_menu
from django.urls import reverse, NoReverseMatch
from .menus import NAVBAR_MENU, FOOTER_MENU


def _resolve_menu_urls(request, items):
    resolved = []
    for item in items:
        item_copy = dict(item)

        # Resolve dynamic url by name
        url_name = item_copy.pop('url_name', None)
        if url_name:
            kwargs = item_copy.pop('url_kwargs', {}) or {}
            # Evaluate callables in kwargs using request
            evaluated_kwargs = {
                key: (value(request) if callable(value) else value)
                for key, value in kwargs.items()
            }
            try:
                item_copy['url'] = reverse(url_name, kwargs=evaluated_kwargs)
            except NoReverseMatch:
                item_copy['url'] = '#'

        # Recurse into submenu
        if 'submenu' in item_copy and item_copy['submenu']:
            item_copy['submenu'] = _resolve_menu_urls(request, item_copy['submenu'])

        resolved.append(item_copy)
    return resolved


def menus(request):
    navbar = _resolve_menu_urls(request, NAVBAR_MENU)
    footer = _resolve_menu_urls(request, FOOTER_MENU)
    return {
        'navbar_menu': generate_menu(request, navbar),
        'footer_menu': generate_menu(request, footer),
    }


