/**
 * API service for communicating with the backend.
 */

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8002/api';

async function handleResponse(response) {
  if (!response.ok) {
    let errorDetail = 'Request failed';
    try {
      const error = await response.json();
      errorDetail = error.detail || error.message || JSON.stringify(error);
    } catch (e) {
      errorDetail = `Server returned ${response.status}: ${response.statusText}`;
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

export const api = {
  // Health check
  async health() {
    try {
      const response = await fetch(`${API_BASE}/health`);
      return handleResponse(response);
    } catch (err) {
      throw new Error("Cannot connect to server. Is the backend running?");
    }
  },

  // Initialize database
  async initDb() {
    const response = await fetch(`${API_BASE}/init-db`, { method: 'POST' });
    return handleResponse(response);
  },

  // Upload sales CSV
  async uploadSales(file) {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE}/upload-sales`, {
        method: 'POST',
        body: formData,
      });
      return handleResponse(response);
    } catch (err) {
      if (err.message.includes('Failed to fetch')) {
        throw new Error("Network error: Could not reach the server. Please ensure the backend is running.");
      }
      throw err;
    }
  },

  // Get all stores
  async getStores() {
    const response = await fetch(`${API_BASE}/stores`);
    return handleResponse(response);
  },

  // Get store details
  async getStore(storeId) {
    const response = await fetch(`${API_BASE}/stores/${storeId}`);
    return handleResponse(response);
  },

  // Get store SKUs
  async getStoreSKUs(storeId) {
    const response = await fetch(`${API_BASE}/stores/${storeId}/skus`);
    return handleResponse(response);
  },

  // Run forecast
  async runForecast(storeId, horizon = 7, skuIds = null) {
    const response = await fetch(`${API_BASE}/run-forecast`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        store_id: storeId,
        horizon,
        sku_ids: skuIds,
      }),
    });
    return handleResponse(response);
  },

  // Get forecasts
  async getForecast(storeId, horizon = 7, skuId = null) {
    let url = `${API_BASE}/get-forecast?store_id=${storeId}&horizon=${horizon}`;
    if (skuId) {
      url += `&sku_id=${skuId}`;
    }
    const response = await fetch(url);
    return handleResponse(response);
  },

  // Get reorder list (THE MONEY ENDPOINT)
  async getReorderList(storeId, horizon = 7, regenerate = true) {
    const url = `${API_BASE}/get-reorder-list?store_id=${storeId}&horizon=${horizon}&regenerate=${regenerate}`;
    const response = await fetch(url);
    return handleResponse(response);
  },

  // Get reorder summary
  async getReorderSummary(storeId) {
    const response = await fetch(`${API_BASE}/reorder-summary?store_id=${storeId}`);
    return handleResponse(response);
  },

  // Get festivals
  async getFestivals() {
    const response = await fetch(`${API_BASE}/festivals`);
    return handleResponse(response);
  },

  // Seed festivals
  async seedFestivals(year) {
    const response = await fetch(`${API_BASE}/festivals/seed?year=${year}`, { method: 'POST' });
    return handleResponse(response);
  },

  // Update stock levels
  async updateStock(storeId, updates) {
    const response = await fetch(`${API_BASE}/stores/${storeId}/update-stock`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    return handleResponse(response);
  },

  // Get external market prices (Mandi Prices)
  async getMandiPrices(commodity = null, state = null) {
    let url = `${API_BASE}/mandi-prices`;
    const params = new URLSearchParams();
    if (commodity) params.append('commodity', commodity);
    if (state) params.append('state', state);
    if (params.toString()) url += `?${params.toString()}`;

    const response = await fetch(url);
    return handleResponse(response);
  },
};

export default api;
