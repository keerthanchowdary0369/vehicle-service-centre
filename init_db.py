import sqlite3
import os

def init_db():
    db_path = 'vsc.db'
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute('PRAGMA foreign_keys = ON;')

    schema = """
    CREATE TABLE Customer (
      CustomerID INTEGER PRIMARY KEY AUTOINCREMENT,
      Name VARCHAR(60) NOT NULL,
      Phone CHAR(10) NOT NULL UNIQUE,
      Email VARCHAR(80) UNIQUE,
      Address VARCHAR(150)
    );

    CREATE TABLE Vehicle (
      RegNo VARCHAR(12) PRIMARY KEY,
      CustomerID INTEGER NOT NULL,
      Make VARCHAR(30) NOT NULL,
      Model VARCHAR(30) NOT NULL,
      MfgYear INTEGER CHECK (MfgYear BETWEEN 1990 AND 2030),
      FuelType VARCHAR(10) CHECK (FuelType IN ('Petrol','Diesel','CNG','Electric')),
      FOREIGN KEY (CustomerID) REFERENCES Customer(CustomerID) ON DELETE CASCADE
    );

    CREATE TABLE Service_Booking (
      BookingID INTEGER PRIMARY KEY AUTOINCREMENT,
      RegNo VARCHAR(12) NOT NULL,
      BookingDate DATE NOT NULL,
      SlotTime TIME NOT NULL,
      Status VARCHAR(12) DEFAULT 'Booked' CHECK (Status IN ('Booked','Checked-In','Completed','Cancelled')),
      UNIQUE (RegNo, BookingDate, SlotTime),
      FOREIGN KEY (RegNo) REFERENCES Vehicle(RegNo)
    );

    CREATE TABLE Job_Card (
      JobCardID INTEGER PRIMARY KEY AUTOINCREMENT,
      BookingID INTEGER NOT NULL UNIQUE,
      DateIn DATE NOT NULL,
      DateOut DATE,
      JobStatus VARCHAR(12) DEFAULT 'Open' CHECK (JobStatus IN ('Open','In Progress','Closed')),
      CHECK (DateOut IS NULL OR DateOut >= DateIn),
      FOREIGN KEY (BookingID) REFERENCES Service_Booking(BookingID)
    );

    CREATE TABLE Mechanic (
      MechanicID INTEGER PRIMARY KEY AUTOINCREMENT,
      Name VARCHAR(60) NOT NULL,
      Specialization VARCHAR(40),
      Phone CHAR(10) UNIQUE
    );

    CREATE TABLE Task (
      TaskID INTEGER PRIMARY KEY AUTOINCREMENT,
      TaskName VARCHAR(60) NOT NULL UNIQUE,
      LaborRate DECIMAL(8,2) CHECK (LaborRate >= 0)
    );

    CREATE TABLE Assignment (
      AssignmentID INTEGER PRIMARY KEY AUTOINCREMENT,
      JobCardID INTEGER NOT NULL,
      TaskID INTEGER NOT NULL,
      MechanicID INTEGER NOT NULL,
      StartTime DATETIME NOT NULL,
      EndTime DATETIME,
      Status VARCHAR(12) DEFAULT 'Assigned',
      CHECK (EndTime IS NULL OR EndTime > StartTime),
      FOREIGN KEY (JobCardID) REFERENCES Job_Card(JobCardID),
      FOREIGN KEY (TaskID) REFERENCES Task(TaskID),
      FOREIGN KEY (MechanicID) REFERENCES Mechanic(MechanicID)
    );

    CREATE TABLE Spare_Part (
      PartID INTEGER PRIMARY KEY AUTOINCREMENT,
      PartName VARCHAR(60) NOT NULL UNIQUE,
      UnitPrice DECIMAL(8,2) CHECK (UnitPrice > 0),
      StockQty INTEGER NOT NULL DEFAULT 0 CHECK (StockQty >= 0),
      ReorderLevel INTEGER DEFAULT 5
    );

    CREATE TABLE Part_Usage (
      UsageID INTEGER PRIMARY KEY AUTOINCREMENT,
      JobCardID INTEGER NOT NULL,
      PartID INTEGER NOT NULL,
      Quantity INTEGER NOT NULL CHECK (Quantity > 0),
      BilledUnitPrice DECIMAL(8,2) NOT NULL,
      FOREIGN KEY (JobCardID) REFERENCES Job_Card(JobCardID),
      FOREIGN KEY (PartID) REFERENCES Spare_Part(PartID)
    );

    CREATE TABLE Invoice (
      InvoiceID INTEGER PRIMARY KEY AUTOINCREMENT,
      JobCardID INTEGER NOT NULL UNIQUE,
      LaborTotal DECIMAL(10,2) DEFAULT 0,
      PartsTotal DECIMAL(10,2) DEFAULT 0,
      NetAmount DECIMAL(10,2) DEFAULT 0,
      PaymentStatus VARCHAR(10) DEFAULT 'Unpaid',
      FOREIGN KEY (JobCardID) REFERENCES Job_Card(JobCardID)
    );

    -- Triggers
    CREATE TRIGGER trg_no_overlap
    BEFORE INSERT ON Assignment
    FOR EACH ROW
    BEGIN
      SELECT CASE
        WHEN EXISTS (
          SELECT 1 FROM Assignment
          WHERE MechanicID = NEW.MechanicID
            AND (NEW.StartTime < EndTime AND NEW.EndTime > StartTime)
        )
        THEN RAISE(ABORT, 'Mechanic already booked in that time slot')
      END;
    END;

    CREATE TRIGGER trg_check_stock
    BEFORE INSERT ON Part_Usage
    FOR EACH ROW
    BEGIN
      SELECT CASE
        WHEN (SELECT StockQty FROM Spare_Part WHERE PartID = NEW.PartID) < NEW.Quantity
        THEN RAISE(ABORT, 'Insufficient stock')
      END;
    END;

    CREATE TRIGGER trg_deduct_stock
    AFTER INSERT ON Part_Usage
    FOR EACH ROW
    BEGIN
      UPDATE Spare_Part
      SET StockQty = StockQty - NEW.Quantity
      WHERE PartID = NEW.PartID;
    END;
    """

    cursor.executescript(schema)

    # Sample Data
    sample_data = [
        "INSERT INTO Customer (Name, Phone, Email, Address) VALUES ('Ravi Kumar', '9876543210', 'ravi@mail.com', 'Madhapur');",
        "INSERT INTO Customer (Name, Phone, Email, Address) VALUES ('Anita Rao', '9123456780', 'anita@mail.com', 'Gachibowli');",
        "INSERT INTO Customer (Name, Phone, Email, Address) VALUES ('Suresh Reddy', '9988776655', 'suresh@mail.com', 'Kukatpally');",
        
        "INSERT INTO Vehicle VALUES ('TS09AB1234', 1, 'Honda', 'City', 2019, 'Petrol');",
        "INSERT INTO Vehicle VALUES ('TS08CD5678', 2, 'Hyundai', 'Creta', 2021, 'Diesel');",
        "INSERT INTO Vehicle VALUES ('TS10EF9012', 1, 'Maruti', 'Swift', 2017, 'Petrol');",
        
        "INSERT INTO Service_Booking (RegNo, BookingDate, SlotTime, Status) VALUES ('TS09AB1234', '2026-10-05', '10:00', 'Checked-In');",
        "INSERT INTO Service_Booking (RegNo, BookingDate, SlotTime, Status) VALUES ('TS08CD5678', '2026-10-06', '11:30', 'Booked');",
        "INSERT INTO Service_Booking (RegNo, BookingDate, SlotTime, Status) VALUES ('TS10EF9012', '2026-09-20', '09:30', 'Completed');",
        
        "INSERT INTO Job_Card (BookingID, DateIn, DateOut, JobStatus) VALUES (1, '2026-10-05', NULL, 'In Progress');",
        "INSERT INTO Job_Card (BookingID, DateIn, DateOut, JobStatus) VALUES (3, '2026-09-20', '2026-09-22', 'Closed');",
        
        "INSERT INTO Mechanic (Name, Specialization, Phone) VALUES ('Imran Khan', 'Engine', '9000011111');",
        "INSERT INTO Mechanic (Name, Specialization, Phone) VALUES ('Prakash', 'Electrical', '9000022222');",
        
        "INSERT INTO Task (TaskName, LaborRate) VALUES ('Oil Change', 300);",
        "INSERT INTO Task (TaskName, LaborRate) VALUES ('Brake Pad Replacement', 800);",
        "INSERT INTO Task (TaskName, LaborRate) VALUES ('Battery Check', 200);",
        
        "INSERT INTO Assignment (JobCardID, TaskID, MechanicID, StartTime, EndTime) VALUES (1, 1, 1, '2026-10-05 10:15:00', '2026-10-05 10:45:00');",
        "INSERT INTO Assignment (JobCardID, TaskID, MechanicID, StartTime, EndTime) VALUES (1, 2, 1, '2026-10-05 11:00:00', '2026-10-05 12:00:00');",
        
        "INSERT INTO Spare_Part (PartName, UnitPrice, StockQty, ReorderLevel) VALUES ('Engine Oil 1L', 450, 40, 10);",
        "INSERT INTO Spare_Part (PartName, UnitPrice, StockQty, ReorderLevel) VALUES ('Brake Pad Set', 1800, 3, 5);",
        "INSERT INTO Spare_Part (PartName, UnitPrice, StockQty, ReorderLevel) VALUES ('Air Filter', 350, 12, 5);",
        
        "INSERT INTO Part_Usage (JobCardID, PartID, Quantity, BilledUnitPrice) VALUES (1, 1, 4, 450);",
        "INSERT INTO Part_Usage (JobCardID, PartID, Quantity, BilledUnitPrice) VALUES (1, 2, 1, 1800);",
        
        "INSERT INTO Invoice (JobCardID, LaborTotal, PartsTotal, NetAmount, PaymentStatus) VALUES (2, 300, 450, 885, 'Paid');"
    ]

    for stmt in sample_data:
        cursor.execute(stmt)
        
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == '__main__':
    init_db()
