import frappe

def get_context(context):
    """Context for Kitchen Display page"""
    station = frappe.form_dict.get("station")
    branch = frappe.form_dict.get("branch")
    
    context.station = station
    context.branch = branch
    context.no_cache = 1
    
    # Get station name
    if station:
        station_doc = frappe.db.get_value(
            "Kitchen Station",
            station,
            ["station_name", "station_name_ar", "color"],
            as_dict=True
        )
        if station_doc:
            context.station_name = station_doc.station_name
            context.station_color = station_doc.color
    
    # Get settings
    try:
        settings = frappe.get_cached_doc("Restaurant Settings")
        context.settings = {
            "kds_refresh_interval": settings.kds_refresh_interval or 5,
            "kds_columns": settings.kds_columns or 4,
            "kds_sound_enabled": settings.kds_sound_enabled,
            "kot_alert_time": settings.kot_alert_time or 10
        }
    except Exception:
        context.settings = {
            "kds_refresh_interval": 5,
            "kds_columns": 4,
            "kds_sound_enabled": True,
            "kot_alert_time": 10
        }
    
    return context
