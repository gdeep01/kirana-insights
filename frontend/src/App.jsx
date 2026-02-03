/**
 * Retail Demand Prediction System - Main App
 */

import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import DashboardPage from './pages/DashboardPage';
import ReorderPage from './pages/ReorderPage';
import ForecastPage from './pages/ForecastPage';
import UploadPage from './pages/UploadPage';
import SettingsPage from './pages/SettingsPage';
import {
  LayoutDashboard,
  ShoppingCart,
  TrendingUp,
  Upload,
  Settings,
  BarChart3
} from 'lucide-react';
import './index.css';

function App() {
  return (
    <Router>
      <div className="app">
        {/* Navigation */}
        <nav className="nav">
          <div className="nav-content">
            <NavLink to="/" className="nav-brand">
              <span className="nav-brand-icon">
                <BarChart3 size={24} />
              </span>
              Kirana Insights
            </NavLink>
            <div className="nav-links">
              <NavLink
                to="/"
                className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                end
              >
                <LayoutDashboard size={18} />
                Dashboard
              </NavLink>
              <NavLink
                to="/reorder"
                className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
              >
                <ShoppingCart size={18} />
                Reorder List
              </NavLink>
              <NavLink
                to="/forecast"
                className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
              >
                <TrendingUp size={18} />
                Forecast
              </NavLink>
              <NavLink
                to="/upload"
                className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
              >
                <Upload size={18} />
                Upload
              </NavLink>
              <NavLink
                to="/settings"
                className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
              >
                <Settings size={18} />
                Settings
              </NavLink>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main className="main-content">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/reorder" element={<ReorderPage />} />
            <Route path="/forecast" element={<ForecastPage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;

