# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

"""
Order API - Public endpoints for placing orders
These APIs are accessible without login (guest access)
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, now_datetime, random_string
import json


@frappe.whitelist(allow_guest=True)
def place_order(table_code, items, customer_name=None, customer_phone=None, 
                notes=None, order_type="Dine In", language="ar"):
    """
    Place a new order from the digital menu
    
    Args:
        table_code: QR code identifier for the table
        items: List of items with quantities and modifiers
        customer_name: Optional customer name
        customer_phone: Optional customer phone
        notes: Order notes/special instructions
        order_type: Dine In, Takeaway, Delivery
        language: Language for responses
    
    Returns:
        dict: Order confirmation with order ID and estimated time
    """
    try:
        # Validate table
        table = frappe.db.get_value(
            "Restaurant Table",
            {"qr_code": table_code, "enabled": 1},
            ["name", "table_number", "branch", "current_session"],
            as_dict=True
        )
        
        if not table:
            return {"success": False, "message": _("Invalid table")}
        
        # Parse items if string
        if isinstance(items, str):
            items = json.loads(items)
        
        if not items:
            return {"success": False, "message": _("No items in order")}
        
        # Validate items and calculate totals
        validated_items, item_errors = validate_order_items(items, table.branch)
        
        if item_errors:
            return {"success": False, "message": item_errors[0], "errors": item_errors}
        
        # Get or create table session
        session = get_or_create_table_session(table.name, customer_name, customer_phone)
        
        # Calculate totals
        subtotal = sum(item["total"] for item in validated_items)
        settings = frappe.get_single("Restaurant Settings")
        
        service_charge = flt(subtotal * (settings.service_charge_percent or 0) / 100)
        vat = flt((subtotal + service_charge) * (settings.vat_percent or 15) / 100)
        grand_total = subtotal + service_charge + vat
        
        # Create the order
        order = frappe.new_doc("Restaurant Order")
        order.table = table.name
        order.table_number = table.table_number
        order.branch = table.branch
        order.table_session = session
        order.order_type = order_type
        order.customer_name = customer_name
        order.customer_phone = customer_phone
        order.notes = notes
        order.language = language
        order.status = "New"
        
        # Financials
        order.subtotal = subtotal
        order.service_charge = service_charge
        order.service_charge_percent = settings.service_charge_percent or 0
        order.vat = vat
        order.vat_percent = settings.vat_percent or 15
        order.grand_total = grand_total
        
        # Add items
        max_prep_time = 0
        for item in validated_items:
            order.append("items", {
                "menu_item": item["menu_item"],
                "item_code": item["item_code"],
                "item_name": item["item_name"],
                "item_name_ar": item["item_name_ar"],
                "qty": item["qty"],
                "rate": item["rate"],
                "amount": item["total"],
                "modifiers": json.dumps(item.get("modifiers", [])),
                "special_instructions": item.get("notes", ""),
                "kitchen_station": item["kitchen_station"],
                "preparation_time": item["preparation_time"],
                "status": "Pending"
            })
            
            if item["preparation_time"] > max_prep_time:
                max_prep_time = item["preparation_time"]
        
        order.estimated_preparation_time = max_prep_time
        order.insert(ignore_permissions=True)
        
        # Create Kitchen Orders (KOT) by station
        create_kitchen_orders(order)
        
        # Send real-time notification to kitchen
        notify_kitchen_new_order(order)
        
        # Send notification to waiters
        notify_waiters_new_order(order)
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _("Order placed successfully"),
            "data": {
                "order_id": order.name,
                "order_number": order.order_number,
                "table_number": table.table_number,
                "estimated_time": max_prep_time,
                "grand_total": grand_total,
                "status": "New",
                "status_text": _("Order Received"),
                "track_url": f"/order-status/{order.name}"
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Place Order Error: {str(e)}", "Restaurant POS")
        return {"success": False, "message": _("Error placing order. Please try again.")}


def validate_order_items(items, branch=None):
    """Validate order items and calculate totals"""
    validated = []
    errors = []
    
    for item in items:
        menu_item_name = item.get("item") or item.get("menu_item")
        qty = cint(item.get("qty", 1))
        modifiers = item.get("modifiers", [])
        
        if qty < 1:
            continue
        
        # Get menu item details
        menu_item = frappe.db.get_value(
            "Menu Item",
            menu_item_name,
            ["name", "item_code", "item_name", "item_name_ar", "price", 
             "is_available", "enabled", "kitchen_station", "preparation_time_minutes"],
            as_dict=True
        )
        
        if not menu_item:
            errors.append(f"Item not found: {menu_item_name}")
            continue
        
        if not menu_item.enabled:
            errors.append(f"Item not available: {menu_item.item_name}")
            continue
        
        # Check availability
        from restaurant_pos.api.menu import check_item_availability
        if not check_item_availability(menu_item.item_code, branch):
            errors.append(f"Item out of stock: {menu_item.item_name}")
            continue
        
        # Calculate price with modifiers
        base_price = flt(menu_item.price)
        modifier_price = 0
        
        for mod in modifiers:
            if mod.get("additional_price"):
                modifier_price += flt(mod["additional_price"])
        
        unit_price = base_price + modifier_price
        total = unit_price * qty
        
        validated.append({
            "menu_item": menu_item.name,
            "item_code": menu_item.item_code,
            "item_name": menu_item.item_name,
            "item_name_ar": menu_item.item_name_ar,
            "qty": qty,
            "rate": unit_price,
            "total": total,
            "modifiers": modifiers,
            "notes": item.get("notes", ""),
            "kitchen_station": menu_item.kitchen_station,
            "preparation_time": menu_item.preparation_time_minutes or 10
        })
    
    return validated, errors


def get_or_create_table_session(table, customer_name=None, customer_phone=None):
    """Get existing session or create new one for a table"""
    # Check for active session
    existing = frappe.db.get_value(
        "Table Session",
        {"table": table, "status": ["in", ["Active", "Ordering"]]},
        "name"
    )
    
    if existing:
        return existing
    
    # Create new session
    session = frappe.new_doc("Table Session")
    session.table = table
    session.customer_name = customer_name
    session.customer_phone = customer_phone
    session.status = "Ordering"
    session.started_at = now_datetime()
    session.insert(ignore_permissions=True)
    
    # Update table with current session
    frappe.db.set_value("Restaurant Table", table, "current_session", session.name)
    
    return session.name


def create_kitchen_orders(order):
    """Create Kitchen Order Tickets (KOT) grouped by kitchen station"""
    # Group items by kitchen station
    station_items = {}
    
    for item in order.items:
        station = item.kitchen_station or "Main Kitchen"
        if station not in station_items:
            station_items[station] = []
        station_items[station].append(item)
    
    # Create KOT for each station
    for station, items in station_items.items():
        kot = frappe.new_doc("Kitchen Order")
        kot.restaurant_order = order.name
        kot.table = order.table
        kot.table_number = order.table_number
        kot.branch = order.branch
        kot.kitchen_station = station
        kot.order_type = order.order_type
        kot.status = "New"
        kot.priority = "Normal"
        kot.notes = order.notes
        
        for item in items:
            kot.append("items", {
                "order_item": item.name,
                "menu_item": item.menu_item,
                "item_name": item.item_name,
                "item_name_ar": item.item_name_ar,
                "qty": item.qty,
                "modifiers": item.modifiers,
                "special_instructions": item.special_instructions,
                "status": "Pending"
            })
        
        kot.insert(ignore_permissions=True)


def notify_kitchen_new_order(order):
    """Send real-time notification to kitchen displays"""
    frappe.publish_realtime(
        event="restaurant:new_order",
        message={
            "order_id": order.name,
            "order_number": order.order_number,
            "table_number": order.table_number,
            "order_type": order.order_type,
            "items_count": len(order.items),
            "branch": order.branch,
            "timestamp": str(now_datetime())
        },
        room=f"kitchen:{order.branch}"
    )


def notify_waiters_new_order(order):
    """Send notification to waiters"""
    frappe.publish_realtime(
        event="restaurant:new_order",
        message={
            "order_id": order.name,
            "order_number": order.order_number,
            "table_number": order.table_number,
            "customer_name": order.customer_name,
            "grand_total": order.grand_total,
            "branch": order.branch,
        },
        room=f"waiters:{order.branch}"
    )


@frappe.whitelist(allow_guest=True)
def get_order_status(order_id):
    """
    Get the current status of an order
    
    Args:
        order_id: Order ID or order number
    
    Returns:
        dict: Order status and details
    """
    try:
        # Find order by ID or order number
        order = None
        if frappe.db.exists("Restaurant Order", order_id):
            order = frappe.get_doc("Restaurant Order", order_id)
        else:
            order_name = frappe.db.get_value(
                "Restaurant Order", 
                {"order_number": order_id}, 
                "name"
            )
            if order_name:
                order = frappe.get_doc("Restaurant Order", order_name)
        
        if not order:
            return {"success": False, "message": _("Order not found")}
        
        # Get item statuses
        items_status = []
        for item in order.items:
            items_status.append({
                "item_name": item.item_name_ar or item.item_name,
                "qty": item.qty,
                "status": item.status,
                "status_text": get_status_text(item.status)
            })
        
        # Calculate progress
        total_items = len(order.items)
        completed_items = len([i for i in order.items if i.status in ["Ready", "Served"]])
        progress = int((completed_items / total_items) * 100) if total_items > 0 else 0
        
        return {
            "success": True,
            "data": {
                "order_id": order.name,
                "order_number": order.order_number,
                "table_number": order.table_number,
                "status": order.status,
                "status_text": get_status_text(order.status),
                "progress": progress,
                "estimated_time": order.estimated_preparation_time,
                "items": items_status,
                "grand_total": order.grand_total,
                "is_paid": order.is_paid,
                "created_at": str(order.creation),
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Order Status Error: {str(e)}", "Restaurant POS")
        return {"success": False, "message": _("Error getting order status")}


def get_status_text(status):
    """Get localized status text"""
    status_map = {
        "New": _("Order Received"),
        "Pending": _("Pending"),
        "Confirmed": _("Confirmed"),
        "Preparing": _("Being Prepared"),
        "Ready": _("Ready"),
        "Served": _("Served"),
        "Completed": _("Completed"),
        "Cancelled": _("Cancelled")
    }
    return status_map.get(status, status)


@frappe.whitelist(allow_guest=True)
def add_items_to_order(order_id, items, language="ar"):
    """
    Add more items to an existing order
    
    Args:
        order_id: Existing order ID
        items: New items to add
        language: Language for responses
    
    Returns:
        dict: Updated order details
    """
    try:
        order = frappe.get_doc("Restaurant Order", order_id)
        
        if order.status in ["Completed", "Cancelled", "Paid"]:
            return {"success": False, "message": _("Cannot modify this order")}
        
        # Parse items
        if isinstance(items, str):
            items = json.loads(items)
        
        # Validate new items
        validated_items, errors = validate_order_items(items, order.branch)
        
        if errors:
            return {"success": False, "message": errors[0]}
        
        # Add items to order
        for item in validated_items:
            order.append("items", {
                "menu_item": item["menu_item"],
                "item_code": item["item_code"],
                "item_name": item["item_name"],
                "item_name_ar": item["item_name_ar"],
                "qty": item["qty"],
                "rate": item["rate"],
                "amount": item["total"],
                "modifiers": json.dumps(item.get("modifiers", [])),
                "special_instructions": item.get("notes", ""),
                "kitchen_station": item["kitchen_station"],
                "preparation_time": item["preparation_time"],
                "status": "Pending"
            })
        
        # Recalculate totals
        order.subtotal = sum(item.amount for item in order.items)
        order.service_charge = flt(order.subtotal * order.service_charge_percent / 100)
        order.vat = flt((order.subtotal + order.service_charge) * order.vat_percent / 100)
        order.grand_total = order.subtotal + order.service_charge + order.vat
        
        order.save(ignore_permissions=True)
        
        # Create new KOTs for added items
        create_kitchen_orders_for_items(order, validated_items)
        
        # Notify kitchen
        notify_kitchen_new_order(order)
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _("Items added successfully"),
            "data": {
                "order_id": order.name,
                "grand_total": order.grand_total,
                "items_count": len(order.items)
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Add Items Error: {str(e)}", "Restaurant POS")
        return {"success": False, "message": _("Error adding items")}


def create_kitchen_orders_for_items(order, new_items):
    """Create KOTs for newly added items"""
    # Group by station
    station_items = {}
    for item in new_items:
        station = item["kitchen_station"] or "Main Kitchen"
        if station not in station_items:
            station_items[station] = []
        station_items[station].append(item)
    
    # Create or append to existing KOT
    for station, items in station_items.items():
        kot = frappe.new_doc("Kitchen Order")
        kot.restaurant_order = order.name
        kot.table = order.table
        kot.table_number = order.table_number
        kot.branch = order.branch
        kot.kitchen_station = station
        kot.order_type = order.order_type
        kot.status = "New"
        kot.priority = "Normal"
        kot.is_additional = 1
        
        for item in items:
            kot.append("items", {
                "menu_item": item["menu_item"],
                "item_name": item["item_name"],
                "item_name_ar": item["item_name_ar"],
                "qty": item["qty"],
                "modifiers": json.dumps(item.get("modifiers", [])),
                "special_instructions": item.get("notes", ""),
                "status": "Pending"
            })
        
        kot.insert(ignore_permissions=True)
