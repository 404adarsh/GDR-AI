"""File system operations and document inspection tools.
Supports text files, semantic search, PDFs, DOCX, and Excel spreadsheets.
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from gdr.tools.registry import tool
from gdr.safety.untrusted import wrap_untrusted_content


@tool(name="list_directory", description="List files and folders in a directory.", category="files", tier="AUTO")
def list_directory(path: str = ".") -> str:
    p = Path(os.path.expanduser(path)).resolve()
    if not p.exists():
        return f"Error: Path '{p}' does not exist."
    if not p.is_dir():
        return f"Error: Path '{p}' is not a directory."

    items = []
    try:
        for entry in sorted(p.iterdir()):
            kind = "📁 [DIR] " if entry.is_dir() else "📄 [FILE]"
            size = f"{entry.stat().st_size:,} bytes" if entry.is_file() else ""
            items.append(f"{kind} {entry.name:<30} {size}")
        return "\n".join(items) if items else "(Empty directory)"
    except Exception as e:
        return f"Error listing directory: {e}"


@tool(name="read_file", description="Read content from a text file with line numbers.", category="files", tier="AUTO")
def read_file(path: str, max_lines: int = 500) -> str:
    p = Path(os.path.expanduser(path)).resolve()
    if not p.exists():
        return f"Error: File '{p}' does not exist."
    if not p.is_file():
        return f"Error: '{p}' is not a regular file."

    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            lines = [f.readline() for _ in range(max_lines)]
        content = "".join(f"{i+1:4d} | {line}" for i, line in enumerate(lines))
        return wrap_untrusted_content(f"file ({p.name})", content)
    except Exception as e:
        return f"Error reading file: {e}"


@tool(name="write_file", description="Write text content to a file.", category="files", tier="AUTO")
def write_file(path: str, content: str) -> str:
    p = Path(os.path.expanduser(path)).resolve()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to {p}."
    except Exception as e:
        return f"Error writing to file: {e}"


@tool(name="append_file", description="Append text to an existing file.", category="files", tier="AUTO")
def append_file(path: str, content: str) -> str:
    p = Path(os.path.expanduser(path)).resolve()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully appended to {p}."
    except Exception as e:
        return f"Error appending to file: {e}"


@tool(name="delete_file", description="Delete a file from disk. Requires APPROVAL.", category="files", tier="APPROVAL", requires_approval=True)
def delete_file(path: str) -> str:
    p = Path(os.path.expanduser(path)).resolve()
    if not p.exists():
        return f"File '{p}' does not exist."
    try:
        if p.is_dir():
            return f"Error: '{p}' is a directory. Refusing recursive deletion."
        p.unlink()
        return f"Successfully deleted {p}."
    except Exception as e:
        return f"Error deleting file: {e}"


@tool(name="read_document", description="Read PDF, DOCX, or Excel (XLSX) documents.", category="files", tier="AUTO")
def read_document(path: str) -> str:
    p = Path(os.path.expanduser(path)).resolve()
    if not p.exists():
        return f"Error: File '{p}' does not exist."

    suffix = p.suffix.lower()
    text = ""
    try:
        if suffix == ".pdf":
            import pypdf
            reader = pypdf.PdfReader(str(p))
            extracted = []
            for i, page in enumerate(reader.pages[:25]):  # limit to 25 pages
                extracted.append(f"--- Page {i+1} ---\n" + (page.extract_text() or ""))
            text = "\n\n".join(extracted)

        elif suffix in (".docx", ".doc"):
            import docx
            doc = docx.Document(str(p))
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())

        elif suffix in (".xlsx", ".xls"):
            import openpyxl
            wb = openpyxl.load_workbook(str(p), data_only=True)
            sheet_texts = []
            for sheet_name in wb.sheetnames[:5]:
                sheet = wb[sheet_name]
                rows = []
                for row in sheet.iter_rows(max_row=50, values_only=True):
                    row_vals = [str(c) if c is not None else "" for c in row]
                    if any(row_vals):
                        rows.append("\t".join(row_vals))
                sheet_texts.append(f"Sheet: {sheet_name}\n" + "\n".join(rows))
            text = "\n\n".join(sheet_texts)
        else:
            return f"Unsupported document format: {suffix}. Supported: .pdf, .docx, .xlsx"

        return wrap_untrusted_content(f"document ({p.name})", text)
    except Exception as e:
        return f"Error reading document '{p}': {e}"

