"""
app/routes/chat.py
JWT-protected chat API and chat page.

POST /api/chat
    Body:  { "message": str, "clear_history": bool }
    Returns:
    {
        "response":   str,
        "intent":     str,
        "route":      "sql" | "rag",
        "citations":  list[str],
        "latency_ms": int
    }
"""
from flask import Blueprint, render_template, request, jsonify, g
from app.services.ai_chat_service import chat, clear_history, get_history
from app.models import CustomerProfile

chat_bp = Blueprint("chat", __name__)

SUGGESTED_PROMPTS = [
    "What is my current account balance?",
    "Show me my last 5 transactions",
    "When is my next EMI due?",
    "What is my CIBIL credit score?",
    "What is the SentinelBank home loan interest rate?",
    "How do I reset my internet banking password?",
    "What does RBI say about unauthorized transactions?",
    "Explain the HLPP insurance policy",
]


@chat_bp.route("/chat")
def chat_page():
    return render_template("pages/chat.html", suggested_prompts=SUGGESTED_PROMPTS)


@chat_bp.route("/api/chat", methods=["POST"])
def api_chat():
    user = getattr(g, "current_user", None)
    if not user:
        return jsonify({"error": "Unauthorized — please log in"}), 401

    body = request.get_json(silent=True) or {}
    message = (body.get("message") or "").strip()

    if not message:
        return jsonify({"error": "Message cannot be empty"}), 400
    if len(message) > 1000:
        return jsonify({"error": "Message too long (max 1000 characters)"}), 400

    # Optional: clear conversation history
    if body.get("clear_history"):
        clear_history(user.id)

    # Resolve customer_id from the authenticated user
    customer    = CustomerProfile.query.filter_by(user_id=user.id).first()
    customer_id = customer.id if customer else None

    result = chat(message=message, user_id=user.id, customer_id=customer_id)

    return jsonify({
        "response":   result["response"],
        "intent":     result["intent"],
        "route":      result["route"],
        "citations":  result["citations"],
        "latency_ms": result["latency_ms"],
    }), 200


@chat_bp.route("/api/chat/history", methods=["GET"])
def api_history():
    user = getattr(g, "current_user", None)
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"history": get_history(user.id)}), 200


@chat_bp.route("/api/chat/history", methods=["DELETE"])
def api_clear_history():
    user = getattr(g, "current_user", None)
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    clear_history(user.id)
    return jsonify({"status": "ok", "message": "Conversation cleared"}), 200
