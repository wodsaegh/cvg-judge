from typing import Tuple, List

from exceptions.double_char_exceptions import *
from exceptions.double_char_exceptions import *
from dodona.translator import Translator


class DoubleChar:
    type: str
    open: str
    close: str
    is_unambiguous: bool
    _is_open: bool
    check_inside: bool
    check_in_between: bool
    line: int
    pos: int

    def __repr__(self) -> str: ...

    def create(self, is_open: bool, line: int, pos: int):
        """return new instance of DoubleChar with is_open set to the desired value"""
        ...

    def is_open(self) -> bool: ...

    def is_close(self) -> bool: ...

    def len_open(self) -> int: ...

    def len_close(self) -> int: ...

    def match_open(self, s: str) -> bool: ...

    def match_close(self, s:str) -> bool: ...


class Round(DoubleChar): ...

class Angle(DoubleChar): ...

class Curly(DoubleChar): ...

class Square(DoubleChar): ...

class Single(DoubleChar): ...

class Double(DoubleChar): ...

class HtmlComment(DoubleChar): ...

class CssComment(DoubleChar): ...


class Generator:
    ls : [DoubleChar]
    def __init__(self): ...

    def create(self, s: str, line: int, pos: int) -> Tuple[DoubleChar, str]: ...


class DoubleCharsValidator:

    translator: Translator

    def __init__(self, translator: Translator): ...

    @staticmethod
    def parse_content(s: str) -> List: ...

    def validate_content(self, text: str): ...
