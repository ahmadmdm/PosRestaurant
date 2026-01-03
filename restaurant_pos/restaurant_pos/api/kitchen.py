# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

"""
Kitchen API - Endpoints for Kitchen Display System (KDS)
"""

import frappe
from frappe import _
from frappe.utils import now_datetime, time_diff_in_seconds


@frappe.whitelist()
def get_kitchen_orders(station=None, branch=None, status=None):
    """
    Get orders for kitchen display
    
    Args:
        station: Kitchen station filter
        branch: Branch filter
        status: Status filter (New, Preparing, Ready)
    
    Returns:
        list: Kitchen orders
    """
    filters = {}
    
    if station:
        filters["kitchen_station"] = station
    if branch:
        filters["branch"] = branch
    if status:
        filters["status"] = status
    else:
        filters["status"] = ["in", ["New", "Preparing"]]
    
    orders = frappe.get_all(
        "Kitchen Order",
        filters=filters,
        fields=[
            "name", "restaurant_order", "table_number", "order_type",
            "kitchen_station", "status", "priority", "notes",
            "creation", "started_at", "completed_at", "is_additional"
        ],
        order_by="priority desc, creation asc"
    )
    
    result = []
    for order in orders:
        # Get order items
        items = frappe.get_all(
            "Kitchen Order Item",
            filters={"parent": order.name},
            fields=[
                "name", "menu_item", "item_name", "item_name_ar",
                "qty", "modifiers", "special_instructions", "status"
            ],
            order_by="idx asc"
        )
        
        # Calculate elapsed time
        elapsed_time = 0
        if order.status == "Preparing" and order.started_at:
            elapsed_time = time_diff_in_seconds(now_datetime(), order.started_at)
        
        result.append({
            "id": order.name,
            "order_id": order.restaurant_order,
            "table_number": order.table_number,
            "order_type": order.order_type,
            "station": order.kitchen_station,
            "status": order.status,
            "priority": order.priority,
            "notes": order.notes,
            "is_additional": order.is_additional,
            "elapsed_time": int(elapsed_time),
            "created_at": str(order.creation),
            "items": [{
                "id": item.name,
                "name": item.item_name,
                "name_ar": item.item_name_ar,
                "qty": item.qty,
                "modifiers": frappe.parse_json(item.modifiers) if item.modifiers else [],
                "notes": item.special_instructions,
                "status": item.status
            } for item in items]
        })
    
    return {"success": True, "data": result}


@frappe.whitelist()
def update_order_status(kot_id, status, item_id=None):
    """
    Update kitchen order or item status
    
    Args:
        kot_id: Kitchen Order ID
        status: New status
        item_id: Specific item ID (optional)
    
    Returns:
        dict: Updated status
    """
    try:
        kot = frappe.get_doc("Kitchen Order", kot_id)
        
        if item_id:
            # Update specific item
            for item in kot.items:
                if item.name == item_id:
                    item.status = status
                    if status == "Preparing":
                        item.started_at = now_datetime()
                    elif status == "Ready":
                        item.completed_at = now_datetime()
                    break
            
            # Check if all items are ready
            all_ready = all(item.status == "Ready" for item in kot.items)
            if all_ready:
                kot.status = "Ready"
                kot.completed_at = now_datetime()
        else:
            # Update entire order
            kot.status = status
            if status == "Preparing":
                kot.started_at = now_datetime()
                # Update all pending items
                for item in kot.items:
                    if item.status == "Pending":
                        item.status = "Preparing"
                        item.started_at = now_datetime()
            elif status == "Ready":
                kot.completed_at = now_datetime()
                # Update all items
                for item in kot.items:
                    if item.status != "Ready":
                        item.status = "Ready"
                        item.completed_at = now_datetime()
        
        kot.save(ignore_permissions=True)
        
        # Update main order status
        update_restaurant_order_status(kot.restaurant_order)
        
        # Send real-time update
        frappe.publish_realtime(
            event="restaurant:kot_update",
            message={
                "kot_id": kot_id,
                "order_id": kot.restaurant_order,
                "table_number": kot.table_number,
                "status": kot.status,
                "station": kot.kitchen_station,
                "timestamp": str(now_datetime())
            },
            room=f"kitchen:{kot.branch}"
        )
        
        # Notify waiters if ready
        if kot.status == "Ready":
            frappe.publish_realtime(
                event="restaurant:order_ready",
                message={
                    "kot_id": kot_id,
                    "order_id": kot.restaurant_order,
                    "table_number": kot.table_number,
                    "station": kot.kitchen_station,
                },
                room=f"waiters:{kot.branch}"
            )
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _("Status updated"),
            "data": {
                "kot_id": kot_id,
                "status": kot.status
            }
        }
        
    except Exception as e:
        frappe.log_error(f"KOT Update Error: {str(e)}", "Restaurant POS")
        return {"success": False, "message": str(e)}


