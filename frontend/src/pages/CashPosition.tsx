import React, { useState, useEffect } from 'react';

interface CashAccount {
  account_id: string;
  bank_name: string;
  account_number: string;
  account_type: string;
  raw_balance: number;
  outstanding_cheques: number;
  uncleared_deposits: number;
  pending_transfers: number;
  adjusted_balance: number;
  last_transaction_date: string;
  transaction_count: number;
  alerts: string[];
}

interface CashPosition {
  accounts: CashAccount[];
  totals: {
    raw_balance: number;
    outstanding_cheques: number;
    uncleared_deposits: number;
    pending_transfers: number;
    adjusted_position: number;
  };
  by_bank: Record<string, number>;
  stale_cheques: Array<{ cheque_number: string; amount: number; payee: string; days_outstanding: number }>;
  alerts: string[];
  trend: {
    previous_position: number | null;
    change_amount: number | null;
    change_percent: number | null;
  };
  safety_threshold: number;
  below_threshold: boolean;
}

interface ForecastDay {
  date: string;
  day_name: string;
  inflow: number;
  outflow: number;
  balance: number;
  is_weekend: boolean;
  events: string[];
  is_critical: boolean;
}

interface CashForecast {
  starting_balance: number;
  days: ForecastDay[];
  summary: {
    min_balance: number;
    min_balance_date: string;
    max_balance: number;
    total_inflow: number;
    total_outflow: number;
    net_change: number;
    critical_days: number;
    below_threshold_date: string | null;
  };
  alerts: string[];
  detected_patterns: Array<{
    type: string;
    description: string;
    amount: number;
    frequency: string;
    next_date: string;
    confidence: number;
    occurrences: number;
  }>;
}

const formatETB = (n: number) => new Intl.NumberFormat('en-ET', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);

