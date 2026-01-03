# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class POSPrinter(Document):
	def validate(self):
		if self.is_default:
			# Unset other default printers
			frappe.db.sql("""
				UPDATE `tabPOS Printer`
				SET is_default = 0
				WHERE name != %s
			""", self.name)
