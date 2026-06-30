import React, { useState, useEffect } from 'react';
import ReconciliationPage from './pages/Reconciliation';
import ChequesPage from './pages/Cheques';
import DashboardPage from './pages/Dashboard';
import CashPositionPage from './pages/CashPosition';
import LoginPage from './pages/Login';

type Page = 'dashboard' | 'cash' | 'reconciliation' | 'cheques' | 'gl-mappings' | 'periods' | 'exceptions';

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  company_id: string;
  company_name: string;
}

function App() {
  const [currentPage, setCurrentPage] = useState<Page>('dashboard');
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Check for existing session
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      fetch('/api/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then(res => {
          if (res.ok) return res.json();
          throw new Error('Token expired');
        })
        .then(data => setUser(data))
        .catch(() => {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const handleLogin = (userData: User) => {
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (!user) {
    return <LoginPage onLogin={handleLogin} />;
  }

  const navItems: { id: Page; label: string; icon: React.ReactNode }[] = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" /></svg>,
    },
    {
      id: 'cash',
      label: 'Cash Position',
      icon: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
    },
    {
      id: 'reconciliation',
      label: 'Reconciliation',
      icon: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" /></svg>,
    },
    {
      id: 'cheques',
      label: 'Cheques',
      icon: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" /></svg>,
    },
    {
      id: 'gl-mappings',
      label: 'GL Mappings',
      icon: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" /></svg>,
    },
    {
      id: 'periods',
      label: 'Period Lock',
      icon: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>,
    },
    {
      id: 'exceptions',
      label: 'Exceptions',
      icon: <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" /></svg>,
    },
  ];

  const roleColor = {
    clerk: 'bg-blue-100 text-blue-800',
    manager: 'bg-purple-100 text-purple-800',
    cfo: 'bg-green-100 text-green-800',
    auditor: 'bg-yellow-100 text-yellow-800',
  }[user.role] || 'bg-gray-100 text-gray-800';

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="fixed inset-y-0 left-0 w-64 bg-gray-900 text-white flex flex-col">
        <div className="flex items-center justify-center h-16 border-b border-gray-800">
          <h1 className="text-xl font-bold tracking-tight">ReconET</h1>
        </div>
        
        <nav className="mt-6 flex-1 px-3 space-y-1">
          {navItems.map(item => (
            <a
              key={item.id}
              href="#"
              onClick={e => { e.preventDefault(); setCurrentPage(item.id); }}
              className={`flex items-center px-3 py-2.5 rounded-lg text-sm transition-colors ${
                currentPage === item.id
                  ? 'bg-white/10 text-white font-medium'
                  : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <span className="mr-3">{item.icon}</span>
              {item.label}
            </a>
          ))}
        </nav>

        {/* User Card */}
        <div className="p-3 border-t border-gray-800">
          <div className="flex items-center px-3 py-2">
            <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-sm font-bold">
              {user.full_name.charAt(0).toUpperCase()}
            </div>
            <div className="ml-3 flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">{user.full_name}</p>
              <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded-full ${roleColor}`}>
                {user.role.toUpperCase()}
              </span>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full mt-2 px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors text-left"
          >
            Sign Out
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="ml-64">
        {currentPage === 'dashboard' && <DashboardPage companyId={user.company_id} />}
        {currentPage === 'cash' && <CashPositionPage companyId={user.company_id} />}
        {currentPage === 'reconciliation' && <ReconciliationPage />}
        {currentPage === 'cheques' && <ChequesPage />}
        {currentPage === 'gl-mappings' && <GLMappingsPage />}
        {currentPage === 'periods' && <PeriodsPage companyId={user.company_id} />}
        {currentPage === 'exceptions' && <ExceptionsPage />}
      </div>
    </div>
  );
}

// ─── GL Mappings Page ───────────────────────────────────────────

function GLMappingsPage() {
  const [mappings, setMappings] = useState<any[]>([]);
  const [journalResult, setJournalResult] = useState<any>(null);
  const [amount, setAmount] = useState('100040');
  const [bankCharge, setBankCharge] = useState('25');
  const [govTax, setGovTax] = useState('15');

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    fetch('/api/gl-mappings/', { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(d => setMappings(d.mappings || []))
      .catch(() => {});
  }, []);

  const suggestJournal = async () => {
    const token = localStorage.getItem('access_token');
    const res = await fetch('/api/gl-mappings/suggest-journal', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        amount: parseFloat(amount),
        description: 'Vendor payment with fees',
        bank_charge: parseFloat(bankCharge),
        gov_tax: parseFloat(govTax),
      }),
    });
    if (res.ok) setJournalResult(await res.json());
  };

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">GL Account Mappings</h1>
      
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fee Type</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">GL Code</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Account Name</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {mappings.map((m, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-sm font-medium text-gray-900">{m.fee_type}</td>
                <td className="px-4 py-3 text-sm font-mono text-blue-600">{m.gl_account_code}</td>
                <td className="px-4 py-3 text-sm text-gray-700">{m.gl_account_name}</td>
                <td className="px-4 py-3 text-sm text-gray-500">{m.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Journal Entry Suggester */}
      <div className="bg-white p-5 rounded-xl border border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">Journal Entry Suggester</h3>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <label className="text-xs text-gray-500">Amount</label>
            <input value={amount} onChange={e => setAmount(e.target.value)} className="w-full mt-1 px-3 py-2 border rounded-lg text-sm" />
          </div>
          <div>
            <label className="text-xs text-gray-500">Bank Charge</label>
            <input value={bankCharge} onChange={e => setBankCharge(e.target.value)} className="w-full mt-1 px-3 py-2 border rounded-lg text-sm" />
          </div>
          <div>
            <label className="text-xs text-gray-500">Gov Tax</label>
            <input value={govTax} onChange={e => setGovTax(e.target.value)} className="w-full mt-1 px-3 py-2 border rounded-lg text-sm" />
          </div>
        </div>
        <button onClick={suggestJournal} className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">
          Generate Journal Entries
        </button>
        {journalResult && (
          <div className="mt-4 space-y-2">
            {journalResult.journal_entries.map((e: any, i: number) => (
              <div key={i} className="flex justify-between items-center py-2 px-3 bg-gray-50 rounded-lg text-sm">
                <div>
                  <span className="font-mono text-blue-600 mr-2">{e.account_code}</span>
                  <span className="text-gray-700">{e.account_name}</span>
                </div>
                <div className="space-x-4">
                  {e.debit > 0 && <span className="text-red-600 font-medium">Dr {e.debit.toLocaleString()}</span>}
                  {e.credit > 0 && <span className="text-green-600 font-medium">Cr {e.credit.toLocaleString()}</span>}
                </div>
              </div>
            ))}
            <div className={`text-sm font-medium ${journalResult.is_balanced ? 'text-green-600' : 'text-red-600'}`}>
              {journalResult.is_balanced ? '✅ Balanced' : '❌ Not balanced'}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Periods Page ───────────────────────────────────────────────

function PeriodsPage({ companyId }: { companyId: string }) {
  const [periods, setPeriods] = useState<any[]>([]);
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [year, setYear] = useState(new Date().getFullYear());

  const fetchPeriods = async () => {
    const token = localStorage.getItem('access_token');
    const res = await fetch(`/api/periods/${companyId}`, { headers: { Authorization: `Bearer ${token}` } });
    if (res.ok) setPeriods(await res.json());
  };

  useEffect(() => { fetchPeriods(); }, [companyId]);

  const lockPeriod = async () => {
    const token = localStorage.getItem('access_token');
    await fetch(`/api/periods/${companyId}/lock`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ period_month: month, period_year: year }),
    });
    fetchPeriods();
  };

  const unlockPeriod = async () => {
    const token = localStorage.getItem('access_token');
    await fetch(`/api/periods/${companyId}/unlock`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ period_month: month, period_year: year }),
    });
    fetchPeriods();
  };

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Period Lock</h1>
      
      <div className="bg-white p-5 rounded-xl border border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">Lock/Unlock Period</h3>
        <div className="flex items-end gap-4">
          <div>
            <label className="text-xs text-gray-500">Month</label>
            <select value={month} onChange={e => setMonth(+e.target.value)} className="w-full mt-1 px-3 py-2 border rounded-lg text-sm">
              {Array.from({length: 12}, (_, i) => (
                <option key={i+1} value={i+1}>{new Date(2000, i).toLocaleString('en', {month: 'long'})}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500">Year</label>
            <input type="number" value={year} onChange={e => setYear(+e.target.value)} className="w-full mt-1 px-3 py-2 border rounded-lg text-sm" />
          </div>
          <button onClick={lockPeriod} className="px-4 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700">🔒 Lock</button>
          <button onClick={unlockPeriod} className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700">🔓 Unlock</button>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Period</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Locked At</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {periods.map((p, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-sm font-medium">{p.period_month}/{p.period_year}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    p.status === 'locked' ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                  }`}>
                    {p.status === 'locked' ? '🔒 Locked' : '✅ Open'}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-gray-500">{p.locked_at || '—'}</td>
              </tr>
            ))}
            {periods.length === 0 && (
              <tr><td colSpan={3} className="px-4 py-8 text-center text-gray-400">No periods configured yet</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Exceptions Page ───────────────────────────────────────────

function ExceptionsPage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-4">Exceptions</h1>
      <div className="bg-white p-8 rounded-xl border border-gray-200 text-center">
        <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
        </svg>
        <h3 className="mt-2 text-sm font-medium text-gray-900">Exception Reports</h3>
        <p className="mt-1 text-sm text-gray-500">
          Run a reconciliation first. Exceptions will be generated automatically from unmatched transactions.
        </p>
      </div>
    </div>
  );
}

export default App;
