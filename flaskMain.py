#create Flask instance

import sqlite3
import re
from flask import Flask, redirect, render_template, request, url_for
app = Flask(__name__)

SCHEMA_INITIALIZED = False

TABLE_NAMES = {
    "client": "Client",
    "company": "Company",
    "individual": "Individual",
    "storage_location": "StorageLocation",
    "sample": "Sample",
    "technician": "Technician",
    "department": "Department",
    "analyte": "Analyte",
    "subsample": "SubSample",
    "conducts_test_on": "TestRun",
    "test_results": "TestMeasurement",
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
    "analyte": "Analyte",
    "subsample": "SubSample",
    "conducts_test_on": "TestRun",
    "test_results": "TestMeasurement",
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
    "analyte": ["analyteID", "name", "defaultUnit", "dataType"],
    "subsample": ["subSampleID", "sampleID", "parentSubSampleID"],
    "conducts_test_on": ["testRunID", "sampleID", "technicianID", "testType", "performedAt", "instrument", "status", "notes"],
    "test_results": ["testRunID", "analyteID", "valueNumeric", "valueText"],
}

OPTIONAL_FIELDS = {
    "sample": {"sID"},
    "conducts_test_on": {"performedAt", "instrument", "notes"},
    "test_results": {"valueNumeric", "valueText"},
    "analyte": {"defaultUnit"},
    "subsample": {"parentSubSampleID"},
}

TABLE_PRIMARY_KEYS = {
    "client": ["clientID"],
    "company": ["cID"],
    "individual": ["cID"],
    "storage_location": ["storageID"],
    "sample": ["sampleID"],
    "technician": ["technicianID"],
    "department": ["departmentID"],
    "analyte": ["analyteID"],
    "subsample": ["subSampleID", "sampleID"],
    "conducts_test_on": ["testRunID"],
    "test_results": ["testRunID", "analyteID"],
}

SQL_DEMO_TITLES = {
    "join": "Sample Ownership and Assigned Technician (Join)",
    "division": "Clients Whose Every Sample Has Been Tested (Division)",
    "aggregation": "Technician Workload Summary (Aggregation)",
    "group_by": "Client Workload Summary by Number of Samples (Group By)",
    "cascade_delete": "Client Offboarding with Cascading Data Cleanup (Delete + Cascade)",
    "update": "Technician Contact Correction (Update)",
}

#Turn the results from the database into a dictionary
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def format_sql_for_display(query):
    formatted = " ".join(query.split())
    replacements = [
        (r"\bSELECT\b", "\nSELECT"),
        (r"\bFROM\b", "\nFROM"),
        (r"\bLEFT JOIN\b", "\nLEFT JOIN"),
        (r"\bRIGHT JOIN\b", "\nRIGHT JOIN"),
        (r"\bINNER JOIN\b", "\nINNER JOIN"),
        (r"\bCROSS JOIN\b", "\nCROSS JOIN"),
        (r"\bJOIN\b", "\nJOIN"),
        (r"\bWHERE\b", "\nWHERE"),
        (r"\bGROUP BY\b", "\nGROUP BY"),
        (r"\bHAVING\b", "\nHAVING"),
        (r"\bORDER BY\b", "\nORDER BY"),
        (r"\bEXCEPT\b", "\nEXCEPT"),
        (r"\bUNION ALL\b", "\nUNION ALL"),
        (r"\bUNION\b", "\nUNION"),
        (r"\bCASE\b", "\nCASE"),
        (r"\bWHEN\b", "\n  WHEN"),
        (r"\bELSE\b", "\n  ELSE"),
        (r"\bEND\b", "\nEND"),
    ]
    for pattern, replacement in replacements:
        formatted = re.sub(pattern, replacement, formatted, flags=re.IGNORECASE)
    formatted = re.sub(r",\s*", ",\n    ", formatted)
    formatted = formatted.strip()
    if not formatted.endswith(";"):
        formatted += ";"
    return formatted


def get_connection():
    conn = sqlite3.connect('samples.db')
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_schema_updates():
    global SCHEMA_INITIALIZED
    if SCHEMA_INITIALIZED:
        return

    conn = sqlite3.connect('samples.db')
    try:
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(SubSample)")
        subsample_columns = {row[1] for row in cursor.fetchall()}
        if "parentSubSampleID" not in subsample_columns:
            cursor.execute("ALTER TABLE SubSample ADD COLUMN parentSubSampleID CHAR")

        cursor.execute(
            "CREATE TABLE IF NOT EXISTS TestRun ("
            "testRunID INT NOT NULL, "
            "sampleID INT NOT NULL, "
            "technicianID INT NOT NULL, "
            "testType VARCHAR(50) NOT NULL, "
            "performedAt DATETIME, "
            "instrument VARCHAR(50), "
            "status VARCHAR(20) NOT NULL, "
            "notes VARCHAR(300), "
            "PRIMARY KEY (testRunID), "
            "FOREIGN KEY (sampleID) REFERENCES Sample (sampleID), "
            "FOREIGN KEY (technicianID) REFERENCES Technician (technicianID)"
            ")"
        )

        cursor.execute(
            "CREATE TABLE IF NOT EXISTS Analyte ("
            "analyteID INT NOT NULL, "
            "name VARCHAR(100) NOT NULL, "
            "defaultUnit VARCHAR(20), "
            "dataType VARCHAR(20) NOT NULL, "
            "PRIMARY KEY (analyteID)"
            ")"
        )

        cursor.execute(
            "CREATE TABLE IF NOT EXISTS TestMeasurement ("
            "testRunID INT NOT NULL, "
            "analyteID INT NOT NULL, "
            "valueNumeric DECIMAL(12,4), "
            "valueText VARCHAR(200), "
            "PRIMARY KEY (testRunID, analyteID), "
            "FOREIGN KEY (testRunID) REFERENCES TestRun (testRunID), "
            "FOREIGN KEY (analyteID) REFERENCES Analyte (analyteID)"
            ")"
        )

        cursor.execute(
            "INSERT OR IGNORE INTO Analyte (analyteID, name, defaultUnit, dataType) VALUES (1, 'Overall Finding', NULL, 'text')"
        )

        cursor.execute(
            "CREATE TABLE IF NOT EXISTS SubSampleResult ("
            "subSampleID CHAR NOT NULL, "
            "sampleID INT NOT NULL, "
            "tID INT NOT NULL, "
            "description VARCHAR(100) NOT NULL, "
            "actualResult VARCHAR(100), "
            "PRIMARY KEY (subSampleID, sampleID, tID, description), "
            "FOREIGN KEY (subSampleID, sampleID) REFERENCES SubSample (subSampleID, sampleID), "
            "FOREIGN KEY (tID) REFERENCES Technician (technicianID)"
            ")"
        )

        cursor.execute(
            "CREATE TRIGGER IF NOT EXISTS trg_subsample_parent_check_insert "
            "BEFORE INSERT ON SubSample "
            "FOR EACH ROW "
            "WHEN NEW.parentSubSampleID IS NOT NULL "
            "BEGIN "
            "SELECT CASE "
            "WHEN NEW.parentSubSampleID = NEW.subSampleID "
            "THEN RAISE(ABORT, 'SubSample cannot be its own parent') "
            "WHEN NOT EXISTS ("
            "SELECT 1 FROM SubSample s "
            "WHERE s.subSampleID = NEW.parentSubSampleID "
            "AND s.sampleID = NEW.sampleID"
            ") "
            "THEN RAISE(ABORT, 'Parent SubSample must exist in same Sample') "
            "END; "
            "END"
        )

        cursor.execute(
            "CREATE TRIGGER IF NOT EXISTS trg_subsample_parent_check_update "
            "BEFORE UPDATE OF parentSubSampleID, subSampleID, sampleID ON SubSample "
            "FOR EACH ROW "
            "WHEN NEW.parentSubSampleID IS NOT NULL "
            "BEGIN "
            "SELECT CASE "
            "WHEN NEW.parentSubSampleID = NEW.subSampleID "
            "THEN RAISE(ABORT, 'SubSample cannot be its own parent') "
            "WHEN NOT EXISTS ("
            "SELECT 1 FROM SubSample s "
            "WHERE s.subSampleID = NEW.parentSubSampleID "
            "AND s.sampleID = NEW.sampleID"
            ") "
            "THEN RAISE(ABORT, 'Parent SubSample must exist in same Sample') "
            "END; "
            "END"
        )

        conn.commit()
        SCHEMA_INITIALIZED = True
    finally:
        conn.close()


