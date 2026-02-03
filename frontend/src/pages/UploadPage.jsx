/**
 * Upload Page - CSV Data Upload
 * 
 * Allows store owners to upload their sales data.
 */

import { useState, useRef } from 'react';
import {
    Upload,
    BarChart3,
    TrendingUp,
    FileText,
    Zap,
    Shield,
    AlertTriangle,
    CheckCircle2,
    FolderOpen
} from 'lucide-react';
import api from '../services/api';

export default function UploadPage() {
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);
    const [dragover, setDragover] = useState(false);
    const fileInputRef = useRef(null);

    const handleFileSelect = (selectedFile) => {
        if (selectedFile && selectedFile.name.endsWith('.csv')) {
            setFile(selectedFile);
            setResult(null);
            setError(null);
        } else {
            setError('Please select a CSV file');
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setDragover(false);
        const droppedFile = e.dataTransfer.files[0];
        handleFileSelect(droppedFile);
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        setDragover(true);
    };

    const handleDragLeave = () => {
        setDragover(false);
    };

    const handleUpload = async () => {
        if (!file) return;

        setUploading(true);
        setError(null);
        setResult(null);

        try {
            // Initialize database first
            await api.initDb();

            // Upload the file
            const data = await api.uploadSales(file);
            setResult(data);
            setFile(null);
        } catch (err) {
            setError(err.message);
        } finally {
            setUploading(false);
        }
    };

    return (
        <div style={{ maxWidth: '800px', margin: '0 auto' }}>
            {/* Hero Section */}
            <div style={{
                textAlign: 'center',
                padding: 'var(--space-xl) 0',
                background: 'linear-gradient(135deg, var(--color-primary-dark) 0%, var(--bg-primary) 100%)',
                borderRadius: 'var(--radius-xl)',
                marginBottom: 'var(--space-xl)',
                boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2), 0 10px 10px -5px rgba(0, 0, 0, 0.04)'
            }}>
                <h1 style={{
                    fontSize: '2.5rem',
                    marginBottom: 'var(--space-sm)',
                    background: 'linear-gradient(to right, #fff, #94a3b8)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent'
                }}>
                    Upload Sales Inventory
                </h1>
                <p style={{ color: 'var(--text-secondary)', fontSize: '1.1rem' }}>
                    Generate demand forecasts from your sales history.
                </p>
            </div>

            {/* Upload Card */}
            <div className="card" style={{
                border: '1px solid rgba(255,255,255,0.05)',
                background: 'rgba(30, 41, 59, 0.7)',
                backdropFilter: 'blur(10px)'
            }}>
                <div
                    className={`upload-area ${dragover ? 'dragover' : ''}`}
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onClick={() => fileInputRef.current?.click()}
                    style={{
                        minHeight: '300px',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'center',
                        alignItems: 'center',
                        background: dragover ? 'rgba(37, 99, 235, 0.1)' : 'transparent',
                        borderColor: dragover ? 'var(--color-primary)' : 'rgba(255,255,255,0.1)'
                    }}
                >
                    <div className="upload-icon" style={{
                        marginBottom: 'var(--space-lg)',
                        filter: 'drop-shadow(0 0 15px rgba(37, 99, 235, 0.5))',
                        color: 'var(--color-primary)'
                    }}>
                        {uploading ? <div className="spinner" style={{ width: '64px', height: '64px' }}></div> : <FolderOpen size={64} />}
                    </div>

                    <div className="upload-text" style={{ textAlign: 'center' }}>
                        {file ? (
                            <>
                                <strong style={{ fontSize: '1.2rem', color: 'var(--color-primary)' }}>{file.name}</strong>
                                <br />
                                <span style={{ fontSize: '0.9rem', opacity: 0.7 }}>{(file.size / 1024).toFixed(1)} KB</span>
                                <br />
                                <span style={{ fontSize: '0.8rem', opacity: 0.5, marginTop: '10px', display: 'block' }}>Click to change</span>
                            </>
                        ) : (
                            <>
                                <strong style={{ fontSize: '1.2rem' }}>Drag & Drop your CSV here</strong>
                                <br />
                                <span style={{ opacity: 0.7 }}>or click to browse files</span>
                            </>
                        )}
                    </div>

                    <input
                        ref={fileInputRef}
                        type="file"
                        accept=".csv"
                        className="upload-input"
                        onChange={(e) => handleFileSelect(e.target.files[0])}
                    />

                    <button
                        className="btn btn-primary"
                        onClick={(e) => {
                            e.stopPropagation();
                            handleUpload();
                        }}
                        disabled={!file || uploading}
                        style={{
                            marginTop: 'var(--space-lg)',
                            padding: '12px 32px',
                            fontSize: '1rem',
                            boxShadow: '0 4px 14px 0 rgba(37, 99, 235, 0.39)',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px'
                        }}
                    >
                        {uploading ? (
                            <>
                                <div className="spinner" style={{ width: '20px', height: '20px', borderWidth: '2px' }}></div>
                                Processing...
                            </>
                        ) : (
                            <>
                                <Upload size={18} />
                                Start Upload
                            </>
                        )}
                    </button>

                    {uploading && (
                        <p style={{ marginTop: '1rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                            Processing sales records and updating forecasting models...
                        </p>
                    )}
                </div>

                {/* Error Message */}
                {error && (
                    <div className="alert alert-error" style={{ marginTop: 'var(--space-lg)', animation: 'fadeIn 0.3s ease' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <AlertTriangle size={20} />
                            <div>
                                <strong>Upload Failed</strong>
                                <div style={{ fontSize: '0.9rem' }}>{error}</div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Success Message */}
                {result && result.success && (
                    <div className="alert alert-success" style={{ marginTop: 'var(--space-lg)', animation: 'fadeIn 0.3s ease' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <CheckCircle2 size={20} />
                            <div>
                                <strong>Success!</strong>
                                <div style={{ fontSize: '0.9rem' }}>
                                    Processed {result.rows_processed} rows for <strong>{result.store_id}</strong>.
                                    <br />
                                    Forecasts and reorder recommendations are being generated in the background.
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Features / Magic Info */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: 'var(--space-md)',
                marginTop: 'var(--space-xl)'
            }}>
                <div className="card" style={{ textAlign: 'center', padding: 'var(--space-md)' }}>
                    <div style={{ marginBottom: '10px' }}>
                        <BarChart3 size={32} color="var(--color-primary)" style={{ margin: '0 auto' }} />
                    </div>
                    <h3 style={{ fontSize: '1rem' }}>Auto-Mapping</h3>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Standardizes common column names and date formats.</p>
                </div>
                <div className="card" style={{ textAlign: 'center', padding: 'var(--space-md)' }}>
                    <div style={{ marginBottom: '10px' }}>
                        <TrendingUp size={32} color="var(--color-primary)" style={{ margin: '0 auto' }} />
                    </div>
                    <h3 style={{ fontSize: '1rem' }}>Forecasting</h3>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Automated demand prediction logic triggers post-upload.</p>
                </div>
                <div className="card" style={{ textAlign: 'center', padding: 'var(--space-md)' }}>
                    <div style={{ marginBottom: '10px' }}>
                        <Shield size={32} color="var(--color-primary)" style={{ margin: '0 auto' }} />
                    </div>
                    <h3 style={{ fontSize: '1rem' }}>Local Storage</h3>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Data is stored and processed on your local system.</p>
                </div>
            </div>

            {/* Sample Format */}
            <div style={{ marginTop: 'var(--space-xl)', textAlign: 'center', opacity: 0.6 }}>
                <p style={{ fontSize: '0.9rem' }}>Need a template?</p>
                <div style={{
                    marginTop: '10px',
                    background: 'var(--bg-secondary)',
                    padding: '10px',
                    borderRadius: '4px',
                    fontFamily: 'monospace',
                    fontSize: '0.8rem',
                    display: 'inline-block'
                }}>
                    store_id, sku_id, sku_name, date, units_sold
                </div>
            </div>
        </div>
    );
}
