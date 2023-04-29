"""Basic checking library to create evaluation tests for exercises"""
import re
from collections import deque
from copy import copy
from dataclasses import dataclass, field
from typing import Deque, List, Optional, Callable, Union, Dict, TypeVar, Iterable, Iterator
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString

from decorators import flatten_varargs, html_check, css_check
from dodona.dodona_command import Context, TestCase, Message, MessageFormat, SafeAnnotation
from dodona.dodona_config import DodonaConfig
from dodona.translator import Translator
from exceptions.double_char_exceptions import MultipleMissingCharsError, LocatableDoubleCharError
from exceptions.html_exceptions import Warnings, LocatableHtmlValidationError
from exceptions.utils import EvaluationAborted
from utils.flatten import flatten_queue
from utils.html_navigation import find_child, compare_content, match_emmet, find_emmet, contains_comment
from utils.regexes import doctype_re
from validators.css_validator import CssValidator, CssParsingError, Rule, AmbiguousXpath, ElementNotFound
from validators.html_validator import HtmlValidator
import ast

# Custom type hints
Emmet = TypeVar("Emmet", bound=str)
Checks = TypeVar("Checks", bound=Union["Check", Iterable["Check"]])


@dataclass
class Check:
    """Class that represents a single check

    Attributes:
        callback    The function to run in order to perform this test.
        on_success  A list of checks that will only be performed in case this
                    check succeeds. An example of how this could be useful is to
                    first test if an element exists and THEN perform extra checks
                    on its attributes and/or children. This avoids unnecessary spam
                    to the user, because an element that doesn't exist never has
                    the correct specifications.
    """
    callback: Callable[[BeautifulSoup], bool]
    on_success: List["Check"] = field(default_factory=list)
    abort_on_fail: bool = False

    def _find_deepest_nested(self) -> "Check":
        """Find the deepest Check nested with on_success chains"""
        current_deepest = self.on_success[-1]

        # Keep going until the current one no longer contains anything
        while current_deepest.on_success:
            current_deepest = current_deepest.on_success[-1]

        return current_deepest

    def or_abort(self) -> "Check":
        """Prevent the next tests from running if this one fails
        Can be used when a test is necessary for the rest to continue, for example
        the HTML-validation step.
        """
        self.abort_on_fail = True
        return self

    def is_crucial(self) -> "Check":
        """Alias to or_abort()"""
        return self.or_abort()

    @flatten_varargs
    def then(self, *args: Checks) -> "Check":
        """Register a list of checks to perform in case this check succeeds
        When this check already has checks registered, try to find the deepest check
        and append it to that check. The reasoning is that x.then(y).then(z) suggests y should
        complete for z to start. This makes the overall use more fluent and avoids
        a big mess of brackets when it's not necessary at all.

        Returns a reference to itself to allow a fluent interface.
        """
        if not self.on_success:
            self.on_success = list(args)
        else:
            # Find the deepest child check and add to that one
            deepest: "Check" = self._find_deepest_nested()
            deepest.on_success = list(args)

        return self


