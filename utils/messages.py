from types import SimpleNamespace

from dodona.dodona_command import Message, MessageFormat, ErrorType, MessagePermission
from dodona.dodona_config import DodonaConfig
from dodona.translator import Translator
import traceback


def invalid_suites(judge: SimpleNamespace, config: DodonaConfig):
    """Show the students a message saying that the suites were invalid"""
    with Message(
            description=config.translator.translate(Translator.Text.INVALID_TESTSUITE_STUDENTS),
            format=MessageFormat.TEXT
    ):
        pass

    judge.status = config.translator.error_status(ErrorType.RUNTIME_ERROR)
    judge.accepted = False


def invalid_evaluator_file(exception: Exception):
    """Show the teacher a message saying that their evaluator file is invalid"""
    with Message(
            permission=MessagePermission.STAFF,
            description=traceback.format_exc(),
            format=MessageFormat.CODE
    ):
        pass


def missing_evaluator_file(translator: Translator):
    """Show the teacher a message saying that the evaluator file is missing"""
    with Message(
            permission=MessagePermission.STAFF,
            description=translator.translate(Translator.Text.MISSING_EVALUATION_FILE),
            format=MessageFormat.TEXT
    ):
        pass


def missing_create_suite(translator: Translator):
    with Message(
            permission=MessagePermission.STAFF,
            description=translator.translate(Translator.Text.MISSING_CREATE_SUITE),
            format=MessageFormat.TEXT
    ):
        pass


def no_suites_found(translator: Translator):
    with Message(
        permission=MessagePermission.STAFF,
        description=translator.translate(Translator.Text.MISSING_SUITES),
        format=MessageFormat.TEXT
    ):
        pass
