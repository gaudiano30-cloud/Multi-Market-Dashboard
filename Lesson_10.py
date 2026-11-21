# LESSON 10 PYTHON
# SQL; Database Management; Financial Data Providers and Database Libraries

# WHAT IS A DATABASE (DB)? Relational database
# WHAT IS THE LANGUAGE TO OPERATE WITH DATABASE? SQL (STRUCTURE QUERY LANGUAGE)
# HOW TO USE SQL IN PYTHON? you need a package

# On Excel:
# To "query" (=to ask) the database = to ask to get the info back from the database
# Primary key (PK) := when we query the database, it allows us to recognize in an unique way an instance inside an entity
# class entity (customer) in the database -> analogy with Python classes;
# for each object of the class entity we are going to have attributes (columns)
# primary key is an attribute

# you can connect tables (entities) -> spare memory
# Foreign Key (FK):= it links an instance of the entity with another entity
# When you put entities together, the operation is called JOIN

# -----------------------------------------------------------------------------------------------------------------
# How to create entities in SQL?
# Syntax to create a table in SQL
# CAPITAL LETTERS FOR SQL

# I'm in the Spyder environment but the following is not Python code, it's SQL
# CREATE TABLE Customer (attributes of this entity = head of the columns)
# Syntax:
# CREATE TABLE Customer (
#       ID_Customer INTEGER PRIMARY KEY,
#       Name TEXT NOT NULL # integrity
#       Surname TEXT NOT NULL
# )

# -----------------------------------------------------------------------------------------------------------------
# How to use SQL in Python?
# One of the packages that does that is sqlite3
import sqlite3  # it allows put instruction in SQL and make Python do the job

# Create and connect to the database (difference between RAM and hard disk)
# the info about the connection is inside the obj conn
conn = sqlite3.connect("exampledatabase.db")
# if we run it, it creates the db file (now it is empty); if it is present, it just connects
print(type(conn))  # <class 'sqlite3.Connection'>
curs = (
    conn.cursor()
)  # method cursor that returns an object that contains the connection to the db and the possibility to write

# ENABLE FOREIGN KEY CONSTRAINTS
curs.execute("PRAGMA foreign_keys = ON")

# -----------------------------------------------------------------------------------------------------------------
# CREATE TABLE 1: CUSTOMER
# -----------------------------------------------------------------------------------------------------------------
curs.execute(
    """ CREATE TABLE IF NOT EXISTS Customer (
    ID_Customer INTEGER PRIMARY KEY,
    Name VARCHAR(20) NOT NULL,
    Surname VARCHAR(20) NOT NULL, 
    Age INTEGER CHECK (Age >= 18),
    City VARCHAR(30) DEFAULT 'Milan',
    Email VARCHAR(100) UNIQUE
    );
    """
)
# it takes SQL instructions under the form of strings and it elaborates them in Python code
# execute is the interpreter: a way to communicate to Python the SQL

# the connection is opened by the object conn
# the object conn has the method cursor that generates an object that is able to write SQL code into Python code
# cursor has done his job to create the table, now we have to go back to the obj conn that keeps open the connection
# conn.commit()  # before we close the connection, it is good to store
# if you try to create something that already exists: OperationalError: table Customer already exists
# SQL wants to preserve integrity
# conn.close()

# -----------------------------------------------------------------------------------------------------------------
# CREATE TABLE 2: ORDERS
# -----------------------------------------------------------------------------------------------------------------
curs.execute(
    """ CREATE TABLE IF NOT EXISTS Orders (
    ID_Order INTEGER PRIMARY KEY,
    ID_Customer INTEGER NOT NULL,
    order_date DATE NOT NULL,
    order_status TEXT DEFAULT 'Pending',
    order_price DECIMAL(10,2) NOT NULL,
    order_amount INTEGER DEFAULT 0,

    
    FOREIGN KEY (ID_Customer)
    REFERENCES Customer(ID_Customer)
    );
    """
)

conn.commit()  # save everything if something is not saved
conn.close()

# We have learnt how to create a DB; now we have to populate the DB

# -----------------------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------------
# GENERAL SYNTAX TO CREATE A TABLE
# """CREATE TABLE name_table(
#     name_column_1 TYPE_DATA CONSTRAINTS,
#     name_column_2 TYPE_DATA CONSTRAINTS,
#     ...
#     );
#     """

# Each column needs to have a name, a data type and eventually constraints (they are optional)
# Commas separate different columns of a table
# Semicolumns (;) stop the SQL instructions

# DATA TYPE IN SQL: INTEGER, DECIMAL(10,2) -> floating number with max 10 before comma and 2 max after comma
#                   VARCHAR(100) -> string with no more than 100 letters
#                   TEXT, DATE -> 2026-11-14, BOOLEAN -> TRUE or FALSE

# CONSTRAINTS: PRIMARY KEY -> NOT NULL + UNIQUE
#              NOT NULL, UNIQUE, DEFAULT, CHECK
#              DEFAULT + default value
#              CHECK + constraint
#              FOREIGN KEY
# -----------------------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------------

# -----------------------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------------
# BASIC SQL INSTRUCTIONS
# CREATE TABLE
# ALTER TABLE: modify a table
# DROP TABLE: delete a table
# INSERT INTO: put extra instances into a table already created
# SELECT: read the data
# JOIN
# -----------------------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------------


# -----------------------------------------------------------------------------------------------------------------
# INSERT DATA INTO TABLE
# -----------------------------------------------------------------------------------------------------------------
conn = sqlite3.connect("exampledatabase.db")
curs = conn.cursor()
curs.execute("PRAGMA foreign_keys = ON")

# First you have to create something to insert

