# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

"""
Event handlers for Restaurant Order
"""

import frappe
from frappe import _
from frappe.utils import flt, now_datetime, cint


def on_submit(doc, method):
    """Handle Restaurant Order submission"""
    # Create kitchen order
    create_kitchen_order(doc)
    
    # Update table status
    if doc.table:
        update_table_status(doc.table, "Occupied")
    
    # Send notifications
    send_new_order_notification(doc)


def on_cancel(doc, method):
    """Handle Restaurant Order cancellation"""
    # Cancel related kitchen orders
    cancel_kitchen_orders(doc.name)
    
    # Notify kitchen
    frappe.publish_realtime(
        "restaurant_order_cancelled",
        {
            "order": doc.name,
            "table": doc.table
        },
        doctype="Kitchen Order"
    )


def before_submit(doc, method):
    """Validate before submission"""
    # Validate items
    if not doc.items or len(doc.items) == 0:
        frappe.throw(_("Cannot submit order without items"))
    
    # Validate table for dine-in
    if doc.order_type == "Dine In" and not doc.table:
        frappe.throw(_("Table is required for dine-in orders"))
    
    # Calculate totals
    calculate_order_totals(doc)


def create_kitchen_order(restaurant_order):
    """Create kitchen order from restaurant order"""
    settings = frappe.get_single("Restaurant Settings")
    
    # Group items by station
    station_items = {}
    
    for item in restaurant_order.items:
        menu_item = frappe.get_doc("Menu Item", item.menu_item)
        station = menu_item.kitchen_station or settings.default_kitchen_station or "Main Kitchen"
        
        if station not in station_items:
            station_items[station] = []
        
        station_items[station].append({
            "menu_item": item.menu_item,
            "item_name": item.item_name,
            "qty": item.qty,
            "special_instructions": item.special_instructions,
            "modifiers": item.modifiers
        })
    
    # Create kitchen order for each station
    for station, items in station_items.items():
        kitchen_order = frappe.new_doc("Kitchen Order")
        kitchen_order.restaurant_order = restaurant_order.name
        kitchen_order.table = restaurant_order.table
        kitchen_order.order_type = restaurant_order.order_type
        kitchen_order.station = station
        kitchen_order.priority = "Normal"
        kitchen_order.status = "Pending"
        
        for item in items:
            kitchen_order.append("items", {
                "menu_item": item["menu_item"],
                "item_name": item["item_name"],
                "qty": item["qty"],
                "special_instructions": item["special_instructions"],
                "modifiers": item.get("modifiers"),
                "status": "Pending"
            })
        
        kitchen_order.insert(ignore_permissions=True)
        kitchen_order.submit()
        
        # Notify kitchen
        frappe.publish_realtime(
            "new_kitchen_order",
            {
                "name": kitchen_order.name,
                "station": station,
                "table": restaurant_order.table,
                "items_count": len(items),
                "order_type": restaurant_order.order_type
            },
            room=f"kitchen_{station}"
        )


def cancel_kitchen_orders(restaurant_order_name):
    """Cancel all kitchen orders for a restaurant order"""
    kitchen_orders = frappe.get_all(
        "Kitchen Order",
        filters={
            "restaurant_order": restaurant_order_name,
            "docstatus": 1
        }
    )
    
    for ko in kitchen_orders:
        try:
            doc = frappe.get_doc("Kitchen Order", ko.name)
            doc.cancel()
        except Exception as e:
            frappe.log_error(f"Error cancelling kitchen order {ko.name}: {str(e)}")


def update_table_status(table_name, status):
    """Update table status"""
    frappe.db.set_value("Restaurant Table", table_name, "status", status)
    
    frappe.publish_realtime(
        "table_status_update",
        {
            "table": table_name,
            "status": status
        },
        room="restaurant_tables"
    )


def calculate_order_totals(doc):
    """Calculate order totals"""
    subtotal = 0
    
    for item in doc.items:
        item_total = flt(item.rate) * cint(item.qty)
        
        # Add modifier prices
        if item.modifier_total:
            item_total += flt(item.modifier_total)
        
        item.amount = item_total
        subtotal += item_total
    
    doc.subtotal = subtotal
    
    # Apply discount
    if doc.discount_percentage:
        doc.discount_amount = subtotal * flt(doc.discount_percentage) / 100
    
    discounted = subtotal - flt(doc.discount_amount)
    
    # Calculate tax
    if doc.tax_rate:
        doc.tax_amount = discounted * flt(doc.tax_rate) / 100
    
    # Calculate service charge
    if doc.service_charge_rate:
        doc.service_charge = discounted * flt(doc.service_charge_rate) / 100
    
    doc.grand_total = discounted + flt(doc.tax_amount) + flt(doc.service_charge)


def send_new_order_notification(order):
    """Send notification for new order"""
    # Notify kitchen
    frappe.publish_realtime(
        "restaurant_new_order",
        {
            "order": order.name,
            "table": order.table,
            "order_type": order.order_type,
            "items_count": len(order.items)
        },
        doctype="Kitchen Order"
    )
    
    # Notify waiters
    if order.waiter:
        frappe.publish_realtime(
            "restaurant_new_order",
            {
                "order": order.name,
                "table": order.table
            },
            user=order.waiter
        )


def update_order_status(order_name, new_status):
    """Update order status and handle side effects"""
    order = frappe.get_doc("Restaurant Order", order_name)
    old_status = order.status
    
    frappe.db.set_value("Restaurant Order", order_name, "status", new_status)
    
    # Handle status-specific actions
    if new_status == "Ready":
        # Notify waiter
        frappe.publish_realtime(
            "order_ready",
            {
                "order": order_name,
                "table": order.table
            },
            room="restaurant_waiter"
        )
        
        # Notify customer
        if order.table:
            frappe.publish_realtime(
                "order_ready",
                {"order": order_name},
                room=f"table_{order.table}"
            )
    
    elif new_status == "Served":
        # Update timestamp
        frappe.db.set_value("Restaurant Order", order_name, "served_time", now_datetime())
    
    elif new_status == "Cancelled":
        # Cancel kitchen orders
        cancel_kitchen_orders(order_name)


def check_order_completion(restaurant_order_name):
    """Check if all kitchen orders are completed"""
    pending_kitchen_orders = frappe.get_all(
        "Kitchen Order",
        filters={
            "restaurant_order": restaurant_order_name,
            "status": ["not in", ["Completed", "Cancelled"]],
            "docstatus": 1
        }
    )
    
    if not pending_kitchen_orders:
        # All kitchen orders completed - mark order as ready
        frappe.db.set_value("Restaurant Order", restaurant_order_name, {
            "status": "Ready",
            "ready_time": now_datetime()
        })
        
        order = frappe.get_doc("Restaurant Order", restaurant_order_name)
        
        # Notify
        frappe.publish_realtime(
            "order_ready",
            {
                "order": restaurant_order_name,
                "table": order.table
            },
            room="restaurant_waiter"
        )
        
        if order.table:
            frappe.publish_realtime(
                "order_ready",
                {"order": restaurant_order_name, "table": order.table},
                room=f"table_{order.table}"
            )