@dataclass
class Element:
    """Class for an HTML element used in testing

    Attributes:
        tag         The HTML tag of this element.
        id          An optional id to specify when searching for the element,
                    if not specified then the first result found will be used.
        _element    The inner HTML element that was matched in the document,
                    can be None if nothing was found.
    """
    tag: str
    id: Optional[str] = None
    _element: Optional[Tag] = None
    _css_validator: Optional[CssValidator] = None

    def __str__(self):
        if self.id is not None:
            return f"<{self.tag} id={self.id}>"

        return f"<{self.tag}>"

    # HTML utilities
    def get_child(self, tag: Optional[Union[str, Emmet]] = None, index: int = 0, direct: bool = True, **kwargs) -> "Element":
        """Find the child element that matches the specifications

        :param tag:     the tag to search for
        :param index:   in case multiple children are found, specify the index to fetch
                        if not enough children were found, return an EmptyElement
        :param direct:  indicate that only direct children should be considered
        """
        child = find_child(self._element, tag=tag,
                           index=index, from_root=direct, **kwargs)

        if child is None:
            return EmptyElement()

        return Element(child.name, child.get("id", None), child, self._css_validator)

    def get_children(self, tag: Optional[Union[str, Emmet]] = None, direct: bool = True, **kwargs) -> "ElementContainer":
        """Get all children of this element that match the requested input"""
        # This element doesn't exist so it has no children
        if self._element is None:
            return ElementContainer([])

        # Emmet syntax requested
        if match_emmet(tag):
            # Index parameter is not relevant here & it won't be used anyways
            matches = find_emmet(
                self._element, tag, 0, from_root=direct, match_multiple=True, **kwargs)

            # Nothing found
            if matches is None:
                return ElementContainer([])
        elif tag is not None:
            # If a tag was specified, only search for those
            matches = self._element.find_all(
                tag, recursive=not direct, **kwargs)
        else:
            # Otherwise, use all children instead
            matches = self._element.children if direct else self._element.descendants

            # Filter out string content
            matches = list(filter(lambda x: isinstance(x, Tag), matches))

        return ElementContainer.from_tags(matches, self._css_validator)

    # HTML checks
    def exists(self) -> Check:
        """Check that this element was found"""

        def _inner(_: BeautifulSoup) -> bool:
            return self._element is not None

        return Check(_inner)

    @html_check
    def has_child(self, tag: Optional[Union[str, Emmet]] = None, direct: bool = True, **kwargs) -> Check:
        """Check that this element has a child with the given tag

        :param tag:     the tag to search for
        :param direct:  indicate that only direct children should be considered,
                        not children of children
        """
        def _inner(_: BeautifulSoup) -> bool:
            child = find_child(self._element, tag=tag,
                               from_root=direct, **kwargs)
            return child is not None

        return Check(_inner)

    def has_parent(self, tag: str, direct: bool = True, **kwargs) -> Check:
        """Check that this element has a parent with the given tag"""
        def _inner(_: BeautifulSoup) -> bool:
            if self._element is None:
                return False

            first_matching_parent = self._element.find_parent(
                name=tag, **kwargs)

            # No parents matched
            if first_matching_parent is None:
                return False

            if not direct:
                # Not direct, any matching parent will do
                # we already have one (found above) so we can return True here
                return True

            # Get direct parent
            direct_parent = self._element.find_parent()

            # No parents found
            # shouldn't happen, but just in case
            if direct_parent is None:
                return False

            # Check if the direct parent is the same as the first parent that matched
            # Using eq should be safe here because different levels of parents should have
            # different child elements
            return first_matching_parent == direct_parent

        return Check(_inner)

    @html_check
    def has_content(self, text: Optional[str] = None, case_insensitive: bool = False) -> Check:
        """Check if this element has given text as content.
        In case no text is passed, any non-empty string will make the test pass

        Example:
        >>> suite = TestSuite("<p>This is some text</p>")
        >>> element = suite.element("p")
        >>> element.has_content()
        True
        >>> element.has_content("This is some text")
        True
        >>> element.has_content("Something else")
        False
        """

        def _inner(_: BeautifulSoup) -> bool:
            # No text in this element
            if self._element.text is None or len(self._element.text) == 0:
                return False

            if text is not None:
                return compare_content(self._element.text, text, case_insensitive)

            return len(self._element.text.strip()) > 0

        return Check(_inner)

    def _has_tag(self, tag: str) -> bool:
        """Internal function that checks if this element has the required tag"""
        return self._element.name.lower() == tag.lower()

    @html_check
    def has_tag(self, tag: str) -> Check:
        """Check that this element has the required tag"""

        def _inner(_: BeautifulSoup) -> bool:
            return self._has_tag(tag)

        return Check(_inner)

    @html_check
    def no_loose_text(self) -> Check:
        """Check that there is no content floating around in this tag"""

        def _inner(_: BeautifulSoup) -> bool:
            children = self._element.children

            for child in children:
                # Child is a text instance which is not allowed
                # Empty tags shouldn't count as text, but for some reason bs4
                # still picks these up so they're filtered out as well
                if isinstance(child, NavigableString) and child.text.strip():
                    return False

            return True

        return Check(_inner)

    def _get_attribute(self, attr: str) -> Optional[Union[List[str], str]]:
        """Internal function that gets an attribute"""
        attribute = self._element.get(attr.lower())

        return attribute

    def _compare_attribute_list(self, attribute: List[str], value: Optional[str] = None,
                                case_insensitive: bool = False,
                                mode: int = 0, flags: Union[int, re.RegexFlag] = 0) -> bool:
        """Attribute check for attributes that contain lists (eg. Class). Can handle all 3 modes.
        0: exact match (exists)
        1: substring (contains)
        2: regex match (matches)
        """
        # Attribute doesn't exist
        if not attribute:
            return False

        # Any value is good enough
        if value is None:
            return True

        if case_insensitive:
            value = value.lower()
            attribute = list(map(lambda x: x.lower(), attribute))

        # Exact match
        if mode == 0:
            return value in attribute

        # Contains substring
        if mode == 1:
            return any(value in v for v in attribute)

        # Match regex
        if mode == 2:
            for v in attribute:
                if re.search(value, v, flags) is not None:
                    return True

            return False

        # Possible future modes
        return False

    @html_check
    def attribute_exists(self, attr: str, value: Optional[str] = None, case_insensitive: bool = False) -> Check:
        """Check that this element has the required attribute, optionally with a value
        :param attr:                The name of the attribute to check.
        :param value:               The value to check. If no value is passed, this will not be checked.
        :param case_insensitive:    Indicate that the casing of the attribute does not matter.
        """

        def _inner(_: BeautifulSoup) -> bool:
            attribute = self._get_attribute(attr)

            # Attribute wasn't found
            if attribute is None:
                return False

            if isinstance(attribute, list):
                return self._compare_attribute_list(attribute, value, case_insensitive, mode=0)

            # No value specified
            if value is None:
                return True

            if case_insensitive:
                return attribute.lower() == value.lower()

            return attribute == value

        return Check(_inner)

    @html_check
    def attribute_contains(self, attr: str, substr: str, case_insensitive: bool = False) -> Check:
        """Check that the value of this attribute contains a substring"""

        def _inner(_: BeautifulSoup) -> bool:
            attribute = self._get_attribute(attr)

            # Attribute wasn't found
            if attribute is None:
                return False

            if isinstance(attribute, list):
                return self._compare_attribute_list(attribute, substr, case_insensitive, mode=1)

            if case_insensitive:
                return substr.lower() in attribute.lower()

            return substr in attribute

        return Check(_inner)

    @html_check
    def attribute_matches(self, attr: str, regex: str, flags: Union[int, re.RegexFlag] = 0) -> Check:
        """Check that the value of an attribute matches a regex pattern"""

        def _inner(_: BeautifulSoup) -> bool:
            attribute = self._get_attribute(attr)

            # Attribute wasn't found
            if attribute is None:
                return False

            if isinstance(attribute, list):
                return self._compare_attribute_list(attribute, regex, mode=2, flags=flags)

            return re.search(regex, attribute, flags) is not None

        return Check(_inner)

    @html_check
    def has_table_header(self, header: List[str]) -> Check:
        """If this element is a table, check that the header content matches up"""

        def _inner(_: BeautifulSoup) -> bool:
            # This element is not a table
            if not self._has_tag("table"):
                return False

            # List of all headers in this table
            ths = self._element.find_all("th")

            # Not the same amount of headers
            if len(ths) != len(header):
                return False

            # Check if all headers have the same content in the same order
            for i in range(len(header)):
                if not compare_content(header[i], ths[i].text):
                    return False

            return True

        return Check(_inner)

    @html_check
    def has_table_content(self, rows: List[List[str]], has_header: bool = True, case_insensitive: bool = False) -> Check:
        """Check that a table's rows have the requested content
        :param rows:                The data of all the rows to check
        :param has_header:          Boolean that indicates that this table has a header,
                                    so the first row will be ignored (!)
        :param case_insensitive:    Indicate that comparison should ignore casing or not
        """

        def _inner(_: BeautifulSoup) -> bool:
            # This element is not a table
            if not self._has_tag("table"):
                return False

            trs = self._element.find_all("tr")

            # No rows found
            if not trs:
                return False

            # Cut header out
            if has_header:
                trs = trs[1:]

                # Table only had a header, no actual content
                if not trs:
                    return False

            # Incorrect amount of rows
            if len(trs) != len(rows):
                return False

            # Compare tds (actual data)
            for i in range(len(rows)):
                data = trs[i].find_all("td")

                # Row doesn't have the same amount of tds
                if len(data) != len(rows[i]):
                    return False

                # Compare content
                for j in range(len(rows[i])):
                    # Content doesn't match
                    if not compare_content(data[j].text, rows[i][j], case_insensitive):
                        return False

            return True

        return Check(_inner)

    @html_check
    def table_row_has_content(self, row: List[str], case_insensitive: bool = False) -> Check:
        """Check the content of one row instead of the whole table"""

        def _inner(_: BeautifulSoup) -> bool:
            # Check that this element is a <tr>
            if not self._has_tag("tr"):
                return False

            tds = self._element.find_all("td")

            # Amount of items doesn't match up
            if len(tds) != len(row):
                return False

            for i in range(len(row)):
                # Text doesn't match
                if not compare_content(row[i], tds[i].text, case_insensitive):
                    return False

            return True

        return Check(_inner)

    @html_check
    def has_url_with_fragment(self, fragment: Optional[str] = None) -> Check:
        """Check if a url has a fragment
        If no fragment is passed, any non-empty fragment will do
        """

        def _inner(_: BeautifulSoup) -> bool:
            if not self._has_tag("a"):
                return False

            url = self._get_attribute("href")

            # No url present
            if url is None:
                return False

            split = urlsplit(url)

            # No fragment present
            if not split.fragment:
                return False

            # No value required
            if fragment is None:
                return True

            return fragment == split.fragment

        return Check(_inner)

    @html_check
    def has_outgoing_url(self, allowed_domains: Optional[List[str]] = None, attr: str = "href") -> Check:
        """Check if a tag has an outgoing link
        :param allowed_domains: A list of domains that should not be considered "outgoing",
                                defaults to ["dodona.ugent.be", "users.ugent.be"]
        :param attr:            The attribute the link should be in
        """
        if allowed_domains is None:
            allowed_domains = ["dodona.ugent.be", "users.ugent.be"]

        def _inner(_: BeautifulSoup) -> bool:
            url = self._get_attribute(attr.lower())

            # No url present
            if url is None:
                return False

            spl = urlsplit(url)

            if spl.netloc:
                # Ignore www. in the start to allow the arguments to be shorter
                netloc = spl.netloc.lower().removeprefix("www.")
                return netloc not in list(map(lambda x: x.lower(), allowed_domains))

            return False

        return Check(_inner)

    @html_check
    def contains_comment(self, comment: Optional[str] = None) -> Check:
        """Check if the element contains a comment, optionally matching a value"""

        def _inner(_: BeautifulSoup) -> bool:
            return contains_comment(self._element, comment)

        return Check(_inner)

    # CSS checks
    def _find_css_property(self, prop: str, inherit: bool, pseudo: Optional[str] = None) -> Optional[Rule]:
        """Find a css property recursively if necessary
        Properties by parent elements are applied onto their children, so
        an element can inherit a property from its parent
        """
        prop = prop.lower()

        # Inheritance is not allowed
        if not inherit:
            return self._css_validator.find(self._element, prop, pseudo)

        current_element = self._element
        prop_value = None

        # Keep going higher up the tree until a match is found
        while prop_value is None and current_element is not None:
            # Check if the current element has this rule & applies it onto the child
            prop_value = self._css_validator.find(
                current_element, prop, pseudo)

            if prop_value is None:
                parents = current_element.find_parents()

                # find_parents() always returns the entire document as well,
                # even when the current element is the root
                # So at least 2 parents are required
                if len(parents) <= 2:
                    current_element = None
                else:
                    current_element = parents[0]

        return prop_value

    @css_check
    def has_styling(self, prop: str, value: Optional[str] = None, important: Optional[bool] = None, pseudo: Optional[str] = None, allow_inheritance: bool = False, any_order: bool = False) -> Check:
        """Check that this element has a CSS property
        :param prop:                the required CSS property to check
        :param value:               an optional value to add that must be checked against,
                                    in case nothing is supplied any value will pass
        :param important:           indicate that this must (or may not be) marked as important
        :param pseudo:              the css selector pseudo class to check the property for (example "hover", or "clicked")
        :param allow_inheritance:   allow a parent element to have this property and apply it onto the child
        :param any_order:           indicate that the order of the properties doesn't matter (double bar syntax for
                                    shorthand properties)
        """

        def _inner(_: BeautifulSoup) -> bool:
            prop_value = self._find_css_property(
                prop, allow_inheritance, pseudo)
            # If the property is not found, it is None
            return False if prop_value is None else prop_value.compare_to(value, important, any_order)

        return Check(_inner)

    @css_check
    def has_color(self, prop: str, color: str, important: Optional[bool] = None, pseudo: Optional[str] = None, allow_inheritance: bool = False) -> Check:
        """Check that this element has a given color
        More flexible version of has_styling because it also allows RGB(r, g, b), hex format, ...

        :param prop:                the required CSS property to check (background-color, color, ...)
        :param color:               the color to check this property's value against, in any format
        :param important:           indicate that this must (or may not be) marked as important
        :param allow_inheritance:   allow a parent element to have this property and apply it onto the child
        """

        def _inner(_: BeautifulSoup) -> bool:
            # Find the CSS Rule
            prop_rule = self._find_css_property(
                prop, allow_inheritance, pseudo)

            # Property not found
            if prop_rule is None:
                return False

            # !important modifier is incorrect
            if important is not None and prop_rule.important != important:
                return False

            return prop_rule.has_color(color)

        return Check(_inner)


