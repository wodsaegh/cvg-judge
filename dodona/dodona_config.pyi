from types import SimpleNamespace
from typing import TextIO


class DodonaConfig(SimpleNamespace):
    memory_limit: int
    time_limit: int
    programming_language: str
    natural_language: str
    resources: str
    source: str
    judge: str
    workdir: str

    def __init__(self, **kwargs): ...

    @classmethod
    def from_json(cls, json_file: TextIO) -> "DodonaConfig": ...

    def sanity_check(self): ...
