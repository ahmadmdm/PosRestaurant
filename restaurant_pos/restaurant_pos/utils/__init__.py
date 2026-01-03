# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

"""
Utility functions for Restaurant POS
"""

import frappe
import json
from frappe import _
from frappe.utils import cint, flt, now_datetime, get_datetime, time_diff_in_seconds

__all__ = [
    "get_restaurant_settings",
    "format_currency",
    "get_table_qr_url",
    "calculate_order_total",
    "get_order_wait_time",
    "get_kitchen_order_priority",
    "format_time_elapsed",
    "get_available_menu_items",
]


def get_restaurant_settings():
    """Get restaurant settings"""
    return frappe.get_single("Restaurant Settings")


def format_currency(amount, currency=None):
    """Format amount as currency"""
    if not currency:
        settings = get_restaurant_settings()
        currency = settings.get("default_currency") or frappe.defaults.get_global_default("currency")
    
    return frappe.utils.fmt_money(amount, currency=currency)


def get_table_qr_url(table_name):
    """Get QR menu URL for a table"""
    table = frappe.get_doc("Restaurant Table", table_name)
    if table.qr_code_url:
        return table.qr_code_url
    
    site_url = frappe.utils.get_url()
    return f"{site_url}/menu?table={table_name}"


def calculate_order_total(items, tax_rate=0, service_charge_rate=0, discount_amount=0, discount_percent=0):
    """Calculate order totals"""
    subtotal = 0
    
    for item in items:
        item_total = flt(item.get("rate", 0)) * cint(item.get("qty", 1))
        
        # Add modifier prices
        if item.get("modifiers"):
            for modifier in item.get("modifiers", []):
                item_total += flt(modifier.get("price", 0))
        
        subtotal += item_total
    
    # Apply discount
    if discount_percent:
        discount_amount = subtotal * flt(discount_percent) / 100
    
    discounted_total = subtotal - flt(discount_amount)
    
    # Calculate tax
    tax_amount = discounted_total * flt(tax_rate) / 100
    
    # Calculate service charge
    service_charge = discounted_total * flt(service_charge_rate) / 100
    
    grand_total = discounted_total + tax_amount + service_charge
    
    return {
        "subtotal": subtotal,
        "discount_amount": discount_amount,
        "tax_amount": tax_amount,
        "service_charge": service_charge,
        "grand_total": grand_total
    }


def get_order_wait_time(order):
    """Calculate wait time for an order in minutes"""
    if isinstance(order, str):
        order = frappe.get_doc("Restaurant Order", order)
    
    created = get_datetime(order.creation)
    now = now_datetime()
    
    wait_seconds = time_diff_in_seconds(now, created)
    return int(wait_seconds / 60)


def get_kitchen_order_priority(order):
    """Calculate priority score for kitchen orders"""
    priority_score = 0
    
    # Base priority from order type
    order_type_priority = {
        "Dine In": 1,
        "Takeaway": 2,
        "Delivery": 3
    }
    priority_score += order_type_priority.get(order.get("order_type", "Dine In"), 1) * 10
    
    # Wait time factor (higher score for longer wait)
    wait_time = get_order_wait_time(order)
    priority_score += wait_time * 2
    
    # Rush order bonus
    if order.get("is_rush"):
        priority_score += 50
    
    # VIP table bonus
    if order.get("table"):
        table = frappe.get_cached_doc("Restaurant Table", order.get("table"))
        if table.is_vip:
            priority_score += 30
    
    return priority_score


def format_time_elapsed(minutes):
    """Format time elapsed as human-readable string"""
    if minutes < 1:
        return _("Just now")
    elif minutes == 1:
        return _("1 min")
    elif minutes < 60:
        return _("{0} mins").format(minutes)
    elif minutes < 120:
        return _("1 hour")
    else:
        hours = int(minutes / 60)
        return _("{0} hours").format(hours)


def get_available_menu_items(category=None, search=None, table=None):
    """Get available menu items with filters"""
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
            "spice_level", "calories", "preparation_time",
            "is_popular", "is_new", "is_chef_special"
        ],
        order_by="display_order"
    )
    
    if search:
        search_lower = search.lower()
        items = [
            item for item in items
            if search_lower in item.get("item_name", "").lower()
            or search_lower in item.get("item_name_ar", "").lower()
            or search_lower in item.get("description", "").lower()
        ]
    
    # Get modifiers for each item
    for item in items:
        item["modifiers"] = get_item_modifiers(item.name)
    
    return items


def get_item_modifiers(item_name):
    """Get modifiers for a menu item"""
    modifiers = []
    
    links = frappe.get_all(
        "Menu Item Modifier Link",
        filters={"parent": item_name},
        fields=["modifier", "is_required"],
        order_by="idx"
    )
    
    for link in links:
        modifier = frappe.get_doc("Menu Item Modifier", link.modifier)
        modifier_data = {
            "name": modifier.name,
            "modifier_name": modifier.modifier_name,
            "modifier_name_ar": modifier.modifier_name_ar,
            "selection_type": modifier.selection_type,
            "min_selections": modifier.min_selections,
            "max_selections": modifier.max_selections,
            "is_required": link.is_required,
            "options": []
        }
        
        for option in modifier.options:
            modifier_data["options"].append({
                "name": option.name,
                "option_name": option.option_name,
                "option_name_ar": option.option_name_ar,
                "price": option.additional_price,
                "is_default": option.is_default
            })
        
        modifiers.append(modifier_data)
    
    return modifiers


def generate_order_number():
    """Generate unique order number"""
    today = now_datetime().strftime("%Y%m%d")
    
    # Get count of orders today
    count = frappe.db.count(
        "Restaurant Order",
        filters={
            "creation": [">=", now_datetime().replace(hour=0, minute=0, second=0)]
        }
    )
    
    return f"ORD-{today}-{str(count + 1).zfill(4)}"


def send_order_notification(order_name, event_type):
    """Send real-time notification for order events"""
    order = frappe.get_doc("Restaurant Order", order_name)
    
    notification_data = {
        "order_name": order.name,
        "table": order.table,
        "status": order.status,
        "event_type": event_type
    }
    
    # Notify kitchen
    if event_type in ["new_order", "order_updated", "order_cancelled"]:
        frappe.publish_realtime(
            "restaurant_order_update",
            notification_data,
            doctype="Kitchen Order"
        )
    
    # Notify waiters
    if event_type in ["order_ready", "order_served"]:
        frappe.publish_realtime(
            "restaurant_order_update",
            notification_data,
            room=f"restaurant_waiter"
        )
    
    # Notify customer
    if order.table:
        frappe.publish_realtime(
            "restaurant_order_update",
            notification_data,
            room=f"table_{order.table}"
        )


def get_daily_stats():
    """Get daily restaurant statistics"""
    today_start = now_datetime().replace(hour=0, minute=0, second=0)
    
    orders = frappe.get_all(
        "Restaurant Order",
        filters={"creation": [">=", today_start]},
        fields=["status", "grand_total"]
    )
    
    total_orders = len(orders)
    completed_orders = len([o for o in orders if o.status in ["Served", "Paid"]])
    cancelled_orders = len([o for o in orders if o.status == "Cancelled"])
    pending_orders = total_orders - completed_orders - cancelled_orders
    
    total_revenue = sum(flt(o.grand_total) for o in orders if o.status in ["Served", "Paid"])
    
    return {
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "cancelled_orders": cancelled_orders,
        "pending_orders": pending_orders,
        "total_revenue": total_revenue
    }