@dataclass
class EmptyElement(Element):
    """Class that represents an element that could not be found"""

    def __init__(self):
        super().__init__("", None, None, None)

    def __str__(self) -> str:
        return "<EmptyElement>"


@dataclass
class ElementContainer:
    """Class used for collections of elements fetched from the HTML
    This class was made to avoid potential IndexErrors in the evaluation file
    when using indexing.

    The example below assumes that there are two <div>s in the solution in order
    to set up the checklist, but the student's current file may not have these.
    This would cause IndexErrors when parsing the file.

    By letting get_children() return this container class, we can just return an
    empty Element() object when the list doesn't have enough elements, and then
    other checks will just fail instead of crashing.
    Example:
    >>> suite = TestSuite("<body>"
    ...                     "<div id='div1'>"
    ...                         "..."
    ...                     "</div>"
    ...                     "<div id='div2'>"
    ...                         "..."
    ...                     "</div>"
    ...                   "</body>")
    >>> all_divs = suite.element("body").get_children("div")
    >>> all_divs[1].has_child("...")  # IndexError if student doesn't have this!

    Attributes:
        elements       the elements to add into this container
    """
    elements: List[Element]
    _size: int = field(init=False)

    def __post_init__(self):
        # Avoid calling len() all the time
        self._size = len(self.elements)

    def __getitem__(self, item) -> Union[Element, List[Element]]:
        if not isinstance(item, (int, slice)):
            raise TypeError(
                f"Key {item} was of type {item}, not int or slice.")

        # Out of range
        if isinstance(item, int) and item >= self._size:
            return EmptyElement()

        return self.elements[item]

    def __iter__(self) -> Iterator[Element]:
        for el in self.elements:
            yield el

    def __len__(self):
        return self._size

    @classmethod
    def from_tags(cls, tags: List[Tag], css_validator: CssValidator) -> "ElementContainer":
        """Construct a container from a list of bs4 Tag instances"""
        elements = list(map(lambda x: Element(
            x.name, x.get("id", None), x, css_validator), tags))
        return ElementContainer(elements)

    def get(self, index: int) -> Element:
        """Get an item at a given index, same as []-operator"""
        return self[index]

    def at_most(self, amount: int) -> Check:
        """Check that a container has at most [amount] elements"""

        def _inner(_: BeautifulSoup):
            return self._size <= amount

        return Check(_inner)

    def at_least(self, amount: int) -> Check:
        """Check that a container has at least [amount] elements"""

        def _inner(_: BeautifulSoup):
            return self._size >= amount

        return Check(_inner)

    def exactly(self, amount: int) -> Check:
        """Check that a container has exactly [amount] elements"""

        def _inner(_: BeautifulSoup) -> bool:
            return self._size == amount

        return Check(_inner)

    def all(self, func: Callable[[Element], Check]) -> Check:
        """Check if all elements in this container match a Check
        Requires the container to be non-empty, fails otherwise
        """
        return self.at_least(1).then(all_of(func(el) for el in self.elements))

    def any(self, func: Callable[[Element], Check]) -> Check:
        """Check if one element in this container matches a Check
        Requires the container to be non-empty, fails otherwise
        """
        return self.at_least(1).then(any_of(func(el) for el in self.elements))


