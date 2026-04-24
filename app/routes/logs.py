from flask import Blueprint, jsonify, request
from app.stores.log_store import get_events, get_today_count, clear_events
from app.stores.face_store import get_enrolled_count

logs_bp = Blueprint("logs", __name__)


@logs_bp.route('/log')
def get_log():
    return jsonify({"events": get_events(50)})


@logs_bp.route('/log', methods=['DELETE'])
def clear_log():
    clear_events()
    return jsonify({"message": "Log cleared."})


@logs_bp.route('/stats')
def get_stats():
    return jsonify({
        "enrolled_count": get_enrolled_count(),
        "today_recognitions": get_today_count(),
    })


@logs_bp.route('/settings', methods=['POST'])
def update_settings():
    data = request.get_json(force=True)
    tolerance = float(data.get("tolerance", 0.5))
    tolerance = max(0.3, min(0.7, tolerance))
    from app.services.recognition_service import get_recognizer
    get_recognizer().tolerance = tolerance
    return jsonify({"message": f"Tolerance updated to {tolerance:.2f}"})
