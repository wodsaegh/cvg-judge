from bs4 import BeautifulSoup


def is_empty_document(document: str) -> bool:
    """Check if a document is empty, not allowing comments"""
    document = document.strip()

    # Completely empty (barring whitespace)
    if not document:
        return True

    try:
        parsed = BeautifulSoup(document, "html.parser")
    except Exception:
        # The document was not empty, but it also wasn't valid
        # the HTML validator should catch this and warn about it, ignore it here
        return False

    # Find() doesn't return comments by default, so if None comes out of this
    # then we know that there's no content in the document
    return parsed.find() is None
