# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

"""
Event handlers for POS Invoice
"""

import frappe
from frappe import _
from frappe.utils import flt


def on_submit(doc, method):
    """Handle POS Invoice submission"""
    # Link to restaurant order if exists
    if doc.custom_restaurant_order:
        update_restaurant_order_payment(doc)


def on_cancel(doc, method):
    """Handle POS Invoice cancellation"""
    if doc.custom_restaurant_order:
        revert_restaurant_order_payment(doc)


def update_restaurant_order_payment(invoice):
    """Update restaurant order when payment is made"""
    try:
        order = frappe.get_doc("Restaurant Order", invoice.custom_restaurant_order)
        
        if order.docstatus == 1:  # Only update submitted orders
            # Calculate total paid
            total_paid = flt(order.paid_amount) + flt(invoice.grand_total)
            
            frappe.db.set_value("Restaurant Order", order.name, {
                "paid_amount": total_paid,
                "payment_status": "Paid" if total_paid >= flt(order.grand_total) else "Partial",
                "status": "Paid" if total_paid >= flt(order.grand_total) else order.status
            })
            
            # Update table status if fully paid
            if total_paid >= flt(order.grand_total) and order.table:
                check_and_update_table_status(order.table)
            
            frappe.publish_realtime(
                "restaurant_payment_update",
                {
                    "order": order.name,
                    "table": order.table,
                    "paid_amount": total_paid,
                    "status": "Paid" if total_paid >= flt(order.grand_total) else "Partial"
                },
                room=f"table_{order.table}" if order.table else None
            )
    except Exception as e:
        frappe.log_error(f"Error updating restaurant order payment: {str(e)}")


def revert_restaurant_order_payment(invoice):
    """Revert restaurant order payment status on cancellation"""
    try:
        order = frappe.get_doc("Restaurant Order", invoice.custom_restaurant_order)
        
        # Recalculate paid amount
        total_paid = flt(order.paid_amount) - flt(invoice.grand_total)
        total_paid = max(0, total_paid)  # Don't go negative
        
        frappe.db.set_value("Restaurant Order", order.name, {
            "paid_amount": total_paid,
            "payment_status": "Paid" if total_paid >= flt(order.grand_total) else ("Partial" if total_paid > 0 else "Unpaid"),
            "status": "Served"  # Revert to served status
        })
    except Exception as e:
        frappe.log_error(f"Error reverting restaurant order payment: {str(e)}")


def check_and_update_table_status(table_name):
    """Check if all orders for a table are paid and update table status"""
    unpaid_orders = frappe.get_all(
        "Restaurant Order",
        filters={
            "table": table_name,
            "status": ["not in", ["Cancelled", "Paid"]],
            "docstatus": 1
        }
    )
    
    if not unpaid_orders:
        # All orders paid - table can be cleaned
        frappe.db.set_value("Restaurant Table", table_name, "status", "Cleaning")
        
        # Close active session
        active_session = frappe.get_all(
            "Table Session",
            filters={"table": table_name, "status": "Active"},
            limit=1
        )
        
        if active_session:
            frappe.db.set_value("Table Session", active_session[0].name, {
                "status": "Closed",
                "end_time": frappe.utils.now_datetime()
            })
