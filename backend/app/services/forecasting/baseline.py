"""
Baseline Forecasting Models.

Start simple, stay boring:
1. Naive baseline: Last 7-day average × horizon
2. Moving average with configurable window

If these don't work, we have bigger problems than model selection.
"""

import pandas as pd
import numpy as np
from datetime import date, timedelta
from typing import List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ForecastPoint:
    """Single forecast data point."""
    date: date
    predicted_units: float
    confidence_lower: Optional[float] = None
    confidence_upper: Optional[float] = None


class BaselineForecaster:
    """
    Simple baseline forecasting models.
    These should be your first try - if ARIMA doesn't beat these, stop.
    """
    
    def __init__(self, data: pd.DataFrame):
        """
        Initialize with sales data.
        
        Args:
            data: DataFrame with columns ['date', 'units_sold']
        """
        self.data = data.copy()
        self.data['date'] = pd.to_datetime(self.data['date'])
        self.data = self.data.sort_values('date')
    
    @property
    def days_of_data(self) -> int:
        """Number of days of data available."""
        if len(self.data) == 0:
            return 0
        return (self.data['date'].max() - self.data['date'].min()).days + 1
    
    def naive_forecast(self, horizon: int = 7) -> List[ForecastPoint]:
        """
        Naive baseline: Last 7-day average repeated for horizon.
        
        This is the simplest possible forecast.
        If your fancy model can't beat this, it's useless.
        """
        if len(self.data) == 0:
            return self._empty_forecast(horizon)
        
        # Get last 7 days average (or whatever is available)
        lookback = min(7, len(self.data))
        recent_data = self.data.tail(lookback)
        avg = recent_data['units_sold'].mean()
        std = recent_data['units_sold'].std() if len(recent_data) > 1 else avg * 0.2
        
        # Generate forecast points
        last_date = self.data['date'].max()
        forecasts = []
        
        for i in range(1, horizon + 1):
            forecast_date = (last_date + timedelta(days=i)).date()
            forecasts.append(ForecastPoint(
                date=forecast_date,
                predicted_units=round(avg, 2),
                confidence_lower=round(max(0, avg - 1.96 * std), 2),
                confidence_upper=round(avg + 1.96 * std, 2)
            ))
        
        return forecasts
    
    def moving_average_forecast(
        self, 
        horizon: int = 7,
        window: int = 7
    ) -> List[ForecastPoint]:
        """
        Moving average forecast.
        
        Uses rolling average with trend adjustment.
        Good for products with stable demand.
        """
        if len(self.data) < 3:
            return self.naive_forecast(horizon)
        
        # Calculate moving average
        self.data['ma'] = self.data['units_sold'].rolling(
            window=min(window, len(self.data)), 
            min_periods=1
        ).mean()
        
        # Simple trend: difference between recent and older MA
        recent_ma = self.data['ma'].tail(3).mean()
        older_ma = self.data['ma'].head(max(3, len(self.data) // 2)).mean()
        
        # Trend per day
        days_between = max(1, len(self.data) // 2)
        daily_trend = (recent_ma - older_ma) / days_between
        
        # Cap trend to avoid extreme forecasts
        max_trend = recent_ma * 0.1  # Max 10% change per day
        daily_trend = np.clip(daily_trend, -max_trend, max_trend)
        
        # Standard deviation for confidence intervals
        std = self.data['units_sold'].std()
        
        # Generate forecasts
        last_date = self.data['date'].max()
        base_value = self.data['ma'].iloc[-1]
        forecasts = []
        
        for i in range(1, horizon + 1):
            forecast_date = (last_date + timedelta(days=i)).date()
            predicted = base_value + (daily_trend * i)
            predicted = max(0, predicted)  # No negative demand
            
            # Widen confidence interval further into future
            ci_width = std * (1 + 0.1 * i)
            
            forecasts.append(ForecastPoint(
                date=forecast_date,
                predicted_units=round(predicted, 2),
                confidence_lower=round(max(0, predicted - 1.96 * ci_width), 2),
                confidence_upper=round(predicted + 1.96 * ci_width, 2)
            ))
        
        return forecasts
    
    def _empty_forecast(self, horizon: int) -> List[ForecastPoint]:
        """Return zero forecast when no data available."""
        today = date.today()
        return [
            ForecastPoint(
                date=today + timedelta(days=i),
                predicted_units=0,
                confidence_lower=0,
                confidence_upper=0
            )
            for i in range(1, horizon + 1)
        ]


def calculate_velocity_change(
    data: pd.DataFrame,
    recent_days: int = 7,
    compare_days: int = 7
) -> float:
    """
    Calculate velocity change percentage.
    
    Compares recent period average to previous period average.
    
    Returns:
        Percentage change (e.g., 40.0 means 40% increase)
    """
    if len(data) < recent_days + compare_days:
        return 0.0
    
    data = data.sort_values('date')
    recent = data.tail(recent_days)['units_sold'].mean()
    previous = data.tail(recent_days + compare_days).head(compare_days)['units_sold'].mean()
    
    if previous == 0:
        return 100.0 if recent > 0 else 0.0
    
    return round(((recent - previous) / previous) * 100, 1)
