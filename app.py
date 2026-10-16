
import sqlite3
from pathlib import Path

from flask import (
    Flask, abort, redirect, render_template_string,
    request, url_for, flash
)

app = Flask(__name__)
app.secret_key = "assignment-demo-key"

DB_DIR = Path(__file__).parent / "databases"
DB_DIR.mkdir(exist_ok=True)

# Each entry points to a separate SQLite database file.
DATABASES = {
    "customers": {
        "name": "Customers",
        "file": "customers.db",
        "fields": {
            "name": "Customer Name",
            "email": "Email Address",
            "city": "City",
        },
        "sample": [
            ("Alice Johnson", "alice@example.com", "Helsinki"),
            ("Mark Smith", "mark@example.com", "Lahti"),
            ("Sara Brown", "sara@example.com", "Tampere"),
        ],
    },
    "products": {
        "name": "Products",
        "file": "products.db",
        "fields": {
            "name": "Product Name",
            "price": "Price (€)",
            "stock": "Stock Quantity",
        },
        "sample": [
            ("Laptop", "899.99", "12"),
            ("Wireless Mouse", "24.90", "50"),
            ("Keyboard", "59.90", "25"),
        ],
    },
    "employees": {
        "name": "Employees",
        "file": "employees.db",
        "fields": {
            "name": "Employee Name",
            "job_title": "Job Title",
            "department": "Department",
        },
        "sample": [
            ("Emma Wilson", "Manager", "Sales"),
            ("John Taylor", "Developer", "IT"),
            ("Olivia Martin", "Accountant", "Finance"),
        ],
    },
}


def connect(db_key):
    """Open the selected database."""
    if db_key not in DATABASES:
        abort(404)

    path = DB_DIR / DATABASES[db_key]["file"]
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_databases():
    """Create all three databases and insert demo data once."""
    for key, config in DATABASES.items():
        fields = list(config["fields"].keys())

        # Field names come only from our fixed configuration.
        columns = ", ".join(f'"{field}" TEXT NOT NULL'
                            for field in fields)

        with connect(key) as db:
            db.execute(
                f'CREATE TABLE IF NOT EXISTS records ('
                f'id INTEGER PRIMARY KEY AUTOINCREMENT, {columns})'
            )

            count = db.execute(
                "SELECT COUNT(*) FROM records"
            ).fetchone()[0]

            if count == 0:
                placeholders = ", ".join("?" for _ in fields)
                db.executemany(
                    f'INSERT INTO records ({", ".join(fields)}) '
                    f'VALUES ({placeholders})',
                    config["sample"],
                )


