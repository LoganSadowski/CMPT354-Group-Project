#create Flask instance

import sqlite3
from flask import Flask, render_template, request
app = Flask(__name__)

TABLE_NAMES = {
    "client": "Client",
    "company": "Company",
    "individual": "Individual",
    "storage_location": "StorageLocation",
    "sample": "Sample",
    "technician": "Technician",
    "department": "Department",
    "subsample": "SubSample",
    "conducts_test_on": "ConductsTestOn",
    "test_results": "TestResults",
}

TABLE_QUERIES = {
    table_key: f"SELECT * FROM {table_name}"
    for table_key, table_name in TABLE_NAMES.items()
}

TABLE_LABELS = {
    "client": "Client",
    "company": "Company",
    "individual": "Individual",
    "storage_location": "Storage Location",
    "sample": "Sample",
    "technician": "Technician",
    "department": "Department",
    "subsample": "SubSample",
    "conducts_test_on": "ConductsTestOn",
    "test_results": "TestResults",
}

DEFAULT_TABLE = "technician"

TABLE_FIELDS = {
    "client": ["clientID", "email"],
    "company": ["cID", "name"],
    "individual": ["cID", "firstName", "lastName"],
    "storage_location": ["storageID", "address", "capacity"],
    "sample": ["sampleID", "description", "dateReceived", "cID", "sID"],
    "technician": ["technicianID", "firstName", "lastName", "email", "phone", "depID"],
    "department": ["departmentID", "name", "managerID"],
    "subsample": ["subSampleID", "sampleID"],
    "conducts_test_on": ["tID", "sID", "time", "instrument"],
    "test_results": ["tID", "sID", "results"],
}

OPTIONAL_FIELDS = {
    "sample": {"sID"},
    "conducts_test_on": {"time", "instrument"},
}

TABLE_PRIMARY_KEYS = {
    "client": ["clientID"],
    "company": ["cID"],
    "individual": ["cID"],
    "storage_location": ["storageID"],
    "sample": ["sampleID"],
    "technician": ["technicianID"],
    "department": ["departmentID"],
    "subsample": ["subSampleID", "sampleID"],
    "conducts_test_on": ["tID", "sID"],
    "test_results": ["tID", "sID", "results"],
}

#Turn the results from the database into a dictionary
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_connection():
    conn = sqlite3.connect('samples.db')
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def run_select_query(query):
    conn = get_connection()
    conn.row_factory = dict_factory

    try:
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        columns = [column[0] for column in cursor.description] if cursor.description else []
        return columns, results
    finally:
        conn.close()


def run_insert_query(table_key, values):
    table_name = TABLE_NAMES[table_key]
    fields = TABLE_FIELDS[table_key]
    placeholders = ", ".join(["?"] * len(fields))
    field_list = ", ".join(fields)
    query = f"INSERT INTO {table_name} ({field_list}) VALUES ({placeholders})"

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, values)
        conn.commit()
    finally:
        conn.close()


def sample_exists(sample_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM Sample WHERE sampleID = ?", (sample_id,))
        return cursor.fetchone() is not None
    finally:
        conn.close()


def run_delete_query(table_key, values):
    table_name = TABLE_NAMES[table_key]
    primary_keys = TABLE_PRIMARY_KEYS[table_key]
    where_clause = " AND ".join([f"{key} = ?" for key in primary_keys])
    query = f"DELETE FROM {table_name} WHERE {where_clause}"

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, values)
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def parse_form_values(fields, optional_fields):
    values = []
    for field in fields:
        value = request.form.get(field, "").strip()
        if not value and field not in optional_fields:
            return None, f"{field} is required."
        if not value and field in optional_fields:
            values.append(None)
        else:
            values.append(value)
    return values, None


@app.route("/")
def home():
    return render_template(
        'index.html',
        table_labels=TABLE_LABELS,
        default_table=DEFAULT_TABLE,
    )


@app.route("/<table_key>", methods=["GET", "POST"])
def table_page(table_key):
    if table_key not in TABLE_QUERIES:
        return "Category not found.", 404

    columns = []
    results = []
    error = None
    action_message = None

    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "add":
            add_fields = TABLE_FIELDS[table_key]
            optional_fields = OPTIONAL_FIELDS.get(table_key, set())
            values, validation_error = parse_form_values(add_fields, optional_fields)
            if validation_error:
                error = validation_error
            else:
                try:
                    if table_key == "subsample":
                        sample_id = values[1]
                        if not sample_exists(sample_id):
                            error = f"Cannot add SubSample: sampleID {sample_id} does not exist in Sample."

                    if error is None:
                        run_insert_query(table_key, values)
                        action_message = f"Added 1 row to {TABLE_LABELS[table_key]}."
                except sqlite3.Error as exc:
                    error = str(exc)

        elif action == "delete":
            delete_fields = TABLE_PRIMARY_KEYS[table_key]
            values, validation_error = parse_form_values(delete_fields, set())
            if validation_error:
                error = validation_error
            else:
                try:
                    deleted_rows = run_delete_query(table_key, values)
                    if deleted_rows == 0:
                        error = "No matching row found to delete."
                    else:
                        action_message = f"Deleted {deleted_rows} row(s) from {TABLE_LABELS[table_key]}."
                except sqlite3.Error as exc:
                    error = str(exc)

        else:
            error = "Invalid action."

    selected_label = TABLE_LABELS[table_key]
    query = TABLE_QUERIES[table_key]

    if error is None:
        try:
            columns, results = run_select_query(query)
        except sqlite3.Error as exc:
            error = str(exc)

    return render_template(
        'home.html',
        query=query,
        selected_table=table_key,
        selected_label=selected_label,
        table_labels=TABLE_LABELS,
        table_fields=TABLE_FIELDS[table_key],
        delete_fields=TABLE_PRIMARY_KEYS[table_key],
        columns=columns,
        results=results,
        error=error,
        action_message=action_message,
    )

#enable debugging
if __name__ == '__main__':
    app.run(debug=True)   