@dataclass(init=False)
class ChecklistItem:
    """An item to add to the checklist

    Attributes:
        message         The message displayed on the Dodona checklist for this item
        checks          List of Checks to run, all of which should pass for this item
                        to be marked as passed/successful on the final list
        _is_verbose     Run all checks inside of this item, even if some fail. This is useful when
                        extending this class to make custom case-specific ChecklistItems, where
                        you may want to display the (entire!) list to the student.
    """
    message: str
    _checks: List[Check] = field(init=False)
    _is_verbose: bool = False

    def __init__(self, message: str, *checks: Checks):
        self.message = message
        self._checks = []

        # Flatten the list of checks and store in internal list
        checks = flatten_queue(checks)
        self._checks = flatten_queue(checks)

    def _process_one(self, check: Check, bs: BeautifulSoup, language: str) -> bool:
        """Process a single check inside of this item
        Inner function to make future modifications cleaner, and allows a bit of abstraction
        """
        return check.callback(bs)

    def evaluate(self, bs: BeautifulSoup, language: str) -> bool:
        """Evaluate all checks inside of this item"""
        queue = copy(self._checks)

        should_abort = False
        success = True

        while queue:
            check = queue.pop(0)

            # Check failed
            if not self._process_one(check, bs, language):
                # Abort testing if necessary
                if check.abort_on_fail:
                    # Only abort instantly if the item is not verbose,
                    # otherwise continue but abort future tests afterwards
                    if not self._is_verbose:
                        raise EvaluationAborted()
                    else:
                        should_abort = True

                # If the item is not verbose, skip future tests
                if not self._is_verbose:
                    return False
                else:
                    success = False

            # Check succeeded, add all on_success checks
            for os_check in reversed(check.on_success):
                queue.insert(0, os_check)

        # Abort future items
        if should_abort:
            raise EvaluationAborted()

        return success