def run_select_query(query):
    ensure_schema_updates()
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


def run_search_query(table_key, search_text):
    ensure_schema_updates()
    table_name = TABLE_NAMES[table_key]
    fields = TABLE_FIELDS[table_key]

    # If no search text is provided, return all rows for the selected category.
    if not search_text:
        return run_select_query(f"SELECT * FROM {table_name}")

    like_token = f"%{search_text}%"
    where_clause = " OR ".join([f"CAST({field} AS TEXT) LIKE ?" for field in fields])
    query = f"SELECT * FROM {table_name} WHERE {where_clause}"
    params = [like_token] * len(fields)

    conn = get_connection()
    conn.row_factory = dict_factory
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        columns = [column[0] for column in cursor.description] if cursor.description else []
        return columns, results
    finally:
        conn.close()


def run_conditional_search_query(table_key, find_field, field_y, value_a, field_z, value_b):
    ensure_schema_updates()
    fields = TABLE_FIELDS[table_key]
    if find_field not in fields or field_y not in fields or field_z not in fields:
        raise ValueError("Invalid field selected for search.")

    query = (
        f"SELECT DISTINCT {find_field} AS result "
        f"FROM {TABLE_NAMES[table_key]} "
        f"WHERE CAST({field_y} AS TEXT) LIKE ? AND CAST({field_z} AS TEXT) LIKE ?"
    )
    params = [f"%{value_a}%", f"%{value_b}%"]

    conn = get_connection()
    conn.row_factory = dict_factory
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        columns = [column[0] for column in cursor.description] if cursor.description else []
        return columns, results
    finally:
        conn.close()


def get_field_value_options(table_key, limit=200):
    table_name = TABLE_NAMES[table_key]
    fields = TABLE_FIELDS[table_key]
    conn = get_connection()
    conn.row_factory = dict_factory
    options = {}
    try:
        cursor = conn.cursor()
        for field in fields:
            query = (
                f"SELECT DISTINCT CAST({field} AS TEXT) AS value "
                f"FROM {table_name} "
                f"WHERE {field} IS NOT NULL "
                "ORDER BY 1 "
                "LIMIT ?"
            )
            cursor.execute(query, (limit,))
            options[field] = [row["value"] for row in cursor.fetchall()]
        return options
    finally:
        conn.close()


def run_parameterized_select(query, params=()):
    ensure_schema_updates()
    conn = get_connection()
    conn.row_factory = dict_factory
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        columns = [column[0] for column in cursor.description] if cursor.description else []
        return columns, results
    finally:
        conn.close()


def run_update_technician_phone(technician_id, new_phone):
    ensure_schema_updates()
    query = "UPDATE Technician SET phone = ? WHERE technicianID = ?"
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, (new_phone, technician_id))
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def run_cascade_delete_client(client_id):
    ensure_schema_updates()
    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT sampleID FROM Sample WHERE cID = ?", (client_id,))
        sample_ids = [row[0] for row in cursor.fetchall()]

        deleted_counts = {
            "test_results": 0,
            "conducts_test_on": 0,
            "subsample": 0,
            "sample": 0,
            "company": 0,
            "individual": 0,
            "client": 0,
        }

        if sample_ids:
            placeholders = ",".join(["?"] * len(sample_ids))
            cursor.execute(
                f"DELETE FROM TestMeasurement WHERE testRunID IN (SELECT testRunID FROM TestRun WHERE sampleID IN ({placeholders}))",
                sample_ids,
            )
            deleted_counts["test_results"] = cursor.rowcount

            cursor.execute(f"DELETE FROM TestRun WHERE sampleID IN ({placeholders})", sample_ids)
            deleted_counts["conducts_test_on"] = cursor.rowcount

            cursor.execute(f"DELETE FROM SubSample WHERE sampleID IN ({placeholders})", sample_ids)
            deleted_counts["subsample"] = cursor.rowcount

        cursor.execute("DELETE FROM Sample WHERE cID = ?", (client_id,))
        deleted_counts["sample"] = cursor.rowcount

        cursor.execute("DELETE FROM Company WHERE cID = ?", (client_id,))
        deleted_counts["company"] = cursor.rowcount

        cursor.execute("DELETE FROM Individual WHERE cID = ?", (client_id,))
        deleted_counts["individual"] = cursor.rowcount

        cursor.execute("DELETE FROM Client WHERE clientID = ?", (client_id,))
        deleted_counts["client"] = cursor.rowcount

        conn.commit()
        return deleted_counts
    finally:
        conn.close()


