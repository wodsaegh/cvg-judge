from __future__ import annotations
from typing import TYPE_CHECKING, List, Iterable

if TYPE_CHECKING:
    from validators.checks import Checks, Check


def flatten_queue(*queue: Checks) -> List["Check"]:
    """Flatten the queue to allow nested lists to be put inside of it"""
    # *args creates tuples so cast the arg into a list first
    # in case it was used in that context (usually)
    queue = list(queue)

    flattened: List["Check"] = []

    while queue:
        el = queue.pop(0)

        # This entry is an iterable too, unpack it
        # & add to front of the queue
        if isinstance(el, Iterable):
            # Cast to a list first (allows map, generators, ...)
            el = list(el)

            # Iterate in reverse to keep the order of checks!
            for nested_el in reversed(el):
                queue.insert(0, nested_el)
        else:
            flattened.append(el)

    return flattened
