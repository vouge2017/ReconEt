import React, { useState } from 'react';

// Types
interface FeeBreakdown {
  strategy: string;
  gross_amount: number;
  bank_charge: number;
  gov_tax: number;
  total_fees: number;
  net_amount: number;
}

interface RichExplanation {
  match_type: string;
  confidence: number;
  confidence_level: string;
  summary_english: string;
  summary_amharic: string;
  components: Array<{
    category: string;
    english: string;
    amharic: string;
    ifrs_reference: string | null;
    detail: string | null;
  }>;
  accounting_treatment: string;
  accounting_treatment_am: string;
  ifrs_standard: string | null;
  compliance_note: string | null;
  compliance_note_am: string | null;
  audit_trail_note: string;
  period_impact: string | null;
  anomaly_flags: string[];
}

interface Match {
  match_id: string;
  match_type: string;
  confidence: number;
  explanation: string;
  rich_explanation: RichExplanation;
  status: string;
  amount_strategy: string;
  bank_transaction: {
    id: string;
    date: string;
    amount: number;
    reference: string;
    description: string;
  };
  gl_entry_ids: string[];
  fee_breakdown: FeeBreakdown | null;
  anomaly_flags: string[];
}

interface FeeSummary {
  total_fees_extracted: number;
  total_bank_charges: number;
  total_gov_tax: number;
  transactions_with_fees: number;
}

interface ReconciliationResult {
  summary: {
    total_bank_transactions: number;
    total_matched: number;
    total_unmatched: number;
    match_rate: string;
    fee_summary: FeeSummary;
  };
  matches: Match[];
}