class VerboseChecklistItem(ChecklistItem):
    """A ChecklistItem that displays the entire checklist when evaluated

    Supports translations, but requires all languages to have the same amount of translations.
    Default values are NOT supported, and this class is meant for internal use.
    """
    # Print the messages depending on when a Check fails or succeeds,
    # True for only on success, False for only on failure, None for always
    only_when_status: Optional[bool]
    messages: Dict[str, List[str]] = field(default_factory=Dict)
    _is_verbose: bool = field(init=False)

    def __init__(self, message: str, messages: Dict[str, List[str]], only_when_status: bool, *checks: Checks):
        self.only_when_status = only_when_status
        self.messages = messages
        self._is_verbose = True
        super().__init__(message, checks)

        # Check that all translations have the correct amount of items
        for k, v in self.messages.items():
            assert len(v) == len(
                self._checks), f"Incorrect amount of translations for language {k} ({len(v)} instead of {len(self._checks)})."

    def _process_one(self, check: Check, bs: BeautifulSoup, language: str) -> bool:
        """Modify the processing function to show the checks inside of it"""
        res = check.callback(bs)
        # Check if message should be printed
        if self.only_when_status is None or res == self.only_when_status:
            message = self.messages[language][self._checks.index(check)]

            with Message(description=message, format="plain"):
                pass

        return res


@dataclass
class TestSuite:
    """Main test suite class

    Attributes:
        content     The HTML of the document to perform the tests on
        checklist   A list of all checks to perform on this document
    """
    name: str
    content: str
    check_recommended: bool = True
    checklist: List[ChecklistItem] = field(default_factory=list)
    translations: Dict[str, List[str]] = field(default_factory=dict)
    _bs: BeautifulSoup = field(init=False)
    _html_validator: HtmlValidator = field(init=False)
    _css_validator: Optional[CssValidator] = field(init=False)
    _html_validated: bool = field(init=False)
    _css_validated: bool = field(init=False)

    def __post_init__(self):
        self._bs = BeautifulSoup(self.content, "html.parser")
        self._html_validated = False

        try:
            self._css_validator = CssValidator(self.content)
            self._css_validated = True
        except CssParsingError:
            # Css is invalid, can't create the validator
            self._css_validator = None
            self._css_validated = False

    def create_validator(self, config: DodonaConfig):
        """Create the HTML validator from outside the Suite
        The Suite is created in the evaluation file by teachers, so we
        avoid passing extra arguments into the constructor as much as we can.
        """
        self._html_validator = HtmlValidator(
            config.translator, recommended=self.check_recommended)

    def html_is_valid(self) -> bool:
        """Return whether or not the HTML has been validated
        Avoids private property access
        """
        return self._html_validated

    def css_is_valid(self) -> bool:
        """Return if the CSS was valid
        Avoids private property access
        """
        return self._css_validated

    def add_item(self, check: ChecklistItem):
        """Add an item to the checklist
        This is a shortcut to suite.checklist.append(item)
        """
        self.checklist.append(check)

    @flatten_varargs
    def make_item(self, message: str, *args: Checks):
        """Create a new ChecklistItem
        This is a shortcut for suite.checklist.append(ChecklistItem(message, check))"""
        self.checklist.append(ChecklistItem(message, list(args)))

    def make_item_from_emmet(self, message: str, *emmets: Emmet):
        """Create a new ChecklistItem, the check will compare the submission to the emmet expression.
            The emmet expression is seen as the minimal required elements/attributes, so the submission may contain more
            or equal elements"""
        from utils.emmet import emmet_to_check

        emmet_checks = []

        # Add multiple emmet checks under one main item
        for e in emmets:
            emmet_checks.append(emmet_to_check(e, self))

        self.make_item(message, *emmet_checks)

    def validate_html(self, allow_warnings: bool = True) -> Check:
        """Check that the HTML is valid
        This is done in here so that all errors and warnings can be sent to
        Dodona afterwards by reading them out of here

        The CODE format is used because it preserves spaces & newlines
        """

        def _inner(_: BeautifulSoup) -> bool:
            try:
                # Do basic HTML checks first
                self._html_validator.validate_content(self.content)
            except Warnings as war:
                with Message(description=str(war), format=MessageFormat.CODE):
                    for exc in war.exceptions:
                        with SafeAnnotation(row=exc.line, text=exc.annotation_str(), type="warning"):
                            pass
                    self._html_validated = allow_warnings
                    return allow_warnings
            except LocatableHtmlValidationError as err:
                with Message(description=err.message_str(), format=MessageFormat.CODE):
                    with SafeAnnotation(row=err.line, text=err.annotation_str(), type="error"):
                        pass
                    return False
            except MultipleMissingCharsError as errs:
                with Message(description=str(errs), format=MessageFormat.CODE):
                    err: LocatableDoubleCharError
                    for err in errs.exceptions:
                        with SafeAnnotation(row=err.line, text=err.annotation_str(), type="error"):
                            pass
                    return False

            # Empty submission is invalid HTML
            if not self.content.strip():
                return False

            # If no validation errors were raised, the HTML is valid
            self._html_validated = True
            return True

        return Check(_inner)

    def return_true(self) -> Check:
        def _inner(_: BeautifulSoup) -> bool:
            return True
        return Check(_inner)

    def return_false(self) -> Check:
        def _inner(_: BeautifulSoup) -> bool:
            return False
        return Check(_inner)

    def validate_css(self) -> Check:
        """Check that CSS was valid"""

        def _inner(_: BeautifulSoup) -> bool:
            return self._css_validated

        return Check(_inner)

    def add_check_validate_css_if_present(self):
        """Adds a check for CSS-validation only if there is some CSS supplied"""
        if self._css_validated and self._css_validator:
            self.add_item(ChecklistItem(
                "The css is valid.", self.validate_css()))
            if "nl" in self.translations:
                self.translations["nl"].append("De CSS is geldig.")

    def compare_to_solution(self, solution: str, translator: Translator, **kwargs) -> Check:
        """Compare the submission to the solution html."""

        def _inner(_: BeautifulSoup):
            from validators.structure_validator import compare, get_similarity
            from exceptions.structure_exceptions import NotTheSame
            try:
                compare(solution, self.content, translator, **kwargs)
            except NotTheSame as err:
                description = err.message_str()

                # Only calculate similarity for valid HTML
                if self._html_validated:
                    html_sim, css_sim = get_similarity(solution, self.content)
                    html_sim_str = f"\n HTML{translator.translate(Translator.Text.SIMILARITY)}: {round(html_sim * 100)}%"
                    css_sim_str = f"\n CSS{translator.translate(Translator.Text.SIMILARITY)}: {round(css_sim* 100)}%" if css_sim != 1 else ""
                    description += html_sim_str + css_sim_str

                with Message(description=description, format=MessageFormat.CODE):
                    with SafeAnnotation(row=err.line, text=err.annotation_str(), type="error"):
                        pass

                    return False
            return True

        return Check(_inner)

    def document_matches(self, regex: str, flags: Union[int, re.RegexFlag] = 0) -> Check:
        """Check that the document matches a regex"""

        def _inner(_: BeautifulSoup) -> bool:
            return re.search(regex, self.content, flags) is not None

        return Check(_inner)

    def contains_comment(self, comment: Optional[str] = None) -> Check:
        """Check if the document contains a comment, optionally matching a value"""
        def _inner(_: BeautifulSoup) -> bool:
            return contains_comment(self._bs, comment)

        return Check(_inner)

    def contains_css(self, css_selector: str, prop: str, value: Optional[str] = None, important: Optional[bool] = None, any_order: bool = False) -> Check:
        """Check if the given css rule exists for the given css selector"""
        def _inner(_: BeautifulSoup) -> bool:
            rule: Rule = self._css_validator.find_by_css_selector(
                css_selector, prop)
            # If the property is not found, it is None
            return False if rule is None else rule.compare_to(value, important, any_order)

        return Check(_inner)

    def has_doctype(self) -> Check:
        """Check if the document starts with <!DOCTYPE HTML"""
        def _inner(_: BeautifulSoup) -> bool:
            # Do NOT use the BS Doctype for this, because it repairs
            # incorrect/broken HTML which invalidates this function
            return re.search(doctype_re.pattern, self.content, doctype_re.flags) is not None

        return Check(_inner)

    def element(self, tag: Optional[Union[str, Emmet]] = None, index: int = 0, from_root: bool = False, **kwargs) -> Element:
        """Create a reference to an HTML element
        :param tag:         the name of the HTML tag to search for
        :param index:       in case multiple elements match, specify which should be chosen
        :param from_root:   find the element as a child of the root node instead of anywhere
                            in the document
        """
        element = find_child(self._bs, tag=tag, index=index,
                             from_root=from_root, **kwargs)

        if element is None:
            return EmptyElement()

        return Element(element.name, kwargs.get("id", None), element, self._css_validator)

    def all_elements(self, tag: Optional[Union[str, Emmet]] = None, from_root: bool = False, **kwargs) -> ElementContainer:
        """Get references to ALL HTML elements that match a query"""
        if match_emmet(tag):
            elements = find_emmet(
                self._bs, tag, 0, from_root=from_root, match_multiple=True, **kwargs)

            if elements is None:
                return ElementContainer([])
        else:
            elements = self._bs.find_all(
                tag, recursive=not from_root, **kwargs)

        return ElementContainer.from_tags(elements, self._css_validator)

    def _create_language_lists(self):
        """Init the lists of languages to avoid IndexErrors"""
        for language in ["en", "nl"]:
            if language not in self.translations:
                self.translations[language] = []

    def evaluate(self, translator: Translator) -> int:
        """Run the test suite, and print the Dodona output
        :returns:   the amount of failed tests
        :rtype:     int
        """
        aborted = -1
        failed_tests = 0

        lang_abr = translator.language.name.lower()

        # Run all items on the checklist & mark them as successful if they pass
        for i, item in enumerate(self.checklist):
            # Get translated version if possible, else use the message in the item
            message: str = item.message \
                if lang_abr not in self.translations or i >= len(self.translations[lang_abr]) \
                else self.translations[lang_abr][i]

            with Context(), TestCase(message) as test_case:
                # Make it False by default so crashing doesn't make it default to True
                test_case.accepted = False

                # Evaluation was aborted, print a message and skip this test
                if aborted >= 0:
                    with Message(description=translator.translate(translator.Text.TESTCASE_NO_LONGER_EVALUATED),
                                 format=MessageFormat.TEXT):
                        failed_tests += 1
                        continue

                # Can't set items on tuples so overwrite it
                try:
                    test_case.accepted = item.evaluate(self._bs, lang_abr)
                except EvaluationAborted:
                    # Crucial test failed, stop evaluation and let the next tests
                    # all be marked as wrong
                    aborted = i

                    with Message(description=translator.translate(translator.Text.TESTCASE_ABORTED),
                                 format=MessageFormat.TEXT):
                        pass
                except (AmbiguousXpath, ElementNotFound,):
                    with Message(description=translator.translate(translator.Text.AMBIGUOUS_XPATH), format=MessageFormat.TEXT):
                        pass
                except Exception:
                    # If anything else fails while evaluating, tell the student instead of crashing completely
                    with Message(description=translator.translate(translator.Text.EVALUATION_FAILED), format=MessageFormat.TEXT):
                        pass

                # If the test wasn't marked as True above, increase the counter for failed tests
                if not test_case.accepted:
                    failed_tests += 1

        return failed_tests


