from sqlalchemy import Column, Integer, String, Numeric, Date, Text, SmallInteger, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class ProductLine(Base):
    __tablename__ = "productlines"
    productLine = Column("productLine", String(50), primary_key=True)
    textDescription = Column("textDescription", String(4000))
    htmlDescription = Column("htmlDescription", Text)
    products = relationship("Product", back_populates="product_line")

class Product(Base):
    __tablename__ = "products"
    productCode = Column("productCode", String(15), primary_key=True)
    productName = Column("productName", String(70), nullable=False)
    productLine = Column("productLine", String(50), ForeignKey("productlines.productLine"))
    productScale = Column("productScale", String(10))
    productVendor = Column("productVendor", String(50))
    productDescription = Column("productDescription", Text)
    quantityInStock = Column("quantityInStock", Integer)
    buyPrice = Column("buyPrice", Numeric(10, 2))
    MSRP = Column("MSRP", Numeric(10, 2))
    product_line = relationship("ProductLine", back_populates="products")

class Office(Base):
    __tablename__ = "offices"
    officeCode = Column("officeCode", String(10), primary_key=True)
    city = Column("city", String(50), nullable=False)
    phone = Column("phone", String(50))
    addressLine1 = Column("addressLine1", String(50))
    addressLine2 = Column("addressLine2", String(50))
    state = Column("state", String(50))
    country = Column("country", String(50))
    postalCode = Column("postalCode", String(15))
    territory = Column("territory", String(10))
    employees = relationship("Employee", back_populates="office")

class Employee(Base):
    __tablename__ = "employees"
    employeeNumber = Column("employeeNumber", Integer, primary_key=True)
    lastName = Column("lastName", String(50), nullable=False)
    firstName = Column("firstName", String(50), nullable=False)
    extension = Column("extension", String(10))
    email = Column("email", String(100))
    officeCode = Column("officeCode", String(10), ForeignKey("offices.officeCode"))
    reportsTo = Column("reportsTo", Integer, ForeignKey("employees.employeeNumber"))
    jobTitle = Column("jobTitle", String(50))
    office = relationship("Office", back_populates="employees")
    customers = relationship("Customer", back_populates="sales_rep")

class Customer(Base):
    __tablename__ = "customers"
    customerNumber = Column("customerNumber", Integer, primary_key=True)
    customerName = Column("customerName", String(50), nullable=False)
    contactLastName = Column("contactLastName", String(50))
    contactFirstName = Column("contactFirstName", String(50))
    phone = Column("phone", String(50))
    addressLine1 = Column("addressLine1", String(50))
    addressLine2 = Column("addressLine2", String(50))
    city = Column("city", String(50))
    state = Column("state", String(50))
    postalCode = Column("postalCode", String(15))
    country = Column("country", String(50))
    salesRepEmployeeNumber = Column("salesRepEmployeeNumber", Integer, ForeignKey("employees.employeeNumber"))
    creditLimit = Column("creditLimit", Numeric(10, 2))
    sales_rep = relationship("Employee", back_populates="customers")
    orders = relationship("Order", back_populates="customer")
    payments = relationship("Payment", back_populates="customer")

class Payment(Base):
    __tablename__ = "payments"
    customerNumber = Column("customerNumber", Integer, ForeignKey("customers.customerNumber"), primary_key=True)
    checkNumber = Column("checkNumber", String(50), primary_key=True)
    paymentDate = Column("paymentDate", Date)
    amount = Column("amount", Numeric(10, 2))
    customer = relationship("Customer", back_populates="payments")

class Order(Base):
    __tablename__ = "orders"
    orderNumber = Column("orderNumber", Integer, primary_ksey=True)
    orderDate = Column("orderDate", Date)
    requiredDate = Column("requiredDate", Date)
    shippedDate = Column("shippedDate", Date)
    status = Column("status", String(15))
    comments = Column("comments", Text)
    customerNumber = Column("customerNumber", Integer, ForeignKey("customers.customerNumber"))
    customer = relationship("Customer", back_populates="orders")
    order_details = relationship("OrderDetail", back_populates="order")

class OrderDetail(Base):
    __tablename__ = "orderdetails"
    orderNumber = Column("orderNumber", Integer, ForeignKey("orders.orderNumber"), primary_key=True)
    productCode = Column("productCode", String(15), ForeignKey("products.productCode"), primary_key=True)
    quantityOrdered = Column("quantityOrdered", Integer)
    priceEach = Column("priceEach", Numeric(10, 2))
    orderLineNumber = Column("orderLineNumber", SmallInteger)
    order = relationship("Order", back_populates="order_details")