from flask import Blueprint, render_template

dashboards_bp = Blueprint("dashboards", __name__)

@dashboards_bp.get("/warehouse-demo")
def warehouse_demo():
    """Demo page for dynamic warehouse dropdown"""
    return render_template("warehouse-demo.html")

@dashboards_bp.get("/farmer")
def farmer_page():
    return render_template("farmer.html")

@dashboards_bp.get("/warehouse")
def warehouse_page():
    return render_template("warehouse.html")


@dashboards_bp.get("/logistics")
def logistics_page():
    return render_template("logistics.html")

@dashboards_bp.get("/admin")
@dashboards_bp.get("/admin-dashboard")
def admin_dashboard_page():
    """Admin dashboard for system monitoring"""
    return render_template("admin.html")

