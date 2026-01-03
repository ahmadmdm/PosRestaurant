# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class RestaurantSettings(Document):
    def validate(self):
        if self.min_order_amount and self.min_order_amount < 0:
            frappe.throw("Minimum order amount cannot be negative")
        
        if self.service_charge_percent and self.service_charge_percent > 100:
            frappe.throw("Service charge cannot exceed 100%")
    
    @staticmethod
    def get_settings():
        """Get restaurant settings as dict"""
        return frappe.get_cached_doc("Restaurant Settings")