const CashPositionPage: React.FC<{ companyId: string }> = ({ companyId }) => {
  const [position, setPosition] = useState<CashPosition | null>(null);
  const [forecast, setForecast] = useState<CashForecast | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'position' | 'forecast' | 'patterns'>('position');

  const token = localStorage.getItem('access_token');
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [posRes, fcastRes] = await Promise.all([
          fetch(`/api/cash/position/${companyId}`, { headers }),
          fetch(`/api/cash/forecast/${companyId}?days=30`, { headers }),
        ]);
        if (posRes.ok) setPosition(await posRes.json());
        if (fcastRes.ok) setForecast(await fcastRes.json());
      } catch (e) {
        console.error('Failed to fetch cash data', e);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [companyId]);

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
    </div>
  );

  if (!position) return (
    <div className="p-6 text-center text-gray-500">
      <p>Upload bank statements to see your cash position.</p>
    </div>
  );

  return (
    <div className="p-6 space-y-6">
      {/* Hero: Adjusted Cash Position */}
      <div className={`p-6 rounded-2xl border-2 ${position.below_threshold ? 'bg-red-50 border-red-300' : 'bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200'}`}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500 uppercase tracking-wide">Adjusted Cash Position</p>
            <p className={`text-4xl font-bold mt-1 ${position.below_threshold ? 'text-red-700' : 'text-gray-900'}`}>
              ETB {formatETB(position.totals.adjusted_position)}
            </p>
            {position.trend.change_percent !== null && (
              <p className={`text-sm mt-1 ${position.trend.change_percent >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {position.trend.change_percent >= 0 ? '▲' : '▼'} {Math.abs(position.trend.change_percent).toFixed(1)}% vs last month
              </p>
            )}
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-500">Safety Threshold</div>
            <div className="text-lg font-semibold text-gray-700">ETB {formatETB(position.safety_threshold)}</div>
            {position.below_threshold && (
              <span className="inline-block mt-1 px-2 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-full">
                ⚠️ Below Threshold
              </span>
            )}
          </div>
        </div>

        {/* Adjustment Breakdown */}
        <div className="mt-4 grid grid-cols-4 gap-4 pt-4 border-t border-blue-100">
          <div>
            <p className="text-xs text-gray-500">Raw Balance</p>
            <p className="text-lg font-semibold text-gray-800">ETB {formatETB(position.totals.raw_balance)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Outstanding Cheques</p>
            <p className="text-lg font-semibold text-red-600">-ETB {formatETB(position.totals.outstanding_cheques)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Uncleared Deposits</p>
            <p className="text-lg font-semibold text-green-600">+ETB {formatETB(position.totals.uncleared_deposits)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Pending Transfers</p>
            <p className="text-lg font-semibold text-orange-600">-ETB {formatETB(position.totals.pending_transfers)}</p>
          </div>
        </div>
      </div>

      {/* Alerts */}
      {position.alerts.length > 0 && (
        <div className="space-y-2">
          {position.alerts.map((alert, i) => (
            <div key={i} className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
              {alert}
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex space-x-1 bg-gray-100 rounded-lg p-1">
        {(['position', 'forecast', 'patterns'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors ${
              activeTab === tab ? 'bg-white text-gray-900 shadow' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab === 'position' ? '🏦 By Account' : tab === 'forecast' ? '📈 30-Day Forecast' : '🔄 Patterns'}
          </button>
        ))}
      </div>

      {/* Tab: By Account */}
      {activeTab === 'position' && (
        <div className="space-y-3">
          {/* By Bank Summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Object.entries(position.by_bank).map(([bank, balance]) => (
              <div key={bank} className="bg-white p-4 rounded-xl border border-gray-200">
                <p className="text-xs text-gray-500 uppercase">{bank}</p>
                <p className="text-lg font-bold text-gray-900 mt-1">ETB {formatETB(balance)}</p>
              </div>
            ))}
          </div>

          {/* Account Details */}
          {position.accounts.map(acct => (
            <div key={acct.account_id} className="bg-white p-4 rounded-xl border border-gray-200">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-gray-900">{acct.bank_name}</h3>
                  <p className="text-xs text-gray-500">{acct.account_number} · {acct.account_type}</p>
                </div>
                <div className="text-right">
                  <p className="text-xl font-bold text-gray-900">ETB {formatETB(acct.adjusted_balance)}</p>
                  <p className="text-xs text-gray-500">{acct.transaction_count} transactions</p>
                </div>
              </div>
              <div className="grid grid-cols-4 gap-3 text-sm">
                <div><span className="text-gray-500">Raw:</span> <span className="font-medium">{formatETB(acct.raw_balance)}</span></div>
                <div><span className="text-gray-500">Cheques:</span> <span className="font-medium text-red-600">-{formatETB(acct.outstanding_cheques)}</span></div>
                <div><span className="text-gray-500">Deposits:</span> <span className="font-medium text-green-600">+{formatETB(acct.uncleared_deposits)}</span></div>
                <div><span className="text-gray-500">Last txn:</span> <span className="font-medium">{acct.last_transaction_date || 'N/A'}</span></div>
              </div>
            </div>
          ))}

          {/* Stale Cheques */}
          {position.stale_cheques.length > 0 && (
            <div className="bg-red-50 p-4 rounded-xl border border-red-200">
              <h3 className="font-semibold text-red-800 mb-2">⚠️ Stale Cheques</h3>
              {position.stale_cheques.map((chq, i) => (
                <div key={i} className="flex justify-between py-1 text-sm">
                  <span className="text-red-700">#{chq.cheque_number} — {chq.payee}</span>
                  <span className="font-medium text-red-800">ETB {formatETB(chq.amount)} ({chq.days_outstanding} days)</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab: 30-Day Forecast */}
      {activeTab === 'forecast' && forecast && (
        <div className="space-y-4">
          {/* Forecast Summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-white p-4 rounded-xl border border-gray-200">
              <p className="text-xs text-gray-500">Min Balance</p>
              <p className={`text-lg font-bold ${forecast.summary.min_balance < position.safety_threshold ? 'text-red-600' : 'text-gray-900'}`}>
                ETB {formatETB(forecast.summary.min_balance)}
              </p>
              <p className="text-xs text-gray-400">{forecast.summary.min_balance_date}</p>
            </div>
            <div className="bg-white p-4 rounded-xl border border-gray-200">
              <p className="text-xs text-gray-500">Total Inflow</p>
              <p className="text-lg font-bold text-green-600">+ETB {formatETB(forecast.summary.total_inflow)}</p>
            </div>
            <div className="bg-white p-4 rounded-xl border border-gray-200">
              <p className="text-xs text-gray-500">Total Outflow</p>
              <p className="text-lg font-bold text-red-600">-ETB {formatETB(forecast.summary.total_outflow)}</p>
            </div>
            <div className="bg-white p-4 rounded-xl border border-gray-200">
              <p className="text-xs text-gray-500">Critical Days</p>
              <p className={`text-lg font-bold ${forecast.summary.critical_days > 0 ? 'text-red-600' : 'text-green-600'}`}>
                {forecast.summary.critical_days}
              </p>
            </div>
          </div>

          {/* Forecast Alerts */}
          {forecast.alerts.map((alert, i) => (
            <div key={i} className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800 font-medium">
              {alert}
            </div>
          ))}

          {/* Forecast Chart (ASCII-style bar) */}
          <div className="bg-white p-4 rounded-xl border border-gray-200">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">30-Day Balance Forecast</h3>
            <div className="space-y-1">
              {forecast.days.filter((_, i) => i % 3 === 0).map(day => {
                const maxBal = forecast.summary.max_balance || 1;
                const pct = Math.max(5, (day.balance / maxBal) * 100);
                return (
                  <div key={day.date} className="flex items-center space-x-2 text-xs">
                    <span className="w-16 text-gray-500">{day.date.slice(5)}</span>
                    <div className="flex-1 bg-gray-100 rounded-full h-4 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${day.is_critical ? 'bg-red-400' : day.balance < position.safety_threshold ? 'bg-yellow-400' : 'bg-blue-400'}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className={`w-24 text-right font-mono ${day.is_critical ? 'text-red-600 font-bold' : 'text-gray-700'}`}>
                      {formatETB(day.balance)}
                    </span>
                    {day.events.length > 0 && (
                      <span className="text-gray-400" title={day.events.join(', ')}>
                        {day.events.length}📅
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
            {/* Safety threshold line */}
            <div className="mt-2 pt-2 border-t border-gray-100 flex items-center text-xs text-gray-500">
              <div className="w-3 h-0.5 bg-red-400 mr-2" />
              Safety threshold: ETB {formatETB(position.safety_threshold)}
            </div>
          </div>
        </div>
      )}

      {/* Tab: Detected Patterns */}
      {activeTab === 'patterns' && forecast && (
        <div className="space-y-3">
          {forecast.detected_patterns.length === 0 ? (
            <div className="bg-white p-8 rounded-xl border border-gray-200 text-center text-gray-500">
              <p>No recurring patterns detected yet.</p>
              <p className="text-sm mt-1">Upload more months of data to detect patterns.</p>
            </div>
          ) : (
            forecast.detected_patterns.map((p, i) => (
              <div key={i} className="bg-white p-4 rounded-xl border border-gray-200">
                <div className="flex items-center justify-between">
                  <div>
                    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                      p.type === 'payroll' ? 'bg-blue-100 text-blue-800' :
                      p.type === 'rent' ? 'bg-purple-100 text-purple-800' :
                      p.type === 'loan' ? 'bg-red-100 text-red-800' :
                      p.type === 'standing_order' ? 'bg-green-100 text-green-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {p.type}
                    </span>
                    <h3 className="font-medium text-gray-900 mt-1">{p.description}</h3>
                    <p className="text-xs text-gray-500">
                      {p.frequency} · {p.occurrences} occurrences · {Math.round(p.confidence * 100)}% confidence
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-gray-900">ETB {formatETB(p.amount)}</p>
                    <p className="text-xs text-gray-500">Next: {p.next_date}</p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default CashPositionPage;
