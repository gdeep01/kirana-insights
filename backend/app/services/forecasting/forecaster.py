import pandas as pd
from datetime import date, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models import Store, SKU, SalesTransaction, ForecastResult, ForecastModel
from app.services.forecasting.baseline import BaselineForecaster, ForecastPoint, calculate_velocity_change
from app.services.forecasting.arima import ARIMAForecaster


import concurrent.futures
import os

# Persistent process pool for CPU-bound forecasting tasks
# Initialized on first use to avoid overhead if not used
_forecast_pool = None

def get_forecast_pool():
    global _forecast_pool
    if _forecast_pool is None:
        # Limit to 2-4 workers for local Kirana app to avoid memory pressure
        max_workers = min(os.cpu_count() or 1, 4)
        print(f"Initializing persistent forecast pool with {max_workers} workers...")
        _forecast_pool = concurrent.futures.ProcessPoolExecutor(max_workers=max_workers)
    return _forecast_pool

class ForecasterService:
    """
    Main forecasting service.
    
    Model selection logic per SKU:
    - <30 days: Moving average
    - ≥60 days: ARIMA
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def forecast_store(
        self,
        store_id: str,
        horizon: int = 7,
        sku_ids: Optional[List[str]] = None
    ) -> dict:
        """
        Generate forecasts for all SKUs in a store PARALLELIZED.
        """
        # 1. Get Store
        store = self.db.query(Store).filter(Store.store_id == store_id).first()
        if not store:
            return {}
        
        # 2. Bulk Fetch Data (One Query)
        sku_query = self.db.query(SKU).filter(SKU.store_id == store.id)
        if sku_ids:
            sku_query = sku_query.filter(SKU.sku_id.in_(sku_ids))
        skus = sku_query.all()
        sku_map = {s.id: s for s in skus} 
        
        if not skus:
            return {}
            
        relevant_sku_ids = list(sku_map.keys())
        
        # Optimization: Filter by relevant SKUs and get only needed columns
        transactions = self.db.query(SalesTransaction.sku_id, SalesTransaction.date, SalesTransaction.units_sold).filter(
            SalesTransaction.store_id == store.id,
            SalesTransaction.sku_id.in_(relevant_sku_ids)
        ).order_by(SalesTransaction.date).all()
        
        # Group data by SKU in memory (Faster than multiple queries)
        from collections import defaultdict
        data_by_sku = defaultdict(list)
        for t in transactions:
            data_by_sku[t.sku_id].append({
                'date': t.date,
                'units_sold': t.units_sold
            })
            
        # 3. Prepare Tasks
        tasks = []
        for sku_db_id, sku_obj in sku_map.items():
            records = data_by_sku.get(sku_db_id, [])
            if records:
                tasks.append((sku_obj.sku_id, sku_obj.sku_name, records, horizon))

        # 4. Run Parallel (Persistent Pool)
        results = {}
        
        if not tasks:
            return {}

        pool = get_forecast_pool()
        
        try:
            # Submit all tasks to the persistent pool
            futures = [pool.submit(_worker_forecast_sku, *task) for task in tasks]
            
            # Wait for completion with a timeout to avoid hanging
            for future in concurrent.futures.as_completed(futures, timeout=30):
                try:
                    res = future.result()
                    if res:
                        results[res['sku_id']] = {
                            'sku_name': res['sku_name'],
                            'forecasts': res['forecasts'],
                            'model_used': res['model_used'],
                            'velocity_change': res.get('velocity_change', 0.0)
                        }
                except Exception as e:
                    print(f"Forecast worker failed: {e}")
                    continue
        except Exception as e:
            print(f"Persistent pool execution failed ({e}), falling back to serial...")
            # Fallback to serial for robustness
            for task in tasks:
                try:
                    res = _worker_forecast_sku(*task)
                    if res:
                        results[res['sku_id']] = {
                            'sku_name': res['sku_name'],
                            'forecasts': res['forecasts'],
                            'model_used': res['model_used'],
                            'velocity_change': res.get('velocity_change', 0.0)
                        }
                except Exception as inner_e:
                    print(f"Serial forecast failed for {task[1]}: {inner_e}")

        return results

    def generate_insights(self, forecasts: dict) -> List[str]:
        """
        Generate natural language insights from forecast data.
        Target audience: Non-technical store owners.
        """
        insights = []
        
        if not forecasts:
            return ["Not enough data to generate insights yet."]
            
        total_predicted_volume = 0
        velocity_up = 0
        velocity_down = 0
        top_product = None
        max_demand = -1
        
        for sku_data in forecasts.values():
            # Calc total volume
            vol = sum(f.predicted_units for f in sku_data['forecasts'])
            total_predicted_volume += vol
            
            # Track velocity
            vc = sku_data.get('velocity_change', 0)
            if vc > 10:
                velocity_up += 1
            elif vc < -10:
                velocity_down += 1
                
            # Find top mover
            if vol > max_demand:
                max_demand = vol
                top_product = sku_data['sku_name']
        
        # Insight 1: Overall Trend
        insights.append(f"We predicted a total demand of {int(total_predicted_volume)} units across all products for the next period.")
        
        # Insight 2: Velocity
        if velocity_up > velocity_down:
            insights.append(f"Good news! {velocity_up} products are showing a strong upward sales trend.")
        elif velocity_down > velocity_up:
            insights.append(f"Heads up: {velocity_down} products are selling slower than usual. You might want to run a promotion.")
            
        # Insight 3: Top Mover
        if top_product:
            insights.append(f"Star Performer: '{top_product}' is expected to be your highest selling item.")
            
        return insights

    def generate_insights_from_schema(self, forecasts: List['ForecastResultSchema']) -> List[str]:
        """
        Generate insights from ForecastResultSchema objects (for get_forecast endpoint).
        """
        if not forecasts:
            return ["No forecast data available to generate insights."]
            
        # Group by SKU
        from collections import defaultdict
        sku_groups = defaultdict(list)
        for r in forecasts:
            sku_groups[r.sku_id].append(r)
            
        # Calculate stats
        total_predicted_volume = sum(r.predicted_units for r in forecasts)
        top_product = None
        max_demand = -1
        
        for sku_id, items in sku_groups.items():
            vol = sum(i.predicted_units for i in items)
            if vol > max_demand:
                 max_demand = vol
                 # Get name from first item
                 top_product = items[0].sku_name
                 
        # Generate text
        insights = []
        insights.append(f"Total predicted demand: {int(total_predicted_volume)} units.")
        
        if top_product:
             insights.append(f"Star Performer: '{top_product}' is expected to be your highest selling item.")
             
        # Add a simple volatility/trend insight if possible
        # e.g. check if last day > first day
        return insights
        
    def save_forecasts(
        self,
        store_id: str,
        forecasts: dict,
        horizon: int
    ) -> int:
        """
        Save forecast results to database.
        
        Returns:
            Number of forecasts saved
        """
        store = self.db.query(Store).filter(Store.store_id == store_id).first()
        if not store:
            return 0
        
        # Get all SKUs for lookups
        skus = self.db.query(SKU).filter(SKU.store_id == store.id).all()
        sku_map = {s.sku_id: s.id for s in skus}
        
        forecast_objects = []
        
        for sku_id_str, sku_data in forecasts.items():
            if sku_id_str not in sku_map:
                continue
                
            sku_db_id = sku_map[sku_id_str]
            
            # Get model type
            model_str = sku_data.get('model_used', 'moving_average')
            try:
                model_type = ForecastModel[model_str.upper()]
            except:
                model_type = ForecastModel.MOVING_AVERAGE
            
            for forecast_point in sku_data['forecasts']:
                forecast_objects.append(ForecastResult(
                    store_id=store.id,
                    sku_id=sku_db_id,
                    forecast_date=forecast_point.date,
                    predicted_units=forecast_point.predicted_units,
                    confidence_lower=forecast_point.confidence_lower,
                    confidence_upper=forecast_point.confidence_upper,
                    model_used=model_type,
                    forecast_horizon=horizon
                ))

        # Faster: Delete ALL forecasts for this Store + Horizon (simple)
        forecasted_sku_db_ids = [sku_map[sid] for sid in forecasts.keys() if sid in sku_map]
        
        if forecasted_sku_db_ids:
             self.db.query(ForecastResult).filter(
                 ForecastResult.store_id == store.id,
                 ForecastResult.sku_id.in_(forecasted_sku_db_ids),
                 ForecastResult.forecast_date >= date.today()
             ).delete(synchronize_session=False)

        if forecast_objects:
            self.db.bulk_save_objects(forecast_objects)
            self.db.commit()
            
        return len(forecast_objects)


# --- WORKER FUNCTIONS (Must be at module level for ProcessPoolExecutor) ---

def _worker_forecast_sku(sku_id, sku_name, records, horizon):
    """
    Worker task to forecast a single SKU.
    Runs in a separate process for CPU parallelism.
    """
    try:
        if not records:
            return None
            
        # Convert records to DataFrame
        df = pd.DataFrame(records)
        df['date'] = pd.to_datetime(df['date'])
        
        # 1. Calculate Velocity Change (for insights)
        velocity_change = calculate_velocity_change(df)
        
        # 2. Run Forecast
        # ARIMAForecaster automatically selects best model based on data length
        forecaster = ARIMAForecaster(df)
        forecasts = forecaster.forecast(horizon)
        model_used = forecaster.get_model_used()
        
        return {
            'sku_id': sku_id,
            'sku_name': sku_name,
            'forecasts': forecasts,
            'model_used': model_used,
            'velocity_change': velocity_change
        }
    except Exception as e:
        print(f"Error in _worker_forecast_sku for {sku_name}: {e}")
        return None
