# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class MenuCategory(Document):
    def validate(self):
        self.validate_circular_reference()
        self.validate_availability_time()
    
    def validate_circular_reference(self):
        """Prevent circular parent-child relationships"""
        if self.parent_category:
            parent = self.parent_category
            visited = set([self.name])
            
            while parent:
                if parent in visited:
                    frappe.throw(f"Circular reference detected: {parent}")
                visited.add(parent)
                parent = frappe.db.get_value("Menu Category", parent, "parent_category")
    
    def validate_availability_time(self):
        """Validate from/to times"""
        if self.available_from and self.available_to:
            if self.available_from >= self.available_to:
                frappe.throw("'Available From' must be before 'Available To'")
    
    def is_available_now(self):
        """Check if category is available at current time"""
        if not self.is_active:
            return False
        
        now = now_datetime()
        current_time = now.time()
        current_day = now.strftime("%A")
        
        # Check day availability
        if self.available_days:
            available_days = [d.day for d in self.available_days]
            if current_day not in available_days:
                return False
        
        # Check time availability
        if self.available_from and current_time < self.available_from:
            return False
        if self.available_to and current_time > self.available_to:
            return False
        
        return True
    
    def get_items(self, include_inactive=False):
        """Get all items in this category"""
        filters = {"category": self.name}
        if not include_inactive:
            filters["is_active"] = 1
        
        return frappe.get_all(
            "Menu Item",
            filters=filters,
            fields=["name", "item_name", "item_name_ar", "price", "image"],
            order_by="display_order asc"
        )
