# CMPT 354 Group Project — Geological Sample Management System

## Project Description
This project is a web-based database viewer for managing geological samples,
built using Python (Flask) and SQLite. It allows users to track clients,
technicians, departments, samples, subsamples, storage locations, and test
results through a browser interface. The system demonstrates core relational
database concepts including joins, division, aggregation, cascade deletion,
and update operations.

## Prerequisites (Fresh Environment)

- Python 3.10 or higher
- pip (Python package manager)

**External libraries required:**
```bash
pip install flask
```

No other external dependencies. `sqlite3` is included in Python's standard library.

---

## Step-by-Step Run Guide

### Step 1: Clone the Repository + Go to Folder
```bash
git clone https://github.com/LoganSadowski/CMPT354-Group-Project.git
cd CMPT354-Group-Project
```



### Step 2: Install Dependencies
```bash
pip install flask
```

### Step 3: Run the Application
```bash
python flaskMain.py
```

Open your browser and navigate to: `http://127.0.0.1:5000`

## (Optional) Reinitialize the Database

A `reinit.sh` script is included if you need to reset the database 
back to its original state (e.g., after testing cascade deletes).

> ⚠️ **Warning: This permanently deletes all current data in `samples.db`.**

### On Mac/Linux:
```bash
chmod +x reinit.sh
./reinit.sh
```

### On Windows:
```bash
reinit.sh
```

---

## YouTube Links
- [Implementation Demo](https://youtu.be/u8QNSyg2-gQ)
- [Application Demo](https://www.youtube.com/watch?v=dQw4w9WgXcQ)