def run_insert_query(table_key, values):
    ensure_schema_updates()
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
    ensure_schema_updates()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM Sample WHERE sampleID = ?", (sample_id,))
        return cursor.fetchone() is not None
    finally:
        conn.close()


def run_delete_query(table_key, values):
    ensure_schema_updates()
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


def fetch_company_clients(test_status):
    division_true = (
        "NOT EXISTS ("
        "SELECT 1 FROM Sample s "
        "WHERE s.cID = c.clientID "
        "AND NOT EXISTS (SELECT 1 FROM TestRun tr WHERE tr.sampleID = s.sampleID)"
        ")"
    )
    where_clause = ""
    if test_status == "all_tested":
        where_clause = f"WHERE {division_true}"
    elif test_status == "not_all_tested":
        where_clause = f"WHERE NOT {division_true}"

    query = (
        "SELECT co.cID AS clientID, co.name AS displayName, c.email, "
        f"CASE WHEN {division_true} THEN 1 ELSE 0 END AS allTested "
        "FROM Company co "
        "JOIN Client c ON co.cID = c.clientID "
        f"{where_clause} "
        "ORDER BY co.name"
    )
    return run_select_query(query)[1]


def fetch_individual_clients(test_status):
    division_true = (
        "NOT EXISTS ("
        "SELECT 1 FROM Sample s "
        "WHERE s.cID = c.clientID "
        "AND NOT EXISTS (SELECT 1 FROM TestRun tr WHERE tr.sampleID = s.sampleID)"
        ")"
    )
    where_clause = ""
    if test_status == "all_tested":
        where_clause = f"WHERE {division_true}"
    elif test_status == "not_all_tested":
        where_clause = f"WHERE NOT {division_true}"

    query = (
        "SELECT i.cID AS clientID, i.firstName || ' ' || i.lastName AS displayName, c.email, "
        f"CASE WHEN {division_true} THEN 1 ELSE 0 END AS allTested "
        "FROM Individual i "
        "JOIN Client c ON i.cID = c.clientID "
        f"{where_clause} "
        "ORDER BY i.lastName, i.firstName"
    )
    return run_select_query(query)[1]


def fetch_samples_for_main(sample_filter):
    where_clause = ""
    if sample_filter == "tested":
        where_clause = "WHERE EXISTS (SELECT 1 FROM TestRun tr WHERE tr.sampleID = s.sampleID)"
    elif sample_filter == "untested":
        where_clause = "WHERE NOT EXISTS (SELECT 1 FROM TestRun tr WHERE tr.sampleID = s.sampleID)"

    query = (
        "SELECT s.sampleID, s.description, s.dateReceived, s.cID AS clientID, c.email, s.sID AS storageID, "
        "CASE WHEN EXISTS (SELECT 1 FROM TestRun tr WHERE tr.sampleID = s.sampleID) THEN 1 ELSE 0 END AS tested "
        "FROM Sample s "
        "JOIN Client c ON c.clientID = s.cID "
        f"{where_clause} "
        "ORDER BY s.sampleID"
    )
    return run_select_query(query)[1]


def get_client_type(client_id):
    _, rows = run_parameterized_select(
        "SELECT 'company' AS clientType FROM Company WHERE cID = ? "
        "UNION ALL "
        "SELECT 'individual' AS clientType FROM Individual WHERE cID = ?",
        (client_id, client_id),
    )
    return rows[0]["clientType"] if rows else None


def run_cascade_delete_storage(storage_id):
    ensure_schema_updates()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT sampleID FROM Sample WHERE sID = ?", (storage_id,))
        sample_ids = [row[0] for row in cursor.fetchall()]

        deleted_counts = {
            "test_results": 0,
            "conducts_test_on": 0,
            "subsample": 0,
            "sample": 0,
            "storage_location": 0,
        }

        if sample_ids:
            placeholders = ",".join(["?"] * len(sample_ids))
            cursor.execute(
                f"DELETE FROM TestMeasurement WHERE testRunID IN (SELECT testRunID FROM TestRun WHERE sampleID IN ({placeholders}))",
                sample_ids,
            )
            deleted_counts["test_results"] = cursor.rowcount

            cursor.execute(f"DELETE FROM TestRun WHERE sampleID IN ({placeholders})", sample_ids)
            deleted_counts["conducts_test_on"] = cursor.rowcount

            cursor.execute(f"DELETE FROM SubSample WHERE sampleID IN ({placeholders})", sample_ids)
            deleted_counts["subsample"] = cursor.rowcount

        cursor.execute("DELETE FROM Sample WHERE sID = ?", (storage_id,))
        deleted_counts["sample"] = cursor.rowcount

        cursor.execute("DELETE FROM StorageLocation WHERE storageID = ?", (storage_id,))
        deleted_counts["storage_location"] = cursor.rowcount

        conn.commit()
        return deleted_counts
    finally:
        conn.close()


def get_entry_url(table_key, row):
    if table_key == "client":
        return url_for("client_detail", client_id=row["clientID"])
    if table_key == "storage_location":
        return url_for("storage_location_detail", storage_id=row["storageID"])
    if table_key == "sample":
        return url_for("sample_detail", sample_id=row["sampleID"])
    if table_key == "technician":
        return url_for("technician_detail", technician_id=row["technicianID"])
    if table_key == "department":
        return url_for("department_detail", department_id=row["departmentID"])
    if table_key == "analyte":
        return url_for("analyte_detail", analyte_id=row["analyteID"])
    if table_key == "subsample":
        return url_for("subsample_detail", sub_sample_id=row["subSampleID"], sample_id=row["sampleID"])
    return None


