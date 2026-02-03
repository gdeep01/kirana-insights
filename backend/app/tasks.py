"""
Async Tasks for Celery.
"""

from app.worker import celery_app
from app.models.database import SessionLocal
from app.services.forecasting import ForecasterService
from app.services.reorder import ReorderService

@celery_app.task(bind=True, name="app.tasks.run_forecast_async")
def run_forecast_async(self, store_id: str, horizon: int = 7, sku_ids: list = None):
    """
    Background task to run forecast for a store.
    """
    db = SessionLocal()
    try:
        service = ForecasterService(db)
        
        # 1. Generate Forecasts
        forecasts = service.forecast_store(store_id, horizon, sku_ids)
        service.save_forecasts(store_id, forecasts, horizon)
        
        # 2. Regenerate Reorder Recommendations (chained)
        reorder_service = ReorderService(db)
        recommendations = reorder_service.generate_recommendations(store_id, horizon)
        reorder_service.save_recommendations(store_id, recommendations)
        
        return {
            "store_id": store_id,
            "forecasts_generated": len(forecasts),
            "reorder_recs_generated": len(recommendations),
            "status": "completed"
        }
        
    except Exception as e:
        # Log error?
        print(f"Error in async forecast: {e}")
        raise e
    finally:
        db.close()
