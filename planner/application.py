import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date, datetime, timedelta
from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///planner.db")

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        new_table = request.form.get("new_table")
        temp = db.execute("SELECT * FROM tables WHERE user_id = ? AND name = ?", session["user_id"], new_table)
        if len(temp) != 0:
            flash("That name is already taken")
            return redirect("/")
        db.execute("INSERT INTO tables (user_id, name) VALUES (?, ?)", session["user_id"], new_table)
    tables = db.execute("SELECT DISTINCT * FROM tables WHERE user_id = ?", session["user_id"])
    if len(tables)== 0:
        tables = None
    return render_template("index.html", tables = tables)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("Wrong username or password")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")
    
@app.route("/register", methods=["GET", "POST"])
@login_required
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    else:
        username = request.form.get("username")
        if not username:
            return apology("You need to put in a username")
        rows = db.execute("SELECT username FROM users WHERE username = :username", username=username)
        # Ensure username exists and password is correct
        if len(rows) == 1:
            return apology("Username taken")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        if not password:
            return apology("You need to put in a password")
        if not confirmation:
            return apology("You need to fill in the confirmation")
        if password != confirmation:
            return apology("Your passwords don't match")
        db.execute("INSERT INTO users (username, hash) VALUES (:username, :password)", username=username, password=generate_password_hash(password))
        return redirect("/")

@app.route("/tasks", methods=["GET", "POST"])
@login_required
def tasks():
    table_name = request.form.get("table_name")
    table = db.execute("SELECT * FROM table_values WHERE user_id = ? AND table_name = ? AND completed = 'false'", session["user_id"], table_name)
    if len(table) == 0:
        table = None
    return render_template("tasks.html", table=table, table_name = table_name)
    
@app.route("/remove", methods=["POST"])
@login_required
def remove():
    task = request.form.get("task_submit")
    table_name = request.form.get("table_name")
    today = date.today()
    db.execute("UPDATE table_values SET completed = 'true', completed_date = ? WHERE user_id = ? AND table_name = ? AND task = ?", today, session["user_id"], table_name, task)
    table = db.execute("SELECT * FROM table_values WHERE user_id = ? AND table_name = ? AND completed = 'false'", session["user_id"], table_name)
    return render_template("tasks.html", table = table, table_name = table_name)

@app.route("/add", methods=["POST"])
@login_required
def add():
    table_name = request.form.get("table_name")
    return render_template("add.html", table_name = table_name)

@app.route("/update", methods=["POST"])
@login_required
def update():
    task = request.form.get("new_task")
    date = request.form.get("date")
    priority = request.form.get("priority")
    details = request.form.get("textarea")
    table_name = request.form.get("table_name")
    if not date:
        date = "NA"
    if priority is None:
        priority = "NA"
    if not details:
        details = "NA"
    db.execute("INSERT INTO table_values (user_id, task, table_name, date, priority, completed, details) VALUES (?, ?, ?, ?, ?, ?, ?)", session["user_id"], task, table_name, date, priority, "false", details)
    table = db.execute("SELECT * FROM table_values WHERE user_id = ? AND table_name = ? AND completed = 'false'", session["user_id"], table_name)
    return render_template("/tasks.html", table = table, table_name = table_name)

@app.route("/history")
@login_required
def history():
    table = db.execute("SELECT * FROM table_values WHERE user_id = ? AND completed = 'true' ORDER BY completed_date DESC LIMIT 25", session["user_id"])
    return render_template("history.html", table = table)
    
@app.route("/current", methods=["GET", "POST"])
@login_required
def current():
    today = datetime.today().strftime('%Y-%m-%d')
    overdue = db.execute("SELECT * FROM table_values WHERE user_id = ? AND completed = 'false' AND date < ?", session["user_id"], today)
    if request.method=="GET":
        table = db.execute("SELECT * FROM table_values WHERE user_id = ? AND completed = 'false' AND date = ?", session["user_id"], today)
        return render_template("current.html", table = table, time_frame = "Day", overdue = overdue)
    else:
        time_frame = request.form.get("time_frame")
        dt = datetime.now()
        if time_frame == "all":
            table = db.execute("SELECT * FROM table_values WHERE user_id = ? AND completed = 'false' AND date >= ? ORDER BY date", session["user_id"], today)
            return render_template("current.html", overdue = overdue, table = table, time_frame = time_frame.capitalize())
        elif time_frame == "year":
            td = timedelta(days=365)
        elif time_frame == "month":
            td = timedelta(days=30)
        elif time_frame == "day":
            td = timedelta(days=0)
        else:
            td = timedelta(days=7)
            # your calculated date
        my_date = (dt + td).strftime('%Y-%m-%d')
        table = db.execute("SELECT * FROM table_values WHERE user_id = ? AND completed = 'false' AND date BETWEEN ? AND ? ORDER BY date", session["user_id"], today, my_date)
        return render_template("current.html", table = table, overdue = overdue, time_frame = time_frame.capitalize()) 
        
@app.route("/remove/current", methods=["POST"])
def remove_current():
    task = request.form.get("task_submit")
    table_name = request.form.get("table_name")
    time_frame = request.form.get("time_frame")
    today = date.today()
    db.execute("UPDATE table_values SET completed = 'true', completed_date = ? WHERE user_id = ? AND table_name = ? AND task = ?", today, session["user_id"], table_name, task)
    table = db.execute("SELECT * FROM table_values WHERE user_id = ? AND completed = 'false' AND date = ?", session["user_id"], today)
    overdue = db.execute("SELECT * FROM table_values WHERE user_id = ? AND completed = 'false' AND date < ?", session["user_id"], today)
    return render_template("current.html", table = table, table_name = table_name, overdue = overdue, time_frame = time_frame)

@app.route("/remove/index", methods=["POST"])
def remove_index():
    table = request.form.get("table")
    db.execute("DELETE FROM tables WHERE user_id = ? AND name = ?", session["user_id"], table)
    db.execute("DELETE FROM table_values WHERE user_id = ? AND table_name = ? AND completed = 'false'", session["user_id"], table)
    tables = db.execute("SELECT DISTINCT * FROM tables WHERE user_id = ?", session["user_id"])
    if len(tables) == 0:
        tables = None
    return render_template("index.html", tables = tables)