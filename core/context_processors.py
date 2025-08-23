from menu_generator.menu import generate_menu
from .menus import NAVBAR_MENU, FOOTER_MENU


def menus(request):
    return {
        'navbar_menu': generate_menu(request, NAVBAR_MENU),
        'footer_menu': generate_menu(request, FOOTER_MENU),
    }


