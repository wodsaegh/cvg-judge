from dodona.translator import Translator
from exceptions.utils import DelayedExceptions, FeedbackException


class DoubleCharError(FeedbackException):
    """Base class for double char related exceptions in this module."""
    def __init__(self, trans: Translator, msg: str, line: int = -1, pos: int = -1):
        ...


class LocatableDoubleCharError(FeedbackException):

    def __init__(self, trans: Translator, msg: str, line: int, pos: int):
        ...

    def __lt__(self, other) -> bool: ...

    def __gt__(self, other) -> bool: ...

    def __le__(self, other) -> bool: ...

    def __ge__(self, other) -> bool: ...

    def __eq__(self, other) -> bool: ...

    def __ne__(self, other) -> bool: ...


class MissingOpeningCharError(LocatableDoubleCharError):
    def __init__(self, trans: Translator, char: str, line: int, pos: int):
        ...

class MissingClosingCharError(LocatableDoubleCharError):
    def __init__(self, trans: Translator, char: str, line: int, pos: int):
        ...

class MultipleMissingCharsError(DelayedExceptions):
    translator: Translator

    def __init__(self, translator: Translator): ...

    def __str__(self) -> str: ...
