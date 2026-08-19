import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Frontend route
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Provider info endpoint (used by frontend for the provider badge)
# ---------------------------------------------------------------------------

@app.route("/api/provider", methods=["GET"])
def provider_info():
    from services.ai_provider import get_provider_name
    return jsonify({"provider": get_provider_name()}), 200


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.route("/api/first-aid", methods=["POST"])
def first_aid():
    from services.ai_provider import get_first_aid_guidance

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body. Expected JSON."}), 400

    situation = data.get("situation", "").strip()
    if not situation:
        return jsonify({"error": "Please describe the first-aid situation."}), 400
    if len(situation) > 1000:
        return jsonify({"error": "Description too long. Please keep it under 1000 characters."}), 400

    result = get_first_aid_guidance(situation)

    if "error" in result:
        # Configuration / credential errors → 503; unexpected AI errors → 500
        msg = result["error"]
        if "not set" in msg or "not configured" in msg or "unavailable" in msg:
            return jsonify(result), 503
        return jsonify(result), 500

    return jsonify(result), 200


@app.route("/api/medicine", methods=["POST"])
def medicine():
    from services.ai_provider import get_medicine_info

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body. Expected JSON."}), 400

    medicine_name = data.get("medicine", "").strip()
    if not medicine_name:
        return jsonify({"error": "Please enter a medicine name."}), 400
    if len(medicine_name) > 200:
        return jsonify({"error": "Medicine name too long. Please enter a valid medicine name."}), 400

    result = get_medicine_info(medicine_name)

    if "error" in result:
        msg = result["error"]
        if "not set" in msg or "not configured" in msg or "unavailable" in msg:
            return jsonify(result), 503
        return jsonify(result), 500

    return jsonify(result), 200


# ---------------------------------------------------------------------------
# Global error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found."}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed."}), 405


@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error("Unhandled exception: %s", type(e).__name__)
    return jsonify({"error": "An unexpected server error occurred."}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, host="0.0.0.0", port=5000)
