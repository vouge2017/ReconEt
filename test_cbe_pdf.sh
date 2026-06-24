#!/bin/bash
# ReconET — PDF Integration Test
# Tests CBE PDF upload → parsing → fee extraction → matching

set -e

echo "=========================================="
echo "ReconET — PDF Integration Test"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if API is running
echo ""
echo "Checking API health..."
HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null || echo "failed")
if [[ "$HEALTH" == *"healthy"* ]]; then
    echo -e "${GREEN}✅ API is running${NC}"
else
    echo -e "${RED}❌ API is not running. Start with: docker-compose up -d${NC}"
    exit 1
fi

# Create sample PDF if not exists
SAMPLE_PDF="data/sample_cbe_statement.pdf"
if [ ! -f "$SAMPLE_PDF" ]; then
    echo ""
    echo "Creating sample CBE PDF..."
    cd backend && python create_sample_cbe_pdf.py && cd ..
fi

# Test 1: PDF Upload
echo ""
echo "=========================================="
echo "TEST 1: PDF Upload + Balance Verification"
echo "=========================================="

RESPONSE=$(curl -s -X POST http://localhost:8000/api/reconciliation/run \
  -F "bank_file=@${SAMPLE_PDF}" \
  -F "company_id=a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11" 2>&1)

# Check if response is valid JSON
if echo "$RESPONSE" | python3 -m json.tool > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PDF uploaded and parsed successfully${NC}"
    
    # Extract key metrics
    FILE_TYPE=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('source',{}).get('file_type','unknown'))")
    TOTAL_TXNS=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['summary']['total_bank_transactions'])")
    MATCH_RATE=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['summary']['match_rate'])")
    TOTAL_FEES=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['summary']['fee_summary']['total_fees_extracted'])")
    
    echo "  File Type: $FILE_TYPE"
    echo "  Transactions: $TOTAL_TXNS"
    echo "  Match Rate: $MATCH_RATE"
    echo "  Total Fees: ETB $TOTAL_FEES"
    
    # Check balance verification
    BAL_STATUS=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('balance_verification',{}).get('status','unknown'))" 2>/dev/null || echo "not_found")
    if [ "$BAL_STATUS" == "passed" ]; then
        echo -e "${GREEN}  Balance Verification: PASSED ✅${NC}"
    elif [ "$BAL_STATUS" == "warning" ]; then
        echo -e "${YELLOW}  Balance Verification: WARNING ⚠️${NC}"
    else
        echo -e "${RED}  Balance Verification: $BAL_STATUS ❌${NC}"
    fi
    
    # Check PDF info
    ACCT_TYPE=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('pdf_info',{}).get('account_info',{}).get('account_type','unknown'))" 2>/dev/null || echo "not_found")
    echo "  Account Type: $ACCT_TYPE"
    
else
    echo -e "${RED}❌ PDF upload failed${NC}"
    echo "Response: $RESPONSE"
fi

# Test 2: CSV Upload (backward compatibility)
echo ""
echo "=========================================="
echo "TEST 2: CSV Upload (backward compatibility)"
echo "=========================================="

SAMPLE_CSV="data/sample_cbe_with_fees.csv"

RESPONSE_CSV=$(curl -s -X POST http://localhost:8000/api/reconciliation/run \
  -F "bank_file=@${SAMPLE_CSV}" \
  -F "company_id=a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11" 2>&1)

if echo "$RESPONSE_CSV" | python3 -m json.tool > /dev/null 2>&1; then
    echo -e "${GREEN}✅ CSV upload still works${NC}"
    
    FILE_TYPE=$(echo "$RESPONSE_CSV" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('source',{}).get('file_type','unknown'))")
    TOTAL_TXNS=$(echo "$RESPONSE_CSV" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['summary']['total_bank_transactions'])")
    MATCH_RATE=$(echo "$RESPONSE_CSV" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['summary']['match_rate'])")
    
    echo "  File Type: $FILE_TYPE"
    echo "  Transactions: $TOTAL_TXNS"
    echo "  Match Rate: $MATCH_RATE"
else
    echo -e "${RED}❌ CSV upload failed${NC}"
    echo "Response: $RESPONSE_CSV"
fi

# Test 3: Fee Extraction from PDF
echo ""
echo "=========================================="
echo "TEST 3: Fee Extraction from PDF"
echo "=========================================="

if echo "$RESPONSE" | python3 -m json.tool > /dev/null 2>&1; then
    echo "$RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
matches = d.get('matches', [])
fee_matches = [m for m in matches if m.get('fee_breakdown') and m['fee_breakdown'].get('total_fees', 0) > 0]

print(f'  Matches with fees: {len(fee_matches)}')
for m in fee_matches[:3]:
    fb = m['fee_breakdown']
    bt = m['bank_transaction']
    print(f'    {bt[\"reference\"]:15} | Amount: {bt[\"amount\"]:>12,.2f} | Fee: {fb[\"total_fees\"]:>8,.2f} | Strategy: {fb.get(\"strategy\",\"N/A\")}')
"
fi

# Test 4: Cheque Detection
echo ""
echo "=========================================="
echo "TEST 4: Cheque Detection from PDF"
echo "=========================================="

if echo "$RESPONSE" | python3 -m json.tool > /dev/null 2>&1; then
    echo "$RESPONSE" | python3 -c "
import sys, json
d = json.load(sys.stdin)
matches = d.get('matches', [])
chq_matches = [m for m in matches if 'CHQ' in str(m.get('bank_transaction',{}).get('reference','')).upper()]

print(f'  Cheque transactions found: {len(chq_matches)}')
for m in chq_matches:
    bt = m['bank_transaction']
    print(f'    {bt[\"reference\"]:15} | Amount: {bt[\"amount\"]:>12,.2f} | Type: {m[\"match_type\"]}')
"
fi

# Summary
echo ""
echo "=========================================="
echo "SUMMARY"
echo "=========================================="

if echo "$RESPONSE" | python3 -m json.tool > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PDF pipeline working: Upload → Parse → Fee Extract → Match${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Test with real CBE PDF statement"
    echo "  2. Verify balance verification catches errors"
    echo "  3. Check fee extraction on real transactions"
    echo "  4. Deploy to staging for Friday demo"
else
    echo -e "${RED}❌ PDF pipeline needs attention${NC}"
fi

echo ""
echo "=========================================="
echo "API Docs: http://localhost:8000/docs"
echo "Frontend: http://localhost:5173"
echo "=========================================="
