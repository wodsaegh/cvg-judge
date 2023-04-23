
from dodona.translator import Translator
from exceptions.utils import DelayedExceptions, FeedbackException


class HtmlValidationError(FeedbackException):
    """Base class for HTML related exceptions in this module."""
    def __init__(self, trans: Translator, msg: str, line: int, pos: int):
        super(HtmlValidationError, self).__init__(trans=trans, msg=msg, line=line, pos=pos)


class LocatableHtmlValidationError(HtmlValidationError):
    """Exceptions that can be located"""
    def __init__(self, trans: Translator, msg: str, line: int, pos: int):
        super(LocatableHtmlValidationError, self).__init__(trans=trans, msg=msg, line=line, pos=pos)


"""
EXCEPTIONS FOR TAGS
"""


class MissingOpeningTagError(LocatableHtmlValidationError):
    """Exception that indicates that the opening tag is missing for a tag"""
    def __init__(self, trans: Translator, tag: str, line: int, pos: int):
        msg = f"{trans.translate(Translator.Text.MISSING_OPENING_TAG)} <{tag}>"
        super(MissingOpeningTagError, self).__init__(trans=trans, msg=msg, line=line, pos=pos)



class MissingClosingTagError(LocatableHtmlValidationError):
    """Exception that indicates that the closing tag is missing for a tag"""
    def __init__(self, trans: Translator, tag: str, line: int, pos: int):
        msg = f"{trans.translate(Translator.Text.MISSING_CLOSING_TAG)} <{tag}>"
        super(MissingClosingTagError, self).__init__(trans=trans, msg=msg, line=line, pos=pos)


class InvalidTagError(LocatableHtmlValidationError):
    """Exception that indicates that a tag is invalid (tag doesn't exist or isn't allowed to be used"""
    def __init__(self, trans: Translator, tag: str, line: int, pos: int):
        msg = f"{trans.translate(Translator.Text.INVALID_TAG)}: <{tag}>"
        super(InvalidTagError, self).__init__(trans=trans, msg=msg, line=line, pos=pos)


class NoSelfClosingTagError(LocatableHtmlValidationError):
    def __init__(self, trans: Translator, tag: str, line: int, pos: int):
        msg = f"{trans.translate(Translator.Text.NO_SELF_CLOSING_TAG)}: <{tag}>"
        super(NoSelfClosingTagError, self).__init__(trans=trans, msg=msg, line=line, pos=pos)


class UnexpectedTagError(LocatableHtmlValidationError):
    """Exception that indicates that a certain tag was not expected
        ex: you don't expect a <html> tag inside of a <body> tag
    """
    def __init__(self, trans: Translator, tag: str, line: int, pos: int):
        msg = f"{trans.translate(Translator.Text.UNEXPECTED_TAG)}: <{tag}>"
        super(UnexpectedTagError, self).__init__(trans=trans, msg=msg, line=line, pos=pos)


class UnexpectedClosingTagError(LocatableHtmlValidationError):
    """Exception that indicates that a certain tag was not expected to have a closing tag
        ex: you don't expect an <img> tag to have a </img> closer later on
    """
    def __init__(self, trans: Translator, tag: str, line: int, pos: int):
        msg = f"{trans.translate(Translator.Text.UNEXPECTED_CLOSING_TAG, tag=tag)}"
        super(UnexpectedClosingTagError, self).__init__(trans=trans, msg=msg, line=line, pos=pos)


"""
EXCEPTIONS FOR ATTRIBUTES
"""


class InvalidAttributeError(LocatableHtmlValidationError):
    """Exception that indicates that an attribute is invalid for a tag"""
    def __init__(self, trans: Translator, tag: str, attribute: str, line: int, pos: int):
        msg = f"{trans.translate(Translator.Text.INVALID_ATTRIBUTE)} <{tag}>: " \
               f"{attribute}"
        super(InvalidAttributeError, self).__init__(trans=trans, msg=msg, line=line, pos=pos)


class MissingRequiredAttributesError(LocatableHtmlValidationError):
    """Exception that indicates that a required attribute for a tag is missing"""
    def __init__(self, trans: Translator, tag: str, attribute: str, line: int, pos: int):
        msg = f"{trans.translate(Translator.Text.MISSING_REQUIRED_ATTRIBUTE)} <{tag}>: " \
               f"{attribute}"
        super(MissingRequiredAttributesError, self).__init__(trans=trans, msg=msg, line=line, pos=pos)


class DuplicateIdError(LocatableHtmlValidationError):
    """Exception that indicates that an id is used twice"""
    def __init__(self, trans: Translator, tag: str, attribute: str, line: int, pos: int):
        msg = f"{trans.translate(Translator.Text.DUPLICATE_ID, id=attribute, tag=tag)}"
        super(DuplicateIdError, self).__init__(trans=trans, msg=msg, line=line, pos=pos)


class AttributeValueError(LocatableHtmlValidationError):
    def __init__(self, trans: Translator, msg: str, line: int, pos: int):
        super(AttributeValueError, self).__init__(trans=trans, msg=msg, line=line, pos=pos)


class MissingRecommendedAttributesWarning(LocatableHtmlValidationError):
    """Exception that indicates that a recommended attribute is missing
            this is considered a warning, and all instances of this class will be
            gathered and thrown at the very end if no other exceptions appear
    """
    def __init__(self, trans: Translator, tag: str, attribute: str, line: int, pos: int):
        msg = f"{trans.translate(Translator.Text.MISSING_RECOMMENDED_ATTRIBUTE)} <{tag}>: " \
               f"{attribute}"
        super(MissingRecommendedAttributesWarning, self).__init__(trans=trans, msg=msg, line=line, pos=pos)


class Warnings(DelayedExceptions):
    def __init__(self, translator: Translator):
        super().__init__()
        self.translator = translator
        self.exceptions: [LocatableHtmlValidationError]  # makes them sortable

    def __str__(self):
        self.exceptions.sort(key=lambda x: (x.line, x.pos))
        return f"{self.translator.translate(Translator.Text.WARNINGS)} ({len(self)}):\n{self._print_exceptions()}"
