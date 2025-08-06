import fitz  # PyMuPDF
import re
import uuid
import os

def is_valid_pdf(pdf_path: str) -> bool:
    """Check if the file is a valid PDF"""
    try:
        doc = fitz.open(pdf_path)
        doc.close()
        return True
    except:
        return False

def is_title(line: str) -> bool:
    """
    Uses heuristics to determine if a line is a section title.
    - Titles are generally short.
    - They often start with numbers, letters, or bullets (e.g., "1.", "A.", "(i)").
    - They are often in ALL CAPS or Title Case.
    - They do not end with a period.
    """
    stripped_line = line.strip()
    
    if not stripped_line or len(stripped_line) > 120:
        return False
        
    if stripped_line.endswith('.'):
        return False

    if re.match(r'^\s*(\d{1,2}\.|[A-Z]\.|\([a-z]\)|\([ivx]+\)|•)\s+', stripped_line):
        return True
        
    # Heuristic for short, capitalized lines likely being titles
    if len(stripped_line.split()) < 8:
        if stripped_line.isupper():
            return True
        if stripped_line.istitle():
            return True
            
    return False

def is_junk(line: str) -> bool:
    """
    Determines if a line is boilerplate junk (headers, footers, etc.).
    """
    stripped_line = line.strip().lower()
    
    if not stripped_line:
        return True

    # List of keywords that indicate a line is junk
    junk_keywords = [
        'uin:', 'irda', 'regn. no.', 'reg. no.', 'cin:', 'gstin',
        'subject matter of solicitation', 'trade logo', 'corporate office',
        'registered office', 'toll-free', 'website:', 'e-mail', '.com', '.in',
        'confidential', 'internal use'
    ]
    
    if any(keyword in stripped_line for keyword in junk_keywords):
        return True
        
    if re.search(r'^(page\s*\d+|\d+\s*of\s*\d+)$', stripped_line):
        return True
        
    return False

def extract_structured_sections(pdf_path: str) -> list[dict]:
    """
    Extract structured sections from a PDF document.
    Returns a list of dictionaries containing section information.
    """
    structured_data = []
    doc = fitz.open(pdf_path)

    for page_num, page in enumerate(doc):
        current_title = "General Information"  # Default title for text before the first heading
        current_text_block = ""
        
        text = page.get_text("text")
        lines = text.split('\n')
        
        for line in lines:
            if is_title(line):
                # When we find a new title, the previous section is complete.
                # Save the completed section before starting a new one.
                if current_text_block.strip():
                    structured_data.append({
                        "id": str(uuid.uuid4()),
                        "page_number": page_num + 1,
                        "title": current_title,
                        "text": " ".join(current_text_block.split()),  # Normalize whitespace
                        "source": pdf_path
                    })
                
                # Start the new section
                current_title = line.strip()
                current_text_block = ""
            elif not is_junk(line):
                # If the line is not a title and not junk, it's content.
                current_text_block += " " + line.strip()

        # After the loop, save the last section from the page
        if current_text_block.strip():
            structured_data.append({
                "id": str(uuid.uuid4()),
                "page_number": page_num + 1,
                "title": current_title,
                "text": " ".join(current_text_block.split()),
                "source": pdf_path
            })
    
    doc.close()
    return structured_data
