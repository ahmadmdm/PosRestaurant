# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

"""
Jinja template methods for Restaurant POS
These methods are exposed to Jinja templates via hooks.py
"""

import frappe
from frappe.utils import cint, flt, now_datetime
from restaurant_pos.restaurant_pos.utils import (
    format_currency,
    format_time_elapsed,
    get_order_wait_time
)


def get_restaurant_settings():
    """Get restaurant settings for templates"""
    try:
        return frappe.get_single("Restaurant Settings")
    except Exception:
        return frappe._dict()


def get_menu_categories():
    """Get all active menu categories"""
    return frappe.get_all(
        "Menu Category",
        filters={"is_active": 1},
        fields=["name", "category_name", "category_name_ar", "icon", "image", "display_order"],
        order_by="display_order"
    )


def get_menu_items_by_category(category=None):
    """Get menu items grouped by category"""
    filters = {"is_available": 1}
    if category:
        filters["category"] = category
    
    items = frappe.get_all(
        "Menu Item",
        filters=filters,
        fields=[
            "name", "item_name", "item_name_ar", "category",
            "description", "description_ar", "price",
            "image", "is_vegetarian", "is_vegan", "is_halal",
            "spice_level", "preparation_time", "is_popular"
        ],
        order_by="display_order"
    )
    
    # Group by category
    if not category:
        grouped = {}
        for item in items:
            cat = item.category or "Uncategorized"
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(item)
        return grouped
    
    return items


def get_table_info(table_name):
    """Get table information"""
    if not table_name:
        return None
    
    try:
        table = frappe.get_doc("Restaurant Table", table_name)
        return {
            "name": table.name,
            "table_number": table.table_number,
            "area": table.area,
            "capacity": table.capacity,
            "status": table.status,
            "current_guests": table.current_guests
        }
    except Exception:
        return None


def format_price(amount, show_currency=True):
    """Format price for display"""
    settings = get_restaurant_settings()
    currency_symbol = settings.get("currency_symbol", "SAR")
    
    formatted = "{:,.2f}".format(flt(amount))
    
    if show_currency:
        return f"{currency_symbol} {formatted}"
    return formatted


def get_item_tags(item):
    """Get display tags for a menu item"""
    tags = []
    
    if item.get("is_vegetarian"):
        tags.append({"label": "Vegetarian", "label_ar": "نباتي", "color": "green"})
    
    if item.get("is_vegan"):
        tags.append({"label": "Vegan", "label_ar": "نباتي صرف", "color": "green"})
    
    if item.get("is_halal"):
        tags.append({"label": "Halal", "label_ar": "حلال", "color": "blue"})
    
    if item.get("is_gluten_free"):
        tags.append({"label": "Gluten-Free", "label_ar": "خالي من الغلوتين", "color": "yellow"})
    
    if item.get("is_popular"):
        tags.append({"label": "Popular", "label_ar": "شائع", "color": "orange"})
    
    if item.get("is_new"):
        tags.append({"label": "New", "label_ar": "جديد", "color": "purple"})
    
    if item.get("is_chef_special"):
        tags.append({"label": "Chef Special", "label_ar": "طبق الشيف", "color": "red"})
    
    return tags


def get_spice_level_display(level):
    """Get spice level display"""
    levels = {
        0: {"label": "Not Spicy", "label_ar": "غير حار", "icon": "🌶️", "count": 0},
        1: {"label": "Mild", "label_ar": "خفيف", "icon": "🌶️", "count": 1},
        2: {"label": "Medium", "label_ar": "متوسط", "icon": "🌶️", "count": 2},
        3: {"label": "Hot", "label_ar": "حار", "icon": "🌶️", "count": 3},
        4: {"label": "Very Hot", "label_ar": "حار جداً", "icon": "🌶️", "count": 4},
        5: {"label": "Extreme", "label_ar": "شديد الحرارة", "icon": "🌶️", "count": 5}
    }
    return levels.get(cint(level), levels[0])


def get_order_status_display(status):
    """Get order status display info"""
    statuses = {
        "Pending": {"label": "Pending", "label_ar": "قيد الانتظار", "color": "yellow", "icon": "clock"},
        "Confirmed": {"label": "Confirmed", "label_ar": "مؤكد", "color": "blue", "icon": "check"},
        "Preparing": {"label": "Preparing", "label_ar": "قيد التحضير", "color": "orange", "icon": "fire"},
        "Ready": {"label": "Ready", "label_ar": "جاهز", "color": "green", "icon": "check-circle"},
        "Served": {"label": "Served", "label_ar": "تم التقديم", "color": "gray", "icon": "utensils"},
        "Paid": {"label": "Paid", "label_ar": "مدفوع", "color": "green", "icon": "dollar"},
        "Cancelled": {"label": "Cancelled", "label_ar": "ملغي", "color": "red", "icon": "times"}
    }
    return statuses.get(status, statuses["Pending"])


def get_current_orders_count(table_name=None):
    """Get count of current active orders"""
    filters = {
        "status": ["in", ["Pending", "Confirmed", "Preparing", "Ready"]]
    }
    if table_name:
        filters["table"] = table_name
    
    return frappe.db.count("Restaurant Order", filters)


def is_restaurant_open():
    """Check if restaurant is currently open"""
    settings = get_restaurant_settings()
    
    if not settings.get("operating_hours_enabled"):
        return True
    
    now = now_datetime()
    current_day = now.strftime("%A").lower()
    current_time = now.time()
    
    # Get operating hours for today
    open_time = settings.get(f"{current_day}_open")
    close_time = settings.get(f"{current_day}_close")
    
    if not open_time or not close_time:
        return True
    
    from datetime import datetime
    open_dt = datetime.strptime(str(open_time), "%H:%M:%S").time()
    close_dt = datetime.strptime(str(close_time), "%H:%M:%S").time()
    
    return open_dt <= current_time <= close_dt


def get_popular_items(limit=6):
    """Get popular menu items"""
    return frappe.get_all(
        "Menu Item",
        filters={"is_available": 1, "is_popular": 1},
        fields=["name", "item_name", "item_name_ar", "price", "image", "category"],
        order_by="display_order",
        limit=limit
    )


def get_chef_specials(limit=4):
    """Get chef special items"""
    return frappe.get_all(
        "Menu Item",
        filters={"is_available": 1, "is_chef_special": 1},
        fields=["name", "item_name", "item_name_ar", "price", "image", "category", "description"],
        order_by="display_order",
        limit=limit
    )


def get_allergen_info(item_name):
    """Get allergen information for a menu item"""
    item = frappe.get_doc("Menu Item", item_name)
    allergens = []
    
    if item.contains_nuts:
        allergens.append({"name": "Nuts", "name_ar": "مكسرات", "icon": "🥜"})
    if item.contains_dairy:
        allergens.append({"name": "Dairy", "name_ar": "منتجات الألبان", "icon": "🥛"})
    if item.contains_gluten:
        allergens.append({"name": "Gluten", "name_ar": "غلوتين", "icon": "🌾"})
    if item.contains_seafood:
        allergens.append({"name": "Seafood", "name_ar": "مأكولات بحرية", "icon": "🦐"})
    if item.contains_eggs:
        allergens.append({"name": "Eggs", "name_ar": "بيض", "icon": "🥚"})
    if item.contains_soy:
        allergens.append({"name": "Soy", "name_ar": "صويا", "icon": "🫘"})
    
    return allergens


def translate_text(text_en, text_ar, lang=None):
    """Get text in appropriate language"""
    if not lang:
        lang = frappe.local.lang or "en"
    
    if lang == "ar" and text_ar:
        return text_ar
    return text_en or ""
