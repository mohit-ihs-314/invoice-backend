from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import json
import os

app = Flask(__name__)
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)

# ⭐ Render + Browser preflight fix
@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
    return response

# ================================
# DB CONNECTION (AUTO RECONNECT)
# ================================
def get_db():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASS"),
        database=os.environ.get("DB_NAME"),
        port=3306,
        connection_timeout=30
    )

# ================================
# HOME TEST
# ================================
@app.route("/")
def home():
    return "Invoice API Running 🚀"

# ================================
# SAVE INVOICE
# ================================
@app.route("/save-invoice", methods=["POST"])
def save_invoice():
    try:
        db = get_db()
        cursor = db.cursor()

        data = request.json
        print("📩 RECEIVED:", data["invoiceNumber"])

        sql = """
        INSERT INTO invoices 
        (document_type, invoice_no, client_name, client_email, total, invoice_data)
        VALUES (%s,%s,%s,%s,%s,%s)
        """

        values = (
            data["documentType"],
            data["invoiceNumber"],     # already generated invoice no
            data["billTo"],
            data["billToEmail"],
            float(data["total"]),
            json.dumps(data)           # full invoice JSON save
        )

        cursor.execute(sql, values)
        cursor.close()
        db.close()

        return jsonify({"status": "success"})

    except Exception as e:
        print("❌ SAVE ERROR:", e)
        return jsonify({"status": "error", "message": str(e)})

# ================================
# GET ALL INVOICES (HISTORY)
# ================================
@app.route("/invoices", methods=["GET"])
def get_invoices():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM invoices ORDER BY id DESC")
    rows = cursor.fetchall()

    invoices = []
    for row in rows:
        invoices.append({
            "id": row[0],
            "documentType": row[1],
            "invoiceNumber": row[2],
            "billTo": row[3],
            "billToEmail": row[4],
            "total": row[5],
            "created_at": str(row[7])   # ⭐ CORRECT COLUMN
        })

    cursor.close()
    db.close()

    return jsonify(invoices)
# ================================
# GET SINGLE INVOICE JSON (PDF RE-DOWNLOAD)
# ================================
@app.route("/get-invoice/<id>", methods=["GET"])
def get_invoice(id):
    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute("SELECT invoice_data FROM invoices WHERE id=%s", (id,))
        row = cursor.fetchone()

        cursor.close()
        db.close()

        if row:
            return jsonify(json.loads(row[0]))
        else:
            return jsonify({"error": "Invoice not found"}), 404

    except Exception as e:
        print("❌ GET SINGLE ERROR:", e)
        return jsonify({"error": str(e)})

# ================================
# DELETE INVOICE (optional)
# ================================
@app.route("/delete-invoice/<id>", methods=["DELETE"])
def delete_invoice(id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("DELETE FROM invoices WHERE id=%s", (id,))
    cursor.close()
    db.close()

    return jsonify({"message": "Deleted"})

# ================================
# RUN SERVER
# ================================
if __name__ == "__main__":
    app.run(debug=True)