# -----------------------------------------------------------------------------------------------------------------
# CREATE TABLE 3: Customer_Easy
# -----------------------------------------------------------------------------------------------------------------
curs.execute(
    """ CREATE TABLE IF NOT EXISTS Customer_Easy (
    ID_Customer INTEGER PRIMARY KEY,
    Name TEXT NOT NULL,
    City TEXT
    );
    """
)
# each entry of the list is an entity of the table (so it should be immutable -> tupla)
customers = [(1, "John", "Milan"), (2, "Alice", "Bergamo")]
curs.executemany(""" INSERT INTO Customer_Easy VALUES (?, ?, ?)""", customers)
# ? is placeholder for SQL
# We introduced data into our database
# IntegrityError: UNIQUE constraint failed: Customer_Easy.ID_Customer
# You are reinserting the data again
conn.commit()

# -----------------------------------------------------------------------------------------------------------------
# QUERY - SELECT DATA
# -----------------------------------------------------------------------------------------------------------------
# it is good to provide instructions into a variable
query = """ 
SELECT *
FROM Customer_Easy
"""
results = curs.execute(query)  # iterable
print(results)  # <sqlite3.Cursor object at 0x137af2840>
for row in results:
    print(row)
# -----------------------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------------
import pandas as pd  # make pandas collaborate with SQL

# TRANSFER DATA TO PANDAS
df = pd.read_sql_query(query, conn)
print(df)

# -----------------------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------------
# import os
# check if the database already exists or not
# if os.path.exists("exampledatabase.db"):
#     os.remove("exampledatabase.db")
query_2 = """ 
SELECT *
FROM Customer_Easy
WHERE Name = 'John'
"""  # I select everything from a table under the condition Name = John
results_2 = curs.execute(query_2)
for row in results_2:
    print(row)


# -----------------------------------------------------------------------------------------------------------------
# DROP TABLE
# -----------------------------------------------------------------------------------------------------------------
curs.execute("DROP TABLE Customer_Easy;")

# -----------------------------------------------------------------------------------------------------------------
# JOIN TABLES
# -----------------------------------------------------------------------------------------------------------------
conn_2 = sqlite3.connect(":memory")  # database that stay in the RAM, not a file in the system
curs_2 = conn_2.cursor()
curs_2.execute(
    """ CREATE TABLE IF NOT EXISTS Customer_2 (
    ID_Customer INTEGER PRIMARY KEY,
    Name TEXT NOT NULL
    );
    """
)
curs_2.execute(
    """ CREATE TABLE IF NOT EXISTS Orders_2 (
    ID_Order INTEGER PRIMARY KEY,
    ID_Customer INTEGER
    );
    """
)

# Insert data (Populate)
curs_2.executemany(""" INSERT INTO Customer_2 VALUES (?, ?)""", [(1, "Marco"), (3, "Giulia"), (2, "Davide")])
curs_2.executemany(""" INSERT INTO Orders_2 VALUES (?, ?)""", [(101, 1), (102, 2), (103, 4)])

# LEFT JOIN
curs_2.execute(
    """
               SELECT Customer_2.Name, Orders_2.ID_Order
               FROM Customer_2
               LEFT JOIN Orders_2
               ON Customer_2.ID_Customer = Orders_2.ID_Customer
               """
)
print(curs_2.fetchall())  # [('Marco', 101), ('Davide', 102), ('Giulia', None)]

# RIGHT JOIN
curs_2.execute(
    """
               SELECT Customer_2.Name, Orders_2.ID_Order
               FROM Customer_2
               RIGHT JOIN Orders_2
               ON Customer_2.ID_Customer = Orders_2.ID_Customer
               """
)
print(curs_2.fetchall())  # [('Marco', 101), ('Davide', 102), (None, 103)]

# INNER JOIN
curs_2.execute(
    """
               SELECT Customer_2.Name, Orders_2.ID_Order
               FROM Customer_2
               INNER JOIN Orders_2
               ON Customer_2.ID_Customer = Orders_2.ID_Customer
               ORDER BY Customer_2.ID_Customer
               """
)
print(curs_2.fetchall())  # [('Marco', 101), ('Davide', 102)]

conn.close()  # OperationalError: database is locked: when you not close the db
conn_2.close()

# -----------------------------------------------------------------------------------------------------------------
# SQL COMMANDS
# -----------------------------------------------------------------------------------------------------------------
# SELECT
# WHERE
# ORDER BY
# GROUP BY
# HAVING (filtering)
# COUNT
# SUM
# AVG
# JOIN - INNER, LEFT, RIGHT
# Subquery (query inside another query)


def show_query(query, params=()):
    curs_2.execute(query, params)
    result = curs_2.fetchall()
    for row in result:
        print(row)


# -----------------------------------------------------------------------------------------------------------------
# Radi constructed a financial database
# data_manager constructs the db taking data from Bloomberg ecc
# dashoboard takes data from the db created

# ReadMe file to make it run
# requirements: list of used packages

# TASK FOR THE EXAM: SOFTWARE FOR THE FINANCIAL INDUSTRY
# CREATE A DASHBOARD WHEN YOU HAVE TO ENTER THROUGH A TWO-LEVEL AUTENTHICATION SYSTEM
# DASHBOARD TAKES DATA FROM YAHOO FINANCE, DOWNLOAD THE DATA ABOUT FINANCIAL MARKETS THAT YOU LIKE, DASH OF SEVERAL PAGES
# COMPUTE SOME STATISTICS

# DASHBOARD, THEN COMPILE IT AS AN EXE
# He wants a folder without venv and financial data; also file documentation

# Design an app
# dashboard scalabile
# programmazione ad oggetti
