# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

"""
Table API - Public endpoints for table management
"""

import frappe
from frappe import _
from frappe.utils import now_datetime


@frappe.whitelist(allow_guest=True)
def get_table_session(table_code):
    """
    Get or create a session for a table (when customer scans QR)
    
    Args:
        table_code: QR code identifier
    
    Returns:
        dict: Table and session information
    """
    try:
        # Get table by QR code
        table = frappe.db.get_value(
            "Restaurant Table",
            {"qr_code": table_code, "enabled": 1},
            ["name", "table_number", "branch", "seating_capacity", 
             "area", "current_session", "status"],
            as_dict=True
        )
        
        if not table:
            return {"success": False, "message": _("Invalid QR code")}
        
        # Get branch info
        branch_info = frappe.db.get_value(
            "Branch",
            table.branch,
            ["branch_name", "address", "phone"],
            as_dict=True
        ) if table.branch else {}
        
        # Get active session info
        session_info = None
        if table.current_session:
            session = frappe.db.get_value(
                "Table Session",
                table.current_session,
                ["name", "status", "customer_name", "started_at", "total_orders"],
                as_dict=True
            )
            if session and session.status in ["Active", "Ordering"]:
                session_info = {
                    "session_id": session.name,
                    "status": session.status,
                    "customer_name": session.customer_name,
                    "started_at": str(session.started_at),
                    "orders_count": session.total_orders or 0
                }
        
        # Get pending orders for this table
        pending_orders = []
        if session_info:
            orders = frappe.get_all(
                "Restaurant Order",
                filters={
                    "table_session": session_info["session_id"],
                    "status": ["not in", ["Completed", "Cancelled", "Paid"]]
                },
                fields=["name", "order_number", "status", "grand_total", "creation"],
                order_by="creation desc"
            )
            pending_orders = [{
                "order_id": o.name,
                "order_number": o.order_number,
                "status": o.status,
                "total": o.grand_total,
                "created": str(o.creation)
            } for o in orders]
        
        return {
            "success": True,
            "data": {
                "table": {
                    "id": table.name,
                    "number": table.table_number,
                    "capacity": table.seating_capacity,
                    "area": table.area,
                    "status": table.status
                },
                "branch": branch_info,
                "session": session_info,
                "pending_orders": pending_orders,
                "currency": frappe.defaults.get_global_default("currency"),
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Table Session Error: {str(e)}", "Restaurant POS")
        return {"success": False, "message": _("Error loading table info")}


@frappe.whitelist(allow_guest=True)
def call_waiter(table_code, reason=None):
    """
    Send a call waiter request
    
    Args:
        table_code: QR code identifier
        reason: Optional reason for calling
    
    Returns:
        dict: Confirmation
    """
    try:
        # Get table
        table = frappe.db.get_value(
            "Restaurant Table",
            {"qr_code": table_code, "enabled": 1},
            ["name", "table_number", "branch"],
            as_dict=True
        )
        
        if not table:
            return {"success": False, "message": _("Invalid table")}
        
        # Create waiter call record
        call = frappe.new_doc("Waiter Call")
        call.table = table.name
        call.table_number = table.table_number
        call.branch = table.branch
        call.reason = reason
        call.status = "Pending"
        call.called_at = now_datetime()
        call.insert(ignore_permissions=True)
        
        # Send real-time notification
        frappe.publish_realtime(
            event="restaurant:call_waiter",
            message={
                "call_id": call.name,
                "table_number": table.table_number,
                "branch": table.branch,
                "reason": reason,
                "timestamp": str(now_datetime())
            },
            room=f"waiters:{table.branch}"
        )
        
        # Also send to restaurant manager room
        frappe.publish_realtime(
            event="restaurant:call_waiter",
            message={
                "call_id": call.name,
                "table_number": table.table_number,
                "branch": table.branch,
                "reason": reason,
                "timestamp": str(now_datetime())
            },
            room=f"manager:{table.branch}"
        )
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _("Waiter has been notified"),
            "data": {
                "call_id": call.name
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Call Waiter Error: {str(e)}", "Restaurant POS")
        return {"success": False, "message": _("Error calling waiter")}


@frappe.whitelist(allow_guest=True)
def request_bill(table_code, payment_method=None):
    """
    Request the bill for a table
    
    Args:
        table_code: QR code identifier
        payment_method: Preferred payment method
    
    Returns:
        dict: Bill details
    """
    try:
        # Get table
        table = frappe.db.get_value(
            "Restaurant Table",
            {"qr_code": table_code, "enabled": 1},
            ["name", "table_number", "branch", "current_session"],
            as_dict=True
        )
        
        if not table:
            return {"success": False, "message": _("Invalid table")}
        
        if not table.current_session:
            return {"success": False, "message": _("No active session")}
        
        # Get all orders for this session
        orders = frappe.get_all(
            "Restaurant Order",
            filters={
                "table_session": table.current_session,
                "status": ["not in", ["Cancelled"]]
            },
            fields=["name", "subtotal", "service_charge", "vat", "grand_total", "is_paid"]
        )
        
        if not orders:
            return {"success": False, "message": _("No orders found")}
        
        # Calculate totals
        total_subtotal = sum(o.subtotal for o in orders)
        total_service = sum(o.service_charge for o in orders)
        total_vat = sum(o.vat for o in orders)
        total_amount = sum(o.grand_total for o in orders)
        paid_amount = sum(o.grand_total for o in orders if o.is_paid)
        
        # Send notification to cashier
        frappe.publish_realtime(
            event="restaurant:bill_request",
            message={
                "table_number": table.table_number,
                "session_id": table.current_session,
                "total_amount": total_amount,
                "payment_method": payment_method,
                "branch": table.branch,
                "timestamp": str(now_datetime())
            },
            room=f"cashier:{table.branch}"
        )
        
        return {
            "success": True,
            "message": _("Bill request sent"),
            "data": {
                "table_number": table.table_number,
                "orders_count": len(orders),
                "subtotal": total_subtotal,
                "service_charge": total_service,
                "vat": total_vat,
                "grand_total": total_amount,
                "paid_amount": paid_amount,
                "balance": total_amount - paid_amount,
                "currency": frappe.defaults.get_global_default("currency")
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Request Bill Error: {str(e)}", "Restaurant POS")
        return {"success": False, "message": _("Error requesting bill")}


@frappe.whitelist()
def get_table_status(table=None, branch=None):
    """
    Get status of all tables (for staff)
    
    Args:
        table: Specific table (optional)
        branch: Filter by branch
    
    Returns:
        list: Table statuses
    """
    filters = {"enabled": 1}
    
    if table:
        filters["name"] = table
    if branch:
        filters["branch"] = branch
    
    tables = frappe.get_all(
        "Restaurant Table",
        filters=filters,
        fields=[
            "name", "table_number", "branch", "area",
            "seating_capacity", "status", "current_session"
        ],
        order_by="table_number asc"
    )
    
    result = []
    for t in tables:
        table_info = {
            "id": t.name,
            "number": t.table_number,
            "area": t.area,
            "capacity": t.seating_capacity,
            "status": t.status,
            "session": None,
            "current_order": None,
            "total_amount": 0
        }
        
        if t.current_session:
            session = frappe.db.get_value(
                "Table Session",
                t.current_session,
                ["customer_name", "started_at", "status"],
                as_dict=True
            )
            if session and session.status in ["Active", "Ordering"]:
                table_info["session"] = {
                    "id": t.current_session,
                    "customer": session.customer_name,
                    "started": str(session.started_at)
                }
                
                # Get total amount
                total = frappe.db.sql("""
                    SELECT SUM(grand_total) as total
                    FROM `tabRestaurant Order`
                    WHERE table_session = %s AND status != 'Cancelled'
                """, t.current_session, as_dict=True)
                
                table_info["total_amount"] = total[0].total if total and total[0].total else 0
        
        result.append(table_info)
    
    return {"success": True, "data": result}
