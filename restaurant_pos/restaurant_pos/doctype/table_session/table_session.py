# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class TableSession(Document):
    def before_save(self):
        if self.status == "Closed" and self.started_at and self.ended_at:
            duration = (self.ended_at - self.started_at).total_seconds() / 60
            self.duration_minutes = int(duration)
    
    def close_session(self):
        """Close the session"""
        self.status = "Closed"
        self.ended_at = now_datetime()
        self.save(ignore_permissions=True)
