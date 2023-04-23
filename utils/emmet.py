from emmet import parse_markup_abbreviation, AbbreviationAttribute, AbbreviationNode

from validators.checks import TestSuite, Element, all_of, EmptyElement, Check


def emmet_to_check(emmet_str: str, suite: TestSuite) -> Check:
    """Converts an emmet expression to a Check"""

    # item numbering is not allowed, as it interferes with multiplications
    if "$" in emmet_str:
        return EmptyElement().exists()

    parsed = parse_markup_abbreviation(emmet_str)

    def make_params(node: AbbreviationNode):
        """convert attributes & text to a dict"""
        out = {}
        if node.attributes:
            a: AbbreviationAttribute
            for a in node.attributes:
                if a.name.isdigit():
                    # this is a n-th tag selector, like div[2]
                    # we will do this in the match_one function
                    pass
                else:
                    val = " ".join(a.value)
                    if val.strip().upper() == "DUMMY":
                        # dummy values
                        out.update({a.name: True})
                    else:
                        # normal values, this is a list
                        out.update({a.name: " ".join(a.value)})
        if node.value:
            val = " ".join(node.value)
            if val.strip().upper() == "DUMMY":
                out.update({"text": True})
            else:
                out.update({"text": " ".join(node.value)})
        return out

    def match_one(ls: [Element], node: AbbreviationNode):
        """when ls contains more than one item, it makes the right selection
            if ls is empty, it returns an EmptyElement (which will result in a failing Check)&"""
        if not ls:
            return EmptyElement(), node
        if node.repeat:
            if node.repeat.value < len(ls):
                return ls[node.repeat.value], node
            else:
                return EmptyElement(), node
        return ls[0], node

    ls = []
    # the roots (plural because of possible siblings)
    for root_child in parsed.children:
        params = make_params(root_child)
        ls.append(match_one(suite.all_elements(root_child.name, **params), root_child))
    # now we go deeper in the tree (if possible)
    el: Element
    length = len(ls)
    while length > 0:
        if ls[0][1].children:
            el, abr = ls.pop(0)
            for child in abr.children:
                kwargs = make_params(child)
                ls.append(match_one(el.get_children(child.name, direct=True, **kwargs), child))
                length += 1
        length -= 1
    return all_of(*[x[0].exists() for x in ls])
