from flask import Flask, request, jsonify
from datetime import datetime
from flask_cors import CORS
import mysql.connector
import json
import os

app = Flask(__name__)

# ======================================
# CORS CONFIG (FOR REACT FRONTEND)
# ======================================
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)

@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
    return response


# ======================================
# DATABASE CONNECTION
# ======================================
def get_db():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASS"),
        database=os.environ.get("DB_NAME"),
        port=3306,
        connection_timeout=30
    )


# ======================================
# GENERATE INVOICE NUMBER
# ======================================
def generate_invoice_number(doc_type):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT counter FROM invoice_counters WHERE document_type=%s",
        (doc_type,)
    )

    row = cursor.fetchone()

    if not row:
        counter = 1
        cursor.execute(
            "INSERT INTO invoice_counters (document_type, counter) VALUES (%s,%s)",
            (doc_type, counter)
        )
    else:
        counter = row[0] + 1
        cursor.execute(
            "UPDATE invoice_counters SET counter=%s WHERE document_type=%s",
            (counter, doc_type)
        )

    db.commit()

    prefix = "INV"

    if doc_type == "PROFORMA INVOICE":
        prefix = "PINV"

    elif doc_type == "QUOTATION":
        prefix = "QI"

    now = datetime.now()

    month = now.strftime("%m")
    year = now.strftime("%y")

    invoice_no = f"{prefix}-MQ{month}{year}{str(counter).zfill(4)}"

    cursor.close()
    db.close()

    return invoice_no


# ======================================
# HOME ROUTE
# ======================================
@app.route("/")
def home():
    return "Invoice API Running 🚀"


# ======================================
# SAVE INVOICE
# ======================================
@app.route("/save-invoice", methods=["POST"])
def save_invoice():

    try:

        db = get_db()
        cursor = db.cursor()

        data = request.json

        invoice_no = generate_invoice_number(data["documentType"])

        data["invoiceNumber"] = invoice_no

        sql = """
        INSERT INTO invoices
        (document_type, invoice_no, client_name, client_email, total, invoice_data)
        VALUES (%s,%s,%s,%s,%s,%s)
        """

        values = (
            data["documentType"],
            invoice_no,
            data["billTo"],
            data["billToEmail"],
            float(data["total"]),
            json.dumps(data)
        )

        cursor.execute(sql, values)
        db.commit()

        cursor.close()
        db.close()

        return jsonify({
            "status": "success",
            "invoiceNumber": invoice_no
        })

    except Exception as e:

        print("❌ SAVE ERROR:", e)

        return jsonify({
            "status": "error",
            "message": str(e)
        })


# ======================================
# GET ALL INVOICES
# ======================================
@app.route("/invoices", methods=["GET"])
def get_invoices():

    try:

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
                "created_at": str(row[7])
            })

        cursor.close()
        db.close()

        return jsonify(invoices)

    except Exception as e:

        print("❌ FETCH ERROR:", e)

        return jsonify({
            "error": str(e)
        })


# ======================================
# GET SINGLE INVOICE
# ======================================
@app.route("/get-invoice/<int:id>", methods=["GET"])
def get_invoice(id):

    try:

        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            "SELECT invoice_data FROM invoices WHERE id=%s",
            (id,)
        )

        row = cursor.fetchone()

        cursor.close()
        db.close()

        if row:
            return jsonify(json.loads(row[0]))

        else:
            return jsonify({
                "error": "Invoice not found"
            }), 404

    except Exception as e:

        print("❌ GET ERROR:", e)

        return jsonify({
            "error": str(e)
        })


# ======================================
# DELETE INVOICE
# ======================================
@app.route("/delete-invoice/<int:id>", methods=["DELETE"])
def delete_invoice(id):

    try:

        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            "DELETE FROM invoices WHERE id=%s",
            (id,)
        )

        db.commit()

        deleted = cursor.rowcount

        cursor.close()
        db.close()

        if deleted == 0:

            return jsonify({
                "success": False,
                "message": "Invoice not found"
            }), 404

        return jsonify({
            "success": True,
            "message": "Invoice deleted successfully"
        })

    except Exception as e:

        print("❌ DELETE ERROR:", e)

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ======================================
# RUN SERVER
# ======================================
if __name__ == "__main__":
    app.run(debug=True)
