from src.extraction.pdf_reader import read_all_pdfs


def test_read_all_pdfs_finds_six_documents() -> None:
    records = read_all_pdfs()
    assert len(records) == 6
    assert all(record["document_id"].startswith("PDF_") for record in records)
    assert all(record["text"] for record in records)
    assert all(record["pages"] for record in records)
    assert all("page" in record["pages"][0] for record in records)
    assert all("text" in record["pages"][0] for record in records)
