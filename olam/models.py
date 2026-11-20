"""Dinero en céntimos; cantidades en milésimas. Portable SQLite/MySQL."""
from datetime import datetime, timezone
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'usuarios'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(40))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    session_version: Mapped[int] = mapped_column(default=1)

class Product(Base):
    __tablename__ = 'articulos'
    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    brand: Mapped[str] = mapped_column(String(50))
    presentation: Mapped[str] = mapped_column(String(50))
    category: Mapped[str] = mapped_column(String(30))
    unit: Mapped[str] = mapped_column(String(10))
    price_cents: Mapped[int] = mapped_column(Integer)
    stock_milli: Mapped[int] = mapped_column(Integer)
    minimum_milli: Mapped[int] = mapped_column(Integer, default=10000)
    reward_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(default=1)
    __table_args__ = (CheckConstraint('price_cents > 0'), CheckConstraint('stock_milli >= 0'), CheckConstraint('minimum_milli >= 0'), CheckConstraint('reward_points IS NULL OR reward_points > 0'))

class Client(Base):
    __tablename__ = 'clientes'
    document: Mapped[str] = mapped_column(String(11), primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    phone: Mapped[str] = mapped_column(String(20), default='')
    email: Mapped[str] = mapped_column(String(100), default='')
    kind: Mapped[str] = mapped_column(String(30), default='Particular')
    points: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(default=1)
    __table_args__ = (CheckConstraint('points >= 0'),)

class Sale(Base):
    __tablename__ = 'ventas'
    id: Mapped[int] = mapped_column(primary_key=True)
    request_key: Mapped[str] = mapped_column(String(36), unique=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    client_document: Mapped[str | None] = mapped_column(ForeignKey('clientes.document'), nullable=True)
    client_name: Mapped[str] = mapped_column(String(150))
    user_id: Mapped[int] = mapped_column(ForeignKey('usuarios.id'))
    total_cents: Mapped[int] = mapped_column(Integer)
    points: Mapped[int] = mapped_column(Integer)
    payment: Mapped[str] = mapped_column(String(20))
    cash_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    status: Mapped[str] = mapped_column(String(15), default='Registrada')
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancellation_reason: Mapped[str] = mapped_column(String(250), default='')

class SaleItem(Base):
    __tablename__ = 'venta_detalles'
    id: Mapped[int] = mapped_column(primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey('ventas.id'), index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey('articulos.id'))
    product_name: Mapped[str] = mapped_column(String(150))
    unit: Mapped[str] = mapped_column(String(10))
    quantity_milli: Mapped[int] = mapped_column(Integer)
    price_cents: Mapped[int] = mapped_column(Integer)
    subtotal_cents: Mapped[int] = mapped_column(Integer)
    points: Mapped[int] = mapped_column(Integer)

class Redemption(Base):
    __tablename__ = 'canjes'
    id: Mapped[int] = mapped_column(primary_key=True)
    request_key: Mapped[str] = mapped_column(String(36), unique=True)
    client_document: Mapped[str] = mapped_column(ForeignKey('clientes.document'))
    product_id: Mapped[str] = mapped_column(ForeignKey('articulos.id'))
    product_name: Mapped[str] = mapped_column(String(150))
    quantity: Mapped[int] = mapped_column(Integer)
    points: Mapped[int] = mapped_column(Integer)
    user_id: Mapped[int] = mapped_column(ForeignKey('usuarios.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    status: Mapped[str] = mapped_column(String(15), default='Registrado')

class Movement(Base):
    __tablename__ = 'movimientos'
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey('articulos.id'))
    delta_milli: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(250))
    user_id: Mapped[int] = mapped_column(ForeignKey('usuarios.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

class Audit(Base):
    __tablename__ = 'auditoria'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('usuarios.id'))
    action: Mapped[str] = mapped_column(String(100))
    detail: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
