import React, { useState, useEffect } from 'react';

interface DashboardData {
  match_stats: {
    total_transactions: number;
    matched: number;
    unmatched: number;
    match_rate: number;
    this_month: { transactions: number; matched: number };
  };
  fee_summary: {
    total_fees: number;
    bank_charges: number;
    gov_tax: number;
    transactions_with_fees: number;
    this_month_fees: number;
  };
  cheques: {
    outstanding_count: number;
    outstanding_amount: number;
    stale_count: number;
    stale_amount: number;
  };
  periods: {
    current_period: string;
    current_status: string;
    locked_count: number;
  };
  amounts: {
    total_credits: number;
    total_debits: number;
    net_movement: number;
  };
  recent_activity: Array<{
    action: string;
    entity_type: string;
    details: any;
    created_at: string;
  }>;
}

const formatETB = (n: number) => new Intl.NumberFormat('en-ET', { minimumFractionDigits: 2 }).format(n);

const StatCard: React.FC<{ label: string; value: string; sub?: string; color: string; icon: React.ReactNode }> = 
  ({ label, value, sub, color, icon }) => (
  <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
    <div className="flex items-start justify-between">
      <div>
        <p className="text-sm text-gray-500">{label}</p>
        <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
        {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
      </div>
      <div className={`p-2 rounded-lg bg-opacity-10 ${color.replace('text-', 'bg-')}`}>
        {icon}
      </div>
    </div>
  </div>
);

const Dashboard: React.FC<{ companyId: string }> = ({ companyId }) => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const res = await fetch(`/api/dashboard/${companyId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) setData(await res.json());
      } catch (e) {
        console.error('Dashboard fetch failed', e);
      } finally {
        setLoading(false);
      }
    };
    fetchDashboard();
  }, [companyId]);

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
    </div>
  );

  if (!data) return (
    <div className="text-center py-12 text-gray-500">
      <p>Could not load dashboard. Upload a bank statement first.</p>
    </div>
  );

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500">Period: {data.periods.current_period}</p>
        </div>
        <span className={`px-3 py-1 text-sm font-medium rounded-full ${
          data.periods.current_status === 'locked' 
            ? 'bg-red-100 text-red-800' 
            : 'bg-green-100 text-green-800'
        }`}>
          {data.periods.current_status === 'locked' ? '🔒 Period Locked' : '✅ Period Open'}
        </span>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Match Rate"
          value={`${data.match_stats.match_rate}%`}
          sub={`${data.match_stats.matched} of ${data.match_stats.total_transactions} transactions`}
          color="text-green-600"
          icon={<svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
        <StatCard
          label="Total Fees Paid"
          value={`ETB ${formatETB(data.fee_summary.total_fees)}`}
          sub={`${data.fee_summary.transactions_with_fees} transactions with fees`}
          color="text-orange-600"
          icon={<svg className="w-5 h-5 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
        <StatCard
          label="Outstanding Cheques"
          value={String(data.cheques.outstanding_count)}
          sub={`ETB ${formatETB(data.cheques.outstanding_amount)}`}
          color="text-blue-600"
          icon={<svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" /></svg>}
        />
        <StatCard
          label="Stale Cheques"
          value={String(data.cheques.stale_count)}
          sub={data.cheques.stale_count > 0 ? `ETB ${formatETB(data.cheques.stale_amount)} at risk` : 'None'}
          color={data.cheques.stale_count > 0 ? 'text-red-600' : 'text-gray-600'}
          icon={<svg className="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
        />
      </div>

      {/* Fee Breakdown + Amount Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Fee Breakdown */}
        <div className="bg-white p-5 rounded-xl border border-gray-200">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Fee Breakdown</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Bank Charges</span>
              <span className="font-medium text-orange-600">ETB {formatETB(data.fee_summary.bank_charges)}</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2">
              <div className="bg-orange-400 h-2 rounded-full" style={{ 
                width: `${data.fee_summary.total_fees > 0 ? (data.fee_summary.bank_charges / data.fee_summary.total_fees * 100) : 0}%` 
              }} />
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Gov't Tax (15% VAT)</span>
              <span className="font-medium text-purple-600">ETB {formatETB(data.fee_summary.gov_tax)}</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2">
              <div className="bg-purple-400 h-2 rounded-full" style={{ 
                width: `${data.fee_summary.total_fees > 0 ? (data.fee_summary.gov_tax / data.fee_summary.total_fees * 100) : 0}%` 
              }} />
            </div>
            <div className="pt-3 border-t border-gray-100 flex justify-between items-center">
              <span className="text-sm font-medium text-gray-700">This Month</span>
              <span className="font-bold text-gray-900">ETB {formatETB(data.fee_summary.this_month_fees)}</span>
            </div>
          </div>
        </div>

        {/* Amount Summary */}
        <div className="bg-white p-5 rounded-xl border border-gray-200">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Cash Movement</h3>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-500">Total Credits (Inflow)</span>
                <span className="font-medium text-green-600">+ETB {formatETB(data.amounts.total_credits)}</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-3">
                <div className="bg-green-400 h-3 rounded-full" style={{ width: '100%' }} />
              </div>
            </div>
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-500">Total Debits (Outflow)</span>
                <span className="font-medium text-red-600">-ETB {formatETB(data.amounts.total_debits)}</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-3">
                <div className="bg-red-400 h-3 rounded-full" style={{ 
                  width: `${data.amounts.total_credits > 0 ? (data.amounts.total_debits / data.amounts.total_credits * 100) : 0}%` 
                }} />
              </div>
            </div>
            <div className="pt-3 border-t border-gray-100 flex justify-between items-center">
              <span className="text-sm font-medium text-gray-700">Net Movement</span>
              <span className={`font-bold ${data.amounts.net_movement >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {data.amounts.net_movement >= 0 ? '+' : ''}ETB {formatETB(data.amounts.net_movement)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      {data.recent_activity.length > 0 && (
        <div className="bg-white p-5 rounded-xl border border-gray-200">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Recent Activity</h3>
          <div className="space-y-2">
            {data.recent_activity.map((a, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                <div className="flex items-center space-x-3">
                  <span className={`w-2 h-2 rounded-full ${
                    a.action === 'login' ? 'bg-green-400' :
                    a.action === 'register' ? 'bg-blue-400' :
                    a.action.includes('lock') ? 'bg-red-400' : 'bg-gray-400'
                  }`} />
                  <span className="text-sm text-gray-700">{a.action.replace(/_/g, ' ')}</span>
                  <span className="text-xs text-gray-400">{a.entity_type}</span>
                </div>
                <span className="text-xs text-gray-400">{new Date(a.created_at).toLocaleString()}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
