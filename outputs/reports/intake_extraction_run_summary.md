# Intake Extraction Run Summary

- Extraction mode: `intake`
- PDFs processed: `1`
- JSON outputs written: `1`
- Accuracy report: `intake_extraction_accuracy_summary.md`
- Accuracy CSV: `intake_extraction_accuracy_summary.csv`

## Documents

- `PDF_005` -> `capital_statement` | status=`extracted` | confidence=`0.85`
  schema warnings: ["Schema validation: 'intake' is not one of ['baseline', 'llm']"]
  classification reasons: ["capital_statement: matched 'partner capital account statement'", "capital_statement: matched 'pcap'", "capital_statement: matched 'ending nav'", "capital_statement: matched 'unfunded commitment'", "capital_statement: matched 'capital account roll-forward'", "capital_statement: filename contains 'pcap'"]