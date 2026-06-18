# Baseline Extraction Run Summary

- Extraction mode: `baseline`
- PDFs processed: `6`
- JSON outputs written: `6`
- Accuracy report: `baseline_extraction_accuracy_summary.md`
- Accuracy CSV: `baseline_extraction_accuracy_summary.csv`

## Documents

- `PDF_001` -> `capital_call` | status=`extracted` | confidence=`0.85`
  schema warnings: none
  classification reasons: ["capital_call: matched 'capital call'", "capital_call: matched 'amount due'", "capital_call: matched 'due date'", "capital_call: matched 'funding obligation'", "capital_call: filename contains 'capital_call'"]
- `PDF_002` -> `capital_call` | status=`partial` | confidence=`0.85`
  schema warnings: ['Missing required extracted fields: unfunded_commitment']
  classification reasons: ["capital_call: matched 'capital call'", "capital_call: matched 'amount due'", "capital_call: matched 'due date'", "capital_call: matched 'funding obligation'", "capital_call: filename contains 'capital_call'"]
- `PDF_003` -> `distribution` | status=`extracted` | confidence=`0.85`
  schema warnings: none
  classification reasons: ["distribution: matched 'distribution notice'", "distribution: matched 'payment date'", "distribution: matched 'gross distribution'", "distribution: matched 'distribution components'", "distribution: filename contains 'distribution'"]
- `PDF_004` -> `capital_statement` | status=`extracted` | confidence=`0.85`
  schema warnings: none
  classification reasons: ["capital_statement: matched 'partner capital account statement'", "capital_statement: matched 'pcap'", "capital_statement: matched 'ending nav'", "capital_statement: matched 'unfunded commitment'", "capital_statement: matched 'capital account roll-forward'", "capital_statement: filename contains 'pcap'"]
- `PDF_005` -> `capital_statement` | status=`extracted` | confidence=`0.85`
  schema warnings: none
  classification reasons: ["capital_statement: matched 'partner capital account statement'", "capital_statement: matched 'pcap'", "capital_statement: matched 'ending nav'", "capital_statement: matched 'unfunded commitment'", "capital_statement: matched 'capital account roll-forward'", "capital_statement: filename contains 'pcap'"]
- `PDF_006` -> `newsletter` | status=`extracted` | confidence=`0.85`
  schema warnings: none
  classification reasons: ["newsletter: matched 'quarterly investor newsletter'", "newsletter: matched 'portfolio activity'", "newsletter: matched 'risk notes'", "newsletter: filename contains 'newsletter'"]