def create_subsample(subsample_id, sample_id, parent_subsample_id=None):
    ensure_schema_updates()
    conn = get_connection()
    try:
        cursor = conn.cursor()

        if parent_subsample_id:
            cursor.execute(
                "SELECT 1 FROM SubSample WHERE subSampleID = ? AND sampleID = ?",
                (parent_subsample_id, sample_id),
            )
            if cursor.fetchone() is None:
                raise ValueError("Parent SubSample does not exist for this sample.")

        cursor.execute(
            "INSERT INTO SubSample (subSampleID, sampleID, parentSubSampleID) VALUES (?, ?, ?)",
            (subsample_id, sample_id, parent_subsample_id),
        )
        conn.commit()
    finally:
        conn.close()


def add_sample_result(sample_id, technician_id, analyte_id, actual_result):
    ensure_schema_updates()
    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM Analyte WHERE analyteID = ?", (analyte_id,))
        if cursor.fetchone() is None:
            raise ValueError("Selected analyte does not exist.")

        cursor.execute("SELECT COALESCE(MAX(testRunID), 0) + 1 FROM TestRun")
        test_run_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO TestRun (testRunID, sampleID, technicianID, testType, performedAt, instrument, status, notes) "
            "VALUES (?, ?, ?, ?, DATETIME('now'), NULL, ?, NULL)",
            (test_run_id, sample_id, technician_id, 'Ad Hoc Result Entry', 'completed'),
        )
        cursor.execute(
            "INSERT INTO TestMeasurement (testRunID, analyteID, valueNumeric, valueText) "
            "VALUES (?, ?, ?, ?)",
            (
                test_run_id,
                analyte_id,
                float(actual_result) if actual_result not in (None, "") and _is_number(actual_result) else None,
                None if actual_result not in (None, "") and _is_number(actual_result) else (actual_result if actual_result else None),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _is_number(value):
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def add_subsample_result(subsample_id, sample_id, technician_id, analyte_id, actual_result):
    ensure_schema_updates()
    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM Analyte WHERE analyteID = ?", (analyte_id,))
        analyte_row = cursor.fetchone()
        if analyte_row is None:
            raise ValueError("Selected analyte does not exist.")
        analyte_name = analyte_row[0]

        cursor.execute(
            "INSERT INTO SubSampleResult (subSampleID, sampleID, tID, description, actualResult) VALUES (?, ?, ?, ?, ?)",
            (subsample_id, sample_id, technician_id, analyte_name, actual_result),
        )
        conn.commit()
    finally:
        conn.close()


def get_subsample_hierarchy(sample_id):
    _, rows = run_parameterized_select(
        "SELECT subSampleID, sampleID, parentSubSampleID "
        "FROM SubSample WHERE sampleID = ?",
        (sample_id,),
    )

    by_parent = {}
    for row in rows:
        parent = row["parentSubSampleID"]
        by_parent.setdefault(parent, []).append(row)

    for parent_key in by_parent:
        by_parent[parent_key].sort(key=lambda item: item["subSampleID"])

    ordered = []

    def walk(parent_id, depth):
        for item in by_parent.get(parent_id, []):
            ordered.append(
                {
                    "subSampleID": item["subSampleID"],
                    "sampleID": item["sampleID"],
                    "parentSubSampleID": item["parentSubSampleID"],
                    "depth": depth,
                }
            )
            walk(item["subSampleID"], depth + 1)

    walk(None, 0)
    return ordered


def build_subsample_tree(subsamples):
    node_map = {}
    for subsample in subsamples:
        parent_id = subsample["parentSubSampleID"]
        if isinstance(parent_id, str):
            parent_id = parent_id.strip() or None
        node_map[subsample["subSampleID"]] = {
            "subSampleID": subsample["subSampleID"],
            "sampleID": subsample["sampleID"],
            "parentSubSampleID": parent_id,
            "children": [],
        }

    roots = []
    for node in node_map.values():
        parent_id = node["parentSubSampleID"]
        if parent_id and parent_id in node_map:
            node_map[parent_id]["children"].append(node)
        else:
            roots.append(node)

    def sort_nodes(nodes):
        nodes.sort(key=lambda item: item["subSampleID"])
        for child in nodes:
            sort_nodes(child["children"])

    sort_nodes(roots)
    return roots


@app.route("/")
def home():
    ensure_schema_updates()
    action_message = request.args.get("action_message", "").strip()
    client_test_status = request.args.get("client_test_status", "all")
    if client_test_status not in {"all", "all_tested", "not_all_tested"}:
        client_test_status = "all"

    sample_filter = request.args.get("sample_filter", "all")
    if sample_filter not in {"all", "tested", "untested"}:
        sample_filter = "all"

    companies = fetch_company_clients(client_test_status)
    individuals = fetch_individual_clients(client_test_status)
    samples = fetch_samples_for_main(sample_filter)

    return render_template(
        'index.html',
        table_labels=TABLE_LABELS,
        default_table=DEFAULT_TABLE,
        companies=companies,
        individuals=individuals,
        samples=samples,
        client_test_status=client_test_status,
        sample_filter=sample_filter,
        action_message=action_message,
    )


@app.route("/client/<int:client_id>", methods=["GET", "POST"])
def client_detail(client_id):
    ensure_schema_updates()
    error = None
    action_message = None

    if request.method == "POST":
        action = request.form.get("action", "update").strip()

        if action == "delete_cascade":
            try:
                deleted = run_cascade_delete_client(client_id)
                summary = (
                    f"Deleted client {client_id} with cascade: "
                    f"Client={deleted['client']}, "
                    f"Company={deleted['company']}, "
                    f"Individual={deleted['individual']}, "
                    f"Sample={deleted['sample']}, "
                    f"SubSample={deleted['subsample']}, "
                    f"TestRun={deleted['conducts_test_on']}, "
                    f"TestMeasurement={deleted['test_results']}"
                )
                return redirect(url_for("home", action_message=summary))
            except sqlite3.Error as exc:
                error = str(exc)
        else:
            email = request.form.get("email", "").strip()
            client_type = request.form.get("client_type", "").strip()
            name = request.form.get("name", "").strip()
            first_name = request.form.get("first_name", "").strip()
            last_name = request.form.get("last_name", "").strip()

            if not email:
                error = "email is required."
            else:
                conn = get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE Client SET email = ? WHERE clientID = ?", (email, client_id))

                    if client_type == "company":
                        if not name:
                            raise ValueError("company name is required.")
                        cursor.execute("UPDATE Company SET name = ? WHERE cID = ?", (name, client_id))
                    else:
                        if not first_name or not last_name:
                            raise ValueError("first_name and last_name are required.")
                        cursor.execute(
                            "UPDATE Individual SET firstName = ?, lastName = ? WHERE cID = ?",
                            (first_name, last_name, client_id),
                        )

                    conn.commit()
                    action_message = "Client entry updated successfully."
                except (sqlite3.Error, ValueError) as exc:
                    conn.rollback()
                    error = str(exc)
                finally:
                    conn.close()

    _, client_rows = run_parameterized_select(
        "SELECT c.clientID, c.email, co.name AS companyName, i.firstName, i.lastName "
        "FROM Client c "
        "LEFT JOIN Company co ON co.cID = c.clientID "
        "LEFT JOIN Individual i ON i.cID = c.clientID "
        "WHERE c.clientID = ?",
        (client_id,),
    )
    if not client_rows:
        return "Client not found.", 404

    client = client_rows[0]
    client_type = "company" if client["companyName"] else "individual"

    _, sample_rows = run_parameterized_select(
        "SELECT s.sampleID, s.description, s.dateReceived, "
        "CASE WHEN EXISTS (SELECT 1 FROM TestRun tr WHERE tr.sampleID = s.sampleID) THEN 1 ELSE 0 END AS tested "
        "FROM Sample s "
        "WHERE s.cID = ? "
        "ORDER BY s.sampleID",
        (client_id,),
    )

    _, division_rows = run_parameterized_select(
        "SELECT CASE WHEN NOT EXISTS ("
        "SELECT 1 FROM Sample s "
        "WHERE s.cID = ? "
        "AND NOT EXISTS (SELECT 1 FROM TestRun tr WHERE tr.sampleID = s.sampleID)"
        ") THEN 1 ELSE 0 END AS allSamplesTested",
        (client_id,),
    )
    all_samples_tested = bool(division_rows[0]["allSamplesTested"]) if division_rows else False

    _, sample_count_rows = run_parameterized_select(
        "SELECT c.clientID, c.email, COUNT(s.sampleID) AS sampleCount "
        "FROM Client c "
        "LEFT JOIN Sample s ON c.clientID = s.cID "
        "WHERE c.clientID = ? "
        "GROUP BY c.clientID, c.email",
        (client_id,),
    )
    sample_count = sample_count_rows[0]["sampleCount"] if sample_count_rows else 0
    tested_sample_count = sum(1 for sample in sample_rows if sample["tested"])
    tested_percentage = round((tested_sample_count / sample_count) * 100, 1) if sample_count else 0.0

    return render_template(
        "client_detail.html",
        client=client,
        client_type=client_type,
        sample_rows=sample_rows,
        sample_count=sample_count,
        tested_sample_count=tested_sample_count,
        tested_percentage=tested_percentage,
        all_samples_tested=all_samples_tested,
        error=error,
        action_message=action_message,
    )


@app.route("/storage-location/<int:storage_id>", methods=["GET", "POST"])
def storage_location_detail(storage_id):
    ensure_schema_updates()
    error = None
    action_message = None

    if request.method == "POST":
        action = request.form.get("action", "update")
        try:
            if action == "delete_cascade":
                deleted = run_cascade_delete_storage(storage_id)
                summary = (
                    f"Deleted storage location {storage_id} with cascade: "
                    f"StorageLocation={deleted['storage_location']}, "
                    f"Sample={deleted['sample']}, "
                    f"SubSample={deleted['subsample']}, "
                    f"TestRun={deleted['conducts_test_on']}, "
                    f"TestMeasurement={deleted['test_results']}"
                )
                return redirect(url_for("home", action_message=summary))

            address = request.form.get("address", "").strip()
            capacity = request.form.get("capacity", "").strip()
            if not address or not capacity:
                raise ValueError("address and capacity are required.")

            conn = get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE StorageLocation SET address = ?, capacity = ? WHERE storageID = ?",
                    (address, capacity, storage_id),
                )
                conn.commit()
                action_message = "Storage location updated successfully."
            finally:
                conn.close()
        except (sqlite3.Error, ValueError) as exc:
            error = str(exc)

    _, storage_rows = run_parameterized_select(
        "SELECT storageID, address, capacity FROM StorageLocation WHERE storageID = ?",
        (storage_id,),
    )
    if not storage_rows:
        return "Storage location not found.", 404
    storage = storage_rows[0]

    _, sample_rows = run_parameterized_select(
        "SELECT sampleID, description, dateReceived FROM Sample WHERE sID = ? ORDER BY sampleID",
        (storage_id,),
    )

    _, count_rows = run_parameterized_select(
        "SELECT COUNT(*) AS sampleCount FROM Sample WHERE sID = ?",
        (storage_id,),
    )
    sample_count = count_rows[0]["sampleCount"] if count_rows else 0

    return render_template(
        "storage_location_detail.html",
        storage=storage,
        sample_rows=sample_rows,
        sample_count=sample_count,
        error=error,
        action_message=action_message,
    )


@app.route("/technician/<int:technician_id>", methods=["GET", "POST"])
def technician_detail(technician_id):
    ensure_schema_updates()
    error = None
    action_message = None

    if request.method == "POST":
        values = {
            "firstName": request.form.get("firstName", "").strip(),
            "lastName": request.form.get("lastName", "").strip(),
            "email": request.form.get("email", "").strip(),
            "phone": request.form.get("phone", "").strip(),
            "depID": request.form.get("depID", "").strip(),
        }
        if any(not val for val in values.values()):
            error = "All technician fields are required."
        else:
            try:
                conn = get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE Technician SET firstName = ?, lastName = ?, email = ?, phone = ?, depID = ? "
                        "WHERE technicianID = ?",
                        (
                            values["firstName"],
                            values["lastName"],
                            values["email"],
                            values["phone"],
                            values["depID"],
                            technician_id,
                        ),
                    )
                    conn.commit()
                    action_message = "Technician entry updated successfully."
                finally:
                    conn.close()
            except sqlite3.Error as exc:
                error = str(exc)

    _, tech_rows = run_parameterized_select(
        "SELECT t.technicianID, t.firstName, t.lastName, t.email, t.phone, t.depID, "
        "d.name AS departmentName, d.managerID, "
        "m.firstName || ' ' || m.lastName AS managerName, "
        "COUNT(DISTINCT ct.sampleID) AS sampleCount "
        "FROM Technician t "
        "LEFT JOIN Department d ON d.departmentID = t.depID "
        "LEFT JOIN Technician m ON m.technicianID = d.managerID "
        "LEFT JOIN TestRun ct ON ct.technicianID = t.technicianID "
        "WHERE t.technicianID = ? "
        "GROUP BY t.technicianID, t.firstName, t.lastName, t.email, t.phone, t.depID, d.name, d.managerID, managerName",
        (technician_id,),
    )
    if not tech_rows:
        return "Technician not found.", 404
    technician = tech_rows[0]

    _, tested_samples = run_parameterized_select(
        "SELECT DISTINCT s.sampleID, s.description "
        "FROM TestRun ct "
        "JOIN Sample s ON s.sampleID = ct.sampleID "
        "WHERE ct.technicianID = ? "
        "ORDER BY s.sampleID",
        (technician_id,),
    )

    return render_template(
        "technician_detail.html",
        technician=technician,
        tested_samples=tested_samples,
        error=error,
        action_message=action_message,
    )


