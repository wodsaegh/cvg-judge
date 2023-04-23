import copy

from exceptions.double_char_exceptions import *
from dodona.translator import Translator


class DoubleChar:
    type: str
    open: str
    close: str
    is_unambiguous: bool = True
    _is_open: bool = None
    check_inside: bool = True
    check_in_between: bool = True
    line: int
    pos: int

    def __repr__(self) -> str:
        if self.is_unambiguous:
            s = " open" if self.is_open() else " close"
        else:
            s = ""

        return f"<{self.type}{s}>"

    def create(self, is_open: bool, line: int, pos: int):
        """
        return new instance of DoubleChar with is_open set to the desired value
        """
        c = copy.copy(self)
        if self.is_unambiguous:
            c._is_open = is_open
        c.line = line
        c.pos = pos
        return c

    def is_open(self) -> bool:
        return self._is_open if self.is_unambiguous else None

    def is_close(self) -> bool:
        return not self._is_open if self.is_unambiguous else None

    def len_open(self) -> int:
        return len(self.open)

    def len_close(self) -> int:
        return len(self.close)

    def match_open(self, s: str) -> bool:
        if len(s) < self.len_open():
            return False
        s = s[0:self.len_open()]
        return self.open == s

    def match_close(self, s: str) -> bool:
        if len(s) < self.len_close():
            return False
        s = s[0:self.len_close()]
        return self.close == s


class Round(DoubleChar):
    type = "parentheses"
    open = "("
    close = ")"


class Angle(DoubleChar):
    type = "angle"
    open = "<"
    close = ">"
    check_in_between = False  # content does not need to be checked. ex: <p>This doesn't need to be checked, it is just a string</p>


class Curly(DoubleChar):
    type = "curly"
    open = "{"
    close = "}"


class Square(DoubleChar):
    type = "square"
    open = "["
    close = "]"


class Single(DoubleChar):
    type = "single"
    open = "'"
    close = "'"
    is_unambiguous = False  # open and close is the same
    check_inside = False  # inside 'is just a string, (dont check it)'


class Double(DoubleChar):
    type = "double"
    open = '"'
    close = '"'
    is_unambiguous = False
    check_inside = False


class HtmlComment(DoubleChar):
    type = "html_comment"
    open = "<!--"
    close = "-->"
    check_inside = False


class CssComment(DoubleChar):
    type = "css_comment"
    open = "/*"
    close = "*/"
    check_inside = False


class Generator:
    def __init__(self):
        # sort so we always have longest match first
        self.ls: [DoubleChar] = sorted(
            [Round(), Angle(), Curly(), Square(), Single(), Double(), HtmlComment(), CssComment()],
            key=lambda x: x.len_open() if x.len_open() > x.len_close() else x.len_close(),
            reverse=True
        )

    def create(self, s: str, line: int, pos: int) -> (DoubleChar, str):
        for x in self.ls:
            if x.match_open(s):
                return x.create(True, line, pos), s[x.len_open():]
            if x.match_close(s):
                return x.create(False, line, pos), s[x.len_close():]
        return None, s


class DoubleCharsValidator:
    """
    parses some text & checks that every opening char has an equivalent closing char later in the text (html style)
    checks for:
        * ( )
        * < >
        * { }
        * [ ]
        * ' '
        * " "
    """
    def __init__(self, translator: Translator):
        self.translator = translator

    @staticmethod
    def parse_content(s: str) -> []:
        ls = []
        generator = Generator()
        saved_text = ""
        line, pos = 0, 0
        while s:
            res: DoubleChar
            res, s = generator.create(s, line, pos)
            if res:
                if saved_text:
                    ls.append(saved_text)
                    saved_text = ""
                ls.append(res)
                pos += res.len_open() if res.is_unambiguous and res.is_open() else res.len_close()
            else:
                c = s[0]
                s = s[1:]
                saved_text += c
                pos += 1
                if c == "\n":
                    line += 1
                    pos = 0
        if saved_text:
            ls.append(saved_text)
        return ls

    def validate_content(self, text: str):
        """checks the text"""
        # parse
        text_ls: [] = self.parse_content(text)
        # validate
        stack = []
        wait_until_seen: DoubleChar = None
        # Error checking
        errors = MultipleMissingCharsError(self.translator)

        def push_stack(el: DoubleChar):
            """
            adds an element on the stack, and returns the new value for wait_until_seen if needed
            """
            # don't check inside
            if not el.check_inside:
                wus = el
                wus._is_open = True
            else:
                wus = None
                stack.append(el)
            return wus  # wait_until_seen

        def pop_stack(el: DoubleChar):
            if not el.check_in_between:
                wus = el
                stack.pop()
            else:
                wus = None
                stack.pop()
            return wus

        while text_ls:
            dc = text_ls.pop(0)
            if isinstance(dc, DoubleChar):
                if not wait_until_seen:
                    dc: DoubleChar
                    if (stack and stack[-1].type != dc.type) or (dc.is_unambiguous and dc.is_open()) or not dc.is_unambiguous:
                        wait_until_seen = push_stack(dc)
                    elif stack and stack[-1].type == dc.type:
                        wait_until_seen = pop_stack(dc)
                    else:
                        errors.add(MissingOpeningCharError(trans=self.translator, char=dc.close, line=dc.line, pos=dc.pos))

                else:  # we're inside something that we don't need to check, just whether we need to leave this state
                    if dc.type == wait_until_seen.type:
                        if (not dc.check_in_between and dc.is_unambiguous and dc.is_open()) or dc.check_in_between:
                            wait_until_seen = None
                            push_stack(dc)

        # Error checking
        # the stack should be empty, if not error remaining things
        while stack:
            dc = stack.pop()
            if dc.is_unambiguous and dc.is_close():
                errors.add(MissingOpeningCharError(trans=self.translator, char=dc.close, line=dc.line, pos=dc.pos))
            else:
                errors.add(MissingClosingCharError(trans=self.translator, char=dc.open, line=dc.line, pos=dc.pos))
        # wait_until_seen should be empty
        if wait_until_seen:
            dc = wait_until_seen
            if dc.check_in_between:
                if dc.is_open():
                    errors.add(MissingClosingCharError(trans=self.translator, char=dc.open, line=dc.line, pos=dc.pos))
                else:
                    errors.add(MissingOpeningCharError(trans=self.translator, char=dc.open, line=dc.line, pos=dc.pos))
        if errors:
            raise errors
