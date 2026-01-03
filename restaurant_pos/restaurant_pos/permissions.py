# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

"""
Permission functions for Restaurant POS
"""

import frappe
from frappe import _


def has_restaurant_permission(doctype, doc=None, ptype="read", user=None):
    """Check restaurant-specific permissions"""
    if not user:
        user = frappe.session.user
    
    # Admins have full access
    if "System Manager" in frappe.get_roles(user) or "Restaurant Manager" in frappe.get_roles(user):
        return True
    
    # Check role-based permissions
    user_roles = frappe.get_roles(user)
    
    if doctype == "Restaurant Order":
        return has_order_permission(doc, ptype, user, user_roles)
    
    elif doctype == "Kitchen Order":
        return has_kitchen_order_permission(doc, ptype, user, user_roles)
    
    elif doctype == "Restaurant Table":
        return has_table_permission(doc, ptype, user, user_roles)
    
    elif doctype == "Waiter Call":
        return has_waiter_call_permission(doc, ptype, user, user_roles)
    
    return True


def has_order_permission(doc, ptype, user, user_roles):
    """Check permissions for Restaurant Order"""
    # Waiters can view and create orders
    if "Waiter" in user_roles:
        if ptype in ["read", "create"]:
            return True
        
        # Can only modify their own orders
        if ptype in ["write", "submit"] and doc:
            return doc.get("waiter") == user or doc.get("owner") == user
    
    # Cashiers can view and process payments
    if "Cashier" in user_roles:
        if ptype in ["read", "write"]:
            return True
    
    # Kitchen staff read-only
    if "Kitchen Staff" in user_roles:
        return ptype == "read"
    
    return False


def has_kitchen_order_permission(doc, ptype, user, user_roles):
    """Check permissions for Kitchen Order"""
    # Kitchen staff can read and update
    if "Kitchen Staff" in user_roles:
        if ptype in ["read", "write"]:
            return True
        
        # Check station assignment
        if doc and doc.get("station"):
            # Get user's assigned station
            user_station = get_user_kitchen_station(user)
            if user_station and user_station != doc.get("station"):
                return False
        
        return True
    
    # Waiters can only read
    if "Waiter" in user_roles:
        return ptype == "read"
    
    return False


def has_table_permission(doc, ptype, user, user_roles):
    """Check permissions for Restaurant Table"""
    # Everyone can read
    if ptype == "read":
        return True
    
    # Waiters can modify table status
    if "Waiter" in user_roles:
        if ptype == "write" and doc:
            # Check if assigned to this area
            user_areas = get_user_assigned_areas(user)
            if user_areas and doc.get("area") not in user_areas:
                return False
        return True
    
    return False


def has_waiter_call_permission(doc, ptype, user, user_roles):
    """Check permissions for Waiter Call"""
    # Waiters can view and respond to calls
    if "Waiter" in user_roles:
        if ptype == "read":
            return True
        
        if ptype == "write" and doc:
            # Can respond to calls in their area
            if doc.get("table"):
                table = frappe.get_cached_doc("Restaurant Table", doc.get("table"))
                user_areas = get_user_assigned_areas(user)
                if user_areas and table.area not in user_areas:
                    return False
        
        return True
    
    return False


def get_user_kitchen_station(user):
    """Get the kitchen station assigned to a user"""
    # Check employee link
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    
    if employee:
        return frappe.db.get_value("Employee", employee, "custom_kitchen_station")
    
    return None


def get_user_assigned_areas(user):
    """Get restaurant areas assigned to a user (waiter)"""
    # Check employee link
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    
    if not employee:
        return None
    
    # Get assigned areas from custom field
    areas = frappe.db.get_value("Employee", employee, "custom_assigned_areas")
    
    if areas:
        return [a.strip() for a in areas.split(",")]
    
    return None


def get_permission_query_conditions(user=None):
    """Return SQL conditions for filtering records based on permissions"""
    if not user:
        user = frappe.session.user
    
    # Admins see everything
    if "System Manager" in frappe.get_roles(user) or "Restaurant Manager" in frappe.get_roles(user):
        return ""
    
    return None


def get_order_permission_query_conditions(user=None):
    """Permission query for Restaurant Order"""
    if not user:
        user = frappe.session.user
    
    roles = frappe.get_roles(user)
    
    if "System Manager" in roles or "Restaurant Manager" in roles:
        return ""
    
    if "Waiter" in roles:
        return f"(`tabRestaurant Order`.waiter = {frappe.db.escape(user)} OR `tabRestaurant Order`.owner = {frappe.db.escape(user)})"
    
    if "Cashier" in roles or "Kitchen Staff" in roles:
        return ""
    
    return "1=0"  # No access


def get_kitchen_order_permission_query_conditions(user=None):
    """Permission query for Kitchen Order"""
    if not user:
        user = frappe.session.user
    
    roles = frappe.get_roles(user)
    
    if "System Manager" in roles or "Restaurant Manager" in roles:
        return ""
    
    if "Kitchen Staff" in roles:
        station = get_user_kitchen_station(user)
        if station:
            return f"`tabKitchen Order`.station = {frappe.db.escape(station)}"
        return ""
    
    if "Waiter" in roles:
        return ""
    
    return "1=0"


def validate_table_access(table_name, user=None):
    """Validate if user can access a table"""
    if not user:
        user = frappe.session.user
    
    if "System Manager" in frappe.get_roles(user) or "Restaurant Manager" in frappe.get_roles(user):
        return True
    
    if "Waiter" in frappe.get_roles(user):
        table = frappe.get_doc("Restaurant Table", table_name)
        user_areas = get_user_assigned_areas(user)
        
        if user_areas and table.area not in user_areas:
            return False
    
    return True