@app.route("/department/<int:department_id>", methods=["GET", "POST"])
def department_detail(department_id):
    ensure_schema_updates()
    error = None
    action_message = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        manager_id = request.form.get("managerID", "").strip()
        if not name or not manager_id:
            error = "name and managerID are required."
        else:
            try:
                conn = get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE Department SET name = ?, managerID = ? WHERE departmentID = ?",
                        (name, manager_id, department_id),
                    )
                    conn.commit()
                    action_message = "Department entry updated successfully."
                finally:
                    conn.close()
            except sqlite3.Error as exc:
                error = str(exc)

    _, department_rows = run_parameterized_select(
        "SELECT d.departmentID, d.name, d.managerID, "
        "m.firstName || ' ' || m.lastName AS managerName, "
        "COUNT(ct.sampleID) AS testsPerformed "
        "FROM Department d "
        "LEFT JOIN Technician m ON m.technicianID = d.managerID "
        "LEFT JOIN Technician t ON t.depID = d.departmentID "
        "LEFT JOIN TestRun ct ON ct.technicianID = t.technicianID "
        "WHERE d.departmentID = ? "
        "GROUP BY d.departmentID, d.name, d.managerID, managerName",
        (department_id,),
    )
    if not department_rows:
        return "Department not found.", 404
    department = department_rows[0]

    _, technicians = run_parameterized_select(
        "SELECT technicianID, firstName, lastName, email "
        "FROM Technician WHERE depID = ? ORDER BY technicianID",
        (department_id,),
    )

    return render_template(
        "department_detail.html",
        department=department,
        technicians=technicians,
        error=error,
        action_message=action_message,
    )


