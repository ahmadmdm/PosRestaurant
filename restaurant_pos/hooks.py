app_name = "restaurant_pos"
app_title = "Restaurant POS"
app_publisher = "Ahmad"
app_description = "Professional Restaurant POS System with QR Ordering, Kitchen Display, and Real-time Updates"
app_email = "ahmad8@outlook.com"
app_license = "mit"

# Required Apps
required_apps = ["frappe", "erpnext"]

# Apps Screen
add_to_apps_screen = [
    {
        "name": "restaurant_pos",
        "logo": "/assets/restaurant_pos/images/restaurant-logo.svg",
        "title": "Restaurant POS",
        "route": "/app/restaurant-settings",
    }
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = [
    "/assets/restaurant_pos/css/restaurant_pos.css"
]
app_include_js = [
    "/assets/restaurant_pos/js/restaurant_pos.bundle.js"
]

# include js, css files in header of web template
web_include_css = [
    "/assets/restaurant_pos/css/digital_menu.css"
]
web_include_js = [
    "/assets/restaurant_pos/js/digital_menu.bundle.js"
]

# Website Route Rules
website_route_rules = [
    # QR Menu Route - /menu/{table_code}
    {"from_route": "/menu/<table_code>", "to_route": "menu"},
    # Kitchen Display - /kitchen/{branch}
    {"from_route": "/kitchen/<branch>", "to_route": "kitchen"},
    # Order Status - /order-status/<order_id>
    {"from_route": "/order-status/<order_id>", "to_route": "order_status"},
]


# Jinja Methods
jinja = {
    "methods": [
        "restaurant_pos.restaurant_pos.utils.jinja_methods.get_restaurant_settings",
        "restaurant_pos.restaurant_pos.utils.jinja_methods.get_menu_categories",
        "restaurant_pos.restaurant_pos.utils.jinja_methods.get_menu_items_by_category",
        "restaurant_pos.restaurant_pos.utils.jinja_methods.format_price",
        "restaurant_pos.restaurant_pos.utils.jinja_methods.get_table_info",
        "restaurant_pos.restaurant_pos.utils.jinja_methods.get_item_tags",
        "restaurant_pos.restaurant_pos.utils.jinja_methods.get_spice_level_display",
        "restaurant_pos.restaurant_pos.utils.jinja_methods.get_order_status_display",
        "restaurant_pos.restaurant_pos.utils.jinja_methods.is_restaurant_open",
        "restaurant_pos.restaurant_pos.utils.jinja_methods.get_popular_items",
        "restaurant_pos.restaurant_pos.utils.jinja_methods.translate_text",
    ]
}

# Installation
# ------------

before_install = "restaurant_pos.restaurant_pos.install.before_install"
after_install = "restaurant_pos.restaurant_pos.install.after_install"

# Boot Session
boot_session = "restaurant_pos.restaurant_pos.api.boot.get_boot_info"

# DocType Events
doc_events = {
    "POS Invoice": {
        "on_submit": "restaurant_pos.restaurant_pos.events.pos_invoice.on_submit",
        "on_cancel": "restaurant_pos.restaurant_pos.events.pos_invoice.on_cancel",
    },
    "Stock Entry": {
        "on_submit": "restaurant_pos.restaurant_pos.events.stock_entry.on_submit",
        "on_cancel": "restaurant_pos.restaurant_pos.events.stock_entry.on_cancel",
    },
    "Restaurant Order": {
        "on_submit": "restaurant_pos.restaurant_pos.events.restaurant_order.on_submit",
        "on_cancel": "restaurant_pos.restaurant_pos.events.restaurant_order.on_cancel",
        "before_submit": "restaurant_pos.restaurant_pos.events.restaurant_order.before_submit",
    }
}

# Scheduled Tasks
scheduler_events = {
    "all": [
        "restaurant_pos.restaurant_pos.tasks.all"
    ],
    "hourly": [
        "restaurant_pos.restaurant_pos.tasks.hourly"
    ],
    "daily": [
        "restaurant_pos.restaurant_pos.tasks.daily"
    ],
    "weekly": [
        "restaurant_pos.restaurant_pos.tasks.weekly"
    ],
    "monthly": [
        "restaurant_pos.restaurant_pos.tasks.monthly"
    ],
}

# Fixtures
fixtures = [
    {
        "doctype": "Custom Field",
        "filters": [["module", "=", "Restaurant POS"]]
    },
    {
        "doctype": "Property Setter",
        "filters": [["module", "=", "Restaurant POS"]]
    },
    {
        "doctype": "Workspace",
        "filters": [["module", "=", "Restaurant POS"]]
    }
]

# Permissions
has_permission = {
    "Restaurant Order": "restaurant_pos.restaurant_pos.permissions.has_restaurant_permission",
    "Kitchen Order": "restaurant_pos.restaurant_pos.permissions.has_restaurant_permission",
}

# Permission Query Conditions
permission_query_conditions = {
    "Restaurant Order": "restaurant_pos.restaurant_pos.permissions.get_order_permission_query_conditions",
    "Kitchen Order": "restaurant_pos.restaurant_pos.permissions.get_kitchen_order_permission_query_conditions",
}

# Guest APIs (No login required for QR ordering)
website_guest_api = [
    "restaurant_pos.restaurant_pos.api.menu.get_menu",
    "restaurant_pos.restaurant_pos.api.menu.get_menu_categories",
    "restaurant_pos.restaurant_pos.api.menu.get_item_details",
    "restaurant_pos.restaurant_pos.api.menu.search_items",
    "restaurant_pos.restaurant_pos.api.order.place_order",
    "restaurant_pos.restaurant_pos.api.order.get_order_status",
    "restaurant_pos.restaurant_pos.api.order.add_to_order",
    "restaurant_pos.restaurant_pos.api.table.get_table_session",
    "restaurant_pos.restaurant_pos.api.table.call_waiter",
    "restaurant_pos.restaurant_pos.api.table.get_table_orders",
]

# Export Python type annotations
export_python_type_annotations = True
