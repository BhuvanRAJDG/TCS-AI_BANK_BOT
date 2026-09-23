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
    "Transfer ₹500 to Priya for lunch",
    "What is the CBS Bank home loan interest rate?",
    "How do I reset my internet banking password?",
    "What does RBI say about unauthorized transactions?",
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
        "response":      result["response"],
        "intent":        result["intent"],
        "route":         result["route"],
        "citations":     result["citations"],
        "latency_ms":    result["latency_ms"],
        "transfer_data": result.get("transfer_data"),
    }), 200


@chat_bp.route("/api/chat/transfer-confirm", methods=["POST"])
def api_transfer_confirm():
    user = getattr(g, "current_user", None)
    if not user:
        return jsonify({"error": "Unauthorized — please log in"}), 401

    body = request.get_json(silent=True) or {}
    recipient = (body.get("recipient") or "").strip()
    try:
        amount = float(body.get("amount", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid transfer amount"}), 400

    if amount <= 0:
        return jsonify({"error": "Transfer amount must be greater than zero"}), 400

    pin = str(body.get("pin", "")).strip()
    if not pin:
        return jsonify({"error": "UPI PIN or account password is required"}), 400

    from app.security import verify_password
    is_valid_pin = pin in ('1234', '123456', '9999')
    is_valid_password = verify_password(pin, user.password_hash)

    if not (is_valid_pin or is_valid_password):
        return jsonify({"error": "Incorrect UPI PIN or password. Demo PIN is 1234 or your account password."}), 400

    customer = CustomerProfile.query.filter_by(user_id=user.id).first()
    customer_id = customer.id if customer else 1

    try:
        from app.services.transaction_service import TransactionService
        receipt = TransactionService.process_transfer(customer_id, recipient, amount)

        response_text = (
            f"✅ **Money Transfer Successful!**\n\n"
            f"• **Reference ID:** `{receipt['reference_id']}`\n"
            f"• **Recipient:** {receipt['recipient']}\n"
            f"• **Amount Transferred:** ₹{receipt['amount']:,.2f}\n"
            f"• **Payment Channel:** CBS FastPay UPI\n"
            f"• **Date & Time:** {receipt['timestamp']}\n"
            f"• **Updated Available Balance:** ₹{receipt['new_balance']:,.2f}\n\n"
            f"*(Authorized with UPI PIN • Bank records updated in real-time)*"
        )
        return jsonify({
            "status": "success",
            "receipt": receipt,
            "response": response_text
        }), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as exc:
        return jsonify({"error": f"Transfer failed: {str(exc)}"}), 500


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
