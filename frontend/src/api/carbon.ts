import { apiClient } from './client';

export interface Holdings {
  plant_id: string;
  period: string;
  CEA: number;
  CCER: number;
  total: number;
}

export interface OrderBook {
  allowance_type: string;
  bids: { price: number; qty: number; total: number }[];
  asks: { price: number; qty: number; total: number }[];
  spread: number;
  mid_price: number;
  latest_price: number;
}

export interface OrderRequest {
  plant_id: string;
  side: 'buy' | 'sell';
  allowance_type: 'CEA' | 'CCER';
  order_type: 'market' | 'limit' | 'iceberg';
  qty: number;
  price?: number;
  peak_qty?: number;
}

export interface OrderResponse {
  id: string;
  status: string;
  remaining: number;
  side?: string;
  price?: number;
  qty?: number;
  allowance_type?: string;
}

export interface Trade {
  id: string;
  buy_plant: string;
  sell_plant: string;
  qty: number;
  price: number;
  total: number;
  allowance_type: string;
  settled_at: string;
}

export interface PriceHistory {
  allowance_type: string;
  interval: string;
  data: { o: number; h: number; l: number; c: number; v: number; t: number }[];
}

export interface MarketCalendar {
  trading_hours: string;
  trading_days: string;
  compliance_deadline: string;
  market_status: string;
  next_auction: string;
}

export interface ComplianceStatus {
  plant_id: string;
  period: string;
  holdings: Holdings;
  deadline: { period: string; deadline: string; remaining_days: number };
}

const BASE = '/api/carbon';

export const carbonApi = {
  // Emissions
  emissionsRealtime: (plantId: string) =>
    apiClient.get(`${BASE}/emissions/realtime?plant_id=${plantId}`),

  emissionFactors: () =>
    apiClient.get(`${BASE}/emissions/factors`),

  // Holdings
  getHoldings: (plantId: string, period?: string) =>
    apiClient.get(`${BASE}/holdings?plant_id=${plantId}${period ? `&period=${period}` : ''}`),

  allocate: (plantId: string, period: string, qty: number) =>
    apiClient.post(`${BASE}/holdings/allocate`, { plant_id: plantId, period, qty }),

  transfer: (fromPlant: string, toPlant: string, qty: number, allowanceType: string = 'CEA') =>
    apiClient.post(`${BASE}/holdings/transfer`, {
      from_plant: fromPlant, to_plant: toPlant, qty, allowance_type: allowanceType,
    }),

  // Trading
  getOrderBook: (allowanceType: string = 'CEA', depth: number = 10) =>
    apiClient.get(`${BASE}/trading/order-book?allowance_type=${allowanceType}&depth=${depth}`),

  placeOrder: (order: OrderRequest) =>
    apiClient.post(`${BASE}/trading/orders`, order),

  cancelOrder: (orderId: string) =>
    apiClient.delete(`${BASE}/trading/orders/${orderId}`),

  getMyOrders: (plantId: string, status?: string) =>
    apiClient.get(`${BASE}/trading/orders?plant_id=${plantId}${status ? `&status=${status}` : ''}`),

  getMyTrades: (plantId: string) =>
    apiClient.get(`${BASE}/trading/trades?plant_id=${plantId}`),

  // Compliance
  complianceStatus: (plantId: string, period?: string) =>
    apiClient.get(`${BASE}/compliance/status?plant_id=${plantId}${period ? `&period=${period}` : ''}`),

  surrender: (plantId: string, period: string, qtyCea: number, qtyCcer: number) =>
    apiClient.post(`${BASE}/compliance/surrender`, {
      plant_id: plantId, period, qty_cea: qtyCea, qty_ccer: qtyCcer,
    }),

  // Market
  getLatestPrice: (allowanceType: string = 'CEA') =>
    apiClient.get(`${BASE}/market/price?allowance_type=${allowanceType}`),

  getOHLCV: (allowanceType: string = 'CEA', interval: string = '1h') =>
    apiClient.get(`${BASE}/market/ohlcv?allowance_type=${allowanceType}&interval=${interval}`),

  getMarketCalendar: () =>
    apiClient.get(`${BASE}/market/calendar`),
};
