import React, { useState, useEffect } from 'react';

// Types
interface Cheque {
  id: string;
  cheque_number: string;
  cheque_type: string;
  amount: number;
  payee_name: string | null;
  payer_name: string | null;
  issue_date: string;
  expected_clear_date: string | null;
  days_outstanding: number;
  status: string;
}

interface ChequeSummary {
  count: number;
  total_amount: number;
  cheques: Cheque[];
}

interface NewCheque {
  bank_account_id: string;
  cheque_number: string;
  cheque_type: string;
  amount: number;
  payee_name: string;
  payer_name: string;
  issue_date: string;
  expected_clear_date: string;
  stale_days: number;
}

// Format ETB currency
const formatETB = (amount: number) => {
  return new Intl.NumberFormat('en-ET', {
    style: 'decimal',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
};

// Status badge
const getStatusBadge = (status: string) => {
  const styles: Record<string, string> = {
    issued: 'bg-blue-100 text-blue-800',
    deposited: 'bg-yellow-100 text-yellow-800',
    clearing: 'bg-purple-100 text-purple-800',
    cleared: 'bg-green-100 text-green-800',
    bounced: 'bg-red-100 text-red-800',
    stale: 'bg-orange-100 text-orange-800',
    cancelled: 'bg-gray-100 text-gray-800',
  };

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${styles[status] || 'bg-gray-100 text-gray-800'}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
};

// Stale Alert Card
const StaleAlertCard: React.FC<{ cheque: Cheque }> = ({ cheque }) => (
  <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-3">
    <div className="flex items-center justify-between">
      <div>
        <div className="flex items-center space-x-2">
          <span className="text-red-600 font-bold">⚠️</span>
          <span className="font-mono text-sm font-medium text-red-800">
            CHQ-{cheque.cheque_number}
          </span>
          <span className="text-sm text-red-600">
            {cheque.days_outstanding} days outstanding
          </span>
        </div>
        <div className="mt-1 text-sm text-gray-600">
          {cheque.payee_name || cheque.payer_name || 'Unknown'} · Issued {cheque.issue_date}
        </div>
      </div>
      <div className="text-right">
        <div className="text-lg font-bold text-red-700">
          ETB {formatETB(cheque.amount)}
        </div>
        {getStatusBadge('stale')}
      </div>
    </div>
  </div>
);

// Cheque Card
const ChequeCard: React.FC<{ cheque: Cheque }> = ({ cheque }) => (
  <div className="bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow p-4">
    <div className="flex items-center justify-between mb-2">
      <div className="flex items-center space-x-2">
        <span className="font-mono text-sm font-medium text-gray-800">
          CHQ-{cheque.cheque_number}
        </span>
        {getStatusBadge(cheque.status)}
      </div>
      <div className="text-right">
        <div className="text-lg font-bold text-gray-900">
          ETB {formatETB(cheque.amount)}
        </div>
      </div>
    </div>

    <div className="grid grid-cols-2 gap-2 text-sm text-gray-600">
      <div>
        <span className="text-gray-500">Type:</span>{' '}
        <span className="font-medium">{cheque.cheque_type === 'issued' ? 'Issued' : 'Received'}</span>
      </div>
      <div>
        <span className="text-gray-500">
          {cheque.cheque_type === 'issued' ? 'Payee:' : 'Payer:'}
        </span>{' '}
        <span className="font-medium">
          {cheque.cheque_type === 'issued' ? cheque.payee_name : cheque.payer_name || 'N/A'}
        </span>
      </div>
      <div>
        <span className="text-gray-500">Issued:</span>{' '}
        <span className="font-medium">{cheque.issue_date}</span>
      </div>
      <div>
        <span className="text-gray-500">Days:</span>{' '}
        <span className={`font-medium ${cheque.days_outstanding > 90 ? 'text-red-600' : 'text-gray-700'}`}>
          {cheque.days_outstanding}
        </span>
      </div>
      {cheque.expected_clear_date && (
        <div className="col-span-2">
          <span className="text-gray-500">Expected Clear:</span>{' '}
          <span className="font-medium">{cheque.expected_clear_date}</span>
        </div>
      )}
    </div>
  </div>
);

// Register Cheque Modal
const RegisterChequeModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (cheque: NewCheque) => void;
  loading: boolean;
}> = ({ isOpen, onClose, onSubmit, loading }) => {
  const [form, setForm] = useState<NewCheque>({
    bank_account_id: 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11',
    cheque_number: '',
    cheque_type: 'issued',
    amount: 0,
    payee_name: '',
    payer_name: '',
    issue_date: '',
    expected_clear_date: '',
    stale_days: 90,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(form);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Register New Cheque</h3>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Cheque Number
            </label>
            <input
              type="text"
              value={form.cheque_number}
              onChange={(e) => setForm({ ...form, cheque_number: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="e.g., CHQ-001235"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Type
            </label>
            <select
              value={form.cheque_type}
              onChange={(e) => setForm({ ...form, cheque_type: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="issued">Issued</option>
              <option value="received">Received</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Amount (ETB)
            </label>
            <input
              type="number"
              value={form.amount || ''}
              onChange={(e) => setForm({ ...form, amount: parseFloat(e.target.value) || 0 })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="50000"
              min="0"
              step="0.01"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {form.cheque_type === 'issued' ? 'Payee Name' : 'Payer Name'}
            </label>
            <input
              type="text"
              value={form.cheque_type === 'issued' ? form.payee_name : form.payer_name}
              onChange={(e) =>
                form.cheque_type === 'issued'
                  ? setForm({ ...form, payee_name: e.target.value })
                  : setForm({ ...form, payer_name: e.target.value })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Supplier ABC"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Issue Date
              </label>
              <input
                type="date"
                value={form.issue_date}
                onChange={(e) => setForm({ ...form, issue_date: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Expected Clear
              </label>
              <input
                type="date"
                value={form.expected_clear_date}
                onChange={(e) => setForm({ ...form, expected_clear_date: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Stale Days Threshold
            </label>
            <input
              type="number"
              value={form.stale_days}
              onChange={(e) => setForm({ ...form, stale_days: parseInt(e.target.value) || 90 })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              min="1"
            />
          </div>

          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Registering...' : 'Register Cheque'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Main Cheques Page
const ChequesPage: React.FC = () => {
  const [outstanding, setOutstanding] = useState<ChequeSummary | null>(null);
  const [stale, setStale] = useState<ChequeSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showRegister, setShowRegister] = useState(false);
  const [registerLoading, setRegisterLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'outstanding' | 'stale'>('outstanding');

  const companyId = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11';

  const fetchCheques = async () => {
    setLoading(true);
    setError(null);

    try {
      const [outstandingRes, staleRes] = await Promise.all([
        fetch(`/api/cheques/outstanding/${companyId}`),
        fetch(`/api/cheques/stale/${companyId}`),
      ]);

      if (!outstandingRes.ok || !staleRes.ok) {
        throw new Error('Failed to fetch cheques');
      }

      const outstandingData = await outstandingRes.json();
      const staleData = await staleRes.json();

      setOutstanding(outstandingData);
      setStale(staleData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load cheques');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCheques();
  }, []);

  const handleRegister = async (cheque: NewCheque) => {
    setRegisterLoading(true);
    try {
      const response = await fetch('/api/cheques/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cheque),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to register cheque');
      }

      setShowRegister(false);
      fetchCheques();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to register cheque');
    } finally {
      setRegisterLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Loading cheques...</span>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Cheque Tracking</h1>
            <p className="text-sm text-gray-500 mt-1">
              Monitor outstanding and stale cheques
            </p>
          </div>
          <button
            onClick={() => setShowRegister(true)}
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Register Cheque
          </button>
        </div>
      </div>

      <div className="p-6">
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
            <div className="text-sm text-gray-500 mb-1">Outstanding Cheques</div>
            <div className="text-2xl font-bold text-blue-600">{outstanding?.count || 0}</div>
            <div className="text-xs text-gray-400 mt-1">
              ETB {formatETB(outstanding?.total_amount || 0)} total
            </div>
          </div>

          <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
            <div className="text-sm text-gray-500 mb-1">Stale Cheques</div>
            <div className="text-2xl font-bold text-red-600">{stale?.count || 0}</div>
            <div className="text-xs text-gray-400 mt-1">
              ETB {formatETB(stale?.total_amount || 0)} at risk
            </div>
          </div>

          <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
            <div className="text-sm text-gray-500 mb-1">Total Exposure</div>
            <div className="text-2xl font-bold text-gray-900">
              ETB {formatETB((outstanding?.total_amount || 0) + (stale?.total_amount || 0))}
            </div>
            <div className="text-xs text-gray-400 mt-1">all outstanding + stale</div>
          </div>
        </div>

        {/* Stale Alerts */}
        {stale && stale.count > 0 && (
          <div className="mb-6">
            <div className="flex items-center mb-3">
              <span className="text-red-600 mr-2">⚠️</span>
              <h2 className="text-lg font-semibold text-gray-900">
                Stale Cheque Alerts ({stale.count})
              </h2>
            </div>
            <div className="space-y-2">
              {stale.cheques.map((cheque) => (
                <StaleAlertCard key={cheque.id} cheque={cheque} />
              ))}
            </div>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="border-b border-gray-200 mb-4">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('outstanding')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'outstanding'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Outstanding ({outstanding?.count || 0})
            </button>
            <button
              onClick={() => setActiveTab('stale')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'stale'
                  ? 'border-red-500 text-red-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Stale ({stale?.count || 0})
            </button>
          </nav>
        </div>

        {/* Cheque List */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {activeTab === 'outstanding' && outstanding?.cheques.map((cheque) => (
            <ChequeCard key={cheque.id} cheque={cheque} />
          ))}
          {activeTab === 'stale' && stale?.cheques.map((cheque) => (
            <ChequeCard key={cheque.id} cheque={cheque} />
          ))}
        </div>

        {/* Empty State */}
        {activeTab === 'outstanding' && outstanding?.count === 0 && (
          <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No outstanding cheques</h3>
            <p className="mt-1 text-sm text-gray-500">All cheques have been cleared</p>
          </div>
        )}

        {activeTab === 'stale' && stale?.count === 0 && (
          <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
            <svg className="mx-auto h-12 w-12 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No stale cheques</h3>
            <p className="mt-1 text-sm text-gray-500">All cheques are within the stale threshold</p>
          </div>
        )}
      </div>

      {/* Register Cheque Modal */}
      <RegisterChequeModal
        isOpen={showRegister}
        onClose={() => setShowRegister(false)}
        onSubmit={handleRegister}
        loading={registerLoading}
      />
    </div>
  );
};

export default ChequesPage;
