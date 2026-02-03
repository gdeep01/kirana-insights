"""
ARIMA Forecasting Model.

Only use this for SKUs with 60+ days of data.
If ARIMA doesn't beat baseline, STOP. Don't jump to deep learning.
"""

import pandas as pd
import numpy as np
from datetime import date, timedelta
from typing import List, Optional, Dict
import warnings

# Suppress statsmodels warnings
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.stattools import adfuller
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False

from app.services.forecasting.baseline import ForecastPoint, BaselineForecaster


class ARIMAForecaster:
    """
    ARIMA forecasting for SKUs with sufficient data.
    
    Requirements:
    - Minimum 60 days of data for ARIMA
    - Falls back to moving average if insufficient data
    """
    
    MIN_DAYS_FOR_ARIMA = 60
    MIN_DAYS_FOR_MOVING_AVG = 30
    
    def __init__(self, data: pd.DataFrame, exogenous_features: Optional[pd.DataFrame] = None):
        """
        Initialize ARIMA forecaster.
        
        Args:
            data: DataFrame with columns ['date', 'units_sold']
            exogenous_features: Optional DataFrame with exogenous variables
                               (e.g., is_weekend, is_festival)
        """
        self.data = data.copy()
        self.data['date'] = pd.to_datetime(self.data['date'])
        self.data = self.data.sort_values('date').reset_index(drop=True)
        self.exog = exogenous_features
        
        # Fill missing dates with zeros
        self._fill_missing_dates()
    
    def _fill_missing_dates(self):
        """Fill missing dates in time series with zeros."""
        if len(self.data) < 2:
            return
        
        date_range = pd.date_range(
            start=self.data['date'].min(),
            end=self.data['date'].max(),
            freq='D'
        )
        
        full_df = pd.DataFrame({'date': date_range})
        self.data = full_df.merge(self.data, on='date', how='left')
        self.data['units_sold'] = self.data['units_sold'].fillna(0)
    
    @property
    def days_of_data(self) -> int:
        """Number of days of data."""
        if len(self.data) == 0:
            return 0
        return len(self.data)
    
    def can_use_arima(self) -> bool:
        """Check if we have enough data for ARIMA."""
        return STATSMODELS_AVAILABLE and self.days_of_data >= self.MIN_DAYS_FOR_ARIMA
    
    def forecast(self, horizon: int = 7) -> List[ForecastPoint]:
        """
        Generate forecast using appropriate model based on data availability.
        
        Model selection logic:
        - <30 days: Use naive baseline
        - 30-59 days: Use moving average
        - ≥60 days: Use ARIMA
        """
        if self.days_of_data < self.MIN_DAYS_FOR_MOVING_AVG:
            # Not enough data, use naive baseline
            baseline = BaselineForecaster(self.data)
            return baseline.naive_forecast(horizon)
        
        if not self.can_use_arima():
            # Use moving average
            baseline = BaselineForecaster(self.data)
            return baseline.moving_average_forecast(horizon)
        
        # Use ARIMA
        return self._arima_forecast(horizon)
    
    def _arima_forecast(self, horizon: int) -> List[ForecastPoint]:
        """
        ARIMA forecast implementation.
        
        Uses auto-selection for ARIMA order parameters.
        """
        try:
            # Prepare time series
            ts = self.data.set_index('date')['units_sold']
            
            # Determine differencing order
            d = self._get_differencing_order(ts)
            
            # Fit ARIMA model with reasonable defaults
            # Using (2, d, 2) as a reasonable starting point
            model = ARIMA(ts, order=(2, d, 2))
            fitted = model.fit()
            
            # Generate forecast
            forecast_result = fitted.get_forecast(steps=horizon)
            predicted = forecast_result.predicted_mean
            conf_int = forecast_result.conf_int(alpha=0.05)
            
            # Build forecast points
            last_date = self.data['date'].max()
            forecasts = []
            
            for i in range(horizon):
                forecast_date = (last_date + timedelta(days=i + 1)).date()
                pred = max(0, predicted.iloc[i])  # No negative demand
                
                forecasts.append(ForecastPoint(
                    date=forecast_date,
                    predicted_units=round(pred, 2),
                    confidence_lower=round(max(0, conf_int.iloc[i, 0]), 2),
                    confidence_upper=round(conf_int.iloc[i, 1], 2)
                ))
            
            return forecasts
            
        except Exception as e:
            # Fall back to moving average on any error
            print(f"ARIMA failed, falling back to moving average: {e}")
            baseline = BaselineForecaster(self.data)
            return baseline.moving_average_forecast(horizon)
    
    def _get_differencing_order(self, ts: pd.Series) -> int:
        """
        Determine differencing order using ADF test.
        
        Returns:
            0 if stationary, 1 if needs first differencing, 2 max
        """
        try:
            # Test original series
            result = adfuller(ts.dropna(), autolag='AIC')
            if result[1] < 0.05:  # p-value < 0.05, stationary
                return 0
            
            # Test first difference
            diff1 = ts.diff().dropna()
            if len(diff1) > 10:
                result = adfuller(diff1, autolag='AIC')
                if result[1] < 0.05:
                    return 1
            
            return 1  # Default to 1 if tests fail
        except Exception:
            return 1  # Safe default
    
    def get_model_used(self) -> str:
        """Return which model was/will be used."""
        if self.days_of_data < self.MIN_DAYS_FOR_MOVING_AVG:
            return "naive"
        elif not self.can_use_arima():
            return "moving_average"
        else:
            return "arima"


class FeatureEngineering:
    """
    Feature engineering for exogenous variables.
    Used in ARIMAX for seasonality.
    """
    
    @staticmethod
    def create_features(dates: pd.DatetimeIndex, festivals: Optional[Dict[date, str]] = None) -> pd.DataFrame:
        """
        Create exogenous features for dates.
        
        Features:
        - is_weekend: Saturday or Sunday
        - day_of_week: 0-6 (encoded)
        - is_month_start: First 3 days
        - is_month_end: Last 3 days
        - is_festival: If date matches festival config
        """
        df = pd.DataFrame({'date': dates})
        
        # Weekend
        df['is_weekend'] = df['date'].dt.dayofweek.isin([5, 6]).astype(int)
        
        # Day of week (sine/cosine encoding for cyclical)
        day_of_week = df['date'].dt.dayofweek
        df['dow_sin'] = np.sin(2 * np.pi * day_of_week / 7)
        df['dow_cos'] = np.cos(2 * np.pi * day_of_week / 7)
        
        # Month position
        df['is_month_start'] = (df['date'].dt.day <= 3).astype(int)
        df['is_month_end'] = (df['date'].dt.day >= 28).astype(int)
        
        # Month encoding
        month = df['date'].dt.month
        df['month_sin'] = np.sin(2 * np.pi * month / 12)
        df['month_cos'] = np.cos(2 * np.pi * month / 12)
        
        # Festival flag
        if festivals:
            df['is_festival'] = df['date'].dt.date.isin(festivals.keys()).astype(int)
        else:
            df['is_festival'] = 0
        
        return df.drop(columns=['date'])