# Keep the interface in this file to make setup simple.
PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Multi-Database Manager</title>
    <style>
        * { box-sizing: border-box; }
        body {
            margin: 0; font-family: Arial, sans-serif;
            background: #f3f5f9; color: #202b3c;
        }
        header {
            background: #18263d; color: white;
            padding: 22px 6%;
        }
        header h1 { margin: 0 0 6px; font-size: 25px; }
        header p { margin: 0; color: #cbd5e1; }
        main { max-width: 1100px; margin: 30px auto; padding: 0 20px; }
        .layout {
            display: grid; grid-template-columns: 220px 1fr;
            gap: 24px; align-items: start;
        }
        .panel {
            background: white; padding: 22px; border-radius: 12px;
            box-shadow: 0 3px 14px #1725540d;
        }
        .nav a {
            display: block; padding: 12px; margin: 5px 0;
            border-radius: 7px; color: #344256;
            text-decoration: none;
        }
        .nav a.active, .nav a:hover { background: #e7efff; color: #1d4ed8; }
        .muted { color: #64748b; font-size: 14px; }
        .top {
            display: flex; justify-content: space-between;
            gap: 15px; align-items: center; flex-wrap: wrap;
        }
        .button {
            display: inline-block; border: 0; border-radius: 7px;
            padding: 10px 14px; cursor: pointer;
            background: #2563eb; color: white;
            text-decoration: none; font-size: 14px;
        }
        .secondary { background: #e8edf5; color: #243247; }
        .danger { background: #fee2e2; color: #b91c1c; }
        table { border-collapse: collapse; width: 100%; margin-top: 18px; }
        th, td {
            text-align: left; padding: 13px 10px;
            border-bottom: 1px solid #e5eaf1;
        }
        th { color: #64748b; font-size: 13px; }
        .actions { display: flex; gap: 7px; flex-wrap: wrap; }
        form.inline { display: inline; }
        label { display: block; margin: 16px 0 6px; font-weight: bold; }
        input {
            width: 100%; padding: 11px; border: 1px solid #cbd5e1;
            border-radius: 7px; font-size: 15px;
        }
        .message {
            padding: 12px; background: #dcfce7; color: #166534;
            border-radius: 7px; margin-bottom: 16px;
        }
        .empty { padding: 30px; text-align: center; color: #64748b; }
        @media (max-width: 700px) {
            .layout { grid-template-columns: 1fr; }
            th, td { padding: 10px 6px; }
        }
    </style>
</head>
<body>
<header>
    <h1>Multi-Database Manager</h1>
    <p>Assignment 2 · Access and manage three separate databases</p>
</header>
<main>
    {% for message in get_flashed_messages() %}
        <div class="message">{{ message }}</div>
    {% endfor %}
    <div class="layout">
        <aside class="panel nav">
            <h3>Select database</h3>
            {% for key, config in databases.items() %}
                <a class="{{ 'active' if key == selected else '' }}"
                   href="{{ url_for('index', db_key=key) }}">
                   {{ config.name }}
                </a>
            {% endfor %}
            <p class="muted">Each selection opens a separate SQLite file.</p>
        </aside>
        <section class="panel">
            {% if mode == 'list' %}
                <div class="top">
                    <div>
                        <h2>{{ config.name }} Database</h2>
                        <p class="muted">{{ rows|length }} record(s) displayed</p>
                    </div>
                    <a class="button" href="{{ url_for('add_record', db_key=selected) }}">
                        + Add record
                    </a>
                </div>
                <div style="overflow-x:auto">
                <table>
                    <thead><tr>
                        <th>ID</th>
                        {% for field, label in config.fields.items() %}
                            <th>{{ label }}</th>
                        {% endfor %}
                        <th>Actions</th>
                    </tr></thead>
                    <tbody>
                    {% for row in rows %}
                        <tr>
                            <td>{{ row.id }}</td>
                            {% for field in config.fields %}
                                <td>{{ row[field] }}</td>
                            {% endfor %}
                            <td><div class="actions">
                                <a class="button secondary"
                                   href="{{ url_for('edit_record', db_key=selected, record_id=row.id) }}">
                                   Edit
                                </a>
                                <form class="inline" method="post"
                                      action="{{ url_for('delete_record', db_key=selected, record_id=row.id) }}"
                                      onsubmit="return confirm('Delete this record?')">
                                    <button class="button danger" type="submit">Delete</button>
                                </form>
                            </div></td>
                        </tr>
                    {% else %}
                        <tr><td colspan="{{ config.fields|length + 2 }}"
                            class="empty">No records yet. Add your first record.</td></tr>
                    {% endfor %}
                    </tbody>
                </table>
                </div>
            {% else %}
                <h2>{{ 'Edit' if mode == 'edit' else 'Add' }} {{ config.name[:-1] if config.name.endswith('s') else config.name }}</h2>
                <form method="post">
                    {% for field, label in config.fields.items() %}
                        <label for="{{ field }}">{{ label }}</label>
                        <input id="{{ field }}" name="{{ field }}" required
                               value="{{ record[field] if record else '' }}">
                    {% endfor %}
                    <p style="margin-top:22px">
                        <button class="button" type="submit">Save record</button>
                        <a class="button secondary"
                           href="{{ url_for('index', db_key=selected) }}">Cancel</a>
                    </p>
                </form>
            {% endif %}
        </section>
    </div>
</main>
</body>
</html>
"""


@app.route("/")
def home():
    return redirect(url_for("index", db_key="customers"))


@app.route("/db/<db_key>")
def index(db_key):
    if db_key not in DATABASES:
        abort(404)

    with connect(db_key) as db:
        rows = db.execute("SELECT * FROM records ORDER BY id").fetchall()

    return render_template_string(
        PAGE, databases=DATABASES, selected=db_key,
        config=DATABASES[db_key], rows=rows, mode="list", record=None
    )


@app.route("/db/<db_key>/add", methods=["GET", "POST"])
def add_record(db_key):
    if db_key not in DATABASES:
        abort(404)

    config = DATABASES[db_key]
    fields = list(config["fields"].keys())

    if request.method == "POST":
        values = [request.form.get(field, "").strip() for field in fields]
        if not all(values):
            flash("Please fill in every field.")
        else:
            placeholders = ", ".join("?" for _ in fields)
            columns = ", ".join(f'"{f}"' for f in fields)
            with connect(db_key) as db:
                db.execute(
                    f"INSERT INTO records ({columns}) VALUES ({placeholders})",
                    values
                )
            flash("Record added successfully.")
            return redirect(url_for("index", db_key=db_key))

    return render_template_string(
        PAGE, databases=DATABASES, selected=db_key,
        config=config, mode="add", record=None, rows=[]
    )


@app.route("/db/<db_key>/edit/<int:record_id>", methods=["GET", "POST"])
def edit_record(db_key, record_id):
    if db_key not in DATABASES:
        abort(404)

    config = DATABASES[db_key]
    fields = list(config["fields"].keys())

    with connect(db_key) as db:
        record = db.execute(
            "SELECT * FROM records WHERE id = ?", (record_id,)
        ).fetchone()

        if record is None:
            abort(404)

        if request.method == "POST":
            values = [request.form.get(field, "").strip() for field in fields]
            if not all(values):
                flash("Please fill in every field.")
            else:
                assignments = ", ".join(f'"{f}" = ?' for f in fields)
                db.execute(
                    f"UPDATE records SET {assignments} WHERE id = ?",
                    values + [record_id]
                )
                flash("Record updated successfully.")
                return redirect(url_for("index", db_key=db_key))

    return render_template_string(
        PAGE, databases=DATABASES, selected=db_key,
        config=config, mode="edit", record=record, rows=[]
    )


@app.route("/db/<db_key>/delete/<int:record_id>", methods=["POST"])
def delete_record(db_key, record_id):
    if db_key not in DATABASES:
        abort(404)

    with connect(db_key) as db:
        db.execute("DELETE FROM records WHERE id = ?", (record_id,))

    flash("Record deleted.")
    return redirect(url_for("index", db_key=db_key))


if __name__ == "__main__":
    initialize_databases()
    app.run(debug=True)
