"""
SQLAlchemy Database Models for Retail Demand Prediction System.

Tables:
- stores: Store metadata
- skus: Product catalog
- sales_transactions: Immutable sales data
- forecast_results: Generated forecasts with model info
- reorder_recommendations: Actionable reorder list
- festivals: Festival configuration
"""

from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, 
    ForeignKey, Boolean, Text, Enum as SQLEnum
)
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


class ForecastModel(enum.Enum):
    """Types of forecasting models used."""
    NAIVE = "naive"
    MOVING_AVERAGE = "moving_average"
    ARIMA = "arima"
    ARIMAX = "arimax"


class UrgencyLevel(enum.Enum):
    """Urgency levels for reorder recommendations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Store(Base):
    """Store metadata."""
    __tablename__ = "stores"
    
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    location = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    skus = relationship("SKU", back_populates="store")
    sales = relationship("SalesTransaction", back_populates="store")
    forecasts = relationship("ForecastResult", back_populates="store")
    recommendations = relationship("ReorderRecommendation", back_populates="store")


class SKU(Base):
    """Product catalog."""
    __tablename__ = "skus"
    
    id = Column(Integer, primary_key=True, index=True)
    sku_id = Column(String(50), nullable=False, index=True)
    sku_name = Column(String(300), nullable=False)
    category = Column(String(100))
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    current_stock = Column(Integer, default=0)  # Updated weekly by store
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    store = relationship("Store", back_populates="skus")
    sales = relationship("SalesTransaction", back_populates="sku")
    forecasts = relationship("ForecastResult", back_populates="sku")
    recommendations = relationship("ReorderRecommendation", back_populates="sku")


class SalesTransaction(Base):
    """
    Immutable sales data.
    This is the core input for the forecasting engine.
    """
    __tablename__ = "sales_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    sku_id = Column(Integer, ForeignKey("skus.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    units_sold = Column(Integer, nullable=False)
    price = Column(Float)  # Optional
    discount = Column(Float)  # Optional
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    store = relationship("Store", back_populates="sales")
    sku = relationship("SKU", back_populates="sales")


class ForecastResult(Base):
    """
    Generated forecasts with model info.
    Forecasts are regenerated, not edited.
    """
    __tablename__ = "forecast_results"
    
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    sku_id = Column(Integer, ForeignKey("skus.id"), nullable=False, index=True)
    forecast_date = Column(Date, nullable=False, index=True)  # The date being forecasted
    predicted_units = Column(Float, nullable=False)
    confidence_lower = Column(Float)
    confidence_upper = Column(Float)
    model_used = Column(SQLEnum(ForecastModel), nullable=False)
    forecast_horizon = Column(Integer, nullable=False)  # 7, 14, or 30 days
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    store = relationship("Store", back_populates="forecasts")
    sku = relationship("SKU", back_populates="forecasts")


class ReorderRecommendation(Base):
    """
    Actionable reorder list.
    THIS IS THE PRODUCT - the output a kirana owner uses.
    """
    __tablename__ = "reorder_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    sku_id = Column(Integer, ForeignKey("skus.id"), nullable=False, index=True)
    reorder_qty = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)  # Human-readable explanation
    urgency = Column(SQLEnum(UrgencyLevel), nullable=False, index=True)
    forecasted_demand = Column(Float)
    current_stock = Column(Integer)
    safety_stock = Column(Integer)
    velocity_change_pct = Column(Float)  # % change vs last week
    generated_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True, index=True)  # False when fulfilled
    
    # Relationships
    store = relationship("Store", back_populates="recommendations")
    sku = relationship("SKU", back_populates="recommendations")


class Festival(Base):
    """
    Festival configuration table.
    Used for seasonality features in ARIMAX.
    Do NOT hardcode festivals - use this config table.
    """
    __tablename__ = "festivals"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    date = Column(Date, nullable=False, index=True)
    region = Column(String(100))  # For local festivals
    impact_multiplier = Column(Float, default=1.5)  # Expected demand increase
    created_at = Column(DateTime, default=datetime.utcnow)
