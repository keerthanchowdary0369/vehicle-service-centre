# Vehicle Service Centre DBMS

**Author:** G. Keerthan Chowdary (Roll No: 25WU0102076)

## 🌐 Live Website
**Live Demo Link:** [https://keerthan-vehicle-service.com](https://keerthan-vehicle-service.com)

This project is an end-to-end relational database management system tailored for multi-brand vehicle service facilities, based on the provided presentation (Project 10). It utilizes Python, Flask, and an SQLite 3NF relational database.

## Features implemented from the specification:
- **3NF Relational Database**: Structured following the conceptual ER diagram.
- **Constraints & Triggers**: Includes PK/FK validations, CHECK constraints, UNIQUE rules, and Triggers for resource scheduling and dynamic stock inventory calculation.
- **Service Advisor Interface**: Customer/Vehicle registration and Booking management.
- **Workshop Manager/Billing**: Reviewing invoices and total calculated Net Amounts.
- **Inventory Controller**: Managing and listing stock quantities and automatic reorder level checks.

## Architecture
- **Backend Framework**: Python + Flask
- **Database**: SQLite (built with `PRAGMA foreign_keys = ON;` and database triggers like `trg_no_overlap` and `trg_check_stock`)
- **Frontend**: HTML5 and Bootstrap 5

## How to use
1. Make sure Python is installed.
2. Install dependencies: `py -m pip install flask`
3. Run the application: `py app.py`
4. Access the portal at `http://127.0.0.1:5000`