class BoilerplateTestSuite(TestSuite):
    """Base class for TestSuites that handle some boilerplate things"""
    _default_translations: Optional[Dict[str, List[str]]] = None
    _default_checks: Optional[List[ChecklistItem]] = None
    check_minimal: bool

    def __init__(self, name: str,
                 content: str,
                 check_recommended: bool = True,
                 check_minimal: bool = False):
        super().__init__(name, content, check_recommended)
        self.check_minimal = check_minimal

    def _add_default_translations(self):
        self._create_language_lists()

        if self._default_translations is None:
            return

        # Add in reverse order so we can keep inserting at index 0
        for language, translations in self._default_translations.items():
            for entry in reversed(translations):
                self.translations[language].insert(0, entry)

    def _add_default_checks(self):
        if self._default_checks is None:
            return

        # Add in reverse order so we can keep inserting at index 0
        for item in reversed(self._default_checks):
            self.checklist.insert(0, item)

    def _has_minimal_template(self):
        """Check that the minimal required HTML template is present"""
        # Translations have to be separated here because they work differently than
        # the regular translations do (subchecks instead of separate items)

        translations = {
            "nl": [
                "Het type van het document is niet (correct) gedeclareerd.",
                "De <html>-tag heeft geen taal-attribuut.",
                "De <html>-tag bevat geen <head>-tag.",
                "De <head>-tag bevat geen <title>-tag.",
                "De <title>-tag is bevat geen tekst.",
                "De <head>-tag bevat geen <meta>-tag.",
                "Het charset-attribuut van de <meta>-tag staat niet ingesteld op UTF-8.",
                "De <html>-tag bevat geen <body>-tag."
            ],
            "en": [
                "The type of the document was not declared (correctly).",
                "The <html> tag does not contain a language attribute.",
                "The <html> tag does not contain a <head> tag.",
                "The <head> tag does not contain a <title> tag.",
                "The <title> tag does not contain any content.",
                "The <head> tag does not contain a <meta> tag.",
                "The <meta> tag does not have its charset attribute set to UTF-8.",
                "The <html> tag does not contain a <body> tag."
            ]
        }

        # Elements
        _html = self.element("html")
        _head = _html.get_child("head")
        _title = _head.get_child("title")
        _meta = _head.get_child("meta", charset=True)
        _body = _html.get_child("body")

        if self._default_checks is None:
            self._default_checks = []

        self._default_checks.append(VerboseChecklistItem("The solution contains the minimal required HTML code.", translations, False,
                                                         self.has_doctype(),
                                                         _html.attribute_exists(
                                                             "lang"),
                                                         _head.exists(),
                                                         _title.exists(),
                                                         _title.has_content(),
                                                         _meta.exists(),
                                                         _meta.attribute_exists(
                                                             "charset", "UTF-8", case_insensitive=True),
                                                         _body.exists()
                                                         )
                                    )

        self._default_translations["en"].append(
            "The solution contains the minimal required HTML code.")
        self._default_translations["nl"].append(
            "De oplossing bevat de minimale vereiste HTML-code.")

    def evaluate(self, translator: Translator) -> int:
        # Add minimal HTML template check
        if self.check_minimal:
            self._has_minimal_template()

        self._add_default_translations()
        self._add_default_checks()

        return super().evaluate(translator)


