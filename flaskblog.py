#create Flask instance

import sqlite3
from flask import Flask, render_template, url_for, flash, redirect
app = Flask(__name__)

#Turn the results from the database into a dictionary
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

@app.route("/")

#home page
@app.route("/home")
def home():
    conn = sqlite3.connect('samples.db')
    conn.row_factory = dict_factory

    c = conn.cursor()
    c.execute('SELECT * FROM Technicians')
    technicians = c.fetchall()
    return render_template('home.html', technicians=technicians)

#enable debugging
if __name__ == '__main__':
    app.run(debug=True)   