def update_restaurant_order_status(order_name):
    """Update main order status based on KOT statuses"""
    try:
        # Get all KOTs for this order
        kots = frappe.get_all(
            "Kitchen Order",
            filters={"restaurant_order": order_name},
            fields=["status"]
        )
        
        if not kots:
            return
        
        # Determine order status
        statuses = [k.status for k in kots]
        
        if all(s == "Ready" for s in statuses):
            new_status = "Ready"
        elif any(s == "Preparing" for s in statuses):
            new_status = "Preparing"
        elif all(s == "New" for s in statuses):
            new_status = "Confirmed"
        else:
            new_status = "Preparing"
        
        # Update order
        order = frappe.get_doc("Restaurant Order", order_name)
        if order.status not in ["Served", "Completed", "Cancelled", "Paid"]:
            order.status = new_status
            order.save(ignore_permissions=True)
            
            # Send status update to customer
            frappe.publish_realtime(
                event="restaurant:order_status",
                message={
                    "order_id": order_name,
                    "status": new_status,
                    "table_number": order.table_number,
                },
                room=f"order:{order_name}"
            )
            
    except Exception as e:
        frappe.log_error(f"Order Status Update Error: {str(e)}", "Restaurant POS")


@frappe.whitelist()
def bump_order(kot_id):
    """
    Mark order as served (bump from KDS)
    
    Args:
        kot_id: Kitchen Order ID
    
    Returns:
        dict: Confirmation
    """
    try:
        kot = frappe.get_doc("Kitchen Order", kot_id)
        kot.status = "Served"
        kot.served_at = now_datetime()
        
        for item in kot.items:
            item.status = "Served"
        
        kot.save(ignore_permissions=True)
        
        # Check if all KOTs are served
        all_served = not frappe.db.exists(
            "Kitchen Order",
            {
                "restaurant_order": kot.restaurant_order,
                "status": ["not in", ["Served", "Cancelled"]]
            }
        )
        
        if all_served:
            frappe.db.set_value(
                "Restaurant Order", 
                kot.restaurant_order, 
                "status", 
                "Served"
            )
        
        # Update order items status
        for item in kot.items:
            if item.order_item:
                frappe.db.set_value(
                    "Restaurant Order Item",
                    item.order_item,
                    "status",
                    "Served"
                )
        
        frappe.db.commit()
        
        return {"success": True, "message": _("Order bumped")}
        
    except Exception as e:
        frappe.log_error(f"Bump Order Error: {str(e)}", "Restaurant POS")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def recall_order(kot_id):
    """
    Recall a served order back to KDS
    
    Args:
        kot_id: Kitchen Order ID
    
    Returns:
        dict: Confirmation
    """
    try:
        kot = frappe.get_doc("Kitchen Order", kot_id)
        kot.status = "Ready"
        kot.served_at = None
        
        for item in kot.items:
            item.status = "Ready"
        
        kot.save(ignore_permissions=True)
        
        # Update main order
        frappe.db.set_value(
            "Restaurant Order",
            kot.restaurant_order,
            "status",
            "Ready"
        )
        
        frappe.db.commit()
        
        # Notify kitchen
        frappe.publish_realtime(
            event="restaurant:kot_recall",
            message={
                "kot_id": kot_id,
                "table_number": kot.table_number,
            },
            room=f"kitchen:{kot.branch}"
        )
        
        return {"success": True, "message": _("Order recalled")}
        
    except Exception as e:
        frappe.log_error(f"Recall Order Error: {str(e)}", "Restaurant POS")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def set_priority(kot_id, priority):
    """
    Set order priority (Rush, Normal, Low)
    
    Args:
        kot_id: Kitchen Order ID
        priority: Priority level
    
    Returns:
        dict: Confirmation
    """
    try:
        frappe.db.set_value("Kitchen Order", kot_id, "priority", priority)
        
        kot = frappe.get_doc("Kitchen Order", kot_id)
        
        frappe.publish_realtime(
            event="restaurant:kot_priority",
            message={
                "kot_id": kot_id,
                "priority": priority,
                "table_number": kot.table_number,
            },
            room=f"kitchen:{kot.branch}"
        )
        
        frappe.db.commit()
        
        return {"success": True, "message": _("Priority updated")}
        
    except Exception as e:
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_kitchen_stats(station=None, branch=None):
    """
    Get kitchen statistics
    
    Args:
        station: Kitchen station
        branch: Branch
    
    Returns:
        dict: Statistics
    """
    filters = {}
    if station:
        filters["kitchen_station"] = station
    if branch:
        filters["branch"] = branch
    
    # Count by status
    new_count = frappe.db.count("Kitchen Order", {**filters, "status": "New"})
    preparing_count = frappe.db.count("Kitchen Order", {**filters, "status": "Preparing"})
    ready_count = frappe.db.count("Kitchen Order", {**filters, "status": "Ready"})
    
    # Average preparation time (last 24 hours)
    from frappe.utils import add_days
    yesterday = add_days(now_datetime(), -1)
    
    avg_time = frappe.db.sql("""
        SELECT AVG(TIMESTAMPDIFF(SECOND, started_at, completed_at)) as avg_time
        FROM `tabKitchen Order`
        WHERE status = 'Ready'
        AND completed_at >= %s
        AND started_at IS NOT NULL
        AND completed_at IS NOT NULL
        {station_filter}
        {branch_filter}
    """.format(
        station_filter=f"AND kitchen_station = '{station}'" if station else "",
        branch_filter=f"AND branch = '{branch}'" if branch else ""
    ), yesterday, as_dict=True)
    
    return {
        "success": True,
        "data": {
            "new": new_count,
            "preparing": preparing_count,
            "ready": ready_count,
            "total_active": new_count + preparing_count + ready_count,
            "avg_preparation_time": int(avg_time[0].avg_time or 0) if avg_time else 0
        }
    }
