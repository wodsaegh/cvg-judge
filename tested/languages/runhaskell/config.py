import typing
from pathlib import Path
from typing import List, Tuple

from tested.configs import Bundle
from tested.dodona import AnnotateCode, Message
from tested.languages.config import CallbackResult, Command, Config, Language
from tested.languages.utils import (
    cleanup_description,
    haskell_cleanup_stacktrace,
    haskell_solution,
)
from tested.serialisation import FunctionCall, Statement, Value

if typing.TYPE_CHECKING:
    from tested.languages.generator import PreparedExecutionUnit


class RunHaskell(Language):
    def compilation(self, bundle: Bundle, files: List[str]) -> CallbackResult:
        submission_file = self.with_extension(
            self.conventionalize_namespace(self.submission_name(bundle.suite))
        )
        main_file = list(filter(lambda x: x == submission_file, files))
        if main_file:
            return ["ghc", "-fno-code", main_file[0]], files
        else:
            return [], files

    def compiler_output(
        self, namespace: str, stdout: str, stderr: str
    ) -> Tuple[List[Message], List[AnnotateCode], str, str]:
        return (
            [],
            [],
            "",
            haskell_cleanup_stacktrace(
                stderr, self.with_extension(self.conventionalize_namespace(namespace))
            ),
        )

    def execution(
        self, config: Config, cwd: Path, file: str, arguments: List[str]
    ) -> Command:
        return ["runhaskell", file, *arguments]

    def solution(self, solution: Path, bundle: Bundle):
        haskell_solution(self, solution, bundle)

    def linter(
        self, bundle: Bundle, submission: Path, remaining: float
    ) -> Tuple[List[Message], List[AnnotateCode]]:
        # Import locally to prevent errors.
        from tested.languages.haskell import linter

        return linter.run_hlint(bundle, submission, remaining)

    def filter_dependencies(
        self, bundle: Bundle, files: List[str], context_name: str
    ) -> List[str]:
        return files

    def cleanup_description(self, namespace: str, description: str) -> str:
        return cleanup_description(self, namespace, description)

    def cleanup_stacktrace(
        self, traceback: str, submission_file: str, reduce_all=False
    ) -> str:
        return haskell_cleanup_stacktrace(traceback, submission_file, reduce_all)

    def generate_statement(self, statement: Statement) -> str:
        from tested.languages.haskell import generators

        return generators.convert_statement(statement)

    def generate_execution_unit(self, execution_unit: "PreparedExecutionUnit") -> str:
        from tested.languages.haskell import generators

        return generators.convert_execution_unit(execution_unit)

    def generate_selector(self, contexts: List[str]) -> str:
        from tested.languages.haskell import generators

        return generators.convert_selector(contexts)

    def generate_check_function(self, name: str, function: FunctionCall) -> str:
        from tested.languages.haskell import generators

        return generators.convert_check_function(name, function)

    def generate_encoder(self, values: List[Value]) -> str:
        from tested.languages.haskell import generators

        return generators.convert_encoder(values)