// Format ETB currency
const formatETB = (amount: number) => {
  return new Intl.NumberFormat('en-ET', {
    style: 'decimal',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
};

// Confidence badge color
const getConfidenceColor = (confidence: number) => {
  if (confidence >= 90) return 'bg-green-100 text-green-800';
  if (confidence >= 80) return 'bg-blue-100 text-blue-800';
  if (confidence >= 70) return 'bg-yellow-100 text-yellow-800';
  return 'bg-red-100 text-red-800';
};

// Status badge
const getStatusBadge = (status: string) => {
  switch (status) {
    case 'auto_posted':
      return <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">Auto-Posted</span>;
    case 'pending':
      return <span className="px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-800 rounded-full">Review</span>;
    default:
      return <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded-full">{status}</span>;
  }
};

// Fee Breakdown Card
const FeeBreakdownCard: React.FC<{ fee: FeeBreakdown; confidence: number }> = ({ fee, confidence }) => {
  if (!fee || fee.total_fees === 0) return null;

  return (
    <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-amber-800">Fee Breakdown</span>
        <span className="text-xs text-amber-600">Strategy: {fee.strategy.toUpperCase()}</span>
      </div>
      
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">Gross Amount:</span>
          <span className="font-medium">ETB {formatETB(fee.gross_amount)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Bank Charge:</span>
          <span className="font-medium text-orange-600">ETB {formatETB(fee.bank_charge)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Gov't Tax (15%):</span>
          <span className="font-medium text-orange-600">ETB {formatETB(fee.gov_tax)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Total Fees:</span>
          <span className="font-bold text-red-600">ETB {formatETB(fee.total_fees)}</span>
        </div>
      </div>
      
      <div className="mt-2 pt-2 border-t border-amber-200">
        <div className="flex justify-between text-sm">
          <span className="font-medium text-gray-700">Net Amount (GL):</span>
          <span className="font-bold text-green-700">ETB {formatETB(fee.net_amount)}</span>
        </div>
      </div>
    </div>
  );
};

// Match Card
const MatchCard: React.FC<{ match: Match }> = ({ match }) => {
  const [expanded, setExpanded] = useState(false);
  const rich = match.rich_explanation;

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow">
      <div className="p-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            {getStatusBadge(match.status)}
            <span className={`px-2 py-1 text-xs font-medium rounded-full ${getConfidenceColor(match.confidence)}`}>
              {match.confidence}% confidence
            </span>
            {rich?.ifrs_standard && (
              <span className="px-2 py-1 text-xs font-medium bg-indigo-100 text-indigo-800 rounded-full">
                {rich.ifrs_standard}
              </span>
            )}
          </div>
          <button 
            onClick={() => setExpanded(!expanded)}
            className="text-gray-400 hover:text-gray-600"
          >
            {expanded ? '▼' : '▶'}
          </button>
        </div>

        {/* Transaction Info */}
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-2 mb-1">
              <span className="text-sm font-mono text-gray-500">{match.bank_transaction.reference}</span>
              <span className="text-sm text-gray-400">|</span>
              <span className="text-sm text-gray-600">{match.bank_transaction.date}</span>
            </div>
            <p className="text-sm text-gray-800 truncate">{match.bank_transaction.description}</p>
          </div>
          <div className="text-right ml-4">
            <p className="text-lg font-bold text-gray-900">
              ETB {formatETB(Math.abs(match.bank_transaction.amount))}
            </p>
            {match.bank_transaction.amount < 0 && (
              <span className="text-xs text-red-500">Debit</span>
            )}
          </div>
        </div>

        {/* Rich Explanation (from Explainability Engine) */}
        {rich && (
          <div className="mt-3">
            {/* Summary */}
            <div className="p-2 bg-blue-50 rounded text-sm text-blue-900">
              {rich.summary_english}
            </div>
            
            {/* Accounting Treatment */}
            <div className="mt-2 p-2 bg-green-50 rounded text-xs text-green-800">
              <span className="font-medium">Treatment:</span> {rich.accounting_treatment}
            </div>
            
            {/* Period Impact */}
            {rich.period_impact && (
              <div className={`mt-2 p-2 rounded text-xs ${
                rich.period_impact.includes('⚠️') ? 'bg-yellow-50 text-yellow-800' : 'bg-gray-50 text-gray-700'
              }`}>
                {rich.period_impact}
              </div>
            )}
            
            {/* Anomaly Flags */}
            {rich.anomaly_flags && rich.anomaly_flags.length > 0 && (
              <div className="mt-2 space-y-1">
                {rich.anomaly_flags.map((flag, idx) => (
                  <div key={idx} className="p-2 bg-orange-50 rounded text-xs text-orange-800">
                    ⚠️ {flag.split(': ')[1] || flag}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Fee Breakdown (expandable) */}
        {match.fee_breakdown && match.fee_breakdown.total_fees > 0 && (
          <FeeBreakdownCard fee={match.fee_breakdown} confidence={match.confidence} />
        )}

        {/* Expanded Details */}
        {expanded && rich && (
          <div className="mt-3 pt-3 border-t border-gray-100">
            {/* Match Components */}
            <div className="mb-3">
              <h4 className="text-xs font-medium text-gray-500 uppercase mb-2">Match Components</h4>
              <div className="space-y-1">
                {rich.components.map((comp, idx) => (
                  <div key={idx} className="text-xs text-gray-600">
                    <span className="font-medium capitalize">{comp.category}:</span> {comp.english}
                    {comp.ifrs_reference && (
                      <span className="ml-2 text-indigo-600">({comp.ifrs_reference})</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
            
            {/* Audit Trail Note */}
            <div className="text-xs text-gray-500 italic">
              {rich.audit_trail_note}
            </div>
            
            {/* Match Metadata */}
            <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-gray-500">
              <div>Match Type: <span className="font-medium text-gray-700">{match.match_type}</span></div>
              <div>Strategy: <span className="font-medium text-gray-700">{match.amount_strategy}</span></div>
              <div>Bank Txn ID: <span className="font-mono">{match.bank_transaction.id}</span></div>
              <div>GL Entries: <span className="font-mono">{match.gl_entry_ids?.length || 0}</span></div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Fee Summary Dashboard
const FeeSummaryDashboard: React.FC<{ summary: FeeSummary; matchRate: string }> = ({ summary, matchRate }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      {/* Match Rate */}
      <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
        <div className="text-sm text-gray-500 mb-1">Match Rate</div>
        <div className="text-2xl font-bold text-green-600">{matchRate}</div>
        <div className="text-xs text-gray-400 mt-1">of bank transactions</div>
      </div>

      {/* Total Fees */}
      <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
        <div className="text-sm text-gray-500 mb-1">Total Fees Extracted</div>
        <div className="text-2xl font-bold text-orange-600">ETB {formatETB(summary.total_fees_extracted)}</div>
        <div className="text-xs text-gray-400 mt-1">{summary.transactions_with_fees} transactions</div>
      </div>

      {/* Bank Charges */}
      <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
        <div className="text-sm text-gray-500 mb-1">Bank Charges</div>
        <div className="text-2xl font-bold text-blue-600">ETB {formatETB(summary.total_bank_charges)}</div>
        <div className="text-xs text-gray-400 mt-1">service fees</div>
      </div>

      {/* Government Tax */}
      <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
        <div className="text-sm text-gray-500 mb-1">Gov't Tax (VAT)</div>
        <div className="text-2xl font-bold text-purple-600">ETB {formatETB(summary.total_gov_tax)}</div>
        <div className="text-xs text-gray-400 mt-1">15% on bank services</div>
      </div>
    </div>
  );
};

// Main Reconciliation Page
const ReconciliationPage: React.FC = () => {
  const [result, setResult] = useState<ReconciliationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('bank_csv', file);
    formData.append('company_id', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11');

    try {
      const response = await fetch('/api/reconciliation/run', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Reconciliation</h1>
            <p className="text-sm text-gray-500 mt-1">Upload bank statement to match transactions</p>
          </div>
          <div className="flex items-center space-x-4">
            <label className="inline-flex items-center px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 cursor-pointer transition-colors">
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              Upload CSV
              <input type="file" accept=".csv" onChange={handleUpload} className="hidden" />
            </label>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="ml-3 text-gray-600">Processing bank statement...</span>
          </div>
        )}

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

        {result && (
          <>
            {/* Fee Summary */}
            <FeeSummaryDashboard 
              summary={result.summary.fee_summary} 
              matchRate={result.summary.match_rate} 
            />

            {/* Summary Stats */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="bg-white p-4 rounded-lg border border-gray-200">
                <div className="text-sm text-gray-500">Total Bank Transactions</div>
                <div className="text-xl font-bold">{result.summary.total_bank_transactions}</div>
              </div>
              <div className="bg-white p-4 rounded-lg border border-gray-200">
                <div className="text-sm text-gray-500">Matched</div>
                <div className="text-xl font-bold text-green-600">{result.summary.total_matched}</div>
              </div>
              <div className="bg-white p-4 rounded-lg border border-gray-200">
                <div className="text-sm text-gray-500">Unmatched</div>
                <div className="text-xl font-bold text-orange-600">{result.summary.total_unmatched}</div>
              </div>
            </div>

            {/* Match Results */}
            <div className="mb-4">
              <h2 className="text-lg font-semibold text-gray-900 mb-3">Match Results</h2>
              <div className="space-y-3">
                {result.matches.map((match) => (
                  <MatchCard key={match.match_id} match={match} />
                ))}
              </div>
            </div>

            {/* No matches message */}
            {result.matches.length === 0 && (
              <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
                <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <h3 className="mt-2 text-sm font-medium text-gray-900">No matches found</h3>
                <p className="mt-1 text-sm text-gray-500">Try uploading a bank statement CSV</p>
              </div>
            )}
          </>
        )}

        {/* Empty state */}
        {!loading && !error && !result && (
          <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">Upload Bank Statement</h3>
            <p className="mt-1 text-sm text-gray-500">
              Upload a CBE CSV file to start reconciliation
            </p>
            <div className="mt-6">
              <label className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 cursor-pointer">
                <svg className="-ml-1 mr-2 h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                Select CSV File
                <input type="file" accept=".csv" onChange={handleUpload} className="hidden" />
              </label>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReconciliationPage;
