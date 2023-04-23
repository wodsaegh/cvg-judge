from typing import Optional, Dict, List, Tuple

from bs4.element import Tag
from lxml.etree import ElementBase
from tinycss2.ast import Declaration

from utils.color_converter import Color


def strip(ls: List) -> List: ...


class CssParsingError(Exception):
    pass


def _get_xpath(selector: str) -> str: ...


class Rule:
    selector: List
    selector_str: str
    xpath: str
    pseudo: Optional[str]
    name: str
    value: List
    important: bool
    specificity: Tuple[int, int, int]
    value_str: str
    color: Optional[Color]

    def __init__(self, selector: List, content: Declaration): ...

    def __repr__(self) -> str: ...

    def is_color(self) -> bool: ...

    def has_color(self, color: str) -> bool: ...

    def compare_to(self, value: Optional[str] = None, important: Optional[bool] = None, any_order: bool = False) -> bool: ...



def calc_specificity(selector_str: str) -> Tuple[int, int, int]:  ...

class Rules:
    root: ElementBase
    rules: List
    map: Dict

    def __init__(self, css_content: str): ...

    def __repr__(self) -> str: ...

    def __len__(self) -> int: ...

    def find(self, root: ElementBase, solution_element: ElementBase, key: str, pseudo: Optional[str]) -> Optional[Rule]: ...

    def find_all(self, root: ElementBase, solution_element: ElementBase) -> Dict[str, Rule]: ...

    def find_by_css_selector(self, css_selector: str, key: str) -> Optional[Rule]: ...


class AmbiguousXpath(Exception):
    pass


class ElementNotFound(Exception):
    pass


class CssValidator:
    root: Optional[ElementBase]
    rules: Rules
    xpaths: Dict

    def __init__(self, html: str): ...
    
    def __bool__(self): ...

    def get_xpath_soup(self, element: Tag) -> str: ...

    def _get_xpath_soup(self, element: Tag) -> str: ...

    def find(self, element: Tag, key: str, pseudo: Optional[str] = None) -> Optional[Rule]: ...

    def find_by_css_selector(self, css_selector: str, key: str) -> Optional[Rule]: ...