@app.route("/analyte/<int:analyte_id>", methods=["GET", "POST"])
def analyte_detail(analyte_id):
    ensure_schema_updates()
    error = None
    action_message = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        default_unit = request.form.get("defaultUnit", "").strip()
        data_type = request.form.get("dataType", "").strip()

        if not name or not data_type:
            error = "name and dataType are required."
        else:
            try:
                conn = get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE Analyte SET name = ?, defaultUnit = ?, dataType = ? WHERE analyteID = ?",
                        (name, default_unit if default_unit else None, data_type, analyte_id),
                    )
                    conn.commit()
                    action_message = "Analyte updated successfully."
                finally:
                    conn.close()
            except sqlite3.Error as exc:
                error = str(exc)

    _, analyte_rows = run_parameterized_select(
        "SELECT analyteID, name, defaultUnit, dataType FROM Analyte WHERE analyteID = ?",
        (analyte_id,),
    )
    if not analyte_rows:
        return "Analyte not found.", 404
    analyte = analyte_rows[0]

    _, usage_rows = run_parameterized_select(
        "SELECT COUNT(*) AS measurementCount FROM TestMeasurement WHERE analyteID = ?",
        (analyte_id,),
    )
    measurement_count = usage_rows[0]["measurementCount"] if usage_rows else 0

    return render_template(
        "analyte_detail.html",
        analyte=analyte,
        measurement_count=measurement_count,
        error=error,
        action_message=action_message,
    )


@app.route("/sample/<int:sample_id>", methods=["GET", "POST"])
def sample_detail(sample_id):
    ensure_schema_updates()
    error = None
    action_message = None

    if request.method == "POST":
        action = request.form.get("action", "rename").strip()

        if action == "add_subsample":
            new_subsample_id = request.form.get("new_subsample_id", "").strip()
            if not new_subsample_id:
                error = "new_subsample_id is required."
            else:
                try:
                    create_subsample(new_subsample_id, sample_id, None)
                    action_message = "SubSample created successfully."
                except (sqlite3.Error, ValueError) as exc:
                    error = str(exc)
        elif action == "add_result":
            technician_id = request.form.get("result_tid", "").strip()
            analyte_id = request.form.get("result_analyte_id", "").strip()
            actual_result = request.form.get("result_value", "").strip()

            if not technician_id or not analyte_id:
                error = "result_tid and result_analyte_id are required."
            else:
                try:
                    add_sample_result(sample_id, technician_id, analyte_id, actual_result or None)
                    action_message = "Sample result added successfully."
                except (sqlite3.Error, ValueError) as exc:
                    error = str(exc)
        else:
            new_description = request.form.get("description", "").strip()
            if not new_description:
                error = "description is required."
            else:
                try:
                    conn = get_connection()
                    try:
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE Sample SET description = ? WHERE sampleID = ?",
                            (new_description, sample_id),
                        )
                        conn.commit()
                        action_message = "Sample description updated successfully."
                    finally:
                        conn.close()
                except sqlite3.Error as exc:
                    error = str(exc)

    _, sample_rows = run_parameterized_select(
        "SELECT s.sampleID, s.description, s.dateReceived, s.cID AS clientID, s.sID AS storageID, c.email, "
        "co.name AS companyName, i.firstName, i.lastName, sl.address AS storageAddress "
        "FROM Sample s "
        "JOIN Client c ON c.clientID = s.cID "
        "LEFT JOIN Company co ON co.cID = c.clientID "
        "LEFT JOIN Individual i ON i.cID = c.clientID "
        "LEFT JOIN StorageLocation sl ON sl.storageID = s.sID "
        "WHERE s.sampleID = ?",
        (sample_id,),
    )
    if not sample_rows:
        return "Sample not found.", 404
    sample = sample_rows[0]

    _, result_rows = run_parameterized_select(
        "SELECT tr.technicianID AS tID, a.name AS results, "
        "COALESCE(tm.valueText, CAST(tm.valueNumeric AS TEXT)) AS actualResult, "
        "a.defaultUnit AS resultUnit "
        "FROM TestRun tr "
        "JOIN TestMeasurement tm ON tm.testRunID = tr.testRunID "
        "JOIN Analyte a ON a.analyteID = tm.analyteID "
        "WHERE tr.sampleID = ? "
        "ORDER BY tr.testRunID, tm.analyteID",
        (sample_id,),
    )
    tested = len(result_rows) > 0

    _, analyte_options = run_select_query(
        "SELECT analyteID, name, defaultUnit, dataType FROM Analyte ORDER BY analyteID"
    )

    subsamples = get_subsample_hierarchy(sample_id)
    subsample_tree = build_subsample_tree(subsamples)

    return render_template(
        "sample_detail.html",
        sample=sample,
        tested=tested,
        result_rows=result_rows,
        analyte_options=analyte_options,
        subsamples=subsamples,
        subsample_tree=subsample_tree,
        error=error,
        action_message=action_message,
    )


