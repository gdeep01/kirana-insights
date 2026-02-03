/**
 * Dashboard Page - Overview
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
    Store,
    ShoppingCart,
    TrendingUp,
    Upload,
    ChevronRight,
    BarChart3
} from 'lucide-react';
import api from '../services/api';

export default function DashboardPage() {
    const [stores, setStores] = useState([]);
    const [summary, setSummary] = useState(null);
    const [mandiPrices, setMandiPrices] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedStore, setSelectedStore] = useState('');

    useEffect(() => {
        loadData();
        loadMandiPrices();
    }, []);

    useEffect(() => {
        if (selectedStore) {
            loadSummary();
        }
    }, [selectedStore]);

    const loadData = async () => {
        try {
            const storesData = await api.getStores();
            setStores(storesData);
            if (storesData.length > 0) {
                setSelectedStore(storesData[0].store_id);
            }
        } catch (err) {
            console.error('Failed to load data:', err);
        } finally {
            setLoading(false);
        }
    };

    const loadSummary = async () => {
        try {
            const data = await api.getReorderSummary(selectedStore);
            setSummary(data);
        } catch (err) {
            console.error('Failed to load summary:', err);
        }
    };

    const loadMandiPrices = async () => {
        try {
            const data = await api.getMandiPrices();
            if (data.success) {
                setMandiPrices(data.records);
            }
        } catch (err) {
            console.error('Failed to load mandi prices:', err);
        }
    };

    if (loading) {
        return (
            <div className="loading">
                <div className="spinner"></div>
            </div>
        );
    }

    return (
        <div>
            {/* Welcome Header */}
            <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)', marginBottom: 'var(--space-xs)' }}>
                    <Store size={28} color="var(--color-primary)" />
                    <h1 className="card-title" style={{ marginBottom: 0 }}>Kirana Insights</h1>
                </div>
                <p className="card-subtitle">
                    Know what to reorder, how much, and when — using your sales data.
                </p>
            </div>

            {stores.length === 0 ? (
                // Getting Started
                <div className="card">
                    <div className="empty-state">
                        <div className="empty-state-icon">
                            <Upload size={48} />
                        </div>
                        <h2>Get Started</h2>
                        <p>Upload your sales inventory to generate reorder recommendations.</p>
                        <Link to="/upload" className="btn btn-primary" style={{ marginTop: 'var(--space-lg)' }}>
                            Upload Sales Data
                        </Link>
                    </div>
                </div>
            ) : (
                <>
                    {/* Store Selector */}
                    <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
                        <div className="form-group" style={{ marginBottom: 0 }}>
                            <label className="form-label">Select Store</label>
                            <select
                                className="form-select"
                                value={selectedStore}
                                onChange={(e) => setSelectedStore(e.target.value)}
                                style={{ maxWidth: '300px' }}
                            >
                                {stores.map(store => (
                                    <option key={store.store_id} value={store.store_id}>
                                        {store.name}
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {/* Summary Stats */}
                    {summary && (
                        <div className="stats-grid">
                            <div className="stat-card">
                                <div className="stat-value">{summary.total_items}</div>
                                <div className="stat-label">Items to Reorder</div>
                            </div>
                            <div className="stat-card">
                                <div className="stat-value critical">{summary.critical}</div>
                                <div className="stat-label">Critical</div>
                            </div>
                            <div className="stat-card">
                                <div className="stat-value high">{summary.high}</div>
                                <div className="stat-label">High Priority</div>
                            </div>
                            <div className="stat-card">
                                <div className="stat-value warning">{summary.medium}</div>
                                <div className="stat-label">Medium</div>
                            </div>
                        </div>
                    )}

                    {/* Quick Actions */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 'var(--space-lg)' }}>
                        <Link to="/reorder" className="card" style={{ textDecoration: 'none', color: 'inherit' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)', marginBottom: 'var(--space-sm)' }}>
                                <ShoppingCart size={20} color="var(--color-primary)" />
                                <h2 style={{ margin: 0 }}>View Reorder List</h2>
                            </div>
                            <p className="card-subtitle">See what needs to be ordered right now</p>
                            {summary && summary.critical > 0 && (
                                <div className="alert alert-error" style={{ marginTop: 'var(--space-md)' }}>
                                    {summary.critical} critical items need attention!
                                </div>
                            )}
                        </Link>

                        <Link to="/forecast" className="card" style={{ textDecoration: 'none', color: 'inherit' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)', marginBottom: 'var(--space-sm)' }}>
                                <TrendingUp size={20} color="var(--color-primary)" />
                                <h2 style={{ margin: 0 }}>View Forecasts</h2>
                            </div>
                            <p className="card-subtitle">See predicted demand for the coming days</p>
                        </Link>

                        <Link to="/upload" className="card" style={{ textDecoration: 'none', color: 'inherit' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)', marginBottom: 'var(--space-sm)' }}>
                                <Upload size={20} color="var(--color-primary)" />
                                <h2 style={{ margin: 0 }}>Upload New Data</h2>
                            </div>
                            <p className="card-subtitle">Add more sales data to improve predictions</p>
                        </Link>
                    </div>

                    {/* Mandi Prices / Market Trends */}
                    <div className="card" style={{ marginTop: 'var(--space-lg)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-md)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                                <TrendingUp size={20} color="var(--color-primary)" />
                                <h2 style={{ margin: 0 }}>Market Price Trends (Mandi)</h2>
                            </div>
                            <span style={{ fontSize: '0.8rem', opacity: 0.6 }}>Source: data.gov.in</span>
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--space-md)' }}>
                            {mandiPrices.map((item, idx) => (
                                <div key={idx} style={{ padding: 'var(--space-sm)', background: 'rgba(255,255,255,0.03)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(255,255,255,0.05)' }}>
                                    <div style={{ fontSize: '0.8rem', opacity: 0.6, marginBottom: '4px' }}>{item.commodity}</div>
                                    <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>₹{item.modal_price} / quintal</div>
                                    <div style={{ fontSize: '0.7rem', marginTop: '4px', opacity: 0.5 }}>{item.market}, {item.state}</div>
                                </div>
                            ))}
                        </div>
                    </div>
                </>
            )}

            {/* How it works */}
            <div className="card" style={{ marginTop: 'var(--space-xl)' }}>
                <h2 className="card-title">How It Works</h2>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 'var(--space-lg)', marginTop: 'var(--space-lg)', flexWrap: 'wrap' }}>
                    <div style={{ textAlign: 'center', flex: 1, minWidth: '150px' }}>
                        <div style={{
                            width: '40px',
                            height: '40px',
                            borderRadius: '50%',
                            background: 'var(--color-primary)',
                            color: 'white',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            margin: '0 auto var(--space-sm)',
                            fontWeight: 'bold'
                        }}>1</div>
                        <h3>Upload Data</h3>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                            Upload your daily sales CSV file
                        </p>
                    </div>

                    <ChevronRight className="hide-mobile" style={{ opacity: 0.3 }} />

                    <div style={{ textAlign: 'center', flex: 1, minWidth: '150px' }}>
                        <div style={{
                            width: '40px',
                            height: '40px',
                            borderRadius: '50%',
                            background: 'var(--color-primary)',
                            color: 'white',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            margin: '0 auto var(--space-sm)',
                            fontWeight: 'bold'
                        }}>2</div>
                        <h3>Analyze Demand</h3>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                            Calculates predicted demand using historical trends
                        </p>
                    </div>

                    <ChevronRight className="hide-mobile" style={{ opacity: 0.3 }} />

                    <div style={{ textAlign: 'center', flex: 1, minWidth: '150px' }}>
                        <div style={{
                            width: '40px',
                            height: '40px',
                            borderRadius: '50%',
                            background: 'var(--color-primary)',
                            color: 'white',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            margin: '0 auto var(--space-sm)',
                            fontWeight: 'bold'
                        }}>3</div>
                        <h3>See Reorder List</h3>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                            Know exactly what and how much to order
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
