# Copyright (c) 2026, Ahmad and contributors
# For license information, please see license.txt

"""
Scheduled tasks for Restaurant POS
"""

import frappe
from frappe import _
from frappe.utils import now_datetime, add_to_date, get_datetime, time_diff_in_seconds


def all():
    """Tasks to run every minute"""
    check_stale_orders()
    check_abandoned_carts()


def hourly():
    """Tasks to run every hour"""
    update_table_statistics()
    clean_expired_sessions()


def daily():
    """Tasks to run daily"""
    generate_daily_report()
    archive_old_orders()
    reset_daily_counters()


def weekly():
    """Tasks to run weekly"""
    generate_weekly_report()
    cleanup_old_data()


def monthly():
    """Tasks to run monthly"""
    generate_monthly_report()


def check_stale_orders():
    """Check for orders that have been pending too long"""
    settings = frappe.get_single("Restaurant Settings")
    stale_threshold = settings.get("stale_order_minutes") or 30
    
    threshold_time = add_to_date(now_datetime(), minutes=-stale_threshold)
    
    stale_orders = frappe.get_all(
        "Kitchen Order",
        filters={
            "status": ["in", ["Pending", "Preparing"]],
            "creation": ["<", threshold_time],
            "docstatus": 1
        },
        fields=["name", "restaurant_order", "station", "creation"]
    )
    
    for order in stale_orders:
        # Send alert
        frappe.publish_realtime(
            "stale_order_alert",
            {
                "kitchen_order": order.name,
                "restaurant_order": order.restaurant_order,
                "station": order.station,
                "wait_time": int(time_diff_in_seconds(now_datetime(), get_datetime(order.creation)) / 60)
            },
            room=f"kitchen_{order.station}"
        )


def check_abandoned_carts():
    """Check for abandoned customer sessions"""
    settings = frappe.get_single("Restaurant Settings")
    abandon_threshold = settings.get("cart_abandon_minutes") or 60
    
    threshold_time = add_to_date(now_datetime(), minutes=-abandon_threshold)
    
    # Find sessions with no recent activity
    stale_sessions = frappe.get_all(
        "Table Session",
        filters={
            "status": "Active",
            "modified": ["<", threshold_time]
        },
        fields=["name", "table"]
    )
    
    for session in stale_sessions:
        # Check if there are unpaid orders
        unpaid_orders = frappe.get_all(
            "Restaurant Order",
            filters={
                "table": session.table,
                "status": ["not in", ["Paid", "Cancelled"]],
                "docstatus": 1
            }
        )
        
        if not unpaid_orders:
            # Close abandoned session
            frappe.db.set_value("Table Session", session.name, {
                "status": "Abandoned",
                "end_time": now_datetime()
            })
            
            # Free up table
            frappe.db.set_value("Restaurant Table", session.table, {
                "status": "Available",
                "current_guests": 0
            })


def update_table_statistics():
    """Update table usage statistics"""
    tables = frappe.get_all("Restaurant Table", fields=["name"])
    
    today = now_datetime().replace(hour=0, minute=0, second=0)
    
    for table in tables:
        # Count sessions today
        sessions_today = frappe.db.count(
            "Table Session",
            filters={
                "table": table.name,
                "start_time": [">=", today]
            }
        )
        
        # Calculate average session duration
        completed_sessions = frappe.get_all(
            "Table Session",
            filters={
                "table": table.name,
                "status": "Closed",
                "start_time": [">=", today]
            },
            fields=["start_time", "end_time"]
        )
        
        total_duration = 0
        for session in completed_sessions:
            if session.end_time and session.start_time:
                duration = time_diff_in_seconds(session.end_time, session.start_time)
                total_duration += duration
        
        avg_duration = total_duration / len(completed_sessions) if completed_sessions else 0
        
        # Update stats (store in custom fields or separate table)
        frappe.cache().hset("table_stats", table.name, {
            "sessions_today": sessions_today,
            "avg_duration_minutes": int(avg_duration / 60)
        })


def clean_expired_sessions():
    """Clean up expired table sessions"""
    # Sessions older than 24 hours that are still active
    threshold = add_to_date(now_datetime(), hours=-24)
    
    expired_sessions = frappe.get_all(
        "Table Session",
        filters={
            "status": "Active",
            "start_time": ["<", threshold]
        }
    )
    
    for session in expired_sessions:
        frappe.db.set_value("Table Session", session.name, {
            "status": "Expired",
            "end_time": now_datetime()
        })


