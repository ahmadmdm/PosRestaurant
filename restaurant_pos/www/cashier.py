# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

"""
POS Cashier Page Controller
Main cashier interface for restaurant orders
"""

import frappe
from frappe import _


def get_context(context):
    """Build context for the POS Cashier page"""
    
    # Check if user is logged in and has permission
    if frappe.session.user == "Guest":
        frappe.throw(_("Please login to access POS"), frappe.PermissionError)
    
    # Check for POS User or System Manager role
    user_roles = frappe.get_roles()
    allowed_roles = ["System Manager", "POS User", "Restaurant Manager", "Cashier"]
    
    if not any(role in user_roles for role in allowed_roles):
        frappe.throw(_("You don't have permission to access POS"), frappe.PermissionError)
    
    # Get user's branch (safely check if field exists)
    branch = ""
    try:
        user_doc = frappe.get_doc("User", frappe.session.user)
        branch = getattr(user_doc, "default_branch", "") or ""
    except Exception:
        pass
    
    # Get settings
    try:
        settings = frappe.get_single("Restaurant Settings")
    except Exception:
        settings = frappe._dict()
    
    context.no_cache = 1
    context.show_sidebar = False
    context.branch = branch
    context.settings = settings
    
    # Add page title
    context.title = _("POS Cashier")
    
    return context
