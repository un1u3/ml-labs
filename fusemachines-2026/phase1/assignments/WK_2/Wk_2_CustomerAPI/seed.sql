-- =====================
-- DROP (safe order)
-- =====================
DROP TABLE IF EXISTS orderdetails;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS offices;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS productlines;

-- =====================
-- PRODUCT LINES
-- =====================
CREATE TABLE productlines (
  productline VARCHAR(50) PRIMARY KEY,
  textdescription VARCHAR(4000),
  htmldescription TEXT,
  image BYTEA
);

-- =====================
-- PRODUCTS
-- =====================
CREATE TABLE products (
  productcode VARCHAR(15) PRIMARY KEY,
  productname VARCHAR(70) NOT NULL,
  productline VARCHAR(50) NOT NULL,
  productscale VARCHAR(10) NOT NULL,
  productvendor VARCHAR(50) NOT NULL,
  productdescription TEXT NOT NULL,
  quantityinstock INTEGER NOT NULL,
  buyprice NUMERIC(10,2) NOT NULL,
  msrp NUMERIC(10,2) NOT NULL,
  FOREIGN KEY (productline) REFERENCES productlines(productline)
);

-- =====================
-- OFFICES
-- =====================
CREATE TABLE offices (
  officecode VARCHAR(10) PRIMARY KEY,
  city VARCHAR(50) NOT NULL,
  phone VARCHAR(50) NOT NULL,
  addressline1 VARCHAR(50) NOT NULL,
  addressline2 VARCHAR(50),
  state VARCHAR(50),
  country VARCHAR(50) NOT NULL,
  postalcode VARCHAR(15) NOT NULL,
  territory VARCHAR(10) NOT NULL
);

-- =====================
-- EMPLOYEES
-- =====================
CREATE TABLE employees (
  employeenumber INTEGER PRIMARY KEY,
  lastname VARCHAR(50) NOT NULL,
  firstname VARCHAR(50) NOT NULL,
  extension VARCHAR(10) NOT NULL,
  email VARCHAR(100) NOT NULL,
  officecode VARCHAR(10) NOT NULL,
  reportsto INTEGER,
  jobtitle VARCHAR(50) NOT NULL,
  FOREIGN KEY (officecode) REFERENCES offices(officecode),
  FOREIGN KEY (reportsto) REFERENCES employees(employeenumber)
);

-- =====================
-- CUSTOMERS
-- =====================
CREATE TABLE customers (
  customernumber INTEGER PRIMARY KEY,
  customername VARCHAR(50) NOT NULL,
  contactlastname VARCHAR(50) NOT NULL,
  contactfirstname VARCHAR(50) NOT NULL,
  phone VARCHAR(50) NOT NULL,
  addressline1 VARCHAR(50) NOT NULL,
  addressline2 VARCHAR(50),
  city VARCHAR(50) NOT NULL,
  state VARCHAR(50),
  postalcode VARCHAR(15),
  country VARCHAR(50) NOT NULL,
  salesrepemployeenumber INTEGER,
  creditlimit NUMERIC(10,2),
  FOREIGN KEY (salesrepemployeenumber) REFERENCES employees(employeenumber)
);

-- =====================
-- PAYMENTS
-- =====================
CREATE TABLE payments (
  customernumber INTEGER NOT NULL,
  checknumber VARCHAR(50) NOT NULL,
  paymentdate DATE NOT NULL,
  amount NUMERIC(10,2) NOT NULL,
  PRIMARY KEY (customernumber, checknumber),
  FOREIGN KEY (customernumber) REFERENCES customers(customernumber)
);

-- =====================
-- ORDERS
-- =====================
CREATE TABLE orders (
  ordernumber INTEGER PRIMARY KEY,
  orderdate DATE NOT NULL,
  requireddate DATE NOT NULL,
  shippeddate DATE,
  status VARCHAR(15) NOT NULL,
  comments TEXT,
  customernumber INTEGER NOT NULL,
  FOREIGN KEY (customernumber) REFERENCES customers(customernumber)
);

-- =====================
-- ORDER DETAILS
-- =====================
CREATE TABLE orderdetails (
  ordernumber INTEGER NOT NULL,
  productcode VARCHAR(15) NOT NULL,
  quantityordered INTEGER NOT NULL,
  priceeach NUMERIC(10,2) NOT NULL,
  orderlinenumber SMALLINT NOT NULL,
  PRIMARY KEY (ordernumber, productcode),
  FOREIGN KEY (ordernumber) REFERENCES orders(ordernumber),
  FOREIGN KEY (productcode) REFERENCES products(productcode)
);