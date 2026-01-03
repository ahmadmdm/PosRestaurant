# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

"""
Installation hooks for Restaurant POS
"""

import frappe
from frappe import _


def before_install():
    """Run before installation"""
    pass


def after_install():
    """Run after installation"""
    create_default_settings()
    create_custom_fields()
    create_roles()
    create_default_kitchen_stations()


def create_default_settings():
    """Create default Restaurant Settings"""
    if not frappe.db.exists("Restaurant Settings", "Restaurant Settings"):
        settings = frappe.new_doc("Restaurant Settings")
        settings.restaurant_name = "My Restaurant"
        settings.restaurant_name_ar = "مطعمي"
        settings.currency_symbol = "SAR"
        settings.tax_rate = 15
        settings.service_charge_rate = 0
        settings.enable_qr_ordering = 1
        settings.enable_waiter_calls = 1
        settings.enable_order_notifications = 1
        settings.default_language = "en"
        settings.insert(ignore_permissions=True)
        frappe.db.commit()


def create_custom_fields():
    """Create custom fields for integration with ERPNext"""
    custom_fields = {
        "POS Invoice": [
            {
                "fieldname": "custom_restaurant_order",
                "label": "Restaurant Order",
                "fieldtype": "Link",
                "options": "Restaurant Order",
                "insert_after": "customer",
                "read_only": 1
            },
            {
                "fieldname": "custom_table",
                "label": "Table",
                "fieldtype": "Link",
                "options": "Restaurant Table",
                "insert_after": "custom_restaurant_order",
                "read_only": 1
            }
        ],
        "Stock Entry": [
            {
                "fieldname": "custom_kitchen_order",
                "label": "Kitchen Order",
                "fieldtype": "Link",
                "options": "Kitchen Order",
                "insert_after": "stock_entry_type",
                "read_only": 1
            },
            {
                "fieldname": "custom_restaurant_order",
                "label": "Restaurant Order",
                "fieldtype": "Link",
                "options": "Restaurant Order",
                "insert_after": "custom_kitchen_order",
                "read_only": 1
            }
        ],
        "Employee": [
            {
                "fieldname": "custom_restaurant_section",
                "label": "Restaurant Details",
                "fieldtype": "Section Break",
                "insert_after": "employment_details"
            },
            {
                "fieldname": "custom_is_waiter",
                "label": "Is Waiter",
                "fieldtype": "Check",
                "insert_after": "custom_restaurant_section"
            },
            {
                "fieldname": "custom_is_kitchen_staff",
                "label": "Is Kitchen Staff",
                "fieldtype": "Check",
                "insert_after": "custom_is_waiter"
            },
            {
                "fieldname": "custom_kitchen_station",
                "label": "Kitchen Station",
                "fieldtype": "Link",
                "options": "Kitchen Station",
                "insert_after": "custom_is_kitchen_staff",
                "depends_on": "eval:doc.custom_is_kitchen_staff"
            },
            {
                "fieldname": "custom_assigned_areas",
                "label": "Assigned Table Areas",
                "fieldtype": "Small Text",
                "insert_after": "custom_kitchen_station",
                "depends_on": "eval:doc.custom_is_waiter",
                "description": "Comma-separated list of table areas this waiter is responsible for"
            }
        ],
        "Item": [
            {
                "fieldname": "custom_is_menu_item",
                "label": "Is Menu Item",
                "fieldtype": "Check",
                "insert_after": "is_sales_item"
            },
            {
                "fieldname": "custom_menu_category",
                "label": "Menu Category",
                "fieldtype": "Link",
                "options": "Menu Category",
                "insert_after": "custom_is_menu_item",
                "depends_on": "eval:doc.custom_is_menu_item"
            },
            {
                "fieldname": "custom_preparation_time",
                "label": "Preparation Time (minutes)",
                "fieldtype": "Int",
                "insert_after": "custom_menu_category",
                "depends_on": "eval:doc.custom_is_menu_item"
            },
            {
                "fieldname": "custom_kitchen_station",
                "label": "Kitchen Station",
                "fieldtype": "Link",
                "options": "Kitchen Station",
                "insert_after": "custom_preparation_time",
                "depends_on": "eval:doc.custom_is_menu_item"
            }
        ]
    }
    
    for doctype, fields in custom_fields.items():
        for field in fields:
            field_name = f"{doctype}-{field['fieldname']}"
            if not frappe.db.exists("Custom Field", field_name):
                custom_field = frappe.new_doc("Custom Field")
                custom_field.dt = doctype
                custom_field.module = "Restaurant Pos"
                for key, value in field.items():
                    custom_field.set(key, value)
                custom_field.insert(ignore_permissions=True)
    
    frappe.db.commit()


def create_roles():
    """Create restaurant-specific roles"""
    roles = [
        {
            "role_name": "Restaurant Manager",
            "desk_access": 1,
            "is_custom": 1
        },
        {
            "role_name": "Waiter",
            "desk_access": 1,
            "is_custom": 1
        },
        {
            "role_name": "Kitchen Staff",
            "desk_access": 1,
            "is_custom": 1
        },
        {
            "role_name": "Cashier",
            "desk_access": 1,
            "is_custom": 1
        }
    ]
    
    for role_data in roles:
        if not frappe.db.exists("Role", role_data["role_name"]):
            role = frappe.new_doc("Role")
            for key, value in role_data.items():
                role.set(key, value)
            role.insert(ignore_permissions=True)
    
    frappe.db.commit()


def create_default_kitchen_stations():
    """Create default kitchen stations"""
    stations = [
        {"station_name": "Main Kitchen", "station_name_ar": "المطبخ الرئيسي", "station_type": "Hot Kitchen"},
        {"station_name": "Cold Station", "station_name_ar": "قسم البارد", "station_type": "Cold Kitchen"},
        {"station_name": "Grill Station", "station_name_ar": "قسم الشواء", "station_type": "Grill"},
        {"station_name": "Beverages", "station_name_ar": "المشروبات", "station_type": "Beverages"},
        {"station_name": "Desserts", "station_name_ar": "الحلويات", "station_type": "Desserts"},
    ]
    
    for station_data in stations:
        if not frappe.db.exists("Kitchen Station", station_data["station_name"]):
            station = frappe.new_doc("Kitchen Station")
            for key, value in station_data.items():
                station.set(key, value)
            station.is_active = 1
            station.insert(ignore_permissions=True)
    
    frappe.db.commit()


def uninstall():
    """Clean up on uninstallation"""
    # Remove custom fields
    frappe.db.delete("Custom Field", {"module": "Restaurant Pos"})
    frappe.db.commit()
