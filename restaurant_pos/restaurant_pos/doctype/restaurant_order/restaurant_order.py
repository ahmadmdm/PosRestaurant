# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, flt


class RestaurantOrder(Document):
    def validate(self):
        self.calculate_totals()
    
    def before_submit(self):
        if not self.items:
            frappe.throw(_("Order must have at least one item"))
    
    def on_update(self):
        self.update_table_status()
    
    def calculate_totals(self):
        """Calculate order totals"""
        self.total_qty = 0
        self.subtotal = 0
        
        for item in self.items:
            item.amount = flt(item.rate) * flt(item.qty)
            self.total_qty += flt(item.qty)
            self.subtotal += flt(item.amount)
        
        # Apply service charge
        settings = frappe.get_cached_doc("Restaurant Settings")
        if settings.service_charge_percent:
            self.service_charge = flt(self.subtotal) * flt(settings.service_charge_percent) / 100
        else:
            self.service_charge = 0
        
        # Calculate tax (simplified - you may want to use tax templates)
        self.tax_amount = self.calculate_tax()
        
        # Calculate grand total
        self.grand_total = (
            flt(self.subtotal) +
            flt(self.tax_amount) +
            flt(self.service_charge) +
            flt(self.tip_amount) -
            flt(self.discount_amount)
        )
    
    def calculate_tax(self):
        """Calculate tax amount"""
        # Simplified tax calculation
        # For production, use Item Tax Templates
        total_tax = 0
        for item in self.items:
            if item.tax_rate:
                total_tax += flt(item.amount) * flt(item.tax_rate) / 100
        return total_tax
    
    def update_table_status(self):
        """Update table with current order"""
        if self.restaurant_table and self.status not in ["Cancelled", "Completed", "Paid"]:
            frappe.db.set_value(
                "Restaurant Table",
                self.restaurant_table,
                "current_order",
                self.name
            )
    
    def confirm_order(self):
        """Confirm order and send to kitchen"""
        if self.status != "Draft":
            frappe.throw(_("Only draft orders can be confirmed"))
        
        self.status = "Confirmed"
        self.confirmed_at = now_datetime()
        self.save(ignore_permissions=True)
        
        # Create kitchen orders
        self.create_kitchen_orders()
        
        # Notify kitchen
        frappe.publish_realtime(
            event="restaurant:new_order",
            message={
                "order_id": self.name,
                "table_number": self.table_number,
                "order_type": self.order_type
            },
            room=f"kitchen:{self.branch}"
        )
        
        return True
    
    def create_kitchen_orders(self):
        """Create Kitchen Order Tickets (KOTs) grouped by station"""
        # Group items by kitchen station
        station_items = {}
        
        for item in self.items:
            if item.status in ["Pending", "Sent to Kitchen"]:
                menu_item = frappe.get_doc("Menu Item", item.menu_item)
                station = menu_item.kitchen_station or frappe.db.get_single_value(
                    "Restaurant Settings", "default_kitchen_station"
                )
                
                if station not in station_items:
                    station_items[station] = []
                
                station_items[station].append(item)
        
        # Create KOT for each station
        for station, items in station_items.items():
            kot = frappe.get_doc({
                "doctype": "Kitchen Order",
                "restaurant_order": self.name,
                "restaurant_table": self.restaurant_table,
                "table_number": self.table_number,
                "order_type": self.order_type,
                "branch": self.branch,
                "kitchen_station": station,
                "status": "New",
                "notes": self.special_instructions,
                "items": []
            })
            
            for item in items:
                kot.append("items", {
                    "order_item": item.name,
                    "menu_item": item.menu_item,
                    "item_name": item.item_name,
                    "item_name_ar": item.item_name_ar,
                    "qty": item.qty,
                    "modifiers": item.modifiers,
                    "special_instructions": item.special_instructions,
                    "status": "Pending"
                })
                
                # Update item status
                item.status = "Sent to Kitchen"
                item.db_update()
            
            kot.insert(ignore_permissions=True)
            
            # Auto print KOT
            settings = frappe.get_cached_doc("Restaurant Settings")
            if settings.auto_print_kot:
                self.print_kot(kot.name)
        
        frappe.db.commit()
    
    def print_kot(self, kot_name):
        """Print Kitchen Order Ticket"""
        try:
            # Get print format
            kot = frappe.get_doc("Kitchen Order", kot_name)
            
            # This would integrate with your printer setup
            # For now, just log it
            frappe.log_error(f"Print KOT: {kot_name}", "Restaurant POS - Print")
            
        except Exception as e:
            frappe.log_error(f"KOT Print Error: {str(e)}", "Restaurant POS")
    
    def add_items(self, new_items):
        """Add items to existing order"""
        for item_data in new_items:
            self.append("items", {
                "menu_item": item_data.get("menu_item"),
                "item_name": item_data.get("item_name"),
                "item_name_ar": item_data.get("item_name_ar"),
                "qty": item_data.get("qty", 1),
                "rate": item_data.get("rate"),
                "modifiers": item_data.get("modifiers"),
                "special_instructions": item_data.get("special_instructions"),
                "status": "Pending"
            })
        
        self.calculate_totals()
        self.save(ignore_permissions=True)
        
        # If order was already confirmed, send new items to kitchen
        if self.status in ["Confirmed", "Preparing", "Ready"]:
            self.create_kitchen_orders()
    
    def mark_ready(self):
        """Mark order as ready"""
        self.status = "Ready"
        self.ready_at = now_datetime()
        self.save(ignore_permissions=True)
        
        # Notify waiter
        frappe.publish_realtime(
            event="restaurant:order_ready",
            message={
                "order_id": self.name,
                "table_number": self.table_number
            },
            room=f"waiters:{self.branch}"
        )
    
    def mark_served(self):
        """Mark order as served"""
        self.status = "Served"
        self.served_at = now_datetime()
        self.save(ignore_permissions=True)
    
    def process_payment(self, amount, method):
        """Process payment"""
        self.paid_amount = flt(self.paid_amount) + flt(amount)
        self.payment_method = method
        
        if self.paid_amount >= self.grand_total:
            self.payment_status = "Paid"
            self.status = "Paid"
        elif self.paid_amount > 0:
            self.payment_status = "Partially Paid"
        
        self.save(ignore_permissions=True)
        
        return True
    
    def complete_order(self):
        """Complete order and close table"""
        self.status = "Completed"
        self.completed_at = now_datetime()
        self.save(ignore_permissions=True)
        
        # Close table
        if self.restaurant_table:
            table = frappe.get_doc("Restaurant Table", self.restaurant_table)
            table.close_table()
    
    def cancel_order(self, reason=None):
        """Cancel order"""
        self.status = "Cancelled"
        if reason:
            self.internal_notes = (self.internal_notes or "") + f"\nCancellation reason: {reason}"
        self.save(ignore_permissions=True)
        
        # Cancel all kitchen orders
        kots = frappe.get_all(
            "Kitchen Order",
            filters={"restaurant_order": self.name},
            pluck="name"
        )
        for kot_name in kots:
            frappe.db.set_value("Kitchen Order", kot_name, "status", "Cancelled")
        
        # Free up table
        if self.restaurant_table:
            frappe.db.set_value(
                "Restaurant Table",
                self.restaurant_table,
                {
                    "status": "Available",
                    "current_order": None
                }
            )
        
        frappe.db.commit()
