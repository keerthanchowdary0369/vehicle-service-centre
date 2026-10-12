"""Vehicle Service Centre Management System (DBMS PBL, Project 10)
Python 3 + SQLite (standard library only).
Run:  python service_centre.py          -> interactive menu
      python service_centre.py --demo   -> scripted demonstration
"""
import sqlite3, sys, os

DB_FILE = "service_centre.db"
GST = 0.18

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS Customer (
  CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,
  Name TEXT NOT NULL, Phone TEXT NOT NULL UNIQUE, Email TEXT UNIQUE, Address TEXT);
CREATE TABLE IF NOT EXISTS Vehicle (
  RegNo TEXT PRIMARY KEY,
  CustomerID INTEGER NOT NULL REFERENCES Customer(CustomerID) ON DELETE CASCADE,
  Make TEXT NOT NULL, Model TEXT NOT NULL,
  MfgYear INTEGER CHECK (MfgYear BETWEEN 1990 AND 2030),
  FuelType TEXT CHECK (FuelType IN ('Petrol','Diesel','CNG','Electric')));
CREATE TABLE IF NOT EXISTS Service_Booking (
  BookingID INTEGER PRIMARY KEY AUTOINCREMENT,
  RegNo TEXT NOT NULL REFERENCES Vehicle(RegNo),
  BookingDate TEXT NOT NULL, SlotTime TEXT NOT NULL,
  Status TEXT DEFAULT 'Booked'
    CHECK (Status IN ('Booked','Checked-In','Completed','Cancelled')),
  UNIQUE (RegNo, BookingDate, SlotTime));
CREATE TABLE IF NOT EXISTS Job_Card (
  JobCardID INTEGER PRIMARY KEY AUTOINCREMENT,
  BookingID INTEGER NOT NULL UNIQUE REFERENCES Service_Booking(BookingID),
  DateIn TEXT NOT NULL, DateOut TEXT,
  JobStatus TEXT DEFAULT 'Open' CHECK (JobStatus IN ('Open','In Progress','Closed')),
  CHECK (DateOut IS NULL OR DateOut >= DateIn));
