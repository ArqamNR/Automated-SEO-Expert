import os
import re
import fitz as pymupdf
from langchain_core.documents import Document

def extract_pdf_text(path):
    doc = pymupdf.open(path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def extract_health_checks(text):
    """
    Extracts health check blocks in the format:
    Health Check: NAME
    Issues to look for: ...
    Impact: ...
    """
    # Regex matches one block starting with Health Check
    pattern = r"(Health Check[:\-–]?\s*.*?(?=Health Check[:\-–]?|\Z))"
    matches = re.findall(pattern, text, re.DOTALL)

    docs = []
    for match in matches:
        docs.append({
            "content": match.strip()
        })
    print(docs[0])
    return docs

def process_pdfs_in_directory(pdf_dir):
    all_docs = []
    for filename in os.listdir(pdf_dir):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(pdf_dir, filename)
            raw_text = extract_pdf_text(pdf_path)
            blocks = extract_health_checks(raw_text)

            lc_docs = [
                Document(
                    page_content=item['content'],
                    metadata={"source": filename}
                )
                for item in blocks
            ]
            print(lc_docs)
            all_docs.extend(lc_docs)
    return all_docs

# Example usage
docs = process_pdfs_in_directory('Health Checks')