import os
import sys
import json
from typing import List, Optional

from dodona.dodona_command import Judgement, Message, ErrorType, Tab, MessageFormat
from dodona.dodona_config import DodonaConfig
from dodona.translator import Translator
from exceptions.utils import InvalidTranslation
from utils.evaluation_module import EvaluationModule
from utils.file_loaders import json_loader
from validators import checks
from validators.checks import TestSuite
from utils.render_ready import prep_render
from utils.messages import invalid_suites, invalid_evaluator_file, missing_create_suite, missing_evaluator_file, no_suites_found


def main():
    """
    Main judge method
    """
    # Read config JSON from stdin

    config = DodonaConfig.from_json(sys.stdin)

    with Judgement() as judge:
        # Counter for failed tests because this judge works a bit differently
        # Allows nicer feedback on Dodona (displays amount of failed tests)
        failed_tests = 0

        # Initiate translator
        config.translator = Translator.from_str(config.natural_language)
        # Load HTML
        json_content: str = json_loader(config.source, shorted=False)
        nodes = json_content["nodes"]

        # Compile evaluator code & create test suites
        # If anything goes wrong, show a detailed error message to the teacher
        # and a short message to the student
        try:
            evaluator: Optional[EvaluationModule] = EvaluationModule.build(
                config)
            if evaluator is not None:
                test_suites: List[TestSuite] = evaluator.create_suites(
                    str(json_content))
            else:
                solution = json_loader(os.path.join(
                    config.resources, "./solution.json"))
                if not solution:
                    missing_evaluator_file(config.translator)
                    invalid_suites(judge, config)
                    return
                # compare(sol, html_content, config.translator)
                suite = checks._CompareSuite(
                    json_content, solution, config, check_recommended=getattr(config, "recommended", True))
                test_suites = [suite]
        except FileNotFoundError:
            # solution.html is missing
            missing_evaluator_file(config.translator)
            invalid_suites(judge, config)
            return
        except NotImplementedError:
            # Evaluator.py file doesn't implement create_suites
            missing_create_suite(config.translator)
            invalid_suites(judge, config)
            return
        except Exception as e:
            # Something else went wrong
            invalid_evaluator_file(e)
            invalid_suites(judge, config)
            return

        # No suites found, either no return or an empty list
        if test_suites is None or not test_suites:
            no_suites_found(config.translator)
            invalid_suites(judge, config)
            return

        # Has HTML been validated at least once?
        # Same HTML is used every time so once is enough
        html_validated: bool = False
        css_validated: bool = False
        aborted: bool = False

        # Run all test suites
        for suite in test_suites:
            print
            suite.create_validator(config)

            with Tab(suite.name):
                try:
                    failed_tests += suite.evaluate(config.translator)
                except InvalidTranslation:
                    # One of the translations was invalid
                    invalid_suites(judge, config)

                    aborted = True
                    continue

        if aborted:
            judge.status = config.translator.error_status(
                ErrorType.RUNTIME_ERROR)
            judge.accepted = False
        else:
            status = ErrorType.CORRECT_ANSWER if failed_tests == 0 else ErrorType.WRONG if failed_tests == 1 else ErrorType.WRONG_ANSWER
            judge.status = config.translator.error_status(
                status, amount=failed_tests)


if __name__ == "__main__":
    main()
