from pathlib import Path

import pytest
import yaml
from docx import Document

from render_resume import render_docx, render_pdf

TEMPLATE = Path(__file__).parent.parent / "templates" / "default.docx"


def resume():
    return {
        "basics": {
            "name": "Steven Lien",
            "headline": "Senior Software Engineer",
            "email": "me@example.com",
            "phone": "0900000000",
            "location": "Taipei",
            "links": ["github.com/example"],
            "summary": "Engineer who ships capture engines.",
        },
        "experience": [
            {
                "id": "barco",
                "company": "Barco",
                "title": "Senior Software Engineer",
                "location": "Kortrijk",
                "period": {"start": "2019-03", "end": "present"},
                "achievements": [
                    {"id": "a1", "text": "Integrated WGC, 48-hour long run stable.", "sources": []},
                    {"id": "a2", "text": "Replaced SIFT with template matching.", "sources": []},
                ],
            },
            {
                "id": "ftdi",
                "company": "FTDI",
                "title": "Engineer",
                "period": {"start": "2014", "end": "2018-06"},
                "achievements": [{"id": "a3", "text": "Built a smart home stack.", "sources": []}],
            },
        ],
        "skills": [
            {"name": "C++", "category": "Languages"},
            {"name": "Python", "category": "Languages"},
            {"name": "WinDbg", "category": "Debugging"},
        ],
        "education": [
            {"school": "NTU", "degree": "M.S.", "field": "Electrical Engineering",
             "period": {"start": "2008", "end": "2010"}}
        ],
        "certifications": [{"name": "Java Programmer", "issuer": "Sun"}],
        "languages": [{"name": "English", "level": "Fluent"}],
    }


def lines(path):
    return [p.text for p in Document(path).paragraphs]


def test_render_docx_contains_resume_content(tmp_path):
    out = tmp_path / "resume.docx"
    render_docx(resume(), TEMPLATE, out)
    text = "\n".join(lines(out))
    assert "Steven Lien" in text
    assert "me@example.com | 0900000000 | Taipei | github.com/example" in text
    assert "Barco, Kortrijk\tMar 2019 – Present" in text
    assert "FTDI\t2014 – Jun 2018" in text
    assert "Integrated WGC, 48-hour long run stable." in text
    assert "Languages\tC++, Python" in text
    assert "NTU\t2008 – 2010" in text
    assert "M.S., Electrical Engineering" in text
    assert "Java Programmer, Sun" in text
    assert "English (Fluent)" in text
    assert "{{" not in text and "{%" not in text


def _word_available():
    try:
        import winreg

        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "Word.Application"))
        return True
    except (ImportError, OSError):
        return False


@pytest.mark.skipif(not _word_available(), reason="Microsoft Word is not installed")
def test_render_pdf_produces_pdf(tmp_path):
    docx_path = render_docx(resume(), TEMPLATE, tmp_path / "resume.docx")
    pdf = render_pdf(docx_path, tmp_path / "resume.pdf")
    assert pdf.read_bytes().startswith(b"%PDF")


def test_achievements_tagged_do_not_use_are_not_rendered(tmp_path):
    data = resume()
    data["experience"][0]["achievements"][1]["tags"] = ["poc", "do-not-use"]
    out = render_docx(data, TEMPLATE, tmp_path / "resume.docx")
    text = "\n".join(lines(out))
    assert "Integrated WGC" in text
    assert "Replaced SIFT" not in text
