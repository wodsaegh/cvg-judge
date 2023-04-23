from typing import List

from dodona.translator import Translator
from exceptions.utils import DelayedExceptions, FeedbackException


class HtmlValidationError(FeedbackException):
    def __init__(self, trans: Translator, msg: str, line: int, pos: int):
        ...

class LocatableHtmlValidationError(HtmlValidationError):
    def __init__(self, trans: Translator, msg: str, line: int, pos: int):
        ...

class MissingOpeningTagError(LocatableHtmlValidationError):
    def __init__(self, trans: Translator, tag: str, line: int, pos: int):
        ...

class MissingClosingTagError(LocatableHtmlValidationError):
    def __init__(self, trans: Translator, tag: str, line: int, pos: int):
        ...

class InvalidTagError(LocatableHtmlValidationError):
    def __init__(self, trans: Translator, tag: str, line: int, pos: int):
        ...

class NoSelfClosingTagError(LocatableHtmlValidationError):
    def __init__(self, trans: Translator, tag: str, line: int, pos: int):
        ...

class UnexpectedTagError(LocatableHtmlValidationError):
    def __init__(self, trans: Translator, tag: str, line: int, pos: int):
        ...

class UnexpectedClosingTagError(LocatableHtmlValidationError):
    def __init__(self, trans: Translator, tag: str, line: int, pos: int):
        ...


class InvalidAttributeError(LocatableHtmlValidationError):
    def __init__(self, trans: Translator, tag: str, attribute: str, line: int, pos: int):
        ...


class MissingRequiredAttributesError(LocatableHtmlValidationError):
    def __init__(self, trans: Translator, tag: str, attribute: str, line: int, pos: int):
        ...

class DuplicateIdError(LocatableHtmlValidationError):
    def __init__(self, trans: Translator, tag: str, attribute: str, line: int, pos: int):
        ...

class AttributeValueError(LocatableHtmlValidationError):
    def __init__(self, trans: Translator, msg: str, line: int, pos: int):
        ...

class MissingRecommendedAttributesWarning(LocatableHtmlValidationError):
    def __init__(self, trans: Translator, tag: str, attribute: str, line: int, pos: int):
        ...

class Warnings(DelayedExceptions):
    translator: Translator
    exceptions: List[LocatableHtmlValidationError]

    def __init__(self, translator: Translator): ...

    def __str__(self): ...