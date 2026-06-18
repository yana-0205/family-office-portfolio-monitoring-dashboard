from src.extraction.document_classifier import classify_document


def test_classify_document_capital_call() -> None:
    result = classify_document("Capital Call Notice\nAmount Due\nDue Date", filename="sample_capital_call.pdf")
    assert result["document_type"] == "capital_call"


def test_classify_document_distribution() -> None:
    result = classify_document("Distribution Notice\nPayment Date\nGross Distribution")
    assert result["document_type"] == "distribution"


def test_classify_document_capital_statement() -> None:
    result = classify_document("Partner Capital Account Statement\nEnding NAV\nUnfunded Commitment")
    assert result["document_type"] == "capital_statement"


def test_classify_document_newsletter() -> None:
    result = classify_document("Quarterly Investor Newsletter\nPortfolio Activity\nRisk Notes")
    assert result["document_type"] == "newsletter"
