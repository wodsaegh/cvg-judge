from os import path
from types import ModuleType
from typing import List, Optional

from dodona.dodona_config import DodonaConfig
from validators.checks import TestSuite


class EvaluationModule(ModuleType):
    """Class that represents a module parsed out of an evaluation file"""

    config: DodonaConfig

    def __init__(self, name: str, config: DodonaConfig, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.config = config

    def create_suites(self, content: str) -> List[TestSuite]:
        """Method that we expect the TestSuite to have
        This stops PyCharm from complaining that the method doesn't exist,
        and also allows us to throw an exception in case it wasn't implemented.
        In case the evaluation file does contain a definition for this function,
        it will override this one.

        :param content:         The content of the HTML file submitted by the student
        :raises DodonaException In case this method was not implemented.
                                Does NOT raise a NotImplementedError() so that it can be
                                displayed nicely on Dodona.
        """
        raise NotImplementedError

    @classmethod
    def build(cls, config: DodonaConfig) -> Optional["EvaluationModule"]:
        """Create a new EvaluationModule from a DodonaConfig configuration"""
        # Create filepath
        custom_evaluator_path = path.join(config.resources, "./evaluator.py")

        # Evaluator doesn't exist, show an exception
        if not path.exists(custom_evaluator_path):
            return None

        # Read raw content of .py file
        with open(custom_evaluator_path, "r") as fp:
            # Compile the code into bytecode
            evaluator_script = compile(fp.read(), "<string>", "exec")

            # Create a new module
            evaluator_module = cls("evaluation", config)

            # Build the bytecode & add to the new module
            exec(evaluator_script, evaluator_module.__dict__)

            return evaluator_module
