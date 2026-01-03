# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, getdate


class MenuItem(Document):
    def validate(self):
        self.validate_pricing()
        self.validate_availability_time()
        self.update_sold_out_status()
    
    def validate_pricing(self):
        """Ensure price is valid"""
        if self.price < 0:
            frappe.throw(_("Price cannot be negative"))
        
        if self.discounted_price and self.discounted_price >= self.price:
            frappe.throw(_("Discounted price must be less than regular price"))
    
    def validate_availability_time(self):
        """Validate from/to times"""
        if self.available_from and self.available_to:
            if self.available_from >= self.available_to:
                frappe.throw(_("'Available From' must be before 'Available To'"))
    
    def update_sold_out_status(self):
        """Auto-clear sold out if past expiry"""
        if self.is_sold_out and self.sold_out_until:
            if now_datetime() > self.sold_out_until:
                self.is_sold_out = 0
                self.sold_out_until = None
    
    def is_available_now(self):
        """Check if item is available at current time"""
        if not self.is_active or self.is_sold_out:
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
        
        # Check inventory
        if self.track_inventory and self.available_qty <= 0:
            return False
        
        return True
    
    def get_display_price(self):
        """Get the current display price"""
        if self.discounted_price:
            return self.discounted_price
        return self.price
    
    def get_modifiers(self):
        """Get all modifiers for this item"""
        if not self.allow_customization or not self.modifiers:
            return []
        
        result = []
        for mod_link in self.modifiers:
            modifier = frappe.get_doc("Menu Item Modifier", mod_link.modifier)
            result.append({
                "name": modifier.name,
                "title": modifier.modifier_name,
                "title_ar": modifier.modifier_name_ar,
                "type": modifier.selection_type,
                "required": mod_link.is_required,
                "min_selections": mod_link.min_selections or 0,
                "max_selections": mod_link.max_selections or 99,
                "options": [{
                    "name": opt.name,
                    "label": opt.option_name,
                    "label_ar": opt.option_name_ar,
                    "price": opt.additional_price or 0,
                    "is_default": opt.is_default
                } for opt in modifier.options]
            })
        
        return result
    
    def deduct_inventory(self, qty=1):
        """Deduct from available quantity"""
        if not self.track_inventory:
            return True
        
        if self.available_qty < qty:
            return False
        
        self.available_qty -= qty
        self.db_set("available_qty", self.available_qty)
        
        # Check low stock
        if self.available_qty <= self.low_stock_threshold:
            self.notify_low_stock()
        
        # Auto sold out
        if self.available_qty <= 0:
            self.db_set("is_sold_out", 1)
        
        return True
    
    def notify_low_stock(self):
        """Send low stock notification"""
        frappe.publish_realtime(
            event="restaurant:low_stock",
            message={
                "item": self.name,
                "item_name": self.item_name,
                "qty": self.available_qty
            },
            room="restaurant:managers"
        )
    
    def get_nutrition_info(self):
        """Get nutrition information"""
        return {
            "calories": self.calories,
            "protein": self.protein,
            "carbs": self.carbs,
            "fat": self.fat
        }
    
    def get_allergen_list(self):
        """Get list of allergens"""
        return [a.allergen for a in self.allergens] if self.allergens else []
    
    def get_dietary_tags_list(self):
        """Get list of dietary tags"""
        return [t.tag for t in self.dietary_tags] if self.dietary_tags else []