@app.route("/subsample/<string:sub_sample_id>/<int:sample_id>", methods=["GET", "POST"])
def subsample_detail(sub_sample_id, sample_id):
    ensure_schema_updates()
    error = None
    action_message = None

    current_subsample_id = sub_sample_id

    if request.method == "POST":
        action = request.form.get("action", "rename").strip()
        if action == "add_child":
            child_subsample_id = request.form.get("child_subSampleID", "").strip()
            if not child_subsample_id:
                error = "child_subSampleID is required."
            else:
                try:
                    create_subsample(child_subsample_id, sample_id, current_subsample_id)
                    action_message = "Child SubSample created successfully."
                except (sqlite3.Error, ValueError) as exc:
                    error = str(exc)
        elif action == "add_result":
            technician_id = request.form.get("result_tid", "").strip()
            analyte_id = request.form.get("result_analyte_id", "").strip()
            actual_result = request.form.get("result_value", "").strip()

            if not technician_id or not analyte_id:
                error = "result_tid and result_analyte_id are required."
            else:
                try:
                    add_subsample_result(
                        current_subsample_id,
                        sample_id,
                        technician_id,
                        analyte_id,
                        actual_result or None,
                    )
                    action_message = "SubSample result added successfully."
                except (sqlite3.Error, ValueError) as exc:
                    error = str(exc)
        else:
            new_subsample_id = request.form.get("subSampleID", "").strip()
            if not new_subsample_id:
                error = "subSampleID is required."
            else:
                try:
                    conn = get_connection()
                    try:
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE SubSample SET subSampleID = ? WHERE subSampleID = ? AND sampleID = ?",
                            (new_subsample_id, sub_sample_id, sample_id),
                        )
                        cursor.execute(
                            "UPDATE SubSample SET parentSubSampleID = ? WHERE parentSubSampleID = ? AND sampleID = ?",
                            (new_subsample_id, sub_sample_id, sample_id),
                        )
                        conn.commit()
                        action_message = "SubSample entry updated successfully."
                        current_subsample_id = new_subsample_id
                    finally:
                        conn.close()
                except sqlite3.Error as exc:
                    error = str(exc)

    _, subsample_rows = run_parameterized_select(
        "SELECT ss.subSampleID, ss.sampleID, ss.parentSubSampleID, s.description "
        "FROM SubSample ss "
        "JOIN Sample s ON s.sampleID = ss.sampleID "
        "WHERE ss.subSampleID = ? AND ss.sampleID = ?",
        (current_subsample_id, sample_id),
    )
    if not subsample_rows:
        return "SubSample not found.", 404

    _, child_rows = run_parameterized_select(
        "SELECT subSampleID, sampleID FROM SubSample "
        "WHERE sampleID = ? AND parentSubSampleID = ? ORDER BY subSampleID",
        (sample_id, current_subsample_id),
    )

    _, subsample_result_rows = run_parameterized_select(
        "SELECT ssr.tID, ssr.description, ssr.actualResult, a.defaultUnit AS resultUnit "
        "FROM SubSampleResult "
        "ssr LEFT JOIN Analyte a ON a.name = ssr.description "
        "WHERE ssr.subSampleID = ? AND ssr.sampleID = ? "
        "ORDER BY ssr.tID",
        (current_subsample_id, sample_id),
    )

    subsample_tested = len(subsample_result_rows) > 0

    _, analyte_options = run_select_query(
        "SELECT analyteID, name, defaultUnit, dataType FROM Analyte ORDER BY analyteID"
    )

    return render_template(
        "subsample_detail.html",
        subsample=subsample_rows[0],
        child_rows=child_rows,
        subsample_result_rows=subsample_result_rows,
        analyte_options=analyte_options,
        subsample_tested=subsample_tested,
        error=error,
        action_message=action_message,
    )


@app.route("/search", methods=["GET"])
@app.route("/serach", methods=["GET"])
def search_by_page():
    ensure_schema_updates()
    selected_table = request.args.get("category", DEFAULT_TABLE)
    if selected_table not in TABLE_NAMES:
        selected_table = DEFAULT_TABLE

    search_text = request.args.get("q", "").strip()
    find_field = request.args.get("find", "").strip()
    field_y = request.args.get("y", "").strip()
    value_a = request.args.get("a", "").strip()
    field_z = request.args.get("z", "").strip()
    value_b = request.args.get("b", "").strip()
    quick_field = request.args.get("quick_field", "").strip()
    quick_value = request.args.get("quick_value", "").strip()
    error = None
    columns = []
    results = []
    selected_fields = TABLE_FIELDS[selected_table]
    field_value_options = get_field_value_options(selected_table)

    try:
        has_conditional_search = all([find_field, field_y, value_a, field_z, value_b])
        if has_conditional_search:
            columns, results = run_conditional_search_query(
                selected_table,
                find_field,
                field_y,
                value_a,
                field_z,
                value_b,
            )
        elif quick_field and quick_value:
            if quick_field not in selected_fields:
                raise ValueError("Invalid field selected for dropdown search.")
            query = (
                f"SELECT * FROM {TABLE_NAMES[selected_table]} "
                f"WHERE CAST({quick_field} AS TEXT) = ?"
            )
            columns, results = run_parameterized_select(query, (quick_value,))
        else:
            columns, results = run_search_query(selected_table, search_text)
    except ValueError as exc:
        error = str(exc)
    except sqlite3.Error as exc:
        error = str(exc)

    return render_template(
        "search.html",
        table_labels=TABLE_LABELS,
        selected_table=selected_table,
        selected_label=TABLE_LABELS[selected_table],
        selected_fields=selected_fields,
        search_text=search_text,
        find_field=find_field,
        field_y=field_y,
        value_a=value_a,
        field_z=field_z,
        value_b=value_b,
        quick_field=quick_field,
        quick_value=quick_value,
        field_value_options=field_value_options,
        columns=columns,
        results=results,
        error=error,
    )


