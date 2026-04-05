#create Flask instance

import sqlite3
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
    "subsample": ["subSampleID", "sampleID", "parentSubSampleID"],
    "conducts_test_on": ["tID", "sampleID", "time", "instrument"],
    "test_results": ["tID", "sID", "results", "actualResult"],
}

OPTIONAL_FIELDS = {
    "sample": {"sID"},
    "conducts_test_on": {"time", "instrument"},
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
    "subsample": ["subSampleID", "sampleID"],
    "conducts_test_on": ["tID", "sampleID"],
    "test_results": ["tID", "sID", "results"],
}

SQL_DEMO_TITLES = {
    "join": "Sample Ownership and Assigned Technician (Join)",
    "division": "Technicians Who Tested Every Sample in a Storage Location (Division)",
    "aggregation": "Overall Sample Intake Timeline and Count (Aggregation)",
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

        cursor.execute("PRAGMA table_info(TestResults)")
        test_result_columns = {row[1] for row in cursor.fetchall()}
        if "actualResult" not in test_result_columns:
            cursor.execute("ALTER TABLE TestResults ADD COLUMN actualResult VARCHAR(100)")

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
            cursor.execute(f"DELETE FROM TestResults WHERE sID IN ({placeholders})", sample_ids)
            deleted_counts["test_results"] = cursor.rowcount

            cursor.execute(f"DELETE FROM ConductsTestOn WHERE sampleID IN ({placeholders})", sample_ids)
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
        "AND NOT EXISTS (SELECT 1 FROM TestResults tr WHERE tr.sID = s.sampleID)"
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
        "AND NOT EXISTS (SELECT 1 FROM TestResults tr WHERE tr.sID = s.sampleID)"
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
        where_clause = "WHERE EXISTS (SELECT 1 FROM TestResults tr WHERE tr.sID = s.sampleID)"
    elif sample_filter == "untested":
        where_clause = "WHERE NOT EXISTS (SELECT 1 FROM TestResults tr WHERE tr.sID = s.sampleID)"

    query = (
        "SELECT s.sampleID, s.description, s.dateReceived, s.cID AS clientID, c.email, s.sID AS storageID, "
        "CASE WHEN EXISTS (SELECT 1 FROM TestResults tr WHERE tr.sID = s.sampleID) THEN 1 ELSE 0 END AS tested "
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
            cursor.execute(f"DELETE FROM TestResults WHERE sID IN ({placeholders})", sample_ids)
            deleted_counts["test_results"] = cursor.rowcount

            cursor.execute(f"DELETE FROM ConductsTestOn WHERE sampleID IN ({placeholders})", sample_ids)
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


def add_sample_result(sample_id, technician_id, description, actual_result):
    ensure_schema_updates()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO ConductsTestOn (tID, sampleID, time, instrument) VALUES (?, ?, NULL, NULL)",
            (technician_id, sample_id),
        )
        cursor.execute(
            "INSERT INTO TestResults (tID, sID, results, actualResult) VALUES (?, ?, ?, ?)",
            (technician_id, sample_id, description, actual_result),
        )
        conn.commit()
    finally:
        conn.close()


def add_subsample_result(subsample_id, sample_id, technician_id, description, actual_result):
    ensure_schema_updates()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO SubSampleResult (subSampleID, sampleID, tID, description, actualResult) VALUES (?, ?, ?, ?, ?)",
            (subsample_id, sample_id, technician_id, description, actual_result),
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
        "CASE WHEN EXISTS (SELECT 1 FROM TestResults tr WHERE tr.sID = s.sampleID) THEN 1 ELSE 0 END AS tested "
        "FROM Sample s "
        "WHERE s.cID = ? "
        "ORDER BY s.sampleID",
        (client_id,),
    )

    _, division_rows = run_parameterized_select(
        "SELECT CASE WHEN NOT EXISTS ("
        "SELECT 1 FROM Sample s "
        "WHERE s.cID = ? "
        "AND NOT EXISTS (SELECT 1 FROM TestResults tr WHERE tr.sID = s.sampleID)"
        ") THEN 1 ELSE 0 END AS allSamplesTested",
        (client_id,),
    )
    all_samples_tested = bool(division_rows[0]["allSamplesTested"]) if division_rows else False

    return render_template(
        "client_detail.html",
        client=client,
        client_type=client_type,
        sample_rows=sample_rows,
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
                    f"ConductsTestOn={deleted['conducts_test_on']}, "
                    f"TestResults={deleted['test_results']}"
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
        "LEFT JOIN ConductsTestOn ct ON ct.tID = t.technicianID "
        "WHERE t.technicianID = ? "
        "GROUP BY t.technicianID, t.firstName, t.lastName, t.email, t.phone, t.depID, d.name, d.managerID, managerName",
        (technician_id,),
    )
    if not tech_rows:
        return "Technician not found.", 404
    technician = tech_rows[0]

    _, tested_samples = run_parameterized_select(
        "SELECT DISTINCT s.sampleID, s.description "
        "FROM ConductsTestOn ct "
        "JOIN Sample s ON s.sampleID = ct.sampleID "
        "WHERE ct.tID = ? "
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
        "LEFT JOIN ConductsTestOn ct ON ct.tID = t.technicianID "
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
            result_description = request.form.get("result_description", "").strip()
            actual_result = request.form.get("result_value", "").strip()

            if not technician_id or not result_description:
                error = "result_tid and result_description are required."
            else:
                try:
                    add_sample_result(sample_id, technician_id, result_description, actual_result or None)
                    action_message = "Sample result added successfully."
                except sqlite3.Error as exc:
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
        "SELECT tr.tID, tr.results, tr.actualResult "
        "FROM TestResults tr WHERE tr.sID = ? ORDER BY tr.tID",
        (sample_id,),
    )
    tested = len(result_rows) > 0

    subsamples = get_subsample_hierarchy(sample_id)

    return render_template(
        "sample_detail.html",
        sample=sample,
        tested=tested,
        result_rows=result_rows,
        subsamples=subsamples,
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
            result_description = request.form.get("result_description", "").strip()
            actual_result = request.form.get("result_value", "").strip()

            if not technician_id or not result_description:
                error = "result_tid and result_description are required."
            else:
                try:
                    add_subsample_result(
                        current_subsample_id,
                        sample_id,
                        technician_id,
                        result_description,
                        actual_result or None,
                    )
                    action_message = "SubSample result added successfully."
                except sqlite3.Error as exc:
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
        "SELECT tID, description, actualResult "
        "FROM SubSampleResult "
        "WHERE subSampleID = ? AND sampleID = ? "
        "ORDER BY tID",
        (current_subsample_id, sample_id),
    )

    subsample_tested = len(subsample_result_rows) > 0

    return render_template(
        "subsample_detail.html",
        subsample=subsample_rows[0],
        child_rows=child_rows,
        subsample_result_rows=subsample_result_rows,
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
    error = None
    columns = []
    results = []
    selected_fields = TABLE_FIELDS[selected_table]

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
        columns=columns,
        results=results,
        error=error,
    )


