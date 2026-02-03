from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.models import get_db, Store, SKU, ForecastResult, create_tables
from app.schemas import (
    CSVUploadResponse, 
    ForecastRequest, ForecastResponse, ForecastResultSchema,
    ReorderListResponse, ReorderSummary, ReorderItem,
    StoreResponse, SKUResponse, StockUpdateRequest,
    FestivalCreate, FestivalResponse,
    ForecastModelType
)
from app.services import CSVUploadService, ForecasterService, ReorderService

router = APIRouter()


# ============== Health & Init ==============

@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@router.post("/init-db")
async def initialize_database():
    """Initialize database tables."""
    try:
        create_tables()
        return {"success": True, "message": "Database tables created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== CSV Upload ==============

@router.post("/upload-sales", response_model=CSVUploadResponse)
async def upload_sales(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Upload CSV sales data and AUTO-TRIGGER forecast/reorder pipeline.
    
    Required columns: store_id, sku_id, sku_name, date, units_sold
    Optional columns: price, discount, category
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        content = await file.read()
        content_str = content.decode('utf-8')
        
        service = CSVUploadService(db)
        result = service.process_csv(content_str)
        
        # Auto-trigger pipeline if successful
        if result.success and result.store_id:
            def run_full_pipeline(store_id: str):
                # Create new session for background task
                db_bg = next(get_db())
                try:
                    # 1. Forecast
                    forecaster = ForecasterService(db_bg)
                    forecasts = forecaster.forecast_store(store_id, horizon=7)
                    forecaster.save_forecasts(store_id, forecasts, horizon=7)
                    
                    # 2. Reorder
                    reorder = ReorderService(db_bg)
                    recs = reorder.generate_recommendations(store_id, horizon=7)
                    reorder.save_recommendations(store_id, recs)
                    print(f"Pipeline completed for {store_id}")
                except Exception as e:
                    print(f"Pipeline failed: {e}")
                finally:
                    db_bg.close()

            if background_tasks:
                background_tasks.add_task(run_full_pipeline, result.store_id)
        
        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Upload Crash: {str(e)}")


# ============== Stores ==============

@router.get("/stores", response_model=List[StoreResponse])
async def list_stores(db: Session = Depends(get_db)):
    """List all stores."""
    stores = db.query(Store).all()
    return stores


@router.get("/stores/{store_id}", response_model=StoreResponse)
async def get_store(store_id: str, db: Session = Depends(get_db)):
    """Get a specific store."""
    store = db.query(Store).filter(Store.store_id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


@router.get("/stores/{store_id}/skus", response_model=List[SKUResponse])
async def list_store_skus(store_id: str, db: Session = Depends(get_db)):
    """List all SKUs for a store."""
    store = db.query(Store).filter(Store.store_id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    
    skus = db.query(SKU).filter(SKU.store_id == store.id).all()
    return skus


@router.post("/stores/{store_id}/update-stock")
async def update_stock(
    store_id: str,
    updates: List[StockUpdateRequest],
    db: Session = Depends(get_db)
):
    """
    Update current stock levels for SKUs.
    Store owners should do this weekly for accurate recommendations.
    """
    store = db.query(Store).filter(Store.store_id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    
    updated = 0
    for update in updates:
        sku = db.query(SKU).filter(
            SKU.sku_id == update.sku_id,
            SKU.store_id == store.id
        ).first()
        
        if sku:
            sku.current_stock = update.current_stock
            updated += 1
    
    db.commit()
    return {"updated": updated, "total": len(updates)}


# ============== Forecasting ==============

@router.post("/run-forecast")
async def run_forecast(
    request: ForecastRequest,
    background_tasks: bool = Query(False, description="Run in background (async)"),
    db: Session = Depends(get_db)
):
    """
    Run forecast for a store.
    
    This generates predictions for the next N days.
    If background_tasks=True, runs via Celery/Redis.
    """
    store = db.query(Store).filter(Store.store_id == request.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    
    if background_tasks:
        try:
            from app.tasks import run_forecast_async
            task = run_forecast_async.delay(
                store_id=request.store_id,
                horizon=request.horizon,
                sku_ids=request.sku_ids
            )
            return {
                "success": True,
                "message": "Forecast started in background",
                "task_id": str(task.id)
            }
        except Exception as e:
            # Fallback to sync or error? 
            # For now return error so user knows Redis might be down
            raise HTTPException(status_code=503, detail=f"Failed to queue task (Redis down?): {str(e)}")
            
    # Synchronous execution (default)
    service = ForecasterService(db)
    forecasts = service.forecast_store(
        store_id=request.store_id,
        horizon=request.horizon,
        sku_ids=request.sku_ids
    )
    
    # Save forecasts
    saved_count = service.save_forecasts(request.store_id, forecasts, request.horizon)
    
    # Also regenerate reorder recommendations immediately for sync requests
    reorder_service = ReorderService(db)
    recommendations = reorder_service.generate_recommendations(request.store_id, request.horizon)
    reorder_service.save_recommendations(request.store_id, recommendations)
    
    return {
        "success": True,
        "store_id": request.store_id,
        "horizon": request.horizon,
        "skus_forecasted": len(forecasts),
        "forecasts_saved": saved_count,
        "reorder_recs_generated": len(recommendations)
    }


@router.get("/get-forecast", response_model=ForecastResponse)
async def get_forecast(
    store_id: str,
    horizon: int = Query(default=7, ge=1, le=30),
    sku_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get forecasts for a store or specific SKU."""
    store = db.query(Store).filter(Store.store_id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    
    # Query forecast results
    query = db.query(ForecastResult).filter(
        ForecastResult.store_id == store.id,
        ForecastResult.forecast_horizon == horizon
    )
    
    if sku_id:
        sku = db.query(SKU).filter(
            SKU.sku_id == sku_id,
            SKU.store_id == store.id
        ).first()
        if sku:
            query = query.filter(ForecastResult.sku_id == sku.id)
    
    results = query.order_by(ForecastResult.forecast_date).all()
    
    # Build response
    forecasts = []
    total_predicted = 0
    generated_at = datetime.utcnow()
    
    for r in results:
        sku = db.query(SKU).filter(SKU.id == r.sku_id).first()
        forecasts.append(ForecastResultSchema(
            sku_id=sku.sku_id if sku else "unknown",
            sku_name=sku.sku_name if sku else "Unknown",
            forecast_date=r.forecast_date,
            predicted_units=r.predicted_units,
            confidence_lower=r.confidence_lower,
            confidence_upper=r.confidence_upper,
            model_used=ForecastModelType(r.model_used.value)
        ))
        total_predicted += r.predicted_units
        generated_at = r.generated_at
    
    # Generate insights
    service = ForecasterService(db)
    insights = service.generate_insights_from_schema(forecasts)
    
    return ForecastResponse(
        store_id=store_id,
        horizon=horizon,
        generated_at=generated_at,
        total_predicted=total_predicted,
        forecasts=forecasts,
        insights=insights
    )


# ============== Reorder List (THE MONEY ENDPOINT) ==============

@router.get("/get-reorder-list", response_model=ReorderListResponse)
async def get_reorder_list(
    store_id: str,
    horizon: int = Query(default=7, ge=1, le=30),
    regenerate: bool = Query(default=True),
    db: Session = Depends(get_db)
):
    """
    THE MONEY ENDPOINT.
    
    Get actionable reorder recommendations for a store.
    This is what the kirana owner sees and acts upon.
    
    Must be understandable in 10 seconds.
    """
    store = db.query(Store).filter(Store.store_id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    
    service = ReorderService(db)
    
    if regenerate:
        # Generate fresh recommendations
        recommendations = service.generate_recommendations(store_id, horizon)
        service.save_recommendations(store_id, recommendations)
    else:
        # Load from database
        from app.models import ReorderRecommendation, UrgencyLevel
        recs = db.query(ReorderRecommendation).filter(
            ReorderRecommendation.store_id == store.id,
            ReorderRecommendation.is_active == True
        ).all()
        
        recommendations = []
        for r in recs:
            sku = db.query(SKU).filter(SKU.id == r.sku_id).first()
            recommendations.append(ReorderItem(
                sku_id=sku.sku_id if sku else "unknown",
                sku_name=sku.sku_name if sku else "Unknown",
                reorder_qty=r.reorder_qty,
                reason=r.reason,
                urgency=r.urgency.value,
                forecasted_demand=r.forecasted_demand,
                current_stock=r.current_stock,
                velocity_change_pct=r.velocity_change_pct
            ))
    
    return ReorderListResponse(
        store_id=store_id,
        store_name=store.name,
        generated_at=datetime.utcnow(),
        total_items=len(recommendations),
        critical_items=sum(1 for r in recommendations if r.urgency.value == 'critical'),
        items=recommendations
    )


@router.get("/reorder-summary", response_model=ReorderSummary)
async def get_reorder_summary(
    store_id: str,
    db: Session = Depends(get_db)
):
    """Quick summary of pending reorder recommendations."""
    store = db.query(Store).filter(Store.store_id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    
    service = ReorderService(db)
    summary = service.get_summary(store_id)
    
    if not summary:
        return ReorderSummary(total_items=0, critical=0, high=0, medium=0, low=0)
    
    return summary


# ============== Festivals (Seasonality) ==============

@router.get("/festivals", response_model=List[FestivalResponse])
async def list_festivals(db: Session = Depends(get_db)):
    """List all configured festivals."""
    from app.services.festivals import FestivalService
    service = FestivalService(db)
    return service.get_all_festivals()


@router.post("/festivals/seed")
async def seed_festivals(
    year: int = Query(default=2026, ge=2020, le=2030),
    db: Session = Depends(get_db)
):
    """
    Seed default India festivals for a given year.
    Includes: Diwali, Holi, Eid, Ganesh Chaturthi, Christmas, etc.
    """
    from app.services.festivals import FestivalService
    service = FestivalService(db)
    count = service.seed_default_festivals(year)
    return {"success": True, "festivals_added": count, "year": year}


@router.post("/festivals", response_model=FestivalResponse)
async def add_festival(
    festival: FestivalCreate,
    db: Session = Depends(get_db)
):
    """Add a custom festival."""
    from app.services.festivals import FestivalService
    service = FestivalService(db)
    return service.add_festival(
        name=festival.name,
        festival_date=festival.date,
        region=festival.region,
        impact_multiplier=festival.impact_multiplier
    )


@router.get("/festivals/impact")
async def get_festival_impact(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    db: Session = Depends(get_db)
):
    """Get demand impact multiplier for a specific date."""
    from datetime import datetime as dt
    from app.services.festivals import FestivalService
    
    try:
        target_date = dt.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    service = FestivalService(db)
    multiplier = service.get_impact_multiplier(target_date)
    
    return {
        "date": date,
        "impact_multiplier": multiplier,
        "is_festival_period": multiplier > 1.0
    }


# ============== External Market Integrations ==============

@router.get("/mandi-prices")
async def get_mandi_prices(
    commodity: Optional[str] = None,
    state: Optional[str] = None
):
    """
    Fetch current commodity prices from OGD India (Mandi Prices).
    Integrates with data.gov.in external API.
    """
    from app.services.mandi_prices import MandiPriceService
    
    service = MandiPriceService()
    prices = service.get_latest_prices(commodity=commodity, state=state)
    
    return {
        "success": True,
        "source": "OGD India (data.gov.in)",
        "records": prices
    }

