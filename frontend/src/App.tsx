import React, { useState } from 'react';
import ReconciliationPage from './pages/Reconciliation';
import ChequesPage from './pages/Cheques';

type Page = 'reconciliation' | 'cheques';

function App() {
  const [currentPage, setCurrentPage] = useState<Page>('reconciliation');

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="fixed inset-y-0 left-0 w-64 bg-gray-900 text-white">
        <div className="flex items-center justify-center h-16 border-b border-gray-800">
          <h1 className="text-xl font-bold">ReconET</h1>
        </div>
        <nav className="mt-6">
          <div className="px-4 space-y-2">
            <a
              href="#"
              onClick={(e) => { e.preventDefault(); setCurrentPage('reconciliation'); }}
              className={`flex items-center px-4 py-2 rounded-lg transition-colors ${
                currentPage === 'reconciliation'
                  ? 'text-white bg-gray-800'
                  : 'text-gray-300 hover:bg-gray-800'
              }`}
            >
              <svg className="w-5 h-5 mr-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
              </svg>
              Reconciliation
            </a>
            <a
              href="#"
              onClick={(e) => { e.preventDefault(); setCurrentPage('cheques'); }}
              className={`flex items-center px-4 py-2 rounded-lg transition-colors ${
                currentPage === 'cheques'
                  ? 'text-white bg-gray-800'
                  : 'text-gray-300 hover:bg-gray-800'
              }`}
            >
              <svg className="w-5 h-5 mr-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
              Cheques
            </a>
          </div>
        </nav>
      </div>

      {/* Main Content */}
      <div className="ml-64">
        {currentPage === 'reconciliation' && <ReconciliationPage />}
        {currentPage === 'cheques' && <ChequesPage />}
      </div>
    </div>
  );
}

export default App;