class HtmlSuite(BoilerplateTestSuite):
    """TestSuite that does HTML validation by default"""
    allow_warnings: bool

    def __init__(self, content: str, check_recommended: bool = True, allow_warnings: bool = True, abort: bool = True, check_minimal: bool = False):
        super().__init__("HTML", content, check_recommended, check_minimal)

        # Only abort if necessary
        if abort:
            self._default_checks = [ChecklistItem(
                "The HTML is valid.", self.validate_html(allow_warnings).or_abort())]
        else:
            self._default_checks = [ChecklistItem(
                "The HTML is valid.", self.validate_html(allow_warnings))]

        self._default_translations = {
            "en": ["The HTML is valid."], "nl": ["De HTML is geldig."]}

        self.allow_warnings = allow_warnings


class CssSuite(BoilerplateTestSuite):
    """TestSuite that does HTML and CSS validation by default"""
    allow_warnings: bool

    def __init__(self, content: str, check_recommended: bool = True, allow_warnings: bool = True, abort: bool = True, check_minimal: bool = False):
        super().__init__("CSS", content, check_recommended, check_minimal)

        # Only abort if necessary
        if abort:
            self._default_checks = [ChecklistItem("The HTML is valid.", self.validate_html(allow_warnings).or_abort()),
                                    ChecklistItem(
                                        "The CSS is valid.", self.validate_css().or_abort())
                                    ]
        else:
            self._default_checks = [ChecklistItem("The HTML is valid.", self.validate_html(allow_warnings)),
                                    ChecklistItem(
                                        "The CSS is valid.", self.validate_css())
                                    ]

        self._default_translations = {
            "en": ["The HTML is valid.", "The CSS is valid."],
            "nl": ["De HTML is geldig.", "De CSS is geldig."]
        }

        self.allow_warnings = allow_warnings


class _CompareSuite(HtmlSuite):
    """TestSuite that does:
     * HTML validation
     * CSS validation (if css is present)
     * evaluation by comparing to the solution.html"""

    def __init__(self, content: str, solution: str, config: DodonaConfig, check_recommended: bool = True,
                 allow_warnings: bool = True, abort: bool = True):
        super().__init__(content, check_recommended, allow_warnings, abort)

        # Adds a check for CSS-validation only if there is some CSS supplied
        if self._css_validated and self._css_validator:
            if abort:
                self._default_checks.append(ChecklistItem(
                    "The CSS is valid.", self.validate_css().or_abort()))
            else:
                self._default_checks.append(ChecklistItem(
                    "The CSS is valid.", self.validate_css()))
            # Translations
            self._default_translations["en"].append("The CSS is valid.")
            self._default_translations["nl"].append("De CSS is geldig.")

        # Adds a check for comparing to solution
        params = {"attributes": getattr(config, "attributes", False),
                  "minimal_attributes": getattr(config, "minimal_attributes", False),
                  "contents": getattr(config, "contents", False)}

        self._default_checks.append(
            ChecklistItem("The submission resembles the solution.",
                          self.compare_to_solution(solution, config.translator, **params)))
        # Translations
        self._default_translations["en"].append(
            "The submission resembles the solution.")
        self._default_translations["nl"].append(
            "De ingediende code lijkt op die van de oplossing.")


"""
UTILITY FUNCTIONS
"""


@flatten_varargs
def all_of(*args: Checks) -> Check:
    """Perform an AND-statement on a series of Checks
    Creates a new Check that requires every single one of the checks to pass,
    otherwise returns False.
    """
    # Flatten list of checks
    flattened = flatten_queue(copy(list(args)))
    queue: Deque[Check] = deque(flattened)

    def _inner(bs: BeautifulSoup) -> bool:
        while queue:
            check = queue.popleft()

            # One check failed, return False
            if not check.callback(bs):
                return False

            # Try the other checks
            for sub in reversed(check.on_success):
                queue.appendleft(sub)

        return True

    return Check(_inner)


