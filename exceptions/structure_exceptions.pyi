from dodona.translator import Translator
from exceptions.utils import FeedbackException


class NotTheSame(FeedbackException):
    def __init__(self, trans: Translator, msg: str, line: int, pos: int):
        ...