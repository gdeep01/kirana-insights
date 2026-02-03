"""
Pydantic Schemas for API validation and serialization.

These schemas define the contract between frontend and backend:
- Request validation
- Response serialization
- CSV upload validation
"""

from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum


# ============== Enums ==============

class ForecastModelType(str, Enum):
    """Forecasting model types."""
    NAIVE = "naive"
    MOVING_AVERAGE = "moving_average"
    ARIMA = "arima"
    ARIMAX = "arimax"


class UrgencyLevel(str, Enum):
    """Reorder urgency levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============== CSV Upload ==============

class SalesRowSchema(BaseModel):
    """
    Single row from CSV upload.
    MANDATORY schema - everything converts to this.
    """
    store_id: str = Field(..., min_length=1, max_length=50)
    sku_id: str = Field(..., min_length=1, max_length=50)
    sku_name: str = Field(..., min_length=1, max_length=300)
    date: date
    units_sold: int = Field(..., ge=0)
    price: Optional[float] = Field(None, ge=0)
    discount: Optional[float] = Field(None, ge=0, le=100)
    category: Optional[str] = None

    @field_validator('date', mode='before')
    @classmethod
    def parse_date(cls, v):
        """Parse various date formats."""
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            # Try common formats
            for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%m/%d/%Y']:
                try:
                    return datetime.strptime(v, fmt).date()
                except ValueError:
                    continue
            raise ValueError(f"Cannot parse date: {v}")
        return v


class CSVUploadResponse(BaseModel):
    """Response after CSV upload."""
    success: bool
    rows_processed: int
    rows_failed: int
    errors: List[str] = []
    store_id: Optional[str] = None


# ============== Store ==============

class StoreCreate(BaseModel):
    """Create a new store."""
    store_id: str
    name: str
    location: Optional[str] = None


class StoreResponse(BaseModel):
    """Store response."""
    id: int
    store_id: str
    name: str
    location: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============== SKU ==============

class SKUResponse(BaseModel):
    """SKU response."""
    id: int
    sku_id: str
    sku_name: str
    category: Optional[str]
    current_stock: int

    class Config:
        from_attributes = True


class StockUpdateRequest(BaseModel):
    """Update current stock for SKU."""
    sku_id: str
    current_stock: int = Field(..., ge=0)


# ============== Forecast ==============

class ForecastRequest(BaseModel):
    """Request to run forecast."""
    store_id: str
    sku_ids: Optional[List[str]] = None  # None = all SKUs
    horizon: int = Field(default=7, ge=1, le=30)


class ForecastResultSchema(BaseModel):
    """Single forecast result."""
    sku_id: str
    sku_name: str
    forecast_date: date
    predicted_units: float
    confidence_lower: Optional[float]
    confidence_upper: Optional[float]
    model_used: ForecastModelType

    class Config:
        from_attributes = True


class ForecastResponse(BaseModel):
    """Response with forecast results."""
    store_id: str
    horizon: int
    generated_at: datetime
    total_predicted: float
    forecasts: List[ForecastResultSchema]
    insights: List[str] = []


# ============== Reorder Recommendations ==============

class ReorderItem(BaseModel):
    """
    Single reorder recommendation.
    THIS is what the kirana owner sees.
    Must be understandable in 10 seconds.
    """
    sku_id: str
    sku_name: str
    reorder_qty: int
    reason: str  # Human-readable: "40% increase vs last week"
    urgency: UrgencyLevel
    forecasted_demand: float
    current_stock: int
    velocity_change_pct: Optional[float] = None

    class Config:
        from_attributes = True


class ReorderListResponse(BaseModel):
    """
    Complete reorder list for a store.
    """
    store_id: str
    store_name: str
    generated_at: datetime
    total_items: int
    critical_items: int
    items: List[ReorderItem]


class ReorderSummary(BaseModel):
    """Quick summary for dashboard."""
    total_items: int
    critical: int
    high: int
    medium: int
    low: int
    estimated_value: Optional[float] = None


# ============== Metrics ==============

class AccuracyMetrics(BaseModel):
    """Forecast accuracy metrics."""
    mape: float  # Mean Absolute Percentage Error
    rmse: float  # Root Mean Square Error
    accuracy_pct: float  # 100 - MAPE
    data_points: int


# ============== Festival ==============

class FestivalCreate(BaseModel):
    """Create festival config."""
    name: str
    date: date
    region: Optional[str] = None
    impact_multiplier: float = Field(default=1.5, ge=1.0)


class FestivalResponse(BaseModel):
    """Festival response."""
    id: int
    name: str
    date: date
    region: Optional[str]
    impact_multiplier: float

    class Config:
        from_attributes = True
