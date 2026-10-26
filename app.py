
import os
import time

import psycopg
from flask import Flask, redirect, render_template, request, url_for
from psycopg.rows import dict_row

app = Flask(__name__)

DATABASE_URL = os.environ["DATABASE_URL"]


def get_connection():
    # Retry briefly while PostgreSQL starts up.
    for attempt in range(10):
        try:
            return psycopg.connect(
                DATABASE_URL,
                row_factory=dict_row,
                connect_timeout=3,
            )
        except psycopg.OperationalError:
            if attempt == 9:
                raise
            time.sleep(2)


def initialize_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS health_records (
                id SERIAL PRIMARY KEY,
                patient_code VARCHAR(30) NOT NULL,
                measurement VARCHAR(80) NOT NULL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


@app.route("/")
def index():
    with get_connection() as conn:
        records = conn.execute("""
            SELECT id, patient_code, measurement, recorded_at
            FROM health_records
            ORDER BY id DESC
        """).fetchall()

    return render_template("index.html", records=records)


@app.route("/add", methods=["POST"])
def add_record():
    patient_code = request.form.get("patient_code", "").strip()
    measurement = request.form.get("measurement", "").strip()

    if not patient_code or not measurement:
        return "Both fields are required.", 400

    if len(patient_code) > 30 or len(measurement) > 80:
        return "Input is too long.", 400

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO health_records (patient_code, measurement)
            VALUES (%s, %s)
            """,
            (patient_code, measurement),
        )

    return redirect(url_for("index"))


@app.route("/health")
def health():
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1")
        return {"status": "ok"}, 200
    except psycopg.Error:
        return {"status": "database unavailable"}, 503


if __name__ == "__main__":
    initialize_database()
    app.run(host="0.0.0.0", port=5000)