def generate_daily_report():
    """Generate daily sales report"""
    today = now_datetime().replace(hour=0, minute=0, second=0)
    yesterday = add_to_date(today, days=-1)
    
    # Get yesterday's orders
    orders = frappe.get_all(
        "Restaurant Order",
        filters={
            "creation": [">=", yesterday],
            "creation": ["<", today],
            "status": ["in", ["Paid", "Served"]]
        },
        fields=["name", "grand_total", "order_type", "items"]
    )
    
    total_revenue = sum(o.grand_total or 0 for o in orders)
    total_orders = len(orders)
    
    # Store report
    report_data = {
        "date": yesterday.date(),
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "average_order_value": total_revenue / total_orders if total_orders else 0,
        "order_by_type": {}
    }
    
    # Group by order type
    for order in orders:
        order_type = order.order_type or "Unknown"
        if order_type not in report_data["order_by_type"]:
            report_data["order_by_type"][order_type] = {"count": 0, "revenue": 0}
        report_data["order_by_type"][order_type]["count"] += 1
        report_data["order_by_type"][order_type]["revenue"] += order.grand_total or 0
    
    # Save to cache or create report document
    frappe.cache().hset("daily_reports", str(yesterday.date()), report_data)
    
    # Send summary notification
    settings = frappe.get_single("Restaurant Settings")
    if settings.get("daily_report_email"):
        send_daily_report_email(report_data, settings.daily_report_email)


def archive_old_orders():
    """Archive orders older than retention period"""
    settings = frappe.get_single("Restaurant Settings")
    retention_days = settings.get("order_retention_days") or 365
    
    threshold = add_to_date(now_datetime(), days=-retention_days)
    
    # Get old orders
    old_orders = frappe.get_all(
        "Restaurant Order",
        filters={
            "creation": ["<", threshold],
            "status": ["in", ["Paid", "Cancelled"]]
        },
        limit=100  # Process in batches
    )
    
    for order in old_orders:
        # Archive or delete based on settings
        if settings.get("archive_orders"):
            # Move to archive (implement archive logic)
            pass
        else:
            # Soft delete
            frappe.db.set_value("Restaurant Order", order.name, "is_archived", 1)


def reset_daily_counters():
    """Reset daily counters"""
    frappe.cache().delete_key("daily_order_count")
    frappe.cache().delete_key("daily_revenue")


def generate_weekly_report():
    """Generate weekly sales report"""
    today = now_datetime().replace(hour=0, minute=0, second=0)
    week_start = add_to_date(today, days=-7)
    
    orders = frappe.get_all(
        "Restaurant Order",
        filters={
            "creation": [">=", week_start],
            "creation": ["<", today],
            "status": ["in", ["Paid", "Served"]]
        },
        fields=["name", "grand_total", "creation"]
    )
    
    report_data = {
        "week_start": week_start.date(),
        "week_end": today.date(),
        "total_orders": len(orders),
        "total_revenue": sum(o.grand_total or 0 for o in orders)
    }
    
    frappe.cache().hset("weekly_reports", str(week_start.date()), report_data)


def generate_monthly_report():
    """Generate monthly sales report"""
    today = now_datetime()
    month_start = today.replace(day=1, hour=0, minute=0, second=0)
    prev_month_start = add_to_date(month_start, months=-1)
    
    orders = frappe.get_all(
        "Restaurant Order",
        filters={
            "creation": [">=", prev_month_start],
            "creation": ["<", month_start],
            "status": ["in", ["Paid", "Served"]]
        },
        fields=["name", "grand_total"]
    )
    
    report_data = {
        "month": prev_month_start.strftime("%Y-%m"),
        "total_orders": len(orders),
        "total_revenue": sum(o.grand_total or 0 for o in orders)
    }
    
    frappe.cache().hset("monthly_reports", report_data["month"], report_data)


def cleanup_old_data():
    """Clean up old temporary data"""
    # Clear old cache entries
    threshold = add_to_date(now_datetime(), days=-30)
    
    # Clean old waiter calls
    frappe.db.delete(
        "Waiter Call",
        filters={
            "creation": ["<", threshold],
            "status": ["in", ["Responded", "Cancelled"]]
        }
    )


def send_daily_report_email(report_data, recipients):
    """Send daily report email"""
    from frappe.utils import fmt_money
    
    subject = f"Restaurant Daily Report - {report_data['date']}"
    
    message = f"""
    <h2>Daily Restaurant Report</h2>
    <p><strong>Date:</strong> {report_data['date']}</p>
    
    <h3>Summary</h3>
    <ul>
        <li><strong>Total Orders:</strong> {report_data['total_orders']}</li>
        <li><strong>Total Revenue:</strong> {fmt_money(report_data['total_revenue'])}</li>
        <li><strong>Average Order Value:</strong> {fmt_money(report_data['average_order_value'])}</li>
    </ul>
    
    <h3>Orders by Type</h3>
    <table border="1" cellpadding="5">
        <tr>
            <th>Type</th>
            <th>Count</th>
            <th>Revenue</th>
        </tr>
    """
    
    for order_type, data in report_data.get("order_by_type", {}).items():
        message += f"""
        <tr>
            <td>{order_type}</td>
            <td>{data['count']}</td>
            <td>{fmt_money(data['revenue'])}</td>
        </tr>
        """
    
    message += "</table>"
    
    frappe.sendmail(
        recipients=recipients.split(","),
        subject=subject,
        message=message
    )
