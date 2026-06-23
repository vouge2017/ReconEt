#!/bin/bash
# ReconET — Quick Start
# Shows the integrated system running

set -e

echo "=========================================="
echo "ReconET — Fee-Aware Reconciliation"
echo "=========================================="

# Start PostgreSQL + API
echo ""
echo "Starting docker containers..."
docker-compose up -d

# Wait for PostgreSQL
echo ""
echo "Waiting for PostgreSQL..."
sleep 5

# Create sample CBE CSV
echo ""
echo "Creating sample CBE CSV..."
cat > /tmp/test_cbe.csv << 'EOF'
ቀን,ክፍያ,ገቢ,ማጣቀሻ,መግለጫ,ቀሪ ሂሳብ
15/06/2026,"100,040.00",,"INV-2026-0089","TRANSFER TO ABC TRADING FEE 25 TAX 15","2,450,000.00"
16/06/2026,"50,011.50",,"SALARY-JUN","SALARY PAYMENT TO STAFF FEE 10 TAX 1.50","2,400,000.00"
16/06/2026,,"250,000.00","DEPOSIT-CASH","CASH DEPOSIT FROM CUSTOMER","2,650,000.00"
17/06/2026,"75,028.75","TRANSFER-FEE-001","TRANSFER TO DASHEN BANK FEE 25 TAX 3.75","2,575,000.00"
17/06/2026,"200,000.00",,"CHQ-001234","CHEQUE PAYMENT TO SUPPLIER XYZ","2,375,000.00"
18/06/2026,"15,017.25",,"SO-001","STANDING ORDER RENT PAYMENT FEE 15 TAX 2.25","2,360,000.00"
18/06/2026,"300,000.00",,"TRANSFER-ECO","TRANSFER TO ECOBANK ACCOUNT 2001","2,060,000.00"
19/06/2026,"50,050.00",,"DRAFT-001","DRAFT ISSUANCE FEE 50 TAX 7.50","2,010,000.00"
19/06/2026,,"100,000.00","RECEIPT-001","RECEIPT FROM CUSTOMER ABC","2,110,000.00"
20/06/2026,"100,115.00",,"CERT-001","BALANCE CERTIFICATE FEE 100 TAX 15","2,010,000.00"
EOF

# Test the API
echo ""
echo "Testing /api/reconciliation/run..."
echo "=========================================="

RESPONSE=$(curl -s -X POST http://localhost:8000/api/reconciliation/run \
  -F "bank_csv=@/tmp/test_cbe.csv" \
  -F "company_id=a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")

echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"

echo ""
echo "=========================================="
echo "API is running at http://localhost:8000"
echo "Docs at http://localhost:8000/docs"
echo ""
echo "To stop: docker-compose down"
echo "=========================================="
