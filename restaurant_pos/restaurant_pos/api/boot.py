# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def get_boot_info(bootinfo):
    """Add restaurant-specific info to boot"""
    if frappe.session.user == "Guest":
        return
    
    bootinfo.restaurant_pos = {
        "version": "1.0.0",
        "settings": get_restaurant_settings(),
        "user_roles": get_user_restaurant_roles(),
        "kitchen_stations": get_user_kitchen_stations(),
    }


def get_restaurant_settings():
    """Get restaurant settings for current user"""
    try:
        settings = frappe.get_single("Restaurant Settings")
        return {
            "enable_qr_ordering": settings.enable_qr_ordering,
            "enable_kitchen_display": settings.enable_kitchen_display,
            "enable_call_waiter": settings.enable_call_waiter,
            "default_language": settings.default_language,
            "session_timeout_minutes": settings.session_timeout_minutes,
            "currency": frappe.defaults.get_global_default("currency"),
            "currency_symbol": frappe.db.get_value("Currency", 
                frappe.defaults.get_global_default("currency"), "symbol") or "",
        }
    except Exception:
        return {}


def get_user_restaurant_roles():
    """Get restaurant-specific roles for current user"""
    user_roles = frappe.get_roles()
    restaurant_roles = [
        "Restaurant Manager",
        "Waiter",
        "Kitchen Staff",
        "Cashier",
        "Kitchen Display"
    ]
    return [r for r in restaurant_roles if r in user_roles]


def get_user_kitchen_stations():
    """Get kitchen stations assigned to current user"""
    try:
        stations = frappe.get_all(
            "Kitchen Station User",
            filters={"user": frappe.session.user},
            fields=["parent as station"]
        )
        return [s.station for s in stations]
    except Exception:
        return []
