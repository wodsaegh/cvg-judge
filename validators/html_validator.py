import ntpath
from html.parser import HTMLParser
from typing import Dict

from dodona.translator import Translator
from exceptions.html_exceptions import *
from os import path

from utils.file_loaders import json_loader, html_loader
from validators.double_chars_validator import DoubleCharsValidator
from functools import lru_cache

# Location of this test file
base_path = path.dirname(__file__)
# keynames for the json
REQUIRED_ATR_KEY = "required_attributes"
RECOMMENDED_ATR_KEY = "recommended_attributes"
PERMITTED_CHILDREN_KEY = "permitted_children"
PERMITTED_PARENTS_KEY = "permitted_parents"
VOID_KEY = "void_tag"


class HtmlValidator(HTMLParser):
    """
    parses & validates the html
      the html doesn't need to start with <!DOCTYPE html>, if it is present it will just be ignored
    this class checks the following:
      * each tag that opens must have a corresponding closing tag
        * tags starting with </ are omitted
        * tags that dont need a closing tag (see json) can bit omitted (like <meta>)
        * tags that can self-close like <meta/>
      * is the tag a valid tag
      * does the tag have valid nesting (it checks the permitted parents)
          for example a head tag has the html tag as permitted parent but nothing else
      * required attributes (to be completed in the json)
      * recommended attributes (to be completed in the json)
      * invalid attributes (style attribute is not allowed)
    """

    def __init__(self, translator: Translator, **kwargs):
        """
        kwargs:
        * required: whether or not to check required arguments
        * recommended: whether or not to check recommended arguments
        * nesting: whether or not to check the nesting of tags
µ        """
        super().__init__()
        self.lineno = 0  # override the default starting at 1 instead of 0
        self.translator = translator
        self.warnings = Warnings(self.translator)
        self.tag_stack = []
        self.double_chars_validator = DoubleCharsValidator(translator)
        self.valid_dict = json_loader(path.abspath(path.join(base_path, "html_tags_attributes.json")))
        self.check_required = kwargs.get("required", True)
        self.check_recommended = kwargs.get("recommended", True)
        self.check_nesting = kwargs.get("nesting", True)
        self._id_set: set[str] = set()

    def set_check_required(self, b: bool):
        self.check_required = b

    def set_check_recommended(self, b: bool):
        self.check_recommended = b

    def set_check_nesting(self, b: bool):
        self.check_nesting = b

    def error(self, error: HtmlValidationError):  # make exception classes and throw these instead
        """raises an error"""
        raise error

    def warning(self, warning: MissingRecommendedAttributesWarning):
        """gathers the warnings,
            these will be thrown at the end if no Errors occur
        """
        self.warnings.add(warning)

    def validate_file(self, source_filepath: str):
        """validate the content of a html-file"""
        self._validate(html_loader(source_filepath, shorted=False))

    def validate_content(self, content: str):
        """validate the content"""
        self._validate(content)

    def _validate(self, text: str):
        """here the actual validation occurs"""
        self.tag_stack.clear()
        self.warnings.clear()
        self.reset()
        self.lineno = 0  # self.reset() is also from a superclass and resets lineno to 1 instead of 0
        # check brackets and stuff ( '(', '"', '{', '[', '<')
        self._valid_double_chars(text)
        # check html syntax
        self.feed(text)
        # clear tag stack
        if self.tag_stack:
            raise MissingClosingTagError(trans=self.translator, tag=self.tag_stack.pop(), line=self.getpos()[0], pos=self.getpos()[1])
        # show warnings if any
        if self.warnings:
            raise self.warnings

    def _valid_double_chars(self, text):
        """check whether every opening char has a corresponding closing char"""
        self.double_chars_validator.validate_content(text)

    def handle_starttag(self, tag: str, attributes: [(str, str)]):
        """handles a html tag that opens, like <body>
            attributes hold the (name, value) of the attributes supplied in the tag"""
        tag = tag.lower()
        self._valid_tag(tag)
        if self.check_nesting:
            self._valid_nesting(tag)
        if not self._is_void_tag(tag):
            self.tag_stack.append(tag)
        self._valid_attributes(tag, {a[0].lower(): a[1] for a in attributes})

    def handle_endtag(self, tag: str):
        """handles a html tag that closes, like <body/>"""
        tag = tag.lower()
        self._valid_tag(tag)
        if self._is_void_tag(tag):
            self.error(UnexpectedClosingTagError(trans=self.translator, tag=tag, line=self.getpos()[0], pos=self.getpos()[1]))
        self._validate_corresponding_tag(tag)
        self.tag_stack.pop()

    def handle_startendtag(self, tag, attrs):
        """handles a html tag that opens and instantly closes, like <meta/>"""
        tag = tag.lower()
        if not self._is_void_tag(tag):
            self.error(NoSelfClosingTagError(trans=self.translator, tag=tag, line=self.getpos()[0], pos=self.getpos()[1]))
        else:
            self.handle_starttag(tag, attrs)

    def _validate_corresponding_tag(self, tag: str):
        """validate that each tag that opens has a corresponding closing tag"""
        if not (self.tag_stack and self.tag_stack[-1] == tag):
            if self.tag_stack:
                missing_closing = self.tag_stack.pop()
                self.error(MissingClosingTagError(trans=self.translator, tag=missing_closing, line=self.getpos()[0], pos=self.getpos()[1]))
            elif not self._is_void_tag(tag):
                self.error(MissingOpeningTagError(trans=self.translator, tag=tag, line=self.getpos()[0], pos=self.getpos()[1]))

    @lru_cache()
    def _is_void_tag(self, tag: str) -> bool:
        """indicates whether the tag its corresponding closing tag is omittable or not"""
        return VOID_KEY in self.valid_dict[tag] and self.valid_dict[tag][VOID_KEY]

    @lru_cache()
    def _valid_tag(self, tag: str):
        """validate that a tag is a valid HTML tag (if a tag isn't allowed, this wil also raise an exception"""
        if tag not in self.valid_dict:
            self.error(InvalidTagError(trans=self.translator, tag=tag, line=self.getpos()[0], pos=self.getpos()[1]))

    def _valid_attributes(self, tag: str, attributes: Dict[str, str]):
        """validate attributes
            check whether all required attributes are there, if not, raise an error
            check whether all recommended attributes are there, if not, add a warning
        """
        # no inline css allowed
        if "style" in attributes:
            self.error(InvalidAttributeError(trans=self.translator, tag=tag, attribute="style", line=self.getpos()[0], pos=self.getpos()[1]))

        # id's may not contain spaces
        if "id" in attributes and any(whitespace in attributes["id"] for whitespace in [" ", "\t", "\n"]):
            self.error(
                AttributeValueError(trans=self.translator, msg=self.translator.translate(Translator.Text.NO_WHITESPACE, attr='id'),
                                    line=self.getpos()[0], pos=self.getpos()[1]))

        # Unique id's
        if 'id' in attributes:
            if attributes['id'] in self._id_set:
                self.error(DuplicateIdError(trans=self.translator, tag=tag, attribute=attributes['id'], line=self.getpos()[0], pos=self.getpos()[1]))
            else:
                self._id_set.add(attributes['id'])

        # id's and classnames must be at least one character
        for attr in ["id", "class"]:
            if attr in attributes:
                attr_val = attributes[attr]
                if not attr_val:
                    self.error(
                        AttributeValueError(trans=self.translator, msg=self.translator.translate(Translator.Text.AT_LEAST_ONE_CHAR, attr=attr), line=self.getpos()[0], pos=self.getpos()[1]))

        # check src attribute for absolute filepaths
        if 'src' in attributes:
            link = attributes['src']
            if ntpath.isabs(link):
                self.error(AttributeValueError(trans=self.translator, msg=self.translator.translate(Translator.Text.NO_ABS_PATHS),
                                    line=self.getpos()[0], pos=self.getpos()[1]))

        tag_info = self.valid_dict[tag]

        if self.check_required:
            required = set(tag_info[REQUIRED_ATR_KEY]) if REQUIRED_ATR_KEY in tag_info else set()
            if missing_req := (required - attributes.keys()):
                self.error(MissingRequiredAttributesError(trans=self.translator, tag=tag, attribute=", ".join(missing_req), line=self.getpos()[0], pos=self.getpos()[1]))

        if self.check_recommended:
            recommended = set(tag_info[RECOMMENDED_ATR_KEY]) if RECOMMENDED_ATR_KEY in tag_info else set()
            if missing_rec := (recommended - attributes.keys()):
                self.warning(MissingRecommendedAttributesWarning(trans=self.translator, tag=tag, attribute=", ".join(missing_rec), line=self.getpos()[0], pos=self.getpos()[1]))

    def _valid_nesting(self, tag):
        """check whether the nesting is html-approved,
            some tags can only have specific parent tags
        """
        tag_info = self.valid_dict[tag]
        if PERMITTED_PARENTS_KEY in tag_info:
            # check if the prev tag is in the permitted parents field of the current tag
            prev_tag = self.tag_stack[-1] if self.tag_stack else None
            # prev tag can be None when tag is <html>, you don't expect it has a parent,
            #   if you want a tag without a parent you need to add "permitted_parent: []" in the json for that tag
            if not tag_info[PERMITTED_PARENTS_KEY]:
                if prev_tag is not None:
                    self.error(UnexpectedTagError(trans=self.translator, tag=tag, line=self.getpos()[0], pos=self.getpos()[1]))
            elif prev_tag is not None and prev_tag not in tag_info[PERMITTED_PARENTS_KEY]:
                self.error(UnexpectedTagError(trans=self.translator, tag=tag, line=self.getpos()[0], pos=self.getpos()[1]))

        # Check if this tag is allowed to be inside its parent
        parent = self.tag_stack[-1] if self.tag_stack else None

        # No parent tag
        if parent is None:
            return

        parent_info = self.valid_dict[parent]

        # Parent tag isn't special
        if PERMITTED_CHILDREN_KEY not in parent_info:
            return

        if tag not in parent_info[PERMITTED_CHILDREN_KEY]:
            self.error(UnexpectedTagError(trans=self.translator, tag=tag, line=self.getpos()[0], pos=self.getpos()[1]))
