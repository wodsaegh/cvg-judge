"""
util file with functions to load specific types of files
"""


def html_loader(file_path: str, **kwargs) -> str:
    """Utility function to load a HTML file in order to use the content
    param file_path: the full path to the file
    kwargs:
        param: wrap_head=True => wraps the content in a <head> tag
        param: wrap_body=True => wraps the content in a <body> tag
        param: wrap_html=True => wraps the content in a <html> tag
        param: shorted=False => dont extend the path with .html (default is True)
    """
    # Allow only the name to be passed (shorter)
    if kwargs.get("shorted", True) and not file_path.endswith(".html"):
        file_path += ".html"

    with open(file_path, "r") as file:
        content = file.read()

        if kwargs.get("wrap_head", False):
            content = f"<head>{content}<head>"

        if kwargs.get("wrap_body", False):
            content = f"<body>{content}<body>"

        if kwargs.get("wrap_html", False):
            content = f"<html lang='en'>{content}<html>"

        return content


def json_loader(file_path: str, **kwargs) -> dict:
    """Utility function to load a JSON file in order to use the content
        param file_path: the full path to the file
        kwargs:
            param: shorted=False => dont extend the path with .html (default is True)

    """
    # Allow only the name to be passed (shorter)
    if kwargs.get("shorted", True) and not file_path.endswith(".json"):
        file_path += ".json"

    with open(file_path, "r") as f:
        import json
        return json.load(f)
