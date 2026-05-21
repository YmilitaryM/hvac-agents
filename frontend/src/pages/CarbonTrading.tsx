import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { carbonApi } from '../api/carbon';
import KpiCard from '../components/KpiCard';

type Tab = 'emissions' | 'trading' | 'holdings' | 'compliance';

export default function CarbonTrading() {
  const [tab, setTab] = useState<Tab>('emissions');
  const [plantId, setPlantId] = useState('plant-1');

  const { data: factors } = useQuery({
    queryKey: ['carbon-factors'],
    queryFn: () => carbonApi.emissionFactors(),
  });

  const { data: holdings } = useQuery({
    queryKey: ['carbon-holdings', plantId],
    queryFn: () => carbonApi.getHoldings(plantId),
    refetchInterval: 30000,
  });

  const { data: orderBook } = useQuery({
    queryKey: ['carbon-orderbook'],
    queryFn: () => carbonApi.getOrderBook('CEA', 10),
    refetchInterval: 10000,
  });

  const { data: latestPrice } = useQuery({
    queryKey: ['carbon-price'],
    queryFn: () => carbonApi.getLatestPrice('CEA'),
    refetchInterval: 10000,
  });

  const { data: compliance } = useQuery({
    queryKey: ['carbon-compliance', plantId],
    queryFn: () => carbonApi.complianceStatus(plantId),
    refetchInterval: 60000,
  });

  const { data: orders } = useQuery({
    queryKey: ['carbon-orders', plantId],
    queryFn: () => carbonApi.getMyOrders(plantId),
    refetchInterval: 15000,
  });

  const { data: ohlcv } = useQuery({
    queryKey: ['carbon-ohlcv'],
    queryFn: () => carbonApi.getOHLCV('CEA', '1h'),
    refetchInterval: 60000,
  });

  const tabs: { key: Tab; label: string }[] = [
    { key: 'emissions', label: '排放总览' },
    { key: 'trading', label: '交易市场' },
    { key: 'holdings', label: '碳资产' },
    { key: 'compliance', label: '履约报告' },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">碳管理</h2>
        <div className="flex items-center gap-3">
          <input
            value={plantId}
            onChange={e => setPlantId(e.target.value)}
            className="bg-slate-700 border border-slate-600 rounded px-2 py-1 w-32 text-sm"
            placeholder="Plant ID"
          />
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex border-b border-slate-700 mb-4">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key
                ? 'border-cyan-400 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Emissions Tab ── */}
      {tab === 'emissions' && (
        <div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <KpiCard label="最新碳价 (CEA)" value={`¥${latestPrice?.price?.toFixed(2) || '--'}`} color="text-cyan-400" />
            <KpiCard label="CEA 持仓" value={holdings?.CEA ? `${holdings.CEA.toFixed(0)} t` : '--'} />
            <KpiCard label="CCER 持仓" value={holdings?.CCER ? `${holdings.CCER.toFixed(0)} t` : '--'} />
            <KpiCard label="总资产" value={holdings?.total ? `${holdings.total.toFixed(0)} t` : '--'} color="text-emerald-400" />
          </div>
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 mb-4">
            <h3 className="text-sm text-slate-400 uppercase mb-3">价格走势 (小时K线)</h3>
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={(ohlcv?.data || []).slice(-48)}>
                <defs>
                  <linearGradient id="colorClose" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#38bdf8" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="t" stroke="#64748b" fontSize={11} tickFormatter={t => new Date(t * 1000).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })} />
                <YAxis stroke="#64748b" fontSize={11} domain={['auto', 'auto']} />
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }} />
                <Area type="monotone" dataKey="c" stroke="#38bdf8" fill="url(#colorClose)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
            <h3 className="text-sm text-slate-400 uppercase mb-3">区域排放因子 (tCO₂/MWh)</h3>
            <div className="grid grid-cols-3 md:grid-cols-7 gap-2">
              {factors?.regions && Object.entries(factors.regions as Record<string, number>).map(([region, factor]) => (
                <div key={region} className="bg-slate-700/50 rounded p-2 text-center">
                  <div className="text-xs text-slate-400">{region}</div>
                  <div className="text-sm font-mono text-slate-200">{factor}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Trading Tab ── */}
      {tab === 'trading' && (
        <div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            {/* Order Book */}
            <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
              <h3 className="text-sm text-slate-400 uppercase mb-3">订单簿 (CEA)</h3>
              <div className="space-y-1 text-xs font-mono">
                <div className="text-red-400 font-medium mb-1">卖盘 (Asks)</div>
                {(orderBook?.asks || []).slice().reverse().map((a, i) => (
                  <div key={i} className="flex justify-between">
                    <span className="text-red-300">{a.price.toFixed(2)}</span>
                    <span className="text-slate-400">{a.qty.toFixed(0)} t</span>
                    <span className="text-slate-500">{a.total.toFixed(0)}</span>
                  </div>
                ))}
                <div className="border-t border-slate-600 my-1" />
                <div className="text-center text-lg font-bold text-cyan-400 py-1">
                  ¥{latestPrice?.price?.toFixed(2) || '--'}
                </div>
                <div className="border-t border-slate-600 my-1" />
                <div className="text-green-400 font-medium mb-1">买盘 (Bids)</div>
                {(orderBook?.bids || []).map((b, i) => (
                  <div key={i} className="flex justify-between">
                    <span className="text-green-300">{b.price.toFixed(2)}</span>
                    <span className="text-slate-400">{b.qty.toFixed(0)} t</span>
                    <span className="text-slate-500">{b.total.toFixed(0)}</span>
                  </div>
                ))}
              </div>
              {orderBook?.spread != null && (
                <div className="mt-2 text-xs text-slate-500">价差: {orderBook.spread.toFixed(2)}</div>
              )}
            </div>

            {/* My Orders */}
            <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
              <h3 className="text-sm text-slate-400 uppercase mb-3">当前挂单</h3>
              {!orders?.orders || orders.orders.length === 0 ? (
                <p className="text-slate-500 text-sm">暂无挂单</p>
              ) : (
                <div className="space-y-2">
                  {(orders.orders as any[]).map((o: any) => (
                    <div key={o.id} className="bg-slate-700/50 rounded p-2 flex justify-between text-xs">
                      <div>
                        <span className={o.side === 'buy' ? 'text-green-400' : 'text-red-400'}>
                          {o.side === 'buy' ? '买入' : '卖出'}
                        </span>
                        <span className="text-slate-400 ml-2">{o.allowance_type}</span>
                        <span className="text-slate-500 ml-2">{o.order_type}</span>
                      </div>
                      <div>
                        <span className="text-slate-300">{o.remaining.toFixed(0)} t</span>
                        <span className="text-slate-400 ml-2">@{o.price.toFixed(2)}</span>
                        <span className={`ml-2 ${o.status === 'pending' ? 'text-yellow-400' : 'text-slate-500'}`}>{o.status}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Quick Order Form */}
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
            <h3 className="text-sm text-slate-400 uppercase mb-3">快速下单</h3>
            <QuickOrderForm plantId={plantId} />
          </div>
        </div>
      )}

      {/* ── Holdings Tab ── */}
      {tab === 'holdings' && (
        <div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <KpiCard label="CEA 总持有" value={holdings?.CEA ? `${holdings.CEA.toFixed(0)} t` : '--'} />
            <KpiCard label="CCER 持有" value={holdings?.CCER ? `${holdings.CCER.toFixed(0)} t` : '--'} />
            <KpiCard label="碳资产总值" value={holdings?.total ? `${holdings.total.toFixed(0)} t` : '--'} color="text-emerald-400" />
            <KpiCard label="估算市值" value={holdings?.total && latestPrice?.price ? `¥${(holdings.total * latestPrice.price).toFixed(0)}` : '--'} color="text-cyan-400" />
          </div>
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-4 mb-4">
            <h3 className="text-sm text-slate-400 uppercase mb-3">资产分布</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={[
                { name: 'CEA', value: holdings?.CEA || 0 },
                { name: 'CCER', value: holdings?.CCER || 0 },
              ]}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="name" stroke="#64748b" fontSize={12} />
                <YAxis stroke="#64748b" fontSize={12} />
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #475569', borderRadius: '8px' }} />
                <Bar dataKey="value" fill="#38bdf8" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* ── Compliance Tab ── */}
      {tab === 'compliance' && (
        <div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4">
            <KpiCard label="履约截止" value={compliance?.deadline?.deadline || '--'} />
            <KpiCard label="剩余天数" value={compliance?.deadline?.remaining_days ? `${compliance.deadline.remaining_days} 天` : '--'} />
            <KpiCard label="持仓总量" value={compliance?.holdings?.total ? `${compliance.holdings.total.toFixed(0)} t` : '--'} color="text-cyan-400" />
          </div>
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-4">
            <h3 className="text-sm text-slate-400 uppercase mb-3">履约状态</h3>
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-400">CEA 持仓</span>
                  <span className="text-slate-200">{compliance?.holdings?.CEA?.toFixed(0) || '0'} t</span>
                </div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-400">CCER 持仓</span>
                  <span className="text-slate-200">{compliance?.holdings?.CCER?.toFixed(0) || '0'} t</span>
                </div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-slate-400">时期</span>
                  <span className="text-slate-200">{compliance?.period || '--'}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function QuickOrderForm({ plantId }: { plantId: string }) {
  const [side, setSide] = useState<'buy' | 'sell'>('buy');
  const [orderType, setOrderType] = useState<'limit' | 'market'>('limit');
  const [qty, setQty] = useState(100);
  const [price, setPrice] = useState(80);
  const [msg, setMsg] = useState('');

  const place = async () => {
    try {
      setMsg('下单中...');
      const res = await carbonApi.placeOrder({
        plant_id: plantId, side, allowance_type: 'CEA', order_type: orderType,
        qty, price: orderType === 'market' ? 0 : price,
      });
      setMsg(`已提交: ${res.order?.id?.slice(0, 8)}... 状态: ${res.order?.status}`);
    } catch (e: any) {
      setMsg(`错误: ${e.message}`);
    }
  };

  return (
    <div className="flex flex-wrap items-end gap-3">
      <div>
        <label className="text-xs text-slate-400 block mb-1">方向</label>
        <select value={side} onChange={e => setSide(e.target.value as any)} className="bg-slate-700 border border-slate-600 rounded px-2 py-1 text-sm">
          <option value="buy">买入</option>
          <option value="sell">卖出</option>
        </select>
      </div>
      <div>
        <label className="text-xs text-slate-400 block mb-1">类型</label>
        <select value={orderType} onChange={e => setOrderType(e.target.value as any)} className="bg-slate-700 border border-slate-600 rounded px-2 py-1 text-sm">
          <option value="limit">限价</option>
          <option value="market">市价</option>
        </select>
      </div>
      <div>
        <label className="text-xs text-slate-400 block mb-1">数量 (t)</label>
        <input type="number" value={qty} onChange={e => setQty(Number(e.target.value))} className="bg-slate-700 border border-slate-600 rounded px-2 py-1 w-24 text-sm" />
      </div>
      {orderType === 'limit' && (
        <div>
          <label className="text-xs text-slate-400 block mb-1">价格 (元/t)</label>
          <input type="number" value={price} onChange={e => setPrice(Number(e.target.value))} className="bg-slate-700 border border-slate-600 rounded px-2 py-1 w-24 text-sm" />
        </div>
      )}
      <button onClick={place} className={`px-4 py-1.5 rounded text-sm font-medium ${side === 'buy' ? 'bg-green-600 hover:bg-green-500' : 'bg-red-600 hover:bg-red-500'} text-white`}>
        {side === 'buy' ? '买入' : '卖出'}
      </button>
      {msg && <span className="text-xs text-slate-400">{msg}</span>}
    </div>
  );
}
