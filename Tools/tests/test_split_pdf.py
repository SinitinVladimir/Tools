import os
import sys
from pathlib import Path
from pypdf import PdfReader, PdfWriter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from split_pdf import split_pdf

def make_pdf(path, num_pages=3):
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=72, height=72)
    with open(path, 'wb') as f:
        writer.write(f)

def test_split_all_pages(tmp_path):
    pdf = tmp_path / "sample.pdf"
    make_pdf(pdf)
    split_pdf(str(pdf), out_dir=str(tmp_path))
    assert (tmp_path / "sample_001.pdf").exists()
    assert (tmp_path / "sample_003.pdf").exists()

def test_split_page_range(tmp_path):
    pdf = tmp_path / "sample.pdf"
    make_pdf(pdf, num_pages=5)
    out_dir = tmp_path / "out"
    split_pdf(str(pdf), out_dir=str(out_dir), pages="2-3")
    files = sorted(out_dir.glob("*.pdf"))
    assert len(files) == 2
    names = [f.name for f in files]
    assert names == ["sample_001.pdf", "sample_002.pdf"]

