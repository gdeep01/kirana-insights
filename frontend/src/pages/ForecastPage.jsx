/**
 * Forecast Page - Sales Forecast Visualization
 * 
 * Shows forecast charts and allows running forecasts.
 */

import { useState, useEffect } from 'react';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import {
    TrendingUp,
    Info,
    BarChart3,
    RefreshCw
} from 'lucide-react';
import api from '../services/api';

// Register Chart.js components
ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler
);

export default function ForecastPage() {
    const [stores, setStores] = useState([]);
    const [selectedStore, setSelectedStore] = useState('');
    const [skus, setSkus] = useState([]);
    const [selectedSku, setSelectedSku] = useState('');
    const [horizon, setHorizon] = useState(7);
    const [forecast, setForecast] = useState(null);
    const [loading, setLoading] = useState(false);
    const [running, setRunning] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        loadStores();
    }, []);

    useEffect(() => {
        if (selectedStore) {
            loadSkus();
        }
    }, [selectedStore]);

    const loadStores = async () => {
        try {
            const data = await api.getStores();
            setStores(data);
            if (data.length > 0) {
                setSelectedStore(data[0].store_id);
            }
        } catch (err) {
            setError('Failed to load stores');
        }
    };

    const loadSkus = async () => {
        try {
            const data = await api.getStoreSKUs(selectedStore);
            setSkus(data);
            if (data.length > 0) {
                setSelectedSku(data[0].sku_id);
            }
        } catch (err) {
            console.error('Failed to load SKUs:', err);
        }
    };

    const handleRunForecast = async () => {
        if (!selectedStore) return;

        setRunning(true);
        setError(null);

        try {
            await api.runForecast(selectedStore, horizon);
            await loadForecast();
        } catch (err) {
            setError(err.message);
        } finally {
            setRunning(false);
        }
    };

    const loadForecast = async () => {
        if (!selectedStore) return;

        setLoading(true);
        setError(null);

        try {
            const data = await api.getForecast(selectedStore, horizon, selectedSku || null);
            setForecast(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    // Prepare chart data
    const getChartData = () => {
        if (!forecast || !forecast.forecasts.length) {
            return null;
        }

        // Group by SKU
        const skuData = {};
        forecast.forecasts.forEach(f => {
            if (!skuData[f.sku_id]) {
                skuData[f.sku_id] = {
                    name: f.sku_name,
                    dates: [],
                    values: [],
                    lower: [],
                    upper: [],
                };
            }
            skuData[f.sku_id].dates.push(f.forecast_date);
            skuData[f.sku_id].values.push(f.predicted_units);
            skuData[f.sku_id].lower.push(f.confidence_lower);
            skuData[f.sku_id].upper.push(f.confidence_upper);
        });

        const colors = [
            { main: '#3b82f6', fill: 'rgba(59, 130, 246, 0.1)' },
            { main: '#10b981', fill: 'rgba(16, 185, 129, 0.1)' },
            { main: '#f59e0b', fill: 'rgba(245, 158, 11, 0.1)' },
            { main: '#ef4444', fill: 'rgba(239, 68, 68, 0.1)' },
            { main: '#8b5cf6', fill: 'rgba(139, 92, 246, 0.1)' },
        ];

        const datasets = [];
        let colorIndex = 0;

        Object.entries(skuData).forEach(([skuId, data]) => {
            const color = colors[colorIndex % colors.length];

            // Main line
            datasets.push({
                label: data.name,
                data: data.values,
                borderColor: color.main,
                backgroundColor: color.fill,
                fill: true,
                tension: 0.4,
            });

            colorIndex++;
        });

        // Use dates from first SKU
        const labels = Object.values(skuData)[0]?.dates || [];

        return {
            labels,
            datasets,
        };
    };

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top',
                labels: {
                    color: '#94a3b8',
                },
            },
            title: {
                display: true,
                text: `${horizon}-Day Demand Forecast`,
                color: '#f8fafc',
                font: {
                    size: 16,
                },
            },
        },
        scales: {
            x: {
                ticks: { color: '#94a3b8' },
                grid: { color: 'rgba(148, 163, 184, 0.1)' },
            },
            y: {
                ticks: { color: '#94a3b8' },
                grid: { color: 'rgba(148, 163, 184, 0.1)' },
                beginAtZero: true,
            },
        },
    };

    const chartData = getChartData();

    return (
        <div>
            {/* Header */}
            <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
                <div className="card-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
                        <div style={{
                            background: 'rgba(59, 130, 246, 0.1)',
                            padding: '10px',
                            borderRadius: '8px',
                            color: '#3b82f6'
                        }}>
                            <BarChart3 size={24} />
                        </div>
                        <div>
                            <h1 className="card-title">Demand Forecast</h1>
                            <p className="card-subtitle">AI-powered sales predictions for the next {horizon} days</p>
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
                            value={selectedSku}
                            onChange={(e) => setSelectedSku(e.target.value)}
                            style={{ width: 'auto' }}
                        >
                            <option value="">All Products</option>
                            {skus.map(sku => (
                                <option key={sku.sku_id} value={sku.sku_id}>
                                    {sku.sku_name}
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
                        <button
                            className="btn btn-primary"
                            onClick={handleRunForecast}
                            disabled={running || !selectedStore}
                        >
                            {running ? (
                                <>
                                    <div className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }}></div>
                                    Running...
                                </>
                            ) : (
                                <>
                                    <TrendingUp size={16} />
                                    Run Forecast
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </div>

            {/* ERROR ALERT */}
            {error && (
                <div className="alert alert-error">{error}</div>
            )}

            {/* INSIGHTS SECTION (NEW) */}
            {forecast && forecast.insights && forecast.insights.length > 0 && (
                <div className="card" style={{ marginBottom: 'var(--space-lg)', borderLeft: '4px solid var(--color-primary)' }}>
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-md)' }}>
                        <div style={{ color: 'var(--color-primary)', marginTop: '2px' }}>
                            <Info size={20} />
                        </div>
                        <div>
                            <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 'var(--space-sm)' }}>
                                Forecast Insights
                            </h3>
                            <ul style={{ paddingLeft: '20px', color: 'var(--text-secondary)' }}>
                                {forecast.insights.map((insight, idx) => (
                                    <li key={idx} style={{ marginBottom: '4px' }}>{insight}</li>
                                ))}
                            </ul>
                        </div>
                    </div>
                </div>
            )}

            {/* Stats */}
            {forecast && (
                <div className="stats-grid">
                    <div className="stat-card">
                        <div className="stat-value">{forecast.forecasts.length}</div>
                        <div className="stat-label">Forecast Points</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value success">
                            {Math.round(forecast.total_predicted)}
                        </div>
                        <div className="stat-label">Total Predicted Units</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value">
                            {Math.round(forecast.total_predicted / horizon)}
                        </div>
                        <div className="stat-label">Avg Daily Demand</div>
                    </div>
                </div>
            )}

            {/* Loading */}
            {loading && (
                <div className="loading">
                    <div className="spinner"></div>
                </div>
            )}

            {/* Chart */}
            {!loading && chartData && (
                <div className="card">
                    <div className="chart-container">
                        <Line data={chartData} options={chartOptions} />
                    </div>
                </div>
            )}

            {/* Forecast Table */}
            {!loading && forecast && forecast.forecasts.length > 0 && (
                <div className="card" style={{ marginTop: 'var(--space-lg)' }}>
                    <h3 className="card-title">Detailed Projections</h3>
                    <div className="table-container">
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>Product</th>
                                    <th>Date</th>
                                    <th>Predicted Units</th>
                                    <th>Confidence Range</th>
                                    <th>Model</th>
                                </tr>
                            </thead>
                            <tbody>
                                {forecast.forecasts.slice(0, 20).map((f, idx) => (
                                    <tr key={idx}>
                                        <td>{f.sku_name}</td>
                                        <td>{f.forecast_date}</td>
                                        <td><strong>{f.predicted_units.toFixed(1)}</strong></td>
                                        <td>
                                            {f.confidence_lower?.toFixed(1)} - {f.confidence_upper?.toFixed(1)}
                                        </td>
                                        <td>
                                            <span className="badge badge-low" style={{ background: '#334155', color: '#94a3b8', border: 'none' }}>
                                                {f.model_used}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Empty State */}
            {!loading && (!forecast || forecast.forecasts.length === 0) && (
                <div className="card">
                    <div className="empty-state">
                        <div className="empty-state-icon">
                            <BarChart3 size={64} strokeWidth={1} color="var(--text-muted)" />
                        </div>
                        <h2 style={{ color: 'var(--text-primary)', marginBottom: 'var(--space-sm)' }}>No Forecasts Yet</h2>
                        <p>Upload sales data and run a forecast to see predictions.</p>
                    </div>
                </div>
            )}
        </div>
    );
}
