# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

"""
Waiter POS Page Controller
Mobile-friendly POS interface for waiters
"""

import frappe
from frappe import _


def get_context(context):
    """Build context for the Waiter POS page"""
    
    # Check if user is logged in
    if frappe.session.user == "Guest":
        frappe.throw(_("Please login to access Waiter POS"), frappe.PermissionError)
    
    # Check for Waiter or Restaurant role
    user_roles = frappe.get_roles()
    allowed_roles = ["System Manager", "Waiter", "Restaurant Manager", "POS User"]
    
    if not any(role in user_roles for role in allowed_roles):
        frappe.throw(_("You don't have permission to access Waiter POS"), frappe.PermissionError)
    
    # Get user's branch and name (safely check if fields exist)
    branch = ""
    waiter_name = frappe.session.user
    try:
        user_doc = frappe.get_doc("User", frappe.session.user)
        branch = getattr(user_doc, "default_branch", "") or ""
        waiter_name = user_doc.full_name or frappe.session.user
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
    context.waiter_name = waiter_name
    context.settings = settings
    
    # Add page title
    context.title = _("Waiter POS")
    
    return context
