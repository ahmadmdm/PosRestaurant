# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

"""
Cashier API - Server-side functions for POS operations
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, now_datetime, nowdate, nowtime, getdate
import json


@frappe.whitelist()
def get_pos_data():
    """
    Get initial POS data including menu items, categories, tables, and settings
    """
    try:
        # Get user's branch (safely)
        branch = None
        try:
            user_doc = frappe.get_doc("User", frappe.session.user)
            branch = getattr(user_doc, "default_branch", None)
        except Exception:
            pass
        
        # Get settings safely
        try:
            settings = frappe.get_single("Restaurant Settings")
        except Exception:
            settings = frappe._dict()
        
        # Get categories
        categories = get_menu_categories(branch)
        
        # Get menu items
        items = get_menu_items(branch)
        
        # Get tables
        tables = get_tables(branch)
        
        # Get cashier info
        cashier_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
        
        # Get branch name safely
        branch_name = ""
        if branch:
            try:
                branch_name = frappe.db.get_value("Branch", branch, "branch") or ""
            except Exception:
                pass
        
        return {
            "success": True,
            "data": {
                "cashier_name": cashier_name,
                "branch": branch or "",
                "branch_name": branch_name,
                "categories": categories,
                "items": items,
                "tables": tables,
                "settings": {
                    "vat_percent": getattr(settings, "vat_percent", 15) or 15,
                    "service_charge_percent": getattr(settings, "service_charge_percent", 0) or 0,
                    "currency": frappe.db.get_default("currency") or "SAR",
                    "allow_discount": getattr(settings, "allow_discount", True),
                    "max_discount_percent": getattr(settings, "max_discount_percent", 100) or 100,
                    "default_order_type": "Dine In",
                    "print_kitchen_order": getattr(settings, "print_kitchen_order", True),
                    "auto_print_receipt": getattr(settings, "auto_print_receipt", False)
                }
            }
        }
    except Exception as e:
        frappe.log_error(str(e), "POS Data Error")
        return {"success": False, "message": str(e)}




@frappe.whitelist()
def void_order_item(order_id, item_row_name, reason):
    """
    Void / Cancel a specific item in a Restaurant Order (e.g. if requested by customer after KOT)
    Requires reason for auditing and kitchen updates.
    """
    try:
        order = frappe.get_doc("Restaurant Order", order_id)
        if order.payment_status == "Paid":
            return {"success": False, "message": _("Cannot void items on a paid order")}
            
        found = False
        for item in order.items:
            if item.name == item_row_name:
                item.status = "Cancelled"
                found = True
                # Custom reasoning logging could be done here (e.g., adding a comment)
                if frappe.db.exists("DocType", "Comment"):
                    frappe.get_doc({
                        "doctype": "Comment", 
                        "comment_type": "Info", 
                        "reference_doctype": "Restaurant Order", 
                        "reference_name": order.name, 
                        "content": f"Item {item.item_name} voided. Reason: {reason}"
                    }).insert(ignore_permissions=True)
                break
                
        if found:
            order.save()
            return {"success": True, "message": _("Item voided successfully")}
        else:
            return {"success": False, "message": _("Item not found in order")}
    except Exception as e:
        frappe.log_error(str(e), "Void Item Error")
        return {"success": False, "message": str(e)}

@frappe.whitelist()
def get_menu_categories(branch=None):
    """Get active menu categories"""
    try:
        filters = {"is_active": 1}
        
        # Check if branch field exists in Menu Category
        meta = frappe.get_meta("Menu Category")
        has_branch = meta.has_field("branch")
        
        if branch and has_branch:
            filters["branch"] = ["in", [branch, "", None]]
        
        categories = frappe.get_all(
            "Menu Category",
            filters=filters,
            fields=[
                "name", "category_name", "category_name_ar", 
                "parent_category", "image", "icon", "display_order"
            ],
            order_by="display_order asc, category_name asc"
        )
        
        return categories
    except Exception as e:
        frappe.log_error(str(e), "Get Menu Categories Error")
        return []


@frappe.whitelist()
def get_menu_items(branch=None, category=None, search=None):
    """Get active menu items with optional filters"""
    try:
        filters = {"is_active": 1}
        
        # Check for is_sold_out field
        meta = frappe.get_meta("Menu Item")
        if meta.has_field("is_sold_out"):
            filters["is_sold_out"] = 0
        
        if category and category != "all":
            filters["category"] = category
        
        # Build field list based on what exists
        available_fields = [f.fieldname for f in meta.fields]
        fields = ["name"]
        
        # Add fields that exist
        possible_fields = [
            "item_name", "item_name_ar", "item_code",
            "category", "price", "discounted_price", 
            "image", "thumbnail", "description", "description_ar",
            "kitchen_station", "preparation_time", "calories",
            "allow_customization", "spicy_level", "display_order"
        ]
        
        for f in possible_fields:
            if f in available_fields:
                fields.append(f)
        
        items = frappe.get_all(
            "Menu Item",
            filters=filters,
            fields=fields,
            order_by="display_order asc, item_name asc" if "display_order" in available_fields else "item_name asc"
        )
        
        # Apply search filter
        if search:
            search_lower = search.lower()
            items = [
                item for item in items 
                if search_lower in (item.get("item_name") or "").lower() 
                or search_lower in (item.get("item_name_ar") or "").lower()
                or search_lower in (item.get("item_code") or "").lower()
            ]
        
        # Get modifiers for items that allow customization
        for item in items:
            if item.get("allow_customization"):
                item["modifiers"] = get_item_modifiers(item.name)
            else:
                item["modifiers"] = []
        
        return items
    except Exception as e:
        frappe.log_error(str(e), "Get Menu Items Error")
        return []


@frappe.whitelist()
def get_item_modifiers(item_name):
    """Get modifiers for a menu item"""
    modifiers = frappe.get_all(
        "Menu Item Modifier Link",
        filters={"parent": item_name},
        fields=["modifier", "required", "display_order"],
        order_by="display_order asc"
    )
    
    result = []
    for mod in modifiers:
        modifier_doc = frappe.get_doc("Menu Item Modifier", mod.modifier)
        options = []
        
        for opt in modifier_doc.options:
            options.append({
                "name": opt.option_name,
                "name_ar": opt.option_name_ar,
                "price": opt.price or 0
            })
        
        result.append({
            "name": modifier_doc.name,
            "title": modifier_doc.modifier_name,
            "title_ar": modifier_doc.modifier_name_ar,
            "type": modifier_doc.selection_type,  # Single/Multiple
            "required": mod.required,
            "options": options
        })
    
    return result


@frappe.whitelist()
def get_tables(branch=None):
    """Get restaurant tables"""
    try:
        filters = {"enabled": 1}
        
        # Check if branch field exists
        meta = frappe.get_meta("Restaurant Table")
        has_branch = meta.has_field("branch")
        
        if branch and has_branch:
            filters["branch"] = branch
        
        # Build field list based on what exists
        available_fields = [f.fieldname for f in meta.fields]
        fields = ["name"]
        
        possible_fields = [
            "table_number", "capacity", "status",
            "section", "position_x", "position_y", "current_session"
        ]
        
        for f in possible_fields:
            if f in available_fields:
                fields.append(f)
        
        tables = frappe.get_all(
            "Restaurant Table",
            filters=filters,
            fields=fields,
            order_by="table_number asc" if "table_number" in available_fields else "name asc"
        )
        
        # Get current order info for occupied tables
        for table in tables:
            table_status = table.get("status", "")
            current_session = table.get("current_session", "")
            
            if table_status == "Occupied" and current_session:
                session_orders = frappe.get_all(
                    "Restaurant Order",
                    filters={
                        "table_session": current_session,
                        "payment_status": ["!=", "Paid"]
                    },
                    fields=["name", "grand_total", "status", "creation"],
                    order_by="creation desc",
                    limit=1
                )
                if session_orders:
                    table["current_order"] = session_orders[0]
                else:
                    table["current_order"] = None
            else:
                table["current_order"] = None
        
        return tables
    except Exception as e:
        frappe.log_error(str(e), "Get Tables Error")
        return []


@frappe.whitelist()
def create_order(order_data):
    """
    Create a new restaurant order from POS
    
    Args:
        order_data: dict containing:
            - order_type: Dine In, Takeaway, Delivery, Drive Through
            - table: table name (for Dine In)
            - customer_name: customer name
            - customer_phone: phone number
            - delivery_address: for delivery orders
            - guest_count: number of guests
            - items: list of items with modifiers
            - discount: discount info
            - notes: special instructions
    """
    try:
        if isinstance(order_data, str):
            order_data = json.loads(order_data)
        
        # Get settings
        settings = frappe.get_single("Restaurant Settings")
        try:
            branch = frappe.db.get_value("User", frappe.session.user, "branch") or frappe.db.get_value("User", frappe.session.user, "default_branch")
        except Exception:
            try:
                branch = frappe.defaults.get_user_default("branch")
                if not branch:
                    # Fallback to the first available branch if none is set for the user to avoid errors
                    branches = frappe.db.get_all("Branch", limit=1)
                    if branches:
                        branch = branches[0].name
            except Exception:
                branch = None

        
        # Calculate totals
        items = order_data.get("items", [])
        subtotal = sum(flt(item["total"]) for item in items)
        
        # Discount
        discount = order_data.get("discount", {})
        discount_amount = 0
        if discount:
            if discount.get("type") == "percent":
                discount_amount = flt(subtotal * flt(discount.get("value", 0)) / 100)
            else:
                discount_amount = flt(discount.get("value", 0))
        
        after_discount = subtotal - discount_amount
        
        # Service charge
        service_percent = flt(getattr(settings, "service_charge_percent", 0) or 0)
        service_charge = flt(after_discount * service_percent / 100)
        
        # VAT
        vat_percent = flt(getattr(settings, "vat_percent", 15) or 15)
        vat_amount = flt((after_discount + service_charge) * vat_percent / 100)
        
        grand_total = after_discount + service_charge + vat_amount
        
        # Create order document
        order = frappe.new_doc("Restaurant Order")
        order.order_type = order_data.get("order_type", "Dine In")
        if not branch:
            try:
                branch = frappe.db.get_all("Branch", limit=1)[0].name
            except: pass
        order.branch = branch
        order.status = "Draft"
        
        # Table info
        if order.order_type == "Dine In" and order_data.get("table"):
            table = order_data.get("table")
            order.restaurant_table = table
            order.table_number = frappe.db.get_value("Restaurant Table", table, "table_number")
            
            # Create or get table session
            session = get_or_create_table_session(table, order_data.get("customer_name"), order_data.get("guest_count"))
            order.table_session = session
        
        # Customer info
        order.customer_name = order_data.get("customer_name")
        order.phone = order_data.get("customer_phone")
        if order.order_type == "Delivery":
            order.delivery_address = order_data.get("delivery_address")
        
        order.guest_count = cint(order_data.get("guest_count", 1))
        
        # Financials
        order.subtotal = subtotal
        order.discount_amount = discount_amount
        order.service_charge = service_charge
        order.tax_amount = vat_amount
        order.grand_total = grand_total
        
        order.special_instructions = order_data.get("notes")
        
        # Add items
        for item in items:
            order.append("items", {
                "menu_item": item.get("menu_item"),
                "item_name": item.get("item_name"),
                "item_name_ar": item.get("item_name_ar"),
                "qty": flt(item.get("qty", 1)),
                "rate": flt(item.get("rate")),
                "amount": flt(item.get("total")),
                "modifiers": json.dumps(item.get("modifiers", [])) if item.get("modifiers") else None,
                "special_instructions": item.get("note"),
                "kitchen_station": item.get("kitchen_station")
            })
        
        # Set cashier
        order.flags.cashier = frappe.session.user
        
        order.insert()
        order.submit()
        
        # Update table status
        if order.order_type == "Dine In" and order.restaurant_table:
            frappe.db.set_value("Restaurant Table", order.restaurant_table, "status", "Occupied")
        
        frappe.db.commit()
        
        return {
            "success": True,
            "order_id": order.name,
            "message": _("Order created successfully")
        }
        
    except Exception as e:
        frappe.log_error(str(e), "Create Order Error")
        return {"success": False, "message": str(e)}


def get_or_create_table_session(table, customer_name=None, guest_count=1):
    """Get existing table session or create new one"""
    # Check for existing open session
    existing = frappe.db.get_value(
        "Table Session",
        {"table": table, "status": "Active"},
        "name"
    )
    
    if existing:
        return existing
    
    # Create new session
    session = frappe.new_doc("Table Session")
    session.table = table
    session.customer_name = customer_name
    session.guest_count = cint(guest_count)
    session.status = "Active"
    session.started_at = now_datetime()
    session.insert()
    
    # Update table with session
    frappe.db.set_value("Restaurant Table", table, "current_session", session.name)
    
    return session.name


@frappe.whitelist()
def process_payment(order_id, payment_data):
    """
    Process payment for an order
    
    Args:
        order_id: Restaurant Order ID
        payment_data: dict containing:
            - method: Cash, Card, Mobile, Split
            - amount: paid amount
            - reference: card reference number
    """
    try:
        if isinstance(payment_data, str):
            payment_data = json.loads(payment_data)
        
        order = frappe.get_doc("Restaurant Order", order_id)
        
        if order.payment_status == "Paid":
            return {"success": False, "message": _("Order already paid")}
        
        
        paid_amount = flt(payment_data.get("amount", order.grand_total))
        method = payment_data.get("method", "Cash")
        
        # Try to sync with ERPNext POS Invoice
        pos_invoice_name = None
        try:
            pos_invoice_name = create_pos_invoice_for_order(order, payment_data)
        except Exception as e:
            frappe.log_error(f"Failed to create POS Invoice: {str(e)}", "Restaurant POS Integration")
            # Continue normally for the POS even if backend fails temporarily
            pass

        # Update order
        order.payment_status = "Paid"
        order.paid_amount = paid_amount
        order.payment_method = method
        order.status = "Completed"
        order.completed_at = now_datetime()
        
        if pos_invoice_name:
            order.pos_invoice = pos_invoice_name

        
        # Save
        order.save()
        
        # Close table session if Dine In
        if order.order_type == "Dine In" and order.table_session:
            close_table_session(order.table_session, order.restaurant_table)
        
        frappe.db.commit()
        
        # Calculate change
        change = paid_amount - order.grand_total if paid_amount > order.grand_total else 0
        
        return {
            "success": True,
            "order_id": order.name,
            "change": change,
            "message": _("Payment processed successfully")
        }
        
    except Exception as e:
        frappe.log_error(str(e), "Process Payment Error")
        return {"success": False, "message": str(e)}


def close_table_session(session_name, table_name):
    """Close a table session and free the table"""
    try:
        # Close session
        frappe.db.set_value("Table Session", session_name, {
            "status": "Closed",
            "ended_at": now_datetime()
        })
        
        # Free table
        frappe.db.set_value("Restaurant Table", table_name, {
            "status": "Available",
            "current_session": None
        })
    except Exception as e:
        frappe.log_error(str(e), "Close Table Session Error")


@frappe.whitelist()
def get_pending_orders(branch=None, status=None):
    """Get pending orders for kitchen/cashier view"""
    filters = {"docstatus": 1}
    
    if branch:
        filters["branch"] = branch
    
    if status and status != "all":
        filters["status"] = status
    else:
        filters["status"] = ["in", ["New", "Confirmed", "Preparing", "Ready"]]
    
    orders = frappe.get_all(
        "Restaurant Order",
        filters=filters,
        fields=[
            "name", "order_type", "table_number", "customer_name",
            "status", "grand_total", "creation", "special_instructions"
        ],
        order_by="creation asc"
    )
    
    # Get items for each order
    for order in orders:
        items = frappe.get_all(
            "Restaurant Order Item",
            filters={"parent": order.name},
            fields=["item_name", "item_name_ar", "qty", "rate", "amount", "special_instructions"]
        )
        order["items"] = items
        
        # Calculate waiting time
        order["waiting_minutes"] = int((now_datetime() - order.creation).total_seconds() / 60)
    
    return orders



@frappe.whitelist()
def cancel_order(order_id, reason=""):
    """
    Professionally cancel an entire order.
    If KOTs are already printed, it cancels them.
    If Paid, it checks if it can cancel the POS Invoice.
    """
    try:
        order = frappe.get_doc("Restaurant Order", order_id)
        
        # Check permissions or role
        if "Restaurant Manager" not in frappe.get_roles(frappe.session.user) and "System Manager" not in frappe.get_roles(frappe.session.user):
            return {"success": False, "message": _("Only managers can cancel an existing entire order.")}
            
        # Cancel POS Invoice if generated
        if order.pos_invoice:
            pi_doc = frappe.get_doc("POS Invoice", order.pos_invoice)
            if pi_doc.docstatus == 1:
                pi_doc.cancel()
        
        # Cancel Kitchen Orders
        kots = frappe.get_all("Kitchen Order", filters={"restaurant_order": order.name, "docstatus": 1})
        for kot in kots:
            frappe.get_doc("Kitchen Order", kot.name).cancel()
            
        # Update order items and order status
        for item in order.items:
            item.status = "Cancelled"
            
        order.status = "Cancelled"
        order.payment_status = "Refunded" if order.payment_status == "Paid" else "Unpaid"
        
        # Add tracking comment
        if frappe.db.exists("DocType", "Comment") and reason:
            frappe.get_doc({
                "doctype": "Comment", 
                "comment_type": "Info", 
                "reference_doctype": "Restaurant Order", 
                "reference_name": order.name, 
                "content": f"Order Cancelled. Reason: {reason}"
            }).insert(ignore_permissions=True)
            
        order.save()
        return {"success": True, "message": _("Order cancelled successfully")}
    except Exception as e:
        frappe.log_error(str(e), "Cancel Order Error")
        return {"success": False, "message": str(e)}

@frappe.whitelist()
def update_order_status(order_id, status):
    """Update order status"""
    try:
        order = frappe.get_doc("Restaurant Order", order_id)
        
        # Validate status transition
        valid_transitions = {
            "New": ["Confirmed", "Cancelled"],
            "Confirmed": ["Preparing", "Cancelled"],
            "Preparing": ["Ready", "Cancelled"],
            "Ready": ["Served", "Cancelled"],
            "Served": ["Paid", "Completed"]
        }
        
        current = order.status
        if status not in valid_transitions.get(current, []):
            return {"success": False, "message": _("Invalid status transition")}
        
        order.status = status
        
        # Set timestamps
        if status == "Confirmed":
            order.confirmed_at = now_datetime()
        elif status == "Ready":
            order.ready_at = now_datetime()
        elif status == "Served":
            order.served_at = now_datetime()
        elif status == "Completed":
            order.completed_at = now_datetime()
        
        order.save()
        frappe.db.commit()
        
        return {"success": True, "message": _("Status updated")}
        
    except Exception as e:
        frappe.log_error(str(e), "Update Order Status Error")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_waiter_data():
    """Get data for waiter POS interface"""
    try:
        try:
            branch = frappe.db.get_value("User", frappe.session.user, "branch") or frappe.db.get_value("User", frappe.session.user, "default_branch")
        except Exception:
            try:
                branch = frappe.defaults.get_user_default("branch")
                if not branch:
                    # Fallback to the first available branch if none is set for the user to avoid errors
                    branches = frappe.db.get_all("Branch", limit=1)
                    if branches:
                        branch = branches[0].name
            except Exception:
                branch = None

        waiter_name = frappe.db.get_value("User", frappe.session.user, "full_name")
        
        # Get tables assigned to waiter or all tables
        tables = get_tables(branch)
        
        # Get categories and items
        categories = get_menu_categories(branch)
        items = get_menu_items(branch)
        
        # Get waiter's active orders
        orders = frappe.get_all(
            "Restaurant Order",
            filters={
                "branch": branch,
                "status": ["in", ["New", "Confirmed", "Preparing", "Ready", "Served"]],
                "docstatus": 1
            },
            fields=[
                "name", "order_type", "restaurant_table", "table_number",
                "customer_name", "status", "grand_total", "creation"
            ],
            order_by="creation desc",
            limit=50
        )
        
        # Get pending waiter calls
        calls = frappe.get_all(
            "Waiter Call",
            filters={
                "branch": branch,
                "status": "Pending"
            },
            fields=[
                "name", "table", "table_number", "call_type", "creation", "message"
            ],
            order_by="creation asc"
        )
        
        # Get settings
        settings = frappe.get_single("Restaurant Settings")
        
        return {
            "success": True,
            "data": {
                "waiter_name": waiter_name,
                "branch": branch,
                "tables": tables,
                "categories": categories,
                "items": items,
                "orders": orders,
                "calls": calls,
                "settings": {
                    "vat_percent": getattr(settings, "vat_percent", 15) or 15,
                    "service_charge_percent": getattr(settings, "service_charge_percent", 0) or 0,
                    "currency": frappe.db.get_default("currency") or "SAR"
                }
            }
        }
        
    except Exception as e:
        frappe.log_error(str(e), "Waiter Data Error")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def respond_to_call(call_id, response="acknowledged"):
    """Respond to a waiter call"""
    try:
        call = frappe.get_doc("Waiter Call", call_id)
        
        if call.status == "Completed":
            return {"success": False, "message": _("Call already handled")}
        
        call.status = "Completed" if response == "completed" else "Acknowledged"
        call.responded_by = frappe.session.user
        call.responded_at = now_datetime()
        call.save()
        
        frappe.db.commit()
        
        return {"success": True, "message": _("Call updated")}
        
    except Exception as e:
        frappe.log_error(str(e), "Respond to Call Error")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def hold_order(order_data, hold_name=None):
    """Hold an order for later"""
    try:
        if isinstance(order_data, str):
            order_data = json.loads(order_data)
        
        # Store in session or create held order record
        held_orders = frappe.cache().hget("held_orders", frappe.session.user) or []
        
        order_data["held_at"] = str(now_datetime())
        order_data["held_name"] = hold_name or f"Hold #{len(held_orders) + 1}"
        
        held_orders.append(order_data)
        frappe.cache().hset("held_orders", frappe.session.user, held_orders)
        
        return {
            "success": True,
            "message": _("Order held"),
            "held_count": len(held_orders)
        }
        
    except Exception as e:
        frappe.log_error(str(e), "Hold Order Error")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_held_orders():
    """Get held orders for current user"""
    try:
        held_orders = frappe.cache().hget("held_orders", frappe.session.user) or []
        return {"success": True, "orders": held_orders}
    except Exception as e:
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def recall_held_order(index):
    """Recall a held order"""
    try:
        index = cint(index)
        held_orders = frappe.cache().hget("held_orders", frappe.session.user) or []
        
        if index < 0 or index >= len(held_orders):
            return {"success": False, "message": _("Invalid order index")}
        
        order = held_orders.pop(index)
        frappe.cache().hset("held_orders", frappe.session.user, held_orders)
        
        return {"success": True, "order": order}
        
    except Exception as e:
        frappe.log_error(str(e), "Recall Held Order Error")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def search_customer(query):
    """Search for customers"""
    if not query or len(query) < 2:
        return []
    
    customers = frappe.get_all(
        "Customer",
        filters={
            "disabled": 0
        },
        or_filters={
            "customer_name": ["like", f"%{query}%"],
            "mobile_no": ["like", f"%{query}%"]
        },
        fields=["name", "customer_name", "mobile_no", "email_id"],
        limit=10
    )
    
    return customers


@frappe.whitelist()
def add_items_to_order(order_id, items):
    """Add more items to an existing order"""
    try:
        if isinstance(items, str):
            items = json.loads(items)
        
        order = frappe.get_doc("Restaurant Order", order_id)
        
        if order.status in ["Paid", "Completed", "Cancelled"]:
            return {"success": False, "message": _("Cannot add items to this order")}
        
        # Add items
        items_total = 0
        for item in items:
            items_total += flt(item.get("total", 0))
            order.append("items", {
                "menu_item": item.get("menu_item"),
                "item_name": item.get("item_name"),
                "item_name_ar": item.get("item_name_ar"),
                "qty": flt(item.get("qty", 1)),
                "rate": flt(item.get("rate")),
                "amount": flt(item.get("total")),
                "modifiers": json.dumps(item.get("modifiers", [])) if item.get("modifiers") else None,
                "special_instructions": item.get("note"),
                "kitchen_station": item.get("kitchen_station")
            })
        
        # Recalculate totals
        settings = frappe.get_single("Restaurant Settings")
        
        subtotal = sum(flt(item.amount) for item in order.items)
        after_discount = subtotal - flt(order.discount_amount)
        
        service_percent = flt(getattr(settings, "service_charge_percent", 0) or 0)
        service_charge = flt(after_discount * service_percent / 100)
        
        vat_percent = flt(getattr(settings, "vat_percent", 15) or 15)
        vat_amount = flt((after_discount + service_charge) * vat_percent / 100)
        
        order.subtotal = subtotal
        order.service_charge = service_charge
        order.tax_amount = vat_amount
        order.grand_total = after_discount + service_charge + vat_amount
        
        order.save()
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _("Items added successfully"),
            "new_total": order.grand_total
        }
        
    except Exception as e:
        frappe.log_error(str(e), "Add Items Error")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_order_details(order_id):
    """Get full order details"""
    try:
        order = frappe.get_doc("Restaurant Order", order_id)
        
        items = []
        for item in order.items:
            items.append({
                "name": item.name,
                "menu_item": item.menu_item,
                "item_name": item.item_name,
                "item_name_ar": item.item_name_ar,
                "qty": item.qty,
                "rate": item.rate,
                "amount": item.amount,
                "modifiers": json.loads(item.modifiers) if item.modifiers else [],
                "special_instructions": item.special_instructions
            })
        
        return {
            "success": True,
            "order": {
                "name": order.name,
                "order_type": order.order_type,
                "table": order.restaurant_table,
                "table_number": order.table_number,
                "customer_name": order.customer_name,
                "phone": order.phone,
                "guest_count": order.guest_count,
                "status": order.status,
                "payment_status": order.payment_status,
                "subtotal": order.subtotal,
                "discount_amount": order.discount_amount,
                "service_charge": order.service_charge,
                "tax_amount": order.tax_amount,
                "grand_total": order.grand_total,
                "special_instructions": order.special_instructions,
                "creation": order.creation,
                "items": items
            }
        }
        
    except Exception as e:
        frappe.log_error(str(e), "Get Order Details Error")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def transfer_table(from_table, to_table):
    """Transfer orders from one table to another"""
    try:
        # Get current session from source table
        session = frappe.db.get_value("Restaurant Table", from_table, "current_session")
        
        if not session:
            return {"success": False, "message": _("No active session on source table")}
        
        # Check if destination table is available
        to_status = frappe.db.get_value("Restaurant Table", to_table, "status")
        if to_status != "Available":
            return {"success": False, "message": _("Destination table is not available")}
        
        # Update session with new table
        frappe.db.set_value("Table Session", session, "table", to_table)
        
        # Update orders
        orders = frappe.get_all(
            "Restaurant Order",
            filters={"table_session": session},
            fields=["name"]
        )
        
        to_table_number = frappe.db.get_value("Restaurant Table", to_table, "table_number")
        
        for order in orders:
            frappe.db.set_value("Restaurant Order", order.name, {
                "restaurant_table": to_table,
                "table_number": to_table_number
            })
        
        # Update source table - free it
        frappe.db.set_value("Restaurant Table", from_table, {
            "status": "Available",
            "current_session": None
        })
        
        # Update destination table - occupy it
        frappe.db.set_value("Restaurant Table", to_table, {
            "status": "Occupied",
            "current_session": session
        })
        
        frappe.db.commit()
        
        return {"success": True, "message": _("Table transferred successfully")}
        
    except Exception as e:
        frappe.log_error(str(e), "Transfer Table Error")
        return {"success": False, "message": str(e)}
