# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class KitchenOrder(Document):
    def validate(self):
        if not self.items:
            frappe.throw(_("Kitchen order must have at least one item"))
    
    def on_update(self):
        self.update_order_status()
    
    def update_order_status(self):
        """Update main restaurant order status based on KOT status"""
        from restaurant_pos.api.kitchen import update_restaurant_order_status
        update_restaurant_order_status(self.restaurant_order)
    
    def start_preparation(self):
        """Start preparing this KOT"""
        self.status = "Preparing"
        self.started_at = now_datetime()
        
        for item in self.items:
            if item.status == "Pending":
                item.status = "Preparing"
                item.started_at = now_datetime()
        
        self.save(ignore_permissions=True)
        
        # Notify kitchen display
        frappe.publish_realtime(
            event="restaurant:kot_started",
            message={
                "kot_id": self.name,
                "table_number": self.table_number,
                "station": self.kitchen_station
            },
            room=f"kitchen:{self.branch}"
        )
    
    def mark_ready(self):
        """Mark KOT as ready"""
        self.status = "Ready"
        self.completed_at = now_datetime()
        
        for item in self.items:
            if item.status != "Ready":
                item.status = "Ready"
                item.completed_at = now_datetime()
        
        self.save(ignore_permissions=True)
        
        # Update order items
        for item in self.items:
            if item.order_item:
                frappe.db.set_value(
                    "Restaurant Order Item",
                    item.order_item,
                    "status",
                    "Ready"
                )
        
        # Notify waiters
        frappe.publish_realtime(
            event="restaurant:order_ready",
            message={
                "kot_id": self.name,
                "order_id": self.restaurant_order,
                "table_number": self.table_number,
                "station": self.kitchen_station
            },
            room=f"waiters:{self.branch}"
        )
    
    def mark_served(self):
        """Mark KOT as served"""
        self.status = "Served"
        self.served_at = now_datetime()
        
        for item in self.items:
            item.status = "Served"
        
        self.save(ignore_permissions=True)
        
        # Update order items
        for item in self.items:
            if item.order_item:
                frappe.db.set_value(
                    "Restaurant Order Item",
                    item.order_item,
                    "status",
                    "Served"
                )
    
    def get_preparation_time(self):
        """Get preparation time in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0
    
    def get_elapsed_time(self):
        """Get time since creation"""
        return (now_datetime() - self.creation).total_seconds()
