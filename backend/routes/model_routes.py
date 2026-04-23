# backend/routes/model_routes.py

from flask import Blueprint, request, jsonify
import sys
import os

# Ensure the models directory is accessible
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models"))

from driver_model import DriverModel
from budget_tracker import BudgetTracker
from rolling_forecast import RollingForecast
from multi_dimensional import MultiDimensionalModel
from model_graph import ModelGraph

model_bp = Blueprint("model_bp", __name__)

driver_model = DriverModel()
budget_tracker = BudgetTracker()
rolling_forecast = RollingForecast()
multi_model = MultiDimensionalModel()
model_graph = ModelGraph()

# --- DRIVER MODEL ROUTES ---

@model_bp.route("/api/drivers/calculate", methods=["POST"])
def calculate_drivers():
    data = request.get_json() or {}
    drivers = data.get("drivers", {})
    try:
        res = driver_model.calculate(drivers)
        return jsonify({"status": "success", "result": res})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@model_bp.route("/api/drivers/sensitivity", methods=["POST"])
def driver_sensitivity():
    data = request.get_json() or {}
    drivers = data.get("drivers", {})
    variable = data.get("variable")
    target_metric = data.get("target_metric", "net_profit")
    try:
        res = driver_model.sensitivity(drivers, variable, target_metric)
        return jsonify({"status": "success", "sensitivity": res})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@model_bp.route("/api/drivers/goal-seek", methods=["POST"])
def driver_goal_seek():
    data = request.get_json() or {}
    drivers = data.get("drivers", {})
    target_metric = data.get("target_metric", "net_profit")
    target_value = data.get("target_value", 0)
    variable_driver = data.get("variable_driver")
    try:
        res = driver_model.goal_seek(drivers, target_metric, float(target_value), variable_driver)
        return jsonify({"status": "success", "goal_seek": res})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@model_bp.route("/api/drivers/propagate", methods=["POST"])
def driver_propagate():
    data = request.get_json() or {}
    driver = data.get("driver")
    new_value = data.get("new_value", 0)
    current_drivers = data.get("current_drivers", {})
    try:
        res = model_graph.propagate(driver, float(new_value), current_drivers)
        return jsonify({"status": "success", "propagation": res})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@model_bp.route("/api/drivers/impact", methods=["POST"])
def driver_impact():
    data = request.get_json() or {}
    driver = data.get("driver")
    try:
        res = model_graph.impact_score(driver)
        return jsonify({"status": "success", "impact": res})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- BUDGET TRACKER ROUTES ---

@model_bp.route("/api/budget/set", methods=["POST"])
def budget_set():
    data = request.get_json() or {}
    try:
        budget_tracker.set_budget(
            data["year"], data["month"], data["metric"], data["target"]
        )
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@model_bp.route("/api/budget/vs-actual", methods=["GET"])
def budget_vs_actual():
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    metric = request.args.get("metric", "revenue")
    try:
        res = budget_tracker.compare(year, month, metric)
        return jsonify({"status": "success", "comparison": res})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@model_bp.route("/api/budget/report", methods=["GET"])
def budget_report():
    year = request.args.get("year", type=int)
    try:
        res = budget_tracker.monthly_report(year)
        return jsonify({"status": "success", "report": res})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- FORECAST ROUTES ---

@model_bp.route("/api/forecast/rolling", methods=["GET"])
def forecast_rolling():
    metric = request.args.get("metric", "revenue")
    periods = request.args.get("periods", 6, type=int)
    try:
        res = rolling_forecast.run(metric, periods)
        return jsonify({"status": "success", "forecast": res})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@model_bp.route("/api/forecast/accuracy", methods=["GET"])
def forecast_accuracy():
    try:
        res = rolling_forecast.accuracy()
        return jsonify({"status": "success", "accuracy": res})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- MULTI DIMENSIONAL ROUTES ---

@model_bp.route("/api/model/build", methods=["POST"])
def model_build():
    data = request.get_json() or {}
    dimensions = data.get("dimensions", [])
    metric = data.get("metric", "revenue")
    try:
        res = multi_model.build(dimensions, metric)
        return jsonify({"status": "success", "pivot": res})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@model_bp.route("/api/model/drilldown", methods=["POST"])
def model_drilldown():
    data = request.get_json() or {}
    try:
        res = multi_model.drilldown(data["dimension"], data["value"], data.get("metric", "revenue"))
        return jsonify({"status": "success", "timeseries": res})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@model_bp.route("/api/model/summary", methods=["GET"])
def model_summary():
    metric = request.args.get("metric", "revenue")
    try:
        res = multi_model.summary(metric)
        return jsonify({"status": "success", "summary": res})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
