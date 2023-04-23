from typing import List

from dodona.translator import Translator


class FeedbackException(Exception):
    msg: str
    line: int
    pos: int
    trans: Translator

    def __init__(self, trans: Translator, msg: str, line: int, pos: int, *args): ...

    def __str__(self) -> str: ...

    def message_str(self) -> str:
        """Create the message that should be displayed in the Dodona Tab"""
        ...

    def annotation_str(self) -> str:
        """Create the message that should be displayed in the annotation in the Code Tab"""
        ...


class EvaluationAborted(RuntimeError):
    def __init__(self, *args): ...


class InvalidTranslation(ValueError):
    def __init__(self, *args): ...


class DelayedExceptions(FeedbackException):
    exceptions: List[FeedbackException]

    def __init__(self): ...

    def __len__(self) -> int: ...

    def __bool__(self) -> bool: ...

    def add(self, exception: FeedbackException): ...

    def clear(self): ...

    def _print_exceptions(self) -> str: ...

