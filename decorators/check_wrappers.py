from bs4 import BeautifulSoup


def fail():
    """Return a Check that always fails"""
    # Local import to avoid circular dependencies
    from validators.checks import Check

    def _inner(_: BeautifulSoup) -> bool:
        return False

    return Check(_inner)


def html_check(func):
    """Decorator that checks if an HTML element is not None"""
    def wrapper(*args, **kwargs):
        if args[0]._element is None:
            return fail()

        return func(*args, **kwargs)

    return wrapper


def css_check(func):
    """Decorator that checks if an element's HTML tag and CSS validator are not None"""
    def wrapper(*args, **kwargs):
        if args[0]._element is None or args[0]._css_validator is None:
            return fail()

        return func(*args, **kwargs)

    return wrapper
