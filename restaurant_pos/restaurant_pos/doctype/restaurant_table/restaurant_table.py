# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
import hashlib
import qrcode
from io import BytesIO
import base64


class RestaurantTable(Document):
    def before_insert(self):
        self.generate_qr_code()
    
    def validate(self):
        self.validate_capacity()
    
    def validate_capacity(self):
        if self.capacity and self.capacity < 1:
            frappe.throw(_("Table capacity must be at least 1"))
    
    def generate_qr_code(self):
        """Generate unique QR code for this table"""
        # Generate unique ID
        unique_string = f"{self.branch}-{self.table_number}-{frappe.utils.now()}"
        self.qr_code_id = hashlib.sha256(unique_string.encode()).hexdigest()[:16]
        
        # Generate QR code image
        try:
            settings = frappe.get_cached_doc("Restaurant Settings")
            base_url = settings.qr_code_base_url or frappe.utils.get_url()
            
            qr_url = f"{base_url}/menu?table={self.qr_code_id}"
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Save to file
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            
            # Save as attachment
            file_name = f"table_qr_{self.table_number}.png"
            file_doc = frappe.get_doc({
                "doctype": "File",
                "file_name": file_name,
                "content": buffer.read(),
                "attached_to_doctype": "Restaurant Table",
                "attached_to_name": self.name,
                "is_private": 0
            })
            file_doc.save(ignore_permissions=True)
            
            self.qr_code_image = file_doc.file_url
            
        except Exception as e:
            frappe.log_error(f"QR Code Generation Error: {str(e)}", "Restaurant POS")
    
    def regenerate_qr_code(self):
        """Regenerate QR code (e.g., if compromised)"""
        self.generate_qr_code()
        self.save()
    
    def get_current_guests(self):
        """Get current guest count"""
        if self.current_session:
            return frappe.db.get_value("Table Session", self.current_session, "guest_count")
        return 0
    
    def is_available(self):
        """Check if table is available"""
        return self.status == "Available"
    
    def seat_guests(self, guest_count, waiter=None):
        """Seat guests at this table"""
        if not self.is_available():
            frappe.throw(_("Table is not available"))
        
        # Create session
        session = frappe.get_doc({
            "doctype": "Table Session",
            "restaurant_table": self.name,
            "table_number": self.table_number,
            "branch": self.branch,
            "guest_count": guest_count,
            "waiter": waiter or frappe.session.user,
            "started_at": frappe.utils.now_datetime(),
            "status": "Active"
        })
        session.insert(ignore_permissions=True)
        
        # Update table
        self.status = "Occupied"
        self.current_session = session.name
        if waiter:
            self.assigned_waiter = waiter
        self.save(ignore_permissions=True)
        
        return session
    
    def close_table(self):
        """Close table and end session"""
        if self.current_session:
            frappe.db.set_value(
                "Table Session",
                self.current_session,
                {
                    "status": "Closed",
                    "ended_at": frappe.utils.now_datetime()
                }
            )
        
        self.status = "Available"
        self.current_order = None
        self.current_session = None
        self.save(ignore_permissions=True)


@frappe.whitelist()
def regenerate_qr(table_name):
    """API to regenerate QR code"""
    table = frappe.get_doc("Restaurant Table", table_name)
    table.regenerate_qr_code()
    return {"success": True, "qr_code_id": table.qr_code_id}
