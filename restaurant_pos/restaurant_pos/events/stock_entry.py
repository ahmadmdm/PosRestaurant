# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

"""
Event handlers for Stock Entry
"""

import frappe
from frappe import _
from frappe.utils import flt


def on_submit(doc, method):
    """Handle Stock Entry submission for kitchen consumption"""
    if doc.stock_entry_type == "Material Issue" and doc.custom_kitchen_order:
        update_kitchen_order_stock(doc)


def on_cancel(doc, method):
    """Handle Stock Entry cancellation"""
    if doc.stock_entry_type == "Material Issue" and doc.custom_kitchen_order:
        revert_kitchen_order_stock(doc)


def update_kitchen_order_stock(stock_entry):
    """Update kitchen order when stock is issued"""
    try:
        kitchen_order = frappe.get_doc("Kitchen Order", stock_entry.custom_kitchen_order)
        
        # Mark ingredients as consumed
        frappe.db.set_value("Kitchen Order", kitchen_order.name, {
            "ingredients_consumed": 1,
            "stock_entry": stock_entry.name
        })
    except Exception as e:
        frappe.log_error(f"Error updating kitchen order stock: {str(e)}")


def revert_kitchen_order_stock(stock_entry):
    """Revert kitchen order stock status on cancellation"""
    try:
        kitchen_order = frappe.get_doc("Kitchen Order", stock_entry.custom_kitchen_order)
        
        frappe.db.set_value("Kitchen Order", kitchen_order.name, {
            "ingredients_consumed": 0,
            "stock_entry": None
        })
    except Exception as e:
        frappe.log_error(f"Error reverting kitchen order stock: {str(e)}")


def create_kitchen_stock_entry(kitchen_order_name):
    """Create stock entry for kitchen order ingredients"""
    kitchen_order = frappe.get_doc("Kitchen Order", kitchen_order_name)
    restaurant_order = frappe.get_doc("Restaurant Order", kitchen_order.restaurant_order)
    
    settings = frappe.get_single("Restaurant Settings")
    
    if not settings.auto_consume_stock:
        return
    
    items_to_consume = []
    
    for order_item in restaurant_order.items:
        menu_item = frappe.get_doc("Menu Item", order_item.menu_item)
        
        if menu_item.item_code:  # ERPNext item linked
            # Get BOM for recipe/ingredients
            bom = frappe.get_all(
                "BOM",
                filters={"item": menu_item.item_code, "is_active": 1, "is_default": 1},
                limit=1
            )
            
            if bom:
                bom_doc = frappe.get_doc("BOM", bom[0].name)
                for bom_item in bom_doc.items:
                    items_to_consume.append({
                        "item_code": bom_item.item_code,
                        "qty": flt(bom_item.qty) * flt(order_item.qty),
                        "uom": bom_item.uom
                    })
            else:
                # Direct consumption without BOM
                items_to_consume.append({
                    "item_code": menu_item.item_code,
                    "qty": flt(order_item.qty),
                    "uom": menu_item.stock_uom or "Nos"
                })
    
    if not items_to_consume:
        return
    
    # Create stock entry
    stock_entry = frappe.new_doc("Stock Entry")
    stock_entry.stock_entry_type = "Material Issue"
    stock_entry.custom_kitchen_order = kitchen_order_name
    stock_entry.custom_restaurant_order = kitchen_order.restaurant_order
    
    for item in items_to_consume:
        stock_entry.append("items", {
            "item_code": item["item_code"],
            "qty": item["qty"],
            "uom": item["uom"],
            "s_warehouse": settings.default_kitchen_warehouse
        })
    
    stock_entry.insert(ignore_permissions=True)
    stock_entry.submit()
    
    return stock_entry.name
