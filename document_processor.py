import pymupdf


def extract_text(uploaded_file):
    """Extract text from TXT and PDF business documents."""

    file_name = uploaded_file.name.lower()

    # Read TXT files
    if file_name.endswith(".txt"):
        content = uploaded_file.getvalue()
        return content.decode("utf-8", errors="replace")

    # Read PDF files
    elif file_name.endswith(".pdf"):
        pdf_bytes = uploaded_file.getvalue()

        with pymupdf.open(
            stream=pdf_bytes,
            filetype="pdf"
        ) as document:

            text = ""

            for page in document:
                text += page.get_text() + "\n"

        return text.strip()

    else:
        raise ValueError("Unsupported file type. Upload TXT or PDF.")