# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

"""
Menu API - Public endpoints for digital menu
These APIs are accessible without login (guest access)
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, now_datetime


@frappe.whitelist(allow_guest=True)
def get_menu(table_code=None, branch=None, language="ar"):
    """
    Get the full menu for a restaurant/branch
    
    Args:
        table_code: QR code identifier for the table
        branch: Branch name (optional if table_code provided)
        language: Menu language (ar/en)
    
    Returns:
        dict: Menu data with categories and items
    """
    try:
        # Get table info if table_code provided
        table_info = None
        if table_code:
            table_info = get_table_by_code(table_code)
            if not table_info:
                return {"success": False, "message": _("Invalid table code")}
            branch = table_info.get("branch")
        
        # Get restaurant settings
        settings = frappe.get_single("Restaurant Settings")
        
        # Get menu categories
        categories = frappe.get_all(
            "Menu Category",
            filters={
                "enabled": 1,
                "branch": ["in", [branch, None, ""]] if branch else None
            },
            fields=[
                "name", "category_name", "category_name_ar",
                "description", "description_ar", "image",
                "display_order", "parent_category"
            ],
            order_by="display_order asc"
        )
        
        # Get menu items for each category
        menu_data = []
        for category in categories:
            items = get_category_items(category.name, branch, language)
            
            menu_data.append({
                "name": category.name,
                "title": category.category_name_ar if language == "ar" else category.category_name,
                "description": category.description_ar if language == "ar" else category.description,
                "image": category.image,
                "display_order": category.display_order,
                "parent_category": category.parent_category,
                "items": items
            })
        
        return {
            "success": True,
            "data": {
                "table": table_info,
                "branch": branch,
                "language": language,
                "currency": frappe.defaults.get_global_default("currency"),
                "currency_symbol": get_currency_symbol(),
                "categories": menu_data,
                "settings": {
                    "enable_call_waiter": settings.enable_call_waiter,
                    "enable_online_payment": settings.enable_online_payment if hasattr(settings, 'enable_online_payment') else 0,
                    "min_order_amount": settings.min_order_amount if hasattr(settings, 'min_order_amount') else 0,
                    "service_charge_percent": settings.service_charge_percent if hasattr(settings, 'service_charge_percent') else 0,
                    "vat_percent": settings.vat_percent if hasattr(settings, 'vat_percent') else 15,
                }
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Menu API Error: {str(e)}", "Restaurant POS")
        return {"success": False, "message": _("Error loading menu")}


def get_table_by_code(table_code):
    """Get table info by QR code"""
    table = frappe.db.get_value(
        "Restaurant Table",
        {"qr_code": table_code, "enabled": 1},
        ["name", "table_number", "branch", "seating_capacity", "area"],
        as_dict=True
    )
    return table


def get_category_items(category, branch=None, language="ar"):
    """Get menu items for a category"""
    filters = {
        "enabled": 1,
        "menu_category": category
    }
    
    if branch:
        filters["branch"] = ["in", [branch, None, ""]]
    
    items = frappe.get_all(
        "Menu Item",
        filters=filters,
        fields=[
            "name", "item_code", "item_name", "item_name_ar",
            "description", "description_ar", "image",
            "price", "discounted_price", "is_available",
            "preparation_time_minutes", "calories",
            "is_vegetarian", "is_vegan", "is_spicy", "spice_level",
            "display_order", "item_group"
        ],
        order_by="display_order asc"
    )
    
    result = []
    for item in items:
        # Check real-time availability
        is_available = check_item_availability(item.item_code, branch)
        
        # Get item modifiers
        modifiers = get_item_modifiers(item.name)
        
        result.append({
            "name": item.name,
            "item_code": item.item_code,
            "title": item.item_name_ar if language == "ar" else item.item_name,
            "description": item.description_ar if language == "ar" else item.description,
            "image": item.image,
            "price": flt(item.price),
            "discounted_price": flt(item.discounted_price) if item.discounted_price else None,
            "is_available": is_available,
            "preparation_time": item.preparation_time_minutes,
            "calories": item.calories,
            "tags": {
                "vegetarian": item.is_vegetarian,
                "vegan": item.is_vegan,
                "spicy": item.is_spicy,
                "spice_level": item.spice_level
            },
            "modifiers": modifiers
        })
    
    return result


def check_item_availability(item_code, branch=None):
    """Check if item is available based on stock"""
    try:
        # Get BOM for this item
        bom = frappe.db.get_value("BOM", {"item": item_code, "is_active": 1, "is_default": 1}, "name")
        
        if not bom:
            return True  # No BOM means always available
        
        # Check if all BOM items are in stock
        bom_items = frappe.get_all(
            "BOM Item",
            filters={"parent": bom},
            fields=["item_code", "qty"]
        )
        
        warehouse = get_branch_warehouse(branch) if branch else None
        
        for bom_item in bom_items:
            stock_qty = get_stock_qty(bom_item.item_code, warehouse)
            if stock_qty < bom_item.qty:
                return False
        
        return True
        
    except Exception:
        return True  # Default to available on error


def get_stock_qty(item_code, warehouse=None):
    """Get available stock quantity"""
    try:
        from erpnext.stock.utils import get_stock_balance
        if warehouse:
            return get_stock_balance(item_code, warehouse)
        else:
            return frappe.db.sql("""
                SELECT SUM(actual_qty) FROM `tabBin` WHERE item_code = %s
            """, item_code)[0][0] or 0
    except Exception:
        return 999  # Default high value on error


def get_branch_warehouse(branch):
    """Get default warehouse for a branch"""
    return frappe.db.get_value("Branch", branch, "default_warehouse")


def get_item_modifiers(menu_item):
    """Get modifiers/options for a menu item"""
    modifiers = frappe.get_all(
        "Menu Item Modifier",
        filters={"parent": menu_item},
        fields=[
            "modifier_name", "modifier_name_ar", "modifier_type",
            "is_required", "min_selections", "max_selections",
            "options"
        ],
        order_by="idx asc"
    )
    
    result = []
    for mod in modifiers:
        # Get modifier options
        options = frappe.get_all(
            "Menu Modifier Option",
            filters={"parent": mod.name},
            fields=[
                "option_name", "option_name_ar", 
                "additional_price", "is_default"
            ],
            order_by="idx asc"
        )
        
        result.append({
            "name": mod.modifier_name,
            "name_ar": mod.modifier_name_ar,
            "type": mod.modifier_type,  # single, multiple
            "is_required": mod.is_required,
            "min_selections": mod.min_selections or 0,
            "max_selections": mod.max_selections or 1,
            "options": options
        })
    
    return result


def get_currency_symbol():
    """Get currency symbol"""
    currency = frappe.defaults.get_global_default("currency")
    return frappe.db.get_value("Currency", currency, "symbol") or currency


@frappe.whitelist(allow_guest=True)
def get_item_details(item_name, language="ar"):
    """
    Get detailed information about a menu item
    
    Args:
        item_name: Menu Item name
        language: Language for text (ar/en)
    
    Returns:
        dict: Detailed item information
    """
    try:
        item = frappe.get_doc("Menu Item", item_name)
        
        # Get modifiers
        modifiers = get_item_modifiers(item_name)
        
        # Get related/recommended items
        related = get_related_items(item.menu_category, item_name, language)
        
        return {
            "success": True,
            "data": {
                "name": item.name,
                "item_code": item.item_code,
                "title": item.item_name_ar if language == "ar" else item.item_name,
                "description": item.description_ar if language == "ar" else item.description,
                "long_description": item.long_description_ar if language == "ar" else item.long_description,
                "image": item.image,
                "images": get_item_images(item_name),
                "price": flt(item.price),
                "discounted_price": flt(item.discounted_price) if item.discounted_price else None,
                "is_available": check_item_availability(item.item_code),
                "preparation_time": item.preparation_time_minutes,
                "calories": item.calories,
                "allergens": item.allergens,
                "nutritional_info": {
                    "calories": item.calories,
                    "protein": item.protein,
                    "carbs": item.carbs,
                    "fat": item.fat,
                },
                "tags": {
                    "vegetarian": item.is_vegetarian,
                    "vegan": item.is_vegan,
                    "spicy": item.is_spicy,
                    "spice_level": item.spice_level,
                    "gluten_free": item.is_gluten_free,
                    "halal": item.is_halal,
                },
                "modifiers": modifiers,
                "related_items": related
            }
        }
        
    except frappe.DoesNotExistError:
        return {"success": False, "message": _("Item not found")}
    except Exception as e:
        frappe.log_error(f"Item Details API Error: {str(e)}", "Restaurant POS")
        return {"success": False, "message": _("Error loading item details")}


def get_item_images(menu_item):
    """Get all images for a menu item"""
    images = frappe.get_all(
        "Menu Item Image",
        filters={"parent": menu_item},
        fields=["image", "caption"],
        order_by="idx asc"
    )
    return images


def get_related_items(category, exclude_item, language="ar", limit=4):
    """Get related items from the same category"""
    items = frappe.get_all(
        "Menu Item",
        filters={
            "menu_category": category,
            "name": ["!=", exclude_item],
            "enabled": 1,
            "is_available": 1
        },
        fields=[
            "name", "item_name", "item_name_ar", 
            "image", "price"
        ],
        limit=limit
    )
    
    return [{
        "name": item.name,
        "title": item.item_name_ar if language == "ar" else item.item_name,
        "image": item.image,
        "price": flt(item.price)
    } for item in items]


@frappe.whitelist(allow_guest=True)
def search_menu(query, branch=None, language="ar"):
    """
    Search menu items
    
    Args:
        query: Search query
        branch: Branch filter
        language: Language (ar/en)
    
    Returns:
        list: Matching menu items
    """
    try:
        if not query or len(query) < 2:
            return {"success": True, "data": []}
        
        filters = {
            "enabled": 1,
            "is_available": 1
        }
        
        if branch:
            filters["branch"] = ["in", [branch, None, ""]]
        
        # Search in both languages
        items = frappe.get_all(
            "Menu Item",
            filters=filters,
            or_filters=[
                ["item_name", "like", f"%{query}%"],
                ["item_name_ar", "like", f"%{query}%"],
                ["description", "like", f"%{query}%"],
                ["description_ar", "like", f"%{query}%"],
            ],
            fields=[
                "name", "item_code", "item_name", "item_name_ar",
                "image", "price", "menu_category"
            ],
            limit=20
        )
        
        result = [{
            "name": item.name,
            "title": item.item_name_ar if language == "ar" else item.item_name,
            "image": item.image,
            "price": flt(item.price),
            "category": item.menu_category
        } for item in items]
        
        return {"success": True, "data": result}
        
    except Exception as e:
        frappe.log_error(f"Menu Search Error: {str(e)}", "Restaurant POS")
        return {"success": False, "message": _("Search error")}
