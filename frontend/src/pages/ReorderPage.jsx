/**
 * Reorder Page - THE MOST IMPORTANT PAGE
 * 
 * Must be understandable by a kirana owner in 10 seconds.
 * Shows: SKU | Reorder Qty | Reason | Urgency
 */

import { useState, useEffect } from 'react';
import {
    Package,
    ShoppingCart,
    RefreshCw,
    TrendingUp,
    TrendingDown,
    Minus,
    CheckCircle2
} from 'lucide-react';
import api from '../services/api';

export default function ReorderPage() {
    const [reorderList, setReorderList] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [stores, setStores] = useState([]);
    const [selectedStore, setSelectedStore] = useState('');
    const [horizon, setHorizon] = useState(7);

    // Load stores on mount
    useEffect(() => {
        loadStores();
    }, []);

    // Load reorder list when store changes
    useEffect(() => {
        if (selectedStore) {
            loadReorderList();
        }
    }, [selectedStore, horizon]);

    const loadStores = async () => {
        try {
            const data = await api.getStores();
            setStores(data);
            if (data.length > 0) {
                setSelectedStore(data[0].store_id);
            }
        } catch (err) {
            setError('Failed to load stores. Make sure the backend is running.');
        }
    };

    const loadReorderList = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await api.getReorderList(selectedStore, horizon, true);
            setReorderList(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const getUrgencyBadge = (urgency) => {
        const badges = {
            critical: 'badge badge-critical',
            high: 'badge badge-high',
            medium: 'badge badge-medium',
            low: 'badge badge-low',
        };
        return badges[urgency] || 'badge';
    };

    const getVelocityClass = (velocity) => {
        if (velocity > 0) return 'velocity-change velocity-up';
        if (velocity < 0) return 'velocity-change velocity-down';
        return 'velocity-change velocity-neutral';
    };

    if (!stores.length && !loading) {
        return (
            <div className="card">
                <div className="empty-state">
                    <div className="empty-state-icon">
                        <Package size={48} />
                    </div>
                    <h2>No Stores Found</h2>
                    <p>Upload sales data first to see reorder recommendations.</p>
                </div>
            </div>
        );
    }

    return (
        <div>
            {/* Header */}
            <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
                <div className="card-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
                        <div style={{
                            background: 'rgba(239, 68, 68, 0.1)',
                            padding: '10px',
                            borderRadius: '8px',
                            color: '#ef4444'
                        }}>
                            <ShoppingCart size={24} />
                        </div>
                        <div>
                            <h1 className="card-title">Reorder List</h1>
                            <p className="card-subtitle">What to order, how much, and why</p>
                        </div>
                    </div>
                    <div style={{ display: 'flex', gap: 'var(--space-md)', flexWrap: 'wrap' }}>
                        <select
                            className="form-select"
                            value={selectedStore}
                            onChange={(e) => setSelectedStore(e.target.value)}
                            style={{ width: 'auto' }}
                        >
                            {stores.map(store => (
                                <option key={store.store_id} value={store.store_id}>
                                    {store.name}
                                </option>
                            ))}
                        </select>
                        <select
                            className="form-select"
                            value={horizon}
                            onChange={(e) => setHorizon(Number(e.target.value))}
                            style={{ width: 'auto' }}
                        >
                            <option value={7}>7 Days</option>
                            <option value={14}>14 Days</option>
                            <option value={30}>30 Days</option>
                        </select>
                        <button className="btn btn-primary" onClick={loadReorderList}>
                            <RefreshCw size={16} />
                            Refresh
                        </button>
                    </div>
                </div>
            </div>

            {/* Stats Summary */}
            {reorderList && (
                <div className="stats-grid">
                    <div className="stat-card">
                        <div className="stat-value">{reorderList.total_items}</div>
                        <div className="stat-label">Items to Reorder</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value critical">{reorderList.critical_items}</div>
                        <div className="stat-label">Critical</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value high">
                            {reorderList.items.filter(i => i.urgency === 'high').length}
                        </div>
                        <div className="stat-label">High Priority</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value warning">
                            {reorderList.items.filter(i => i.urgency === 'medium').length}
                        </div>
                        <div className="stat-label">Medium</div>
                    </div>
                </div>
            )}

            {/* Error Message */}
            {error && (
                <div className="alert alert-error">
                    {error}
                </div>
            )}

            {/* Loading State */}
            {loading && (
                <div className="loading">
                    <div className="spinner"></div>
                </div>
            )}

            {/* Reorder Table */}
            {!loading && reorderList && reorderList.items.length > 0 && (
                <div className="card">
                    <div className="table-container">
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>Product</th>
                                    <th>Order Qty</th>
                                    <th>Urgency</th>
                                    <th>Reason</th>
                                    <th>Velocity</th>
                                    <th>Current Stock</th>
                                </tr>
                            </thead>
                            <tbody>
                                {reorderList.items.map((item, index) => (
                                    <tr
                                        key={index}
                                        className={item.urgency === 'critical' ? 'table-row-critical' :
                                            item.urgency === 'high' ? 'table-row-high' : ''}
                                    >
                                        <td>
                                            <strong>{item.sku_name}</strong>
                                            <br />
                                            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                                                {item.sku_id}
                                            </span>
                                        </td>
                                        <td>
                                            <span className="reorder-qty">{item.reorder_qty}</span>
                                            <span style={{ color: 'var(--text-muted)' }}> units</span>
                                        </td>
                                        <td>
                                            <span className={getUrgencyBadge(item.urgency)}>
                                                {item.urgency}
                                            </span>
                                        </td>
                                        <td className="reorder-reason">{item.reason}</td>
                                        <td>
                                            {item.velocity_change_pct !== null && (
                                                <span className={getVelocityClass(item.velocity_change_pct)} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                                    {item.velocity_change_pct > 0 ? (
                                                        <TrendingUp size={14} />
                                                    ) : item.velocity_change_pct < 0 ? (
                                                        <TrendingDown size={14} />
                                                    ) : (
                                                        <Minus size={14} />
                                                    )}
                                                    {Math.abs(item.velocity_change_pct).toFixed(0)}%
                                                </span>
                                            )}
                                        </td>
                                        <td>{item.current_stock}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Empty State */}
            {!loading && reorderList && reorderList.items.length === 0 && (
                <div className="card">
                    <div className="empty-state">
                        <div className="empty-state-icon" style={{ color: 'var(--color-success)' }}>
                            <CheckCircle2 size={64} strokeWidth={1} />
                        </div>
                        <h2 style={{ color: 'var(--text-primary)', marginBottom: 'var(--space-sm)' }}>All Stocked Up!</h2>
                        <p>No items need reordering right now.</p>
                    </div>
                </div>
            )}
        </div>
    );
}