@app.route("/sql-demo", methods=["GET", "POST"])
def sql_demo_page():
    ensure_schema_updates()
    selected_demo = request.values.get("demo", "join")
    result_columns = []
    result_rows = []
    error = None
    action_message = None

    demo_queries = {
        "join": (
            "SELECT s.sampleID, s.description, c.email AS clientEmail, "
            "t.firstName || ' ' || t.lastName AS technicianName "
            "FROM Sample s "
            "JOIN Client c ON s.cID = c.clientID "
            "LEFT JOIN ConductsTestOn ct ON s.sampleID = ct.sampleID "
            "LEFT JOIN Technician t ON ct.tID = t.technicianID "
            "ORDER BY s.sampleID"
        ),
        "division": (
            "SELECT t.technicianID, t.firstName, t.lastName "
            "FROM Technician t "
            "WHERE NOT EXISTS ("
            "SELECT s.sampleID FROM Sample s WHERE s.sID = ? "
            "EXCEPT "
            "SELECT ct.sampleID FROM ConductsTestOn ct WHERE ct.tID = t.technicianID"
            ")"
        ),
        "aggregation": (
            "SELECT COUNT(*) AS totalSamples, "
            "MIN(dateReceived) AS earliestDateReceived, "
            "MAX(dateReceived) AS latestDateReceived "
            "FROM Sample"
        ),
        "group_by": (
            "SELECT c.clientID, c.email, COUNT(s.sampleID) AS sampleCount "
            "FROM Client c "
            "LEFT JOIN Sample s ON c.clientID = s.cID "
            "GROUP BY c.clientID, c.email "
            "ORDER BY sampleCount DESC, c.clientID"
        ),
    }

    storage_id = request.values.get("storage_id", "101").strip()
    technician_id = request.values.get("technician_id", "").strip()
    new_phone = request.values.get("new_phone", "").strip()
    cascade_client_id = request.values.get("cascade_client_id", "").strip()

    if request.method == "POST":
        try:
            if selected_demo in demo_queries:
                if selected_demo == "division":
                    if not storage_id:
                        raise ValueError("storage_id is required for division query.")
                    result_columns, result_rows = run_parameterized_select(
                        demo_queries[selected_demo],
                        (storage_id,),
                    )
                else:
                    result_columns, result_rows = run_select_query(demo_queries[selected_demo])

            elif selected_demo == "update":
                if not technician_id or not new_phone:
                    raise ValueError("technician_id and new_phone are required for update.")
                changed = run_update_technician_phone(technician_id, new_phone)
                action_message = f"Updated {changed} technician row(s)."
                result_columns, result_rows = run_parameterized_select(
                    "SELECT technicianID, firstName, lastName, phone FROM Technician WHERE technicianID = ?",
                    (technician_id,),
                )

            elif selected_demo == "cascade_delete":
                if not cascade_client_id:
                    raise ValueError("cascade_client_id is required for cascade delete.")
                deleted_counts = run_cascade_delete_client(cascade_client_id)
                action_message = (
                    "Cascade delete summary for client "
                    f"{cascade_client_id}: "
                    f"Client={deleted_counts['client']}, "
                    f"Company={deleted_counts['company']}, "
                    f"Individual={deleted_counts['individual']}, "
                    f"Sample={deleted_counts['sample']}, "
                    f"SubSample={deleted_counts['subsample']}, "
                    f"ConductsTestOn={deleted_counts['conducts_test_on']}, "
                    f"TestResults={deleted_counts['test_results']}"
                )
                result_columns = ["table", "deleted_rows"]
                result_rows = [
                    {"table": "Client", "deleted_rows": deleted_counts["client"]},
                    {"table": "Company", "deleted_rows": deleted_counts["company"]},
                    {"table": "Individual", "deleted_rows": deleted_counts["individual"]},
                    {"table": "Sample", "deleted_rows": deleted_counts["sample"]},
                    {"table": "SubSample", "deleted_rows": deleted_counts["subsample"]},
                    {"table": "ConductsTestOn", "deleted_rows": deleted_counts["conducts_test_on"]},
                    {"table": "TestResults", "deleted_rows": deleted_counts["test_results"]},
                ]
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
        demo_titles=SQL_DEMO_TITLES,
        storage_id=storage_id,
        technician_id=technician_id,
        new_phone=new_phone,
        cascade_client_id=cascade_client_id,
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
            FROM TestResults
            WHERE sampleID = ID
        ) THEN "true"
        ELSE "false"
    END as tested
    FROM Sample
    WHERE cID = ''' + clientID)

#enable debugging
if __name__ == '__main__':
    app.run(debug=True)   

