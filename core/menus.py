NAVBAR_MENU = [
    {"name": "Auto Repricer", "url_name": "web:home"},
    {
        "name": "Account",
        "url": "#",
        "submenu": [
            {
                "name": "Profile",
                "url_name": "user:profile_view",
                # Use a callable so we can evaluate per-request
                "url_kwargs": {"pk": (lambda r: r.user.pk)},
            },
            {"name": "Logout", "url_name": "account_logout"},
        ],
    },
]


FOOTER_MENU = [
    {"name": "Privacy", "url": "#privacy"},
    {"name": "Terms", "url": "#terms"},
]


