import frappe

def get_context(context):
    """Context for digital menu page"""
    table_id = frappe.form_dict.get("table")
    lang = frappe.form_dict.get("lang", "en")
    
    context.table_id = table_id
    context.lang = lang
    context.no_cache = 1
    
    # Get restaurant settings
    try:
        settings = frappe.get_cached_doc("Restaurant Settings")
        context.settings = {
            "enable_qr_ordering": settings.enable_qr_ordering,
            "enable_waiter_calls": settings.enable_waiter_calls,
            "show_item_images": settings.show_item_images,
            "show_item_description": settings.show_item_description,
            "show_item_calories": settings.show_item_calories,
            "show_item_allergens": settings.show_item_allergens,
            "currency": settings.currency or "SAR"
        }
    except Exception:
        context.settings = {}
    
    # Get table info if provided
    if table_id:
        table = frappe.db.get_value(
            "Restaurant Table",
            {"qr_code_id": table_id},
            ["name", "table_number", "branch"],
            as_dict=True
        )
        if table:
            context.table = table
    
    return context
