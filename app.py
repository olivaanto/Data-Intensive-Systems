import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent / "databases"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASES = {
    "Customers": {
        "file": DATA_DIR / "Customers.db",
        "table": "customers",
        "columns": {"name": "TEXT", "email": "TEXT"},
        "sample_data": [
            ("Anna Verdi", "anna@example.com"),
            ("Mario Rossi", "mario@example.com"),
        ],
    },

    "Employees": {
        "file": DATA_DIR / "Employees.db",
        "table": "employees",
        "columns": {"name": "TEXT", "email": "TEXT", "department": "TEXT"},
        "sample_data": [
            ("Antonio Oliva", "oliva@company.com", "IT"),
            ("Luca Verdi", "verdi@company.com", "SALES"),
        ],
    },

    "Products": {
        "file": DATA_DIR / "Products.db",
        "table": "products",
        "columns": {"product_name": "TEXT", "price": "REAL", "stock": "INTEGER"},
        "sample_data": [
            ("Notebook", 2.50, 120),
            ("USB drive", 9.99, 35),
            ("Calculator", 14.75, 18),
        ],
    },
}


def connect(db_name):
    return sqlite3.connect(DATABASES[db_name]["file"])


def initialize_databases():
    for db_name, config in DATABASES.items():
        column_sql = ", ".join(
            f'"{column}" {data_type} NOT NULL'
            for column, data_type in config["columns"].items()
        )
        with connect(db_name) as connection:
            connection.execute(
                f'''
                CREATE TABLE IF NOT EXISTS "{config["table"]}" (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    {column_sql}
                )
                '''
            )
            count = connection.execute(
                f'SELECT COUNT(*) FROM "{config["table"]}"'
            ).fetchone()[0]

            if count == 0:
                columns = list(config["columns"].keys())
                placeholders = ", ".join("?" for _ in columns)
                column_names = ", ".join(f'"{column}"' for column in columns)
                connection.executemany(
                    f'INSERT INTO "{config["table"]}" ({column_names}) '
                    f'VALUES ({placeholders})',
                    config["sample_data"],
                )


def read_records(db_name):
    config = DATABASES[db_name]
    with connect(db_name) as connection:
        return pd.read_sql_query(
            f'SELECT * FROM "{config["table"]}" ORDER BY id', connection
        )


def add_record(db_name, values):
    config = DATABASES[db_name]
    columns = list(config["columns"].keys())
    column_names = ", ".join(f'"{column}"' for column in columns)
    placeholders = ", ".join("?" for _ in columns)
    with connect(db_name) as connection:
        connection.execute(
            f'INSERT INTO "{config["table"]}" ({column_names}) VALUES ({placeholders})',
            values,
        )


def update_record(db_name, record_id, values):
    config = DATABASES[db_name]
    columns = list(config["columns"].keys())
    assignments = ", ".join(f'"{column}" = ?' for column in columns)
    with connect(db_name) as connection:
        connection.execute(
            f'UPDATE "{config["table"]}" SET {assignments} WHERE id = ?',
            [*values, record_id],
        )


def delete_record(db_name, record_id):
    config = DATABASES[db_name]
    with connect(db_name) as connection:
        connection.execute(
            f'DELETE FROM "{config["table"]}" WHERE id = ?', (record_id,)
        )


def record_form(db_name, record=None, form_key="add"):
    config = DATABASES[db_name]
    record = record or {}
    values = []
    record_key = record.get("id", "new")

    with st.form(f"{db_name}_{form_key}_form_{record_key}"):
        for column, data_type in config["columns"].items():
            label = column.replace("_", " ").title()
            current_value = record.get(column, "")

            if data_type == "INTEGER":
                value = st.number_input(
                    label,
                    min_value=0,
                    step=1,
                    value=int(current_value) if current_value != "" else 0,
                    key=f"{db_name}_{form_key}_{record_key}_{column}",
                )
            elif data_type == "REAL":
                value = st.number_input(
                    label,
                    min_value=0.0,
                    step=0.5,
                    value=float(current_value) if current_value != "" else 0.0,
                    format="%.2f",
                    key=f"{db_name}_{form_key}_{record_key}_{column}",
                )
            else:
                value = st.text_input(
                    label,
                    value=str(current_value),
                    key=f"{db_name}_{form_key}_{record_key}_{column}",
                )
            values.append(value)

        submitted = st.form_submit_button(
            "Save changes" if form_key == "edit" else "Add record"
        )

    return submitted, values


st.set_page_config(page_title="Simple Database Manager")
initialize_databases()

st.title("Database Manager")

db_names = list(DATABASES.keys())
db_tabs = st.tabs(db_names)

for db_name, tab in zip(db_names, db_tabs):
    with tab:
        st.header(f"{db_name} database")

        records = read_records(db_name)

        edited_records = st.data_editor(
            records,
            width="stretch",
            hide_index=True,
            num_rows="dynamic",
            key=f"{db_name}_editor",
        )

        
        if st.button("Save changes", key=f"{db_name}_save"):
            columns = list(DATABASES[db_name]["columns"].keys())

            # Check that every field in every row is filled in.
            incomplete = False

            for _, row in edited_records.iterrows():
                if any(
                    pd.isna(row[col])
                    or (isinstance(row[col], str) and not row[col].strip())
                    for col in columns
                ):
                    incomplete = True
                    break

            if incomplete:
                st.error(
                    "Some rows have empty fields. "
                    "Please complete or delete them before saving."
                )

            else:
                original = records.set_index("id")
                edited = edited_records.copy()

                edited_ids = set(edited["id"].astype(int))
                original_ids = set(original.index.astype(int))

                # Delete removed rows.
                for record_id in original_ids - edited_ids:
                    delete_record(db_name, record_id)

                # Add new rows and update existing ones.
                for _, row in edited.iterrows():
                    values = [row[col] for col in columns]
                    record_id = int(row["id"])

                    if record_id not in original_ids:
                        add_record(db_name, values)
                    else:
                        old_row = original.loc[record_id]

                        if any(
                            old_row[col] != row[col]
                            for col in columns
                        ):
                            update_record(db_name, record_id, values)

                st.success("Changes saved to the database.")
                st.rerun()