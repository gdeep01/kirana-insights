/**
 * Settings Page - Festival Configuration & Store Settings
 */

import { useState, useEffect } from 'react';

import {
    Settings,
    PartyPopper,
    Calendar,
    PlusCircle,
    CheckCircle2,
    AlertCircle
} from 'lucide-react';
import api from '../services/api';

// Terminology standardized for enterprise use

export default function SettingsPage() {
    const [festivals, setFestivals] = useState([]);
    const [loading, setLoading] = useState(true);
    const [seeding, setSeeding] = useState(false);
    const [message, setMessage] = useState(null);

    useEffect(() => {
        loadFestivals();
    }, []);

    const loadFestivals = async () => {
        setLoading(true);
        try {
            const data = await api.getFestivals();
            setFestivals(data);
        } catch (err) {
            console.error('Failed to load festivals:', err);
        } finally {
            setLoading(false);
        }
    };

    const seedFestivals = async () => {
        setSeeding(true);
        setMessage(null);
        try {
            const data = await api.seedFestivals(2026);
            if (data.success) {
                setMessage({ type: 'success', text: `Added ${data.festivals_added} festivals for ${data.year}` });
                loadFestivals();
            }
        } catch (err) {
            setMessage({ type: 'error', text: 'Failed to synchronize festival configuration' });
        } finally {
            setSeeding(false);
        }
    };

    return (
        <div>
            <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)', marginBottom: 'var(--space-xs)' }}>
                    <Settings size={28} color="var(--color-primary)" />
                    <h1 className="card-title" style={{ marginBottom: 0 }}>Settings</h1>
                </div>
                <p className="card-subtitle">Configure festivals and seasonality for better predictions</p>
            </div>

            {/* Message */}
            {message && (
                <div className={`alert alert-${message.type}`} style={{ marginBottom: 'var(--space-lg)', display: 'flex', alignItems: 'center', gap: '10px' }}>
                    {message.type === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
                    {message.text}
                </div>
            )}

            {/* Festival Configuration */}
            <div className="card">
                <div className="card-header">
                    <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)', marginBottom: 'var(--space-xs)' }}>
                            <PartyPopper size={24} color="var(--color-primary)" />
                            <h2 className="card-title" style={{ marginBottom: 0 }}>Festival Calendar</h2>
                        </div>
                        <p className="card-subtitle">
                            Festivals increase demand. Configure them for better forecasts.
                        </p>
                    </div>
                    <button
                        className="btn btn-primary"
                        onClick={seedFestivals}
                        disabled={seeding}
                        style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
                    >
                        {seeding ? (
                            <>
                                <div className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }}></div>
                                Adding...
                            </>
                        ) : (
                            <>
                                <PlusCircle size={16} />
                                Synchronize Regional Festivals
                            </>
                        )}
                    </button>
                </div>

                {loading ? (
                    <div className="loading">
                        <div className="spinner"></div>
                    </div>
                ) : festivals.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-state-icon">
                            <Calendar size={48} />
                        </div>
                        <h3>No Festivals Configured</h3>
                        <p>Click "Add India Festivals" to add Diwali, Holi, Eid, and more.</p>
                    </div>
                ) : (
                    <div className="table-container">
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>Festival</th>
                                    <th>Date</th>
                                    <th>Region</th>
                                    <th>Demand Impact</th>
                                </tr>
                            </thead>
                            <tbody>
                                {festivals.map((fest, idx) => (
                                    <tr key={idx}>
                                        <td><strong>{fest.name}</strong></td>
                                        <td>{fest.date}</td>
                                        <td>
                                            <span className="badge badge-low">{fest.region || 'All India'}</span>
                                        </td>
                                        <td>
                                            <span style={{
                                                color: fest.impact_multiplier >= 2 ? 'var(--color-danger)' :
                                                    fest.impact_multiplier >= 1.5 ? 'var(--color-warning)' :
                                                        'var(--color-success)'
                                            }}>
                                                {fest.impact_multiplier.toFixed(1)}x demand
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* How it works */}
            <div className="card" style={{ marginTop: 'var(--space-lg)' }}>
                <h3 className="card-title">How Festival Impact Works</h3>
                <div style={{ color: 'var(--text-secondary)', marginTop: 'var(--space-md)' }}>
                    <p>During festival periods, we adjust demand forecasts:</p>
                    <ul style={{ marginTop: 'var(--space-sm)', paddingLeft: '1.5rem' }}>
                        <li><strong>2.5x</strong> - Diwali (highest demand)</li>
                        <li><strong>2.0x</strong> - Eid, Durga Puja</li>
                        <li><strong>1.5-1.8x</strong> - Other major festivals</li>
                    </ul>
                    <p style={{ marginTop: 'var(--space-md)' }}>
                        The impact extends 2 days before and after the festival date.
                    </p>
                </div>
            </div>
        </div>
    );
}
