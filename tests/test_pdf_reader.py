from pathlib import Path

from src.extraction.pdf_reader import read_all_pdfs


def test_read_all_pdfs_finds_six_documents() -> None:
    records = read_all_pdfs()
    assert len(records) == 6
    assert all(record["document_id"].startswith("PDF_") for record in records)
    assert all(record["text"] for record in records)
    assert all(record["pages"] for record in records)
    assert all("page" in record["pages"][0] for record in records)
    assert all("text" in record["pages"][0] for record in records)


def test_read_all_pdfs_supports_custom_source_dir(tmp_path: Path) -> None:
    sample_pdf = next(Path("data/raw/family_office_corrected_dataset_v1/documents").glob("*.pdf"))
    copied_pdf = tmp_path / sample_pdf.name
    copied_pdf.write_bytes(sample_pdf.read_bytes())

    records = read_all_pdfs(source_dir=tmp_path)

    assert len(records) == 1
    assert records[0]["filename"] == sample_pdf.name
