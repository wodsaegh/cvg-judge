from typing import Tuple

from dodona.translator import Translator

def get_similarity(sol: str, sub: str) -> Tuple[float, float]: ...

def compare(solution: str, submission: str, trans: Translator, **kwargs): ...
