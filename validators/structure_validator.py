from dodona.translator import Translator
from lxml.html import fromstring, HtmlElement, HtmlComment

from exceptions.structure_exceptions import NotTheSame
from validators.css_validator import CssValidator
from utils.html_navigation import compare_content
from utils.html_checks import is_empty_document

from typing import Tuple


def get_similarity(sol: str, sub: str) -> Tuple[float, float]:
    # Empty submission is 0% similar
    if is_empty_document(sub):
        return 0, 0

    from html_similarity import style_similarity, structural_similarity
    a = sol.find("<style")
    b = sub.find("<style")
    if a != -1 or b != -1:
        return structural_similarity(sol, sub), style_similarity(sol, sub)
    else:
        return structural_similarity(sol, sub), 1


def compare(solution_str: str, submission_str: str, trans: Translator, **kwargs):
    """compare submission structure to the solution structure (html)
    possible kwargs:
    * attributes: (default: False) check whether attributes are exactly the same in solution and submission
    * minimal_attributes: (default: False) check whether at least the attributes in solution are supplied in the submission
    * contents: (default: False) check whether the contents of each tag in the solution are exactly the same as in the submission
    * css: (default: True) if there are css rules defined in the solution, check if the submission can match these rules.
            We don't compare the css rules itself, but rather whether every element in the submission has at least the css-rules defined in the solution.
    Raises a NotTheSame exception if the solution and the submission are not alike

    the submission html should be valid html
    """
    if is_empty_document(submission_str):
        raise NotTheSame(trans=trans, msg=trans.translate(Translator.Text.EMPTY_SUBMISSION), line=-1, pos=-1)

    # structure is always checked
    check_attributes = kwargs.get("attributes", False)
    check_minimal_attributes = kwargs.get("minimal_attributes", False)
    check_contents = kwargs.get("contents", False)
    check_css = kwargs.get("css", True)
    check_comments = kwargs.get("comments", False)

    sol_css = None
    sub_css = None
    if check_css:
        try:
            sol_css = CssValidator(solution_str)
            sub_css = CssValidator(submission_str)
            if not sol_css.rules:  # no rules in solution file
                check_css = False
        except Exception:
            check_css = False

    solution: HtmlElement = fromstring(solution_str)
    submission: HtmlElement = fromstring(submission_str)
    # start checking structure

    def attrs_a_contains_attrs_b(attrs_a, attrs_b, exact_match):
        # split dummy values from attrs_a
        dummies = set()
        exact = {}
        for a in attrs_a:
            if node_sol.attrib.get(a).strip() == "DUMMY":
                dummies.add(a)
            else:
                exact.update({a: node_sol.attrib.get(a).strip()})
        # check if all attrs in a are in b (if exact, all attrs from b must also be in a)
        for b in attrs_b:
            if b in exact and exact[b] == node_sub.attrib[b]:
                exact.pop(b)
            elif b in dummies:
                dummies.remove(b)
            elif exact_match:
                return False
        if dummies or exact:
            return False
        return True

    queue = ([(solution, submission)])
    while queue:
        node_sol, node_sub = queue.pop()
        if check_comments and isinstance(node_sol, HtmlComment):
            if not isinstance(node_sub, HtmlComment):
                raise NotTheSame(trans=trans, msg=trans.translate(Translator.Text.EXPECTED_COMMENT), line=node_sub.sourceline, pos=-1)
            node_sol.text = node_sol.text.strip().lower() if node_sol.text is not None else ''
            node_sub.text = node_sub.text.strip().lower() if node_sub.text is not None else ''
            if node_sol.text != "dummy" and not compare_content(node_sol.text, node_sub.text):
                raise NotTheSame(trans=trans, msg=trans.translate(Translator.Text.COMMENT_CORRECT_TEXT), line=node_sub.sourceline, pos=-1)
            continue
        node_sol.tag = node_sol.tag.lower()
        node_sub.tag = node_sub.tag.lower()
        node_sol.text = node_sol.text.strip() if node_sol.text is not None else ''
        node_sub.text = node_sub.text.strip() if node_sub.text is not None else ''
        # check name of the node
        if node_sol.tag != node_sub.tag:
            raise NotTheSame(trans=trans, msg=trans.translate(Translator.Text.TAGS_DIFFER), line=node_sub.sourceline, pos=-1)
        # check attributes if wanted
        if check_attributes:
            if not attrs_a_contains_attrs_b(node_sol.attrib, node_sub.attrib, True):
                raise NotTheSame(trans=trans, msg=trans.translate(Translator.Text.ATTRIBUTES_DIFFER), line=node_sub.sourceline, pos=-1)
        if check_minimal_attributes:
            if not attrs_a_contains_attrs_b(node_sol.attrib, node_sub.attrib, False):
                raise NotTheSame(trans=trans, msg=trans.translate(Translator.Text.NOT_ALL_ATTRIBUTES_PRESENT), line=node_sub.sourceline, pos=-1)
        # check content if wanted
        if check_contents:
            if node_sol.text != "DUMMY" and not compare_content(node_sol.text, node_sub.text):
                raise NotTheSame(trans=trans, msg=trans.translate(Translator.Text.CONTENTS_DIFFER), line=node_sub.sourceline, pos=-1)
        # check css
        if check_css:
            rs_sol = sol_css.rules.find_all(solution, node_sol)
            rs_sub = sub_css.rules.find_all(submission, node_sub)
            if rs_sol:
                for r_key in rs_sol:
                    if r_key not in rs_sub:
                        raise NotTheSame(trans=trans, msg=trans.translate(Translator.Text.STYLES_DIFFER, tag=node_sub.tag), line=node_sub.sourceline, pos=-1)
                    if rs_sol[r_key].value_str != rs_sub[r_key].value_str:
                        if not (rs_sol[r_key].is_color() and rs_sol[r_key].has_color(rs_sub[r_key].value_str)):
                            raise NotTheSame(trans=trans, msg=trans.translate(Translator.Text.STYLES_DIFFER, tag=node_sub.tag), line=node_sub.sourceline, pos=-1)
        # check whether the children of the nodes have the same amount of children
        node_sol_children = node_sol.getchildren()
        node_sub_children = node_sub.getchildren()
        if not check_comments:
            node_sol_children = [x for x in node_sol_children if isinstance(x, HtmlElement)]
            node_sub_children = [x for x in node_sub_children if isinstance(x, HtmlElement)]
        if len(node_sol_children) != len(node_sub_children):
            raise NotTheSame(trans=trans, msg=trans.translate(Translator.Text.AMOUNT_CHILDREN_DIFFER), line=node_sub.sourceline, pos=-1)
        # reverse children bc for some reason they are in bottom up order (and we want to review top down)
        queue += zip(reversed(node_sol_children), reversed(node_sub_children))

