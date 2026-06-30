import React, { useState, useEffect } from 'react';

const formatETB = (n: number) => new Intl.NumberFormat('en-ET', { minimumFractionDigits: 2 }).format(n);

interface FeeBreakdown {
  total_fees: number;
  total_bank_charges: number;
  total_vat: number;
  total_wht: number;
  by_type: Record<string, number>;
  metrics: { transaction_count: number; fee_transaction_count: number; total_volume: number; fee_to_volume_ratio: number };
}

interface FeeTrend {
  current: FeeBreakdown;
  previous: FeeBreakdown | null;
  change: { amount: number; percent: number };
  top_drivers: Array<{ label: string; current: number; previous: number; change: number }>;
  savings_opportunities: Array<{ type: string; title: string; title_am: string; description: string; potential_saving: number }>;
}

const FeesPage: React.FC<{ companyId: string }> = ({ companyId }) => {
  const [summary, setSummary] = useState<FeeBreakdown | null>(null);
  const [trend, setTrend] = useState<FeeTrend | null>(null);
  const [benchmark, setBenchmark] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'summary' | 'trend' | 'benchmark'>('summary');

  const token = localStorage.getItem('access_token');
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    Promise.all([
      fetch(`/api/fees/${companyId}/summary`, { headers }).then(r => r.ok ? r.json() : null),
      fetch(`/api/fees/${companyId}/trend`, { headers }).then(r => r.ok ? r.json() : null),
      fetch(`/api/fees/${companyId}/benchmark`, { headers }).then(r => r.ok ? r.json() : null),
    ]).then(([s, t, b]) => {
      setSummary(s);
      setTrend(t);
      setBenchmark(b);
    }).finally(() => setLoading(false));
  }, [companyId]);

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" /></div>;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Fee Intelligence</h1>

      {/* Tabs */}
      <div className="flex space-x-1 bg-gray-100 rounded-lg p-1">
        {(['summary', 'trend', 'benchmark'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${tab === t ? 'bg-white text-gray-900 shadow' : 'text-gray-500'}`}>
            {t === 'summary' ? '💰 Fee Breakdown' : t === 'trend' ? '📈 Trend' : '🏆 Benchmark'}
          </button>
        ))}
      </div>

      {/* Summary Tab */}
      {tab === 'summary' && summary && (
        <div className="space-y-4">
          {/* Hero */}
          <div className="bg-gradient-to-br from-orange-50 to-amber-50 p-6 rounded-2xl border border-orange-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 uppercase">Total Fees This Period</p>
                <p className="text-4xl font-bold text-orange-700">ETB {formatETB(summary.total_fees)}</p>
                <p className="text-sm text-gray-500 mt-1">{summary.metrics.fee_transaction_count} of {summary.metrics.transaction_count} transactions had fees</p>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-500">Fee/Volume Ratio</p>
                <p className="text-2xl font-bold text-gray-800">{(summary.metrics.fee_to_volume_ratio * 100).toFixed(2)}%</p>
              </div>
            </div>
          </div>

          {/* By Type */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {Object.entries(summary.by_type).map(([type, amount]) => (
              <div key={type} className="bg-white p-4 rounded-xl border border-gray-200">
                <p className="text-xs text-gray-500 capitalize">{type.replace('_', ' ')}</p>
                <p className="text-lg font-bold text-gray-900 mt-1">ETB {formatETB(amount)}</p>
              </div>
            ))}
          </div>

          {/* VAT + WHT */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white p-4 rounded-xl border border-gray-200">
              <p className="text-sm text-gray-500">VAT on Fees (15%)</p>
              <p className="text-xl font-bold text-purple-600">ETB {formatETB(summary.total_vat)}</p>
            </div>
            <div className="bg-white p-4 rounded-xl border border-gray-200">
              <p className="text-sm text-gray-500">WHT on Fees (2%)</p>
              <p className="text-xl font-bold text-indigo-600">ETB {formatETB(summary.total_wht)}</p>
            </div>
          </div>
        </div>
      )}

      {/* Trend Tab */}
      {tab === 'trend' && trend && (
        <div className="space-y-4">
          <div className={`p-4 rounded-xl border ${trend.change.percent > 0 ? 'bg-red-50 border-red-200' : 'bg-green-50 border-green-200'}`}>
            <p className="text-sm text-gray-600">Month-over-Month Change</p>
            <p className={`text-3xl font-bold ${trend.change.percent > 0 ? 'text-red-700' : 'text-green-700'}`}>
              {trend.change.percent > 0 ? '+' : ''}{trend.change.percent}% ({trend.change.amount > 0 ? '+' : ''}ETB {formatETB(trend.change.amount)})
            </p>
          </div>

          {trend.top_drivers.length > 0 && (
            <div className="bg-white p-4 rounded-xl border border-gray-200">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Top Fee Drivers</h3>
              {trend.top_drivers.map((d, i) => (
                <div key={i} className="flex justify-between py-2 border-b border-gray-50 last:border-0">
                  <span className="text-sm text-gray-700">{d.label}</span>
                  <span className={`text-sm font-medium ${d.change > 0 ? 'text-red-600' : 'text-green-600'}`}>
                    {d.change > 0 ? '+' : ''}{formatETB(d.change)}
                  </span>
                </div>
              ))}
            </div>
          )}

          {trend.savings_opportunities.length > 0 && (
            <div className="bg-green-50 p-4 rounded-xl border border-green-200">
              <h3 className="text-sm font-semibold text-green-800 mb-3">💡 Savings Opportunities</h3>
              {trend.savings_opportunities.map((s, i) => (
                <div key={i} className="mb-3 last:mb-0">
                  <p className="font-medium text-green-900">{s.title}</p>
                  <p className="text-sm text-green-700">{s.description}</p>
                  <p className="text-xs text-green-600 mt-1">Potential saving: ETB {formatETB(s.potential_saving)}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Benchmark Tab */}
      {tab === 'benchmark' && benchmark && (
        <div className="space-y-4">
          <div className="bg-gradient-to-br from-indigo-50 to-blue-50 p-6 rounded-2xl border border-indigo-200">
            <p className="text-sm text-gray-500 uppercase">Your Fee Ratio</p>
            <p className="text-4xl font-bold text-indigo-700">{(benchmark.your_ratio * 100).toFixed(2)}%</p>
            <p className="text-sm text-gray-600 mt-2">{benchmark.comparison}</p>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="bg-white p-4 rounded-xl border border-gray-200 text-center">
              <p className="text-xs text-gray-500">Your Fees</p>
              <p className="text-lg font-bold text-gray-900">ETB {formatETB(benchmark.your_fees)}</p>
            </div>
            <div className="bg-white p-4 rounded-xl border border-gray-200 text-center">
              <p className="text-xs text-gray-500">Peer Median</p>
              <p className="text-lg font-bold text-blue-600">ETB {formatETB(benchmark.peer_median_fees)}</p>
            </div>
            <div className="bg-white p-4 rounded-xl border border-gray-200 text-center">
              <p className="text-xs text-gray-500">Potential Savings</p>
              <p className="text-lg font-bold text-green-600">ETB {formatETB(benchmark.potential_savings)}</p>
            </div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-gray-200">
            <p className="text-sm text-gray-500">Percentile Rank</p>
            <div className="mt-2 flex items-center space-x-3">
              <div className="flex-1 bg-gray-100 rounded-full h-4 overflow-hidden">
                <div className="bg-indigo-500 h-4 rounded-full" style={{ width: `${benchmark.percentile_rank}%` }} />
              </div>
              <span className="text-sm font-medium text-gray-700">{benchmark.percentile_rank}th</span>
            </div>
            <p className="text-xs text-gray-400 mt-1">Lower is better — you pay less than {100 - benchmark.percentile_rank}% of similar companies</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default FeesPage;