@flatten_varargs
def any_of(*args: Checks) -> Check:
    """Perform an OR-statement on a series of Checks
    Returns True if at least one of the tests succeeds, and stops
    evaluating the rest at that point.
    """
    # Flatten list of checks
    flattened = flatten_queue(copy(list(args)))
    queue: Deque[Check] = deque(flattened)

    def _inner(bs: BeautifulSoup) -> bool:
        while queue:
            check = queue.popleft()

            # One check passed, return True
            if check.callback(bs):
                return True

            # Try the other checks
            for sub in reversed(check.on_success):
                queue.appendleft(sub)

        return False

    return Check(_inner)


@flatten_varargs
def at_least(amount: int, *args: Checks) -> Check:
    """Check that at least [amount] checks passed"""
    # Flatten list of checks
    flattened = flatten_queue(copy(list(args)))
    queue: Deque[Check] = deque(flattened)

    def _inner(bs: BeautifulSoup) -> bool:
        passed = 0

        while queue:
            check = queue.popleft()

            if check.callback(bs):
                passed += 1

            if passed >= amount:
                return True

        return False

    return Check(_inner)


def fail_if(check: Check) -> Check:
    """Fail if the inner Check returns True
    Equivalent to the not-operator.
    """

    def _inner(bs: BeautifulSoup):
        return not check.callback(bs)

    return Check(_inner)


class CVGSuite(BoilerplateTestSuite):
    """TestSuite that does HTML validation by default"""
    allow_warnings: bool
    solution_content: str

    cont_nodes: list
    cont_edges: list

    sol_nodes: list
    sol_edges: list
    succes_tests: bool

    def __init__(self, content: str, solution: str, check_recommended: bool = True, allow_warnings: bool = True, abort: bool = True, check_minimal: bool = False):
        super().__init__("CVG", content, check_recommended, check_minimal)

        content = ast.literal_eval(content)
        # print(content)
        self.cont_nodes = content["nodes"]
        self.cont_edges = content["edges"]

        solution_content: str = solution
        self.sol_nodes = solution_content["nodes"]
        self.sol_edges = solution_content["edges"]
        self.succes_tests = True

    def return_true(self) -> Check:
        def _inner(_: BeautifulSoup) -> bool:
            return True
        return Check(_inner)

    def return_false(self) -> Check:
        def _inner(_: BeautifulSoup) -> bool:
            return False
        return Check(_inner)

    def compare_nodeslength(self) -> Check:

        def _inner(_: BeautifulSoup) -> bool:

            if (self.succes_tests != False):
                self.succes_tests = len(self.sol_nodes) == len(self.cont_nodes)
            return (len(self.sol_nodes) == len(self.cont_nodes))
        return Check(_inner)

    def compare_edgeslength(self) -> Check:

        def _inner(_: BeautifulSoup) -> bool:
            if (self.succes_tests != False):
                self.succes_tests = len(self.sol_edges) == len(self.cont_edges)
            return (len(self.sol_edges) == len(self.cont_edges))
        return Check(_inner)

    def correct_nodes(self) -> Check:

        def _inner(_: BeautifulSoup) -> bool:
            self.cont_nodes.sort()
            self.sol_nodes.sort()
            if (self.succes_tests != False):
                self.succes_tests = (self.cont_nodes == self.sol_nodes)
            return (self.cont_nodes == self.sol_nodes)

        return Check(_inner)

    def correct_edges(self) -> Check:

        def _inner(_: BeautifulSoup) -> bool:
            # 0: from , #1: to , #2 : dashes
            user_edges = []
            sol_edges = []
            for i, edge in enumerate(self.cont_edges):
                temp_edge = [0, 0, 0]
                temp_edge[0] = edge["from"]
                temp_edge[1] = edge["to"]
                temp_edge[2] = edge["dashes"]
                user_edges.append(temp_edge)

            for i, edge in enumerate(self.sol_edges):
                temp_edge = [0, 0, 0]
                temp_edge[0] = edge["from"]
                temp_edge[1] = edge["to"]
                temp_edge[2] = edge["dashes"]
                sol_edges.append(temp_edge)
            user_edges.sort()
            sol_edges.sort()
            if len(user_edges) != len(sol_edges):
                return False
            for i in range(len(user_edges)):
                if user_edges[i][0] != sol_edges[i][0] or user_edges[i][1] != sol_edges[i][1]:
                    self.succes_tests == False
                    return False
            return True

        return Check(_inner)

    def correct_stippel(self) -> Check:

        def _inner(_: BeautifulSoup) -> bool:
            # 0: from , #1: to , #2 : dashes
            user_edges = []
            sol_edges = []
            for i, edge in enumerate(self.cont_edges):
                temp_edge = [0, 0, 0]
                temp_edge[0] = edge["from"]
                temp_edge[1] = edge["to"]
                temp_edge[2] = edge["dashes"]
                user_edges.append(temp_edge)

            for i, edge in enumerate(self.sol_edges):
                temp_edge = [0, 0, 0]
                temp_edge[0] = edge["from"]
                temp_edge[1] = edge["to"]
                temp_edge[2] = edge["dashes"]
                sol_edges.append(temp_edge)
            user_edges.sort()
            sol_edges.sort()
            if len(user_edges) != len(sol_edges):
                self.succes_tests == False
                return False
            for i in range(len(user_edges)):
                if user_edges[i][0] != sol_edges[i][0] or user_edges[i][1] != sol_edges[i][1] or user_edges[i][2] != sol_edges[i][2]:
                    self.succes_tests == False
                    return False
            return True

        return Check(_inner)

    def correct_CVG(self) -> Check:
        def _inner(_: BeautifulSoup) -> bool:
            return self.succes_tests

        return Check(_inner)