CREATE TABLE IF NOT EXISTS Mechanic (
  MechanicID INTEGER PRIMARY KEY AUTOINCREMENT,
  Name TEXT NOT NULL, Specialization TEXT, Phone TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS Task (
  TaskID INTEGER PRIMARY KEY AUTOINCREMENT,
  TaskName TEXT NOT NULL UNIQUE, LaborRate REAL CHECK (LaborRate >= 0));
CREATE TABLE IF NOT EXISTS Assignment (
  AssignmentID INTEGER PRIMARY KEY AUTOINCREMENT,
  JobCardID INTEGER NOT NULL REFERENCES Job_Card(JobCardID),
  TaskID INTEGER NOT NULL REFERENCES Task(TaskID),
  MechanicID INTEGER NOT NULL REFERENCES Mechanic(MechanicID),
  StartTime TEXT NOT NULL, EndTime TEXT, Status TEXT DEFAULT 'Assigned',
  CHECK (EndTime IS NULL OR EndTime > StartTime));
CREATE TABLE IF NOT EXISTS Spare_Part (
  PartID INTEGER PRIMARY KEY AUTOINCREMENT,
  PartName TEXT NOT NULL UNIQUE, UnitPrice REAL CHECK (UnitPrice > 0),
  StockQty INTEGER NOT NULL DEFAULT 0 CHECK (StockQty >= 0),
  ReorderLevel INTEGER DEFAULT 5);
CREATE TABLE IF NOT EXISTS Part_Usage (
  UsageID INTEGER PRIMARY KEY AUTOINCREMENT,
  JobCardID INTEGER NOT NULL REFERENCES Job_Card(JobCardID),
  PartID INTEGER NOT NULL REFERENCES Spare_Part(PartID),
  Quantity INTEGER NOT NULL CHECK (Quantity > 0),
  BilledUnitPrice REAL NOT NULL);
CREATE TABLE IF NOT EXISTS Invoice (
  InvoiceID INTEGER PRIMARY KEY AUTOINCREMENT,
  JobCardID INTEGER NOT NULL UNIQUE REFERENCES Job_Card(JobCardID),
  LaborTotal REAL DEFAULT 0, PartsTotal REAL DEFAULT 0, NetAmount REAL DEFAULT 0,
  PaymentStatus TEXT DEFAULT 'Unpaid');

CREATE TRIGGER IF NOT EXISTS trg_no_overlap
BEFORE INSERT ON Assignment
WHEN NEW.EndTime IS NOT NULL AND EXISTS (
  SELECT 1 FROM Assignment a
  WHERE a.MechanicID = NEW.MechanicID AND a.EndTime IS NOT NULL
    AND NEW.StartTime < a.EndTime AND NEW.EndTime > a.StartTime)
BEGIN SELECT RAISE(ABORT, 'Mechanic already booked in that time slot'); END;

CREATE TRIGGER IF NOT EXISTS trg_check_stock
BEFORE INSERT ON Part_Usage
WHEN (SELECT StockQty FROM Spare_Part WHERE PartID = NEW.PartID) < NEW.Quantity
BEGIN SELECT RAISE(ABORT, 'Insufficient stock'); END;

CREATE TRIGGER IF NOT EXISTS trg_deduct_stock
AFTER INSERT ON Part_Usage
BEGIN UPDATE Spare_Part SET StockQty = StockQty - NEW.Quantity
      WHERE PartID = NEW.PartID; END;
"""

def connect(path=DB_FILE):
    con = sqlite3.connect(path)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA)
    return con

def show(con, title, sql, args=()):
    cur = con.execute(sql, args)
    head = [d[0] for d in cur.description]
    rows = [["" if v is None else (f"{v:.2f}" if isinstance(v, float) else str(v)) for v in r]
            for r in cur.fetchall()]
    w = [max(len(h), *(len(r[i]) for r in rows)) if rows else len(h) for i, h in enumerate(head)]
    print(f"\n== {title} ==")
    print("  ".join(h.ljust(w[i]) for i, h in enumerate(head)))
    print("  ".join("-" * x for x in w))
    for r in rows:
        print("  ".join(c.ljust(w[i]) for i, c in enumerate(r)))
    if not rows:
        print("(no rows)")

def run(con, label, sql, args=()):
    """Execute one write; report success or the database's own error message."""
    try:
        cur = con.execute(sql, args); con.commit()
        print(f"[OK]      {label}"); return cur
    except sqlite3.Error as e:
        con.rollback()
        msg = "Duplicate entry rejected (UNIQUE constraint)" if "UNIQUE" in str(e) else e
        print(f"[BLOCKED] {label} -> {msg}"); return None

# ---- operations ----
def add_customer(con, name, phone, email, address):
    c = run(con, f"Register customer {name}",
            "INSERT INTO Customer (Name,Phone,Email,Address) VALUES (?,?,?,?)",
            (name, phone, email, address))
    return c.lastrowid if c else None

def add_vehicle(con, reg, cid, make, model, year, fuel):
    return run(con, f"Register vehicle {reg}",
               "INSERT INTO Vehicle VALUES (?,?,?,?,?,?)", (reg, cid, make, model, year, fuel))

def book_service(con, reg, date, slot):
    c = run(con, f"Book {reg} on {date} {slot}",
            "INSERT INTO Service_Booking (RegNo,BookingDate,SlotTime) VALUES (?,?,?)",
            (reg, date, slot))
    return c.lastrowid if c else None

def check_in(con, booking_id, date):
    run(con, f"Check in booking {booking_id}",
        "UPDATE Service_Booking SET Status='Checked-In' WHERE BookingID=?", (booking_id,))
    c = run(con, f"Open job card for booking {booking_id}",
            "INSERT INTO Job_Card (BookingID,DateIn,JobStatus) VALUES (?,?, 'In Progress')",
            (booking_id, date))
    return c.lastrowid if c else None

def assign_task(con, job, task, mech, start, end):
    return run(con, f"Assign task {task} to mechanic {mech} ({start[-5:]}-{end[-5:]})",
               "INSERT INTO Assignment (JobCardID,TaskID,MechanicID,StartTime,EndTime) "
               "VALUES (?,?,?,?,?)", (job, task, mech, start, end))

def use_part(con, job, part, qty):
    return run(con, f"Use part {part} x{qty} on job card {job}",
               "INSERT INTO Part_Usage (JobCardID,PartID,Quantity,BilledUnitPrice) "
               "SELECT ?,PartID,?,UnitPrice FROM Spare_Part WHERE PartID=?", (job, qty, part))

def generate_invoice(con, job, date):
    labor = con.execute("SELECT IFNULL(SUM(t.LaborRate),0) FROM Assignment a "
                        "JOIN Task t ON t.TaskID=a.TaskID WHERE a.JobCardID=?", (job,)).fetchone()[0]
    parts = con.execute("SELECT IFNULL(SUM(Quantity*BilledUnitPrice),0) FROM Part_Usage "
                        "WHERE JobCardID=?", (job,)).fetchone()[0]
    net = round((labor + parts) * (1 + GST), 2)
    c = run(con, f"Generate invoice for job card {job} (labor {labor:.0f} + parts {parts:.0f} + 18% GST)",
            "INSERT INTO Invoice (JobCardID,LaborTotal,PartsTotal,NetAmount) VALUES (?,?,?,?)",
            (job, labor, parts, net))
    if c:
        con.execute("UPDATE Job_Card SET JobStatus='Closed', DateOut=? WHERE JobCardID=?", (date, job))
        con.execute("UPDATE Service_Booking SET Status='Completed' WHERE BookingID="
                    "(SELECT BookingID FROM Job_Card WHERE JobCardID=?)", (job,))
        con.commit()

def mark_paid(con, invoice_id):
    run(con, f"Mark invoice {invoice_id} paid",
        "UPDATE Invoice SET PaymentStatus='Paid' WHERE InvoiceID=?", (invoice_id,))

# ---- reports ----
def r_low_stock(con):
    show(con, "Low stock parts", "SELECT PartName, StockQty, ReorderLevel FROM Spare_Part "
         "WHERE StockQty <= ReorderLevel")
def r_workload(con):
    show(con, "Mechanic workload", "SELECT m.Name, COUNT(*) AS Tasks, ROUND(SUM((julianday(a.EndTime)"
         "-julianday(a.StartTime))*24),2) AS Hours FROM Mechanic m JOIN Assignment a "
         "ON a.MechanicID=m.MechanicID GROUP BY m.MechanicID, m.Name")
def r_unpaid(con):
    show(con, "Unpaid invoices", "SELECT i.InvoiceID, c.Name, i.NetAmount FROM Invoice i "
         "JOIN Job_Card j ON j.JobCardID=i.JobCardID JOIN Service_Booking b ON b.BookingID=j.BookingID "
         "JOIN Vehicle v ON v.RegNo=b.RegNo JOIN Customer c ON c.CustomerID=v.CustomerID "
         "WHERE i.PaymentStatus='Unpaid'")
def r_revenue(con):
    show(con, "Monthly revenue", "SELECT strftime('%Y-%m', j.DateOut) AS Month, "
         "SUM(i.NetAmount) AS Revenue FROM Invoice i JOIN Job_Card j ON j.JobCardID=i.JobCardID "
         "WHERE j.DateOut IS NOT NULL GROUP BY Month")
def r_jobs(con):
    show(con, "Job cards", "SELECT j.JobCardID, v.RegNo, j.JobStatus, j.DateIn, j.DateOut "
         "FROM Job_Card j JOIN Service_Booking b ON b.BookingID=j.BookingID "
         "JOIN Vehicle v ON v.RegNo=b.RegNo")

def seed(con):
    con.executemany("INSERT OR IGNORE INTO Mechanic (Name,Specialization,Phone) VALUES (?,?,?)",
                    [("Imran Khan", "Engine", "9000011111"), ("Prakash", "Electrical", "9000022222")])
    con.executemany("INSERT OR IGNORE INTO Task (TaskName,LaborRate) VALUES (?,?)",
                    [("Oil Change", 300), ("Brake Pad Replacement", 800), ("Battery Check", 200)])
    con.executemany("INSERT OR IGNORE INTO Spare_Part (PartName,UnitPrice,StockQty,ReorderLevel) VALUES (?,?,?,?)",
                    [("Engine Oil 1L", 450, 40, 10), ("Brake Pad Set", 1800, 3, 5), ("Air Filter", 350, 12, 5)])
    con.commit()

def demo():
    con = connect(":memory:"); seed(con)
    print("--- Step 1-3: register, book, check in ---")
    cid = add_customer(con, "Ravi Kumar", "9876543210", "ravi@mail.com", "Madhapur")
    add_vehicle(con, "TS09AB1234", cid, "Honda", "City", 2019, "Petrol")
    b = book_service(con, "TS09AB1234", "2026-10-12", "10:00")
    book_service(con, "TS09AB1234", "2026-10-12", "10:00")
    job = check_in(con, b, "2026-10-12")
    print("\n--- Step 4: schedule mechanics (overlap trigger) ---")
    assign_task(con, job, 1, 1, "2026-10-12 10:15", "2026-10-12 10:45")
    assign_task(con, job, 2, 1, "2026-10-12 10:30", "2026-10-12 11:30")
    assign_task(con, job, 2, 1, "2026-10-12 11:00", "2026-10-12 12:00")
    print("\n--- Step 5: spare parts (stock trigger) ---")
    use_part(con, job, 1, 4)
    use_part(con, job, 2, 5)
    use_part(con, job, 2, 1)
    print("\n--- Step 6: billing ---")
    generate_invoice(con, job, "2026-10-12")
    print("\n--- Step 7: reports ---")
    r_jobs(con); r_low_stock(con); r_workload(con); r_unpaid(con); r_revenue(con)
    mark_paid(con, 1); r_unpaid(con)

def ask(p): return input(p).strip()

def menu():
    con = connect(); seed(con)
    items = {
     "1": ("Register customer + vehicle", lambda: add_vehicle(con, ask("RegNo: "),
            add_customer(con, ask("Name: "), ask("Phone: "), ask("Email: "), ask("Address: ")),
            ask("Make: "), ask("Model: "), int(ask("Year: ")), ask("Fuel (Petrol/Diesel/CNG/Electric): "))),
     "2": ("Book service", lambda: book_service(con, ask("RegNo: "), ask("Date YYYY-MM-DD: "), ask("Slot HH:MM: "))),
     "3": ("Check in (open job card)", lambda: check_in(con, int(ask("BookingID: ")), ask("Date YYYY-MM-DD: "))),
     "4": ("Assign task", lambda: assign_task(con, int(ask("JobCardID: ")), int(ask("TaskID: ")),
            int(ask("MechanicID: ")), ask("Start YYYY-MM-DD HH:MM: "), ask("End YYYY-MM-DD HH:MM: "))),
     "5": ("Use spare part", lambda: use_part(con, int(ask("JobCardID: ")), int(ask("PartID: ")), int(ask("Qty: ")))),
     "6": ("Generate invoice", lambda: generate_invoice(con, int(ask("JobCardID: ")), ask("Date YYYY-MM-DD: "))),
     "7": ("Mark invoice paid", lambda: mark_paid(con, int(ask("InvoiceID: ")))),
     "8": ("Report: job cards", lambda: r_jobs(con)),
     "9": ("Report: low stock", lambda: r_low_stock(con)),
     "10": ("Report: mechanic workload", lambda: r_workload(con)),
     "11": ("Report: unpaid invoices", lambda: r_unpaid(con)),
     "12": ("Report: monthly revenue", lambda: r_revenue(con)),
    }
    while True:
        print("\nVEHICLE SERVICE CENTRE MANAGEMENT SYSTEM")
        for k, (t, _) in items.items(): print(f"{k:>3}. {t}")
        print("  0. Exit")
        ch = ask("Choice: ")
        if ch == "0": break
        if ch in items:
            try: items[ch][1]()
            except ValueError: print("Invalid input.")
    con.close()

if __name__ == "__main__":
    demo() if "--demo" in sys.argv else menu()
