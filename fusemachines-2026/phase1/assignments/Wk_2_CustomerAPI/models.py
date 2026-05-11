from sqlalchemy import Column, Integer, String, Numeric, Date, Text, SmallInteger, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class ProductLine(Base):
    __tablename__ = "productlines"
    productLine = Column("productline", String(50), primary_key=True)
    textDescription = Column("textdescription", String(4000))
    htmlDescription = Column("htmldescription", Text)
    products = relationship("Product", back_populates="product_line")

class Product(Base):
    __tablename__ = "products"
    productCode = Column("productcode", String(15), primary_key=True)
    productName = Column("productname", String(70), nullable=False)
    productLine = Column("productline", String(50), ForeignKey("productlines.productline"))
    productScale = Column("productscale", String(10))
    productVendor = Column("productvendor", String(50))
    productDescription = Column("productdescription", Text)
    quantityInStock = Column("quantityinstock", Integer)
    buyPrice = Column("buyprice", Numeric(10, 2))
    MSRP = Column("msrp", Numeric(10, 2))
    product_line = relationship("ProductLine", back_populates="products")

class Office(Base):
    __tablename__ = "offices"
    officeCode = Column("officecode", String(10), primary_key=True)
    city = Column("city", String(50), nullable=False)
    phone = Column("phone", String(50))
    addressLine1 = Column("addressline1", String(50))
    addressLine2 = Column("addressline2", String(50))
    state = Column("state", String(50))
    country = Column("country", String(50))
    postalCode = Column("postalcode", String(15))
    territory = Column("territory", String(10))
    employees = relationship("Employee", back_populates="office")

class Employee(Base):
    __tablename__ = "employees"
    employeeNumber = Column("employeenumber", Integer, primary_key=True)
    lastName = Column("lastname", String(50), nullable=False)
    firstName = Column("firstname", String(50), nullable=False)
    extension = Column("extension", String(10))
    email = Column("email", String(100))
    officeCode = Column("officecode", String(10), ForeignKey("offices.officecode"))
    reportsTo = Column("reportsto", Integer, ForeignKey("employees.employeenumber"))
    jobTitle = Column("jobtitle", String(50))
    office = relationship("Office", back_populates="employees")
    customers = relationship("Customer", back_populates="sales_rep")

class Customer(Base):
    __tablename__ = "customers"
    customerNumber = Column("customernumber", Integer, primary_key=True)
    customerName = Column("customername", String(50), nullable=False)
    contactLastName = Column("contactlastname", String(50))
    contactFirstName = Column("contactfirstname", String(50))
    phone = Column("phone", String(50))
    addressLine1 = Column("addressline1", String(50))
    addressLine2 = Column("addressline2", String(50))
    city = Column("city", String(50))
    state = Column("state", String(50))
    postalCode = Column("postalcode", String(15))
    country = Column("country", String(50))
    salesRepEmployeeNumber = Column("salesrepemployeenumber", Integer, ForeignKey("employees.employeenumber"))
    creditLimit = Column("creditlimit", Numeric(10, 2))
    sales_rep = relationship("Employee", back_populates="customers")
    orders = relationship("Order", back_populates="customer")
    payments = relationship("Payment", back_populates="customer")

class Payment(Base):
    __tablename__ = "payments"
    customerNumber = Column("customernumber", Integer, ForeignKey("customers.customernumber"), primary_key=True)
    checkNumber = Column("checknumber", String(50), primary_key=True)
    paymentDate = Column("paymentdate", Date)
    amount = Column("amount", Numeric(10, 2))
    customer = relationship("Customer", back_populates="payments")

class Order(Base):
    __tablename__ = "orders"
    orderNumber = Column("ordernumber", Integer, primary_key=True)
    orderDate = Column("orderdate", Date)
    requiredDate = Column("requireddate", Date)
    shippedDate = Column("shippeddate", Date)
    status = Column("status", String(15))
    comments = Column("comments", Text)
    customerNumber = Column("customernumber", Integer, ForeignKey("customers.customernumber"))
    customer = relationship("Customer", back_populates="orders")
    order_details = relationship("OrderDetail", back_populates="order")

class OrderDetail(Base):
    __tablename__ = "orderdetails"
    orderNumber = Column("ordernumber", Integer, ForeignKey("orders.ordernumber"), primary_key=True)
    productCode = Column("productcode", String(15), ForeignKey("products.productcode"), primary_key=True)
    quantityOrdered = Column("quantityordered", Integer)
    priceEach = Column("priceeach", Numeric(10, 2))
    orderLineNumber = Column("orderlinenumber", SmallInteger)
    order = relationship("Order", back_populates="order_details")
