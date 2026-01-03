# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

"""
Waiter API - Endpoints for Waiter Operations
"""

import frappe
from frappe import _
from frappe.utils import now_datetime


@frappe.whitelist()
def get_my_tables():
    """
    Get tables assigned to current waiter
    
    Returns:
        list: Tables with current status
    """
    user = frappe.session.user
    branch = frappe.defaults.get_user_default("branch")
    
    tables = frappe.get_all(
        "Restaurant Table",
        filters={
            "assigned_waiter": user,
            "branch": branch
        },
        fields=[
            "name", "table_number", "capacity", "status",
            "current_order", "location"
        ],
        order_by="table_number asc"
    )
    
    result = []
    for table in tables:
        data = {
            "id": table.name,
            "table_number": table.table_number,
            "capacity": table.capacity,
            "status": table.status,
            "location": table.location,
            "current_order": None,
            "guests": 0,
            "order_time": None
        }
        
        if table.current_order:
            order = frappe.db.get_value(
                "Restaurant Order",
                table.current_order,
                ["name", "status", "guest_count", "creation", "grand_total"],
                as_dict=True
            )
            if order:
                data["current_order"] = {
                    "id": order.name,
                    "status": order.status,
                    "total": order.grand_total,
                    "created_at": str(order.creation)
                }
                data["guests"] = order.guest_count
        
        result.append(data)
    
    return {"success": True, "data": result}


@frappe.whitelist()
def get_all_tables(branch=None, location=None):
    """
    Get all tables (for floor view)
    
    Args:
        branch: Branch filter
        location: Location filter (Indoor, Outdoor, etc.)
    
    Returns:
        list: All tables
    """
    if not branch:
        branch = frappe.defaults.get_user_default("branch")
    
    filters = {"branch": branch}
    if location:
        filters["location"] = location
    
    tables = frappe.get_all(
        "Restaurant Table",
        filters=filters,
        fields=[
            "name", "table_number", "capacity", "status",
            "current_order", "location", "assigned_waiter",
            "position_x", "position_y"
        ],
        order_by="table_number asc"
    )
    
    result = []
    for table in tables:
        data = {
            "id": table.name,
            "table_number": table.table_number,
            "capacity": table.capacity,
            "status": table.status,
            "location": table.location,
            "waiter": table.assigned_waiter,
            "position": {
                "x": table.position_x or 0,
                "y": table.position_y or 0
            },
            "current_order": None
        }
        
        if table.current_order and table.status == "Occupied":
            order = frappe.db.get_value(
                "Restaurant Order",
                table.current_order,
                ["name", "status", "guest_count", "creation", "grand_total"],
                as_dict=True
            )
            if order:
                data["current_order"] = {
                    "id": order.name,
                    "status": order.status,
                    "guests": order.guest_count,
                    "total": order.grand_total,
                    "minutes_elapsed": int(
                        (now_datetime() - order.creation).total_seconds() / 60
                    )
                }
        
        result.append(data)
    
    return {"success": True, "data": result}


