# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WaiterCall(Document):
    def after_insert(self):
        """Notify waiters of new call"""
        # Get table's assigned waiter
        waiter = frappe.db.get_value(
            "Restaurant Table", 
            self.restaurant_table, 
            "assigned_waiter"
        )
        
        # Send real-time notification
        frappe.publish_realtime(
            event="restaurant:waiter_call",
            message={
                "call_id": self.name,
                "table_number": self.table_number,
                "call_type": self.call_type,
                "notes": self.notes
            },
            room=f"waiters:{self.branch}"
        )
        
        # Also notify specific waiter if assigned
        if waiter:
            frappe.publish_realtime(
                event="restaurant:waiter_call",
                message={
                    "call_id": self.name,
                    "table_number": self.table_number,
                    "call_type": self.call_type,
                    "notes": self.notes,
                    "urgent": True
                },
                user=waiter
            )
