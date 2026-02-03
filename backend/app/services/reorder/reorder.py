from datetime import datetime, date
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models import Store, SKU, ReorderRecommendation, UrgencyLevel
from app.services.forecasting import ForecasterService, calculate_velocity_change
from app.schemas import ReorderItem, ReorderListResponse, ReorderSummary
from app.config.settings import settings


class ReorderService:
    def __init__(self, db: Session):
        self.db = db
        self.forecaster = ForecasterService(db)
    
    def generate_recommendations(
        self,
        store_id: str,
        horizon: int = 7,
        threshold_velocity_pct: float = 20.0
    ) -> List[ReorderItem]:
        """
        Generate reorder recommendations for a store.
        
        Args:
            store_id: Store identifier
            horizon: Forecast horizon in days
            threshold_velocity_pct: Minimum velocity change to flag
            
        Returns:
            List of reorder recommendations
        """
        store = self.db.query(Store).filter(Store.store_id == store_id).first()
        if not store:
            return []
        
        # Get all SKUs for this store
        skus = self.db.query(SKU).filter(SKU.store_id == store.id).all()
        
        # Get forecasts for all SKUs
        forecasts = self.forecaster.forecast_store(store_id, horizon)
        
        recommendations = []
        
        for sku in skus:
            if sku.sku_id not in forecasts:
                continue
            
            sku_forecast = forecasts[sku.sku_id]
            forecast_points = sku_forecast['forecasts']
            
            # Calculate total forecasted demand
            total_demand = sum(fp.predicted_units for fp in forecast_points)
            
            # Get velocity change (Pre-computed in parallel worker)
            velocity_change = sku_forecast.get('velocity_change', 0.0)
            
            # Calculate reorder quantity
            reorder_qty, reason, urgency = self._calculate_reorder(
                forecasted_demand=total_demand,
                current_stock=sku.current_stock,
                velocity_change=velocity_change,
                threshold_velocity_pct=threshold_velocity_pct,
                horizon=horizon
            )
            
            # Only add if reorder needed
            if reorder_qty > 0:
                recommendations.append(ReorderItem(
                    sku_id=sku.sku_id,
                    sku_name=sku.sku_name,
                    reorder_qty=reorder_qty,
                    reason=reason,
                    urgency=urgency,
                    forecasted_demand=round(total_demand, 1),
                    current_stock=sku.current_stock,
                    velocity_change_pct=velocity_change
                ))
        
        # Sort by urgency (critical first)
        urgency_order = {
            UrgencyLevel.CRITICAL: 0,
            UrgencyLevel.HIGH: 1,
            UrgencyLevel.MEDIUM: 2,
            UrgencyLevel.LOW: 3
        }
        recommendations.sort(key=lambda x: urgency_order.get(x.urgency, 4))
        
        return recommendations
    
    def _calculate_reorder(
        self,
        forecasted_demand: float,
        current_stock: int,
        velocity_change: float,
        threshold_velocity_pct: float,
        horizon: int
    ) -> tuple:
        """
        Calculate reorder quantity, reason, and urgency.
        
        Returns:
            Tuple of (reorder_qty, reason, urgency)
        """
        # Safety stock: configurable multiplier
        safety_stock = int(forecasted_demand * (settings.SAFETY_STOCK_MULTIPLIER - 1))
        
        # Reorder formula
        reorder_qty = max(0, int(
            forecasted_demand + safety_stock - current_stock
        ))
        
        # Determine urgency and reason
        stock_coverage_days = 0
        if forecasted_demand > 0:
            daily_demand = forecasted_demand / horizon
            stock_coverage_days = current_stock / daily_demand if daily_demand > 0 else float('inf')
        
        # Build reason and urgency
        coverage_text = f"{min(99.9, stock_coverage_days):.1f}"
        if stock_coverage_days > 99: coverage_text = "99+"

        if current_stock == 0:
            urgency = UrgencyLevel.CRITICAL
            reason = "Out of stock! Immediate reorder needed."
        elif stock_coverage_days < 2:
            urgency = UrgencyLevel.CRITICAL
            reason = f"Stock-out risk: only {coverage_text} days of stock left."
        elif stock_coverage_days < 4:
            urgency = UrgencyLevel.HIGH
            reason = f"Low stock: {coverage_text} days remaining."
        elif velocity_change >= threshold_velocity_pct:
            urgency = UrgencyLevel.HIGH
            reason = f"{velocity_change:+.0f}% velocity increase vs last week."
        elif velocity_change >= threshold_velocity_pct / 2:
            urgency = UrgencyLevel.MEDIUM
            reason = f"{velocity_change:+.0f}% velocity increase. Monitor closely."
        else:
            urgency = UrgencyLevel.LOW
            reason = f"Regular restock for {horizon}-day forecast."
        
        return reorder_qty, reason, urgency
    
    def save_recommendations(self, store_id: str, recommendations: List[ReorderItem]) -> int:
        """
        Save recommendations to database.
        
        Returns:
            Number of recommendations saved
        """
        store = self.db.query(Store).filter(Store.store_id == store_id).first()
        if not store:
            return 0
        
        # Mark old recommendations as inactive
        self.db.query(ReorderRecommendation).filter(
            ReorderRecommendation.store_id == store.id,
            ReorderRecommendation.is_active == True
        ).update({'is_active': False})
        
        count = 0
        for rec in recommendations:
            sku = self.db.query(SKU).filter(
                SKU.sku_id == rec.sku_id,
                SKU.store_id == store.id
            ).first()
            
            if not sku:
                continue
            
            db_rec = ReorderRecommendation(
                store_id=store.id,
                sku_id=sku.id,
                reorder_qty=rec.reorder_qty,
                reason=rec.reason,
                urgency=UrgencyLevel[rec.urgency.upper()] if isinstance(rec.urgency, str) else rec.urgency,
                forecasted_demand=rec.forecasted_demand,
                current_stock=rec.current_stock,
                velocity_change_pct=rec.velocity_change_pct,
                is_active=True
            )
            self.db.add(db_rec)
            count += 1
        
        self.db.commit()
        return count
    
    def get_summary(self, store_id: str) -> Optional[ReorderSummary]:
        """Get quick summary of pending recommendations."""
        store = self.db.query(Store).filter(Store.store_id == store_id).first()
        if not store:
            return None
        
        recs = self.db.query(ReorderRecommendation).filter(
            ReorderRecommendation.store_id == store.id,
            ReorderRecommendation.is_active == True
        ).all()
        
        if not recs:
            return ReorderSummary(
                total_items=0,
                critical=0,
                high=0,
                medium=0,
                low=0
            )
        
        return ReorderSummary(
            total_items=len(recs),
            critical=sum(1 for r in recs if r.urgency == UrgencyLevel.CRITICAL),
            high=sum(1 for r in recs if r.urgency == UrgencyLevel.HIGH),
            medium=sum(1 for r in recs if r.urgency == UrgencyLevel.MEDIUM),
            low=sum(1 for r in recs if r.urgency == UrgencyLevel.LOW)
        )