@app.route("/sql-demo", methods=["GET", "POST"])
def sql_demo_page():
    ensure_schema_updates()

    def request_value(key, default=""):
        if request.method == "POST":
            return request.form.get(key, request.args.get(key, default))
        return request.args.get(key, default)

    selected_demo = request_value("demo", "join")
    result_columns = []
    result_rows = []
    error = None
    action_message = None

    demo_queries = {
        "division": (
            "SELECT c.clientID, c.email "
            "FROM Client c "
            "WHERE NOT EXISTS ("
            "SELECT s.sampleID FROM Sample s WHERE s.cID = c.clientID "
            "EXCEPT "
            "SELECT tr.sampleID FROM TestRun tr "
            "JOIN Sample s2 ON s2.sampleID = tr.sampleID "
            "WHERE s2.cID = c.clientID"
            ")"
            "ORDER BY c.clientID"
        ),
        "aggregation": (
            "SELECT t.technicianID, t.firstName, t.lastName, "
            "COUNT(tr.testRunID) AS totalTestRuns, "
            "COUNT(DISTINCT tr.sampleID) AS uniqueSamplesTested, "
            "CASE "
            "WHEN totals.totalRuns = 0 THEN 0 "
            "ELSE ROUND(100.0 * COUNT(tr.testRunID) / totals.totalRuns, 1) "
            "END AS workloadPercent "
            "FROM Technician t "
            "LEFT JOIN TestRun tr ON tr.technicianID = t.technicianID "
            "CROSS JOIN (SELECT COUNT(*) AS totalRuns FROM TestRun) totals "
            "GROUP BY t.technicianID, t.firstName, t.lastName, totals.totalRuns "
            "ORDER BY totalTestRuns DESC, uniqueSamplesTested DESC, t.technicianID"
        ),
    }
    demo_queries_display = {
        key: format_sql_for_display(query)
        for key, query in demo_queries.items()
    }

    storage_id = request_value("storage_id", "101").strip()
    technician_id = request_value("technician_id", "").strip()
    join_technician_id = request_value("join_technician_id", "").strip()
    group_client_id = request_value("group_client_id", "").strip()
    cascade_client_id = request_value("cascade_client_id", "").strip()

    _, offboarding_clients = run_select_query(
        "SELECT co.cID AS clientID, co.name AS displayName, 'company' AS clientType "
        "FROM Company co "
        "UNION ALL "
        "SELECT i.cID AS clientID, i.firstName || ' ' || i.lastName AS displayName, 'individual' AS clientType "
        "FROM Individual i "
        "ORDER BY displayName"
    )

    _, technicians_for_update = run_select_query(
        "SELECT technicianID, firstName || ' ' || lastName AS displayName "
        "FROM Technician "
        "ORDER BY technicianID"
    )

    if request.method == "POST":
        try:
            if selected_demo in demo_queries:
                result_columns, result_rows = run_select_query(demo_queries[selected_demo])

            elif selected_demo == "join":
                action_message = (
                    "Sample ownership and assigned technician join is demonstrated on the Technician Detail page. "
                    "Use the link helper in this demo section to open a technician."
                )

            elif selected_demo == "group_by":
                action_message = (
                    "Client workload summary by number of samples is shown on the Client Detail page. "
                    "Use the link helper in this demo section to open a client."
                )

            elif selected_demo == "update":
                action_message = (
                    "Technician contact correction now runs from the Technician Detail page. "
                    "Use the link helper in this demo section to open a technician and update there."
                )

            elif selected_demo == "cascade_delete":
                action_message = (
                    "Client offboarding runs from the Client Detail page. "
                    "Use the link in this demo section to open a client and run cascade delete there."
                )
            else:
                error = "Unknown demo type selected."
        except ValueError as exc:
            error = str(exc)
        except sqlite3.Error as exc:
            error = str(exc)

    return render_template(
        "sql_demo.html",
        selected_demo=selected_demo,
        demo_queries=demo_queries,
        demo_queries_display=demo_queries_display,
        demo_titles=SQL_DEMO_TITLES,
        storage_id=storage_id,
        join_technician_id=join_technician_id,
        group_client_id=group_client_id,
        technician_id=technician_id,
        technicians_for_update=technicians_for_update,
        cascade_client_id=cascade_client_id,
        offboarding_clients=offboarding_clients,
        result_columns=result_columns,
        result_rows=result_rows,
        error=error,
        action_message=action_message,
    )


@app.route("/<table_key>", methods=["GET", "POST"])
def table_page(table_key):
    ensure_schema_updates()
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
        entry_url_builder=get_entry_url,
        error=error,
        action_message=action_message,
    )

def get_individuals():
    run_select_query('''SELECT *
        FROM Individual
        LEFT JOIN Client
        ON Individual.cID = Client.clientID''')

def get_companies():
    run_select_query('''SELECT *
        FROM Company
        LEFT JOIN Client
        ON Company.cID = Client.clientID''')

def samples_by_client(clientID):
    run_select_query('''SELECT sampleID as ID, description, dateRecieved,
    CASE
        WHEN EXISTS(
            SELECT *
            FROM TestRun
            WHERE sampleID = ID
        ) THEN "true"
        ELSE "false"
    END as tested
    FROM Sample
    WHERE cID = ''' + clientID)

#enable debugging
if __name__ == '__main__':
    app.run(debug=True)   

