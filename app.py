from flask import Flask, render_template, request, redirect, url_for, g
import sqlite3
import os

app = Flask(__name__)
DATABASE = 'vsc.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        # Auto-initialize database if it doesn't exist (useful for cloud deployments)
        if not os.path.exists(DATABASE):
            import init_db
            init_db.init_db()
            
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys = ON;')
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def index():
    db = get_db()
    # Summary stats
    stats = {}
    stats['customers'] = db.execute("SELECT COUNT(*) FROM Customer").fetchone()[0]
    stats['active_jobs'] = db.execute("SELECT COUNT(*) FROM Job_Card WHERE JobStatus != 'Closed'").fetchone()[0]
    rev_row = db.execute("SELECT SUM(NetAmount) FROM Invoice").fetchone()
    stats['revenue'] = rev_row[0] if rev_row[0] else 0
    stats['low_stock'] = db.execute("SELECT COUNT(*) FROM Spare_Part WHERE StockQty <= ReorderLevel").fetchone()[0]

    # Chart data: Mechanic Workload
    cur = db.execute("SELECT m.Name, COUNT(a.AssignmentID) as TaskCount FROM Mechanic m LEFT JOIN Assignment a ON m.MechanicID = a.MechanicID GROUP BY m.MechanicID")
    workload = cur.fetchall()
    mechanics = [row['Name'] for row in workload]
    tasks = [row['TaskCount'] for row in workload]

    return render_template('index.html', stats=stats, mechanics=mechanics, tasks=tasks)

@app.route('/customers', methods=['GET', 'POST'])
def customers():
    db = get_db()
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        email = request.form['email']
        address = request.form['address']
        try:
            db.execute("INSERT INTO Customer (Name, Phone, Email, Address) VALUES (?, ?, ?, ?)", (name, phone, email, address))
            db.commit()
        except sqlite3.Error as e:
            return f"An error occurred: {e}"
        return redirect(url_for('customers'))
    
    cur = db.execute("SELECT * FROM Customer")
    customers = cur.fetchall()
    return render_template('customers.html', customers=customers)

@app.route('/vehicles', methods=['GET', 'POST'])
def vehicles():
    db = get_db()
    if request.method == 'POST':
        reg_no = request.form['reg_no']
        customer_id = request.form['customer_id']
        make = request.form['make']
        model = request.form['model']
        year = request.form['year']
        fuel_type = request.form['fuel_type']
        try:
            db.execute("INSERT INTO Vehicle (RegNo, CustomerID, Make, Model, MfgYear, FuelType) VALUES (?, ?, ?, ?, ?, ?)", (reg_no, customer_id, make, model, year, fuel_type))
            db.commit()
        except sqlite3.Error as e:
            return f"An error occurred: {e}"
        return redirect(url_for('vehicles'))
        
    cur = db.execute("SELECT v.*, c.Name as CustomerName FROM Vehicle v JOIN Customer c ON v.CustomerID = c.CustomerID")
    vehicles = cur.fetchall()
    cur = db.execute("SELECT * FROM Customer")
    customers = cur.fetchall()
    return render_template('vehicles.html', vehicles=vehicles, customers=customers)

@app.route('/bookings', methods=['GET', 'POST'])
def bookings():
    db = get_db()
    if request.method == 'POST':
        reg_no = request.form['reg_no']
        booking_date = request.form['booking_date']
        slot_time = request.form['slot_time']
        try:
            db.execute("INSERT INTO Service_Booking (RegNo, BookingDate, SlotTime) VALUES (?, ?, ?)", (reg_no, booking_date, slot_time))
            db.commit()
        except sqlite3.Error as e:
            return f"An error occurred: {e}"
        return redirect(url_for('bookings'))
        
    cur = db.execute("SELECT b.*, v.Make, v.Model, c.Name as CustomerName FROM Service_Booking b JOIN Vehicle v ON b.RegNo = v.RegNo JOIN Customer c ON v.CustomerID = c.CustomerID")
    bookings = cur.fetchall()
    cur = db.execute("SELECT * FROM Vehicle")
    vehicles = cur.fetchall()
    return render_template('bookings.html', bookings=bookings, vehicles=vehicles)

@app.route('/job_cards')
def job_cards():
    db = get_db()
    cur = db.execute("SELECT j.*, b.RegNo FROM Job_Card j JOIN Service_Booking b ON j.BookingID = b.BookingID")
    job_cards = cur.fetchall()
    return render_template('job_cards.html', job_cards=job_cards)

@app.route('/inventory')
def inventory():
    db = get_db()
    cur = db.execute("SELECT * FROM Spare_Part")
    parts = cur.fetchall()
    return render_template('inventory.html', parts=parts)

@app.route('/billing')
def billing():
    db = get_db()
    cur = db.execute("SELECT i.*, b.RegNo, c.Name as CustomerName FROM Invoice i JOIN Job_Card j ON i.JobCardID = j.JobCardID JOIN Service_Booking b ON j.BookingID = b.BookingID JOIN Vehicle v ON b.RegNo = v.RegNo JOIN Customer c ON v.CustomerID = c.CustomerID")
    invoices = cur.fetchall()
    return render_template('billing.html', invoices=invoices)

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
