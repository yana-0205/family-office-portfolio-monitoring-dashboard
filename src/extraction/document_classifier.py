from __future__ import annotations

from collections import Counter


KEYWORDS = {
    "capital_call": [
        "capital call",
        "amount due",
        "due date",
        "funding obligation",
    ],
    "distribution": [
        "distribution notice",
        "payment date",
        "gross distribution",
        "distribution components",
    ],
    "capital_statement": [
        "partner capital account statement",
        "pcap",
        "ending nav",
        "unfunded commitment",
        "capital account roll-forward",
    ],
    "newsletter": [
        "quarterly investor newsletter",
        "market themes",
        "portfolio activity",
        "risk notes",
    ],
}


def classify_document(text: str, filename: str | None = None) -> dict:
    haystack = f"{filename or ''}\n{text}".lower()
    score_counter: Counter[str] = Counter()
    reasons: list[str] = []

    for document_type, keywords in KEYWORDS.items():
        for keyword in keywords:
            if keyword in haystack:
                score_counter[document_type] += 1
                reasons.append(f"{document_type}: matched '{keyword}'")

    if filename:
        lower_name = filename.lower()
        if "capital_call" in lower_name:
            score_counter["capital_call"] += 2
            reasons.append("capital_call: filename contains 'capital_call'")
        if "distribution" in lower_name:
            score_counter["distribution"] += 2
            reasons.append("distribution: filename contains 'distribution'")
        if "pcap" in lower_name:
            score_counter["capital_statement"] += 2
            reasons.append("capital_statement: filename contains 'pcap'")
        if "newsletter" in lower_name:
            score_counter["newsletter"] += 2
            reasons.append("newsletter: filename contains 'newsletter'")

    if not score_counter:
        return {
            "document_type": "capital_call",
            "classification_confidence": 0.0,
            "classification_reasons": ["No classification heuristics matched; defaulted to capital_call."],
        }

    best_type, best_score = score_counter.most_common(1)[0]
    total_score = sum(score_counter.values())
    confidence = round(best_score / total_score, 3) if total_score else 0.0
    filtered_reasons = [reason for reason in reasons if reason.startswith(best_type)]

    return {
        "document_type": best_type,
        "classification_confidence": confidence,
        "classification_reasons": filtered_reasons,
    }


def classify_all_documents(pdf_records: list[dict]) -> list[dict]:
    results = []
    for record in pdf_records:
        classification = classify_document(record.get("text", ""), filename=record.get("filename"))
        results.append({**record, "classification": classification})
    return results