@frappe.whitelist()
def seat_guests(table_id, guest_count):
    """
    Seat guests at a table
    
    Args:
        table_id: Table ID
        guest_count: Number of guests
    
    Returns:
        dict: Table session info
    """
    try:
        table = frappe.get_doc("Restaurant Table", table_id)
        
        if table.status == "Occupied":
            return {
                "success": False,
                "message": _("Table is already occupied")
            }
        
        # Create table session
        session = frappe.get_doc({
            "doctype": "Table Session",
            "restaurant_table": table_id,
            "table_number": table.table_number,
            "branch": table.branch,
            "guest_count": guest_count,
            "waiter": frappe.session.user,
            "started_at": now_datetime(),
            "status": "Active"
        })
        session.insert(ignore_permissions=True)
        
        # Update table status
        table.status = "Occupied"
        table.current_session = session.name
        table.save(ignore_permissions=True)
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _("Guests seated"),
            "data": {
                "session_id": session.name,
                "table_number": table.table_number,
                "guests": guest_count
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Seat Guests Error: {str(e)}", "Restaurant POS")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def transfer_table(from_table, to_table):
    """
    Transfer guests and order to another table
    
    Args:
        from_table: Source table ID
        to_table: Destination table ID
    
    Returns:
        dict: Confirmation
    """
    try:
        source = frappe.get_doc("Restaurant Table", from_table)
        dest = frappe.get_doc("Restaurant Table", to_table)
        
        if dest.status == "Occupied":
            return {
                "success": False,
                "message": _("Destination table is occupied")
            }
        
        if source.status != "Occupied":
            return {
                "success": False,
                "message": _("Source table has no guests")
            }
        
        # Transfer session
        if source.current_session:
            session = frappe.get_doc("Table Session", source.current_session)
            session.restaurant_table = to_table
            session.table_number = dest.table_number
            session.save(ignore_permissions=True)
        
        # Transfer order
        if source.current_order:
            frappe.db.set_value(
                "Restaurant Order",
                source.current_order,
                {
                    "restaurant_table": to_table,
                    "table_number": dest.table_number
                }
            )
        
        # Update tables
        dest.status = "Occupied"
        dest.current_session = source.current_session
        dest.current_order = source.current_order
        dest.save(ignore_permissions=True)
        
        source.status = "Available"
        source.current_session = None
        source.current_order = None
        source.save(ignore_permissions=True)
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _("Table transferred successfully"),
            "data": {
                "from": source.table_number,
                "to": dest.table_number
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Transfer Table Error: {str(e)}", "Restaurant POS")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def merge_tables(table_ids, primary_table):
    """
    Merge multiple tables into one
    
    Args:
        table_ids: List of table IDs to merge
        primary_table: Primary table ID
    
    Returns:
        dict: Merged order info
    """
    try:
        if isinstance(table_ids, str):
            table_ids = frappe.parse_json(table_ids)
        
        primary = frappe.get_doc("Restaurant Table", primary_table)
        
        # Collect all orders
        orders_to_merge = []
        for tid in table_ids:
            if tid == primary_table:
                continue
            table = frappe.get_doc("Restaurant Table", tid)
            if table.current_order:
                orders_to_merge.append(table.current_order)
        
        # Merge orders into primary
        if primary.current_order and orders_to_merge:
            primary_order = frappe.get_doc("Restaurant Order", primary.current_order)
            
            for order_name in orders_to_merge:
                order = frappe.get_doc("Restaurant Order", order_name)
                
                # Transfer items
                for item in order.items:
                    new_item = primary_order.append("items", {})
                    for field in item.as_dict():
                        if field not in ["name", "parent", "parentfield", "parenttype", "idx"]:
                            new_item.set(field, item.get(field))
                
                # Cancel merged order
                order.status = "Merged"
                order.merged_into = primary.current_order
                order.save(ignore_permissions=True)
            
            # Recalculate totals
            primary_order.calculate_totals()
            primary_order.save(ignore_permissions=True)
        
        # Clear merged tables
        for tid in table_ids:
            if tid == primary_table:
                continue
            frappe.db.set_value("Restaurant Table", tid, {
                "status": "Available",
                "current_order": None,
                "current_session": None
            })
        
        # Update primary table info
        merged_numbers = []
        for tid in table_ids:
            num = frappe.db.get_value("Restaurant Table", tid, "table_number")
            merged_numbers.append(num)
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _("Tables merged successfully"),
            "data": {
                "primary_table": primary.table_number,
                "merged_tables": merged_numbers
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Merge Tables Error: {str(e)}", "Restaurant POS")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_waiter_calls(branch=None):
    """
    Get pending waiter calls
    
    Args:
        branch: Branch filter
    
    Returns:
        list: Pending calls
    """
    if not branch:
        branch = frappe.defaults.get_user_default("branch")
    
    user = frappe.session.user
    
    calls = frappe.get_all(
        "Waiter Call",
        filters={
            "branch": branch,
            "status": "Pending",
            "waiter": ["in", [user, None, ""]]
        },
        fields=[
            "name", "restaurant_table", "table_number",
            "call_type", "notes", "creation"
        ],
        order_by="creation asc"
    )
    
    return {
        "success": True,
        "data": [{
            "id": c.name,
            "table_id": c.restaurant_table,
            "table_number": c.table_number,
            "type": c.call_type,
            "notes": c.notes,
            "created_at": str(c.creation),
            "minutes_waiting": int(
                (now_datetime() - c.creation).total_seconds() / 60
            )
        } for c in calls]
    }


@frappe.whitelist()
def respond_to_call(call_id, action="attend"):
    """
    Respond to a waiter call
    
    Args:
        call_id: Call ID
        action: Action taken (attend, complete, dismiss)
    
    Returns:
        dict: Confirmation
    """
    try:
        call = frappe.get_doc("Waiter Call", call_id)
        
        if action == "attend":
            call.status = "Attended"
            call.attended_at = now_datetime()
            call.attended_by = frappe.session.user
        elif action == "complete":
            call.status = "Completed"
            call.completed_at = now_datetime()
        elif action == "dismiss":
            call.status = "Dismissed"
            call.completed_at = now_datetime()
        
        call.save(ignore_permissions=True)
        frappe.db.commit()
        
        # Notify table if using digital menu
        frappe.publish_realtime(
            event="restaurant:call_response",
            message={
                "call_id": call_id,
                "table_number": call.table_number,
                "status": call.status
            },
            room=f"table:{call.restaurant_table}"
        )
        
        return {"success": True, "message": _("Call updated")}
        
    except Exception as e:
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_ready_orders(branch=None):
    """
    Get orders ready for pickup/serving
    
    Args:
        branch: Branch filter
    
    Returns:
        list: Ready orders
    """
    if not branch:
        branch = frappe.defaults.get_user_default("branch")
    
    user = frappe.session.user
    
    # Get tables assigned to waiter
    my_tables = frappe.get_all(
        "Restaurant Table",
        filters={"assigned_waiter": user, "branch": branch},
        pluck="name"
    )
    
    orders = frappe.get_all(
        "Kitchen Order",
        filters={
            "branch": branch,
            "status": "Ready"
        },
        fields=[
            "name", "restaurant_order", "table_number",
            "kitchen_station", "completed_at"
        ],
        order_by="completed_at asc"
    )
    
    result = []
    for order in orders:
        # Get items
        items = frappe.get_all(
            "Kitchen Order Item",
            filters={"parent": order.name, "status": "Ready"},
            fields=["item_name", "qty"]
        )
        
        result.append({
            "kot_id": order.name,
            "order_id": order.restaurant_order,
            "table_number": order.table_number,
            "station": order.kitchen_station,
            "ready_since": str(order.completed_at) if order.completed_at else None,
            "minutes_waiting": int(
                (now_datetime() - order.completed_at).total_seconds() / 60
            ) if order.completed_at else 0,
            "items": [{"name": i.item_name, "qty": i.qty} for i in items],
            "is_my_table": order.restaurant_table in my_tables if order.restaurant_table else False
        })
    
    return {"success": True, "data": result}


@frappe.whitelist()
def mark_order_served(kot_id):
    """
    Mark kitchen order as served
    
    Args:
        kot_id: Kitchen Order ID
    
    Returns:
        dict: Confirmation
    """
    from restaurant_pos.api.kitchen import bump_order
    return bump_order(kot_id)


@frappe.whitelist()
def close_table(table_id):
    """
    Close table and end session
    
    Args:
        table_id: Table ID
    
    Returns:
        dict: Confirmation
    """
    try:
        table = frappe.get_doc("Restaurant Table", table_id)
        
        # Check if order is paid
        if table.current_order:
            order = frappe.get_doc("Restaurant Order", table.current_order)
            if order.status not in ["Paid", "Cancelled"]:
                return {
                    "success": False,
                    "message": _("Please complete payment before closing table")
                }
        
        # Close session
        if table.current_session:
            frappe.db.set_value(
                "Table Session",
                table.current_session,
                {
                    "status": "Closed",
                    "ended_at": now_datetime()
                }
            )
        
        # Reset table
        table.status = "Available"
        table.current_order = None
        table.current_session = None
        table.save(ignore_permissions=True)
        
        frappe.db.commit()
        
        return {"success": True, "message": _("Table closed")}
        
    except Exception as e:
        frappe.log_error(f"Close Table Error: {str(e)}", "Restaurant POS")
        return {"success": False, "message": str(e)}
