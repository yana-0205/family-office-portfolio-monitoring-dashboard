# Llm Extraction Run Summary

- Extraction mode: `llm`
- PDFs processed: `1`
- JSON outputs written: `1`
- Accuracy report: `llm_extraction_accuracy_summary.md`
- Accuracy CSV: `llm_extraction_accuracy_summary.csv`

## Documents

- `PDF_005` -> `capital_statement` | status=`extracted` | confidence=`0.9`
  schema warnings: ["Schema validation: Additional properties are not allowed ('amount_due', 'bank_instruction_changed_flag', 'due_date', 'investment_call', 'management_fee', 'missing_required_field_flag', 'partnership_expense', 'transaction_components', 'urgent_due_date_flag' were unexpected)", "Schema validation: 'period_start_date' is a required property", "Schema validation: 'period_end_date' is a required property", "Schema validation: 'beginning_nav' is a required property", "Schema validation: 'contributions' is a required property", "Schema validation: 'distributions' is a required property", "Schema validation: 'management_fees' is a required property", "Schema validation: 'partnership_expenses' is a required property", "Schema validation: 'realized_gain_loss' is a required property", "Schema validation: 'unrealized_gain_loss' is a required property", "Schema validation: 'ending_nav' is a required property", "Schema validation: 'nav_roll_forward_variance' is a required property", "Schema validation: 'commitment_mismatch_flag' is a required property"]
  classification reasons: ["capital_statement: matched 'partner capital account statement'", "capital_statement: matched 'pcap'", "capital_statement: matched 'ending nav'", "capital_statement: matched 'unfunded commitment'", "capital_statement: matched 'capital account roll-forward'", "capital_statement: filename contains 'pcap'"]