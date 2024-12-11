from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, JSON, TIMESTAMP, Enum
from db_connect import Base

# Customer model
class Customer(Base):
    __tablename__ = 'customer'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)

# Item model
class Item(Base):
    __tablename__ = 'item'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    company = Column(String(50), nullable=False)
    price = Column(Float, nullable=False)

# Order model
class Order(Base):
    __tablename__ = 'order'
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    items = Column(JSON, nullable=False)
    total_price = Column(Float, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=False), nullable=False, default=datetime.now)
    status = Column(Enum("ordered", "shipped", "delivered", "cancelled", name="status_enum"), default="ordered")
