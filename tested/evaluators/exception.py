"""
Exception evaluator.
"""
import logging
from typing import Optional, Tuple

from pydantic import BaseModel

from tested.dodona import ExtendedMessage, Permission, Status, StatusMessage
from tested.evaluators.common import EvaluationResult, EvaluatorConfig
from tested.internationalization import get_i18n_string
from tested.serialisation import ExceptionValue
from tested.testsuite import ExceptionOutputChannel
from tested.utils import Either

logger = logging.getLogger(__name__)


class _ExceptionValue(BaseModel):
    __root__: ExceptionValue


def try_as_exception(config: EvaluatorConfig, value: str) -> Either[ExceptionValue]:
    try:
        actual = _ExceptionValue.parse_raw(value).__root__
        actual = config.bundle.lang_config.exception_output(config.bundle, actual)
        return Either(actual)
    except (TypeError, ValueError) as e:
        return Either(e)


def try_as_readable_exception(
    config: EvaluatorConfig, value: str
) -> Tuple[Optional[str], Optional[ExtendedMessage]]:
    try:
        actual = _ExceptionValue.parse_raw(value).__root__
        actual = config.bundle.lang_config.exception_output(config.bundle, actual)
    except (TypeError, ValueError):
        return None, None
    else:
        readable = actual.readable()
        message = config.bundle.lang_config.clean_stacktrace_to_message(
            actual.stacktrace
        )
        return readable, message


def evaluate(
    config: EvaluatorConfig, channel: ExceptionOutputChannel, actual: str
) -> EvaluationResult:
    """
    Evaluate an exception.

    :param config: Not used.
    :param channel: The channel from the test suite.
    :param actual: The raw actual value of the execution.

    :return: An evaluation result.
    """
    assert isinstance(channel, ExceptionOutputChannel)
    assert channel.exception is not None

    expected = channel.exception

    if not actual:
        return EvaluationResult(
            result=StatusMessage(enum=Status.WRONG),
            readable_expected=expected.readable(),
            readable_actual="",
            messages=[],
        )

    try:
        actual = try_as_exception(config, actual).get()
    except (TypeError, ValueError) as e:
        staff_message = ExtendedMessage(
            description=get_i18n_string(
                "evaluators.exception.staff", actual=actual, exception=e
            ),
            format="text",
            permission=Permission.STAFF,
        )
        student_message = get_i18n_string("evaluators.exception.student")
        return EvaluationResult(
            result=StatusMessage(
                enum=Status.INTERNAL_ERROR,
                human=get_i18n_string("evaluators.exception.status"),
            ),
            readable_expected=expected.readable(),
            readable_actual="",
            messages=[staff_message, student_message],
        )

    message = config.bundle.lang_config.clean_stacktrace_to_message(actual.stacktrace)
    if message:
        messages = [message]
    else:
        messages = []

    if actual.tested is not None:
        # noinspection PyArgumentList
        messages.append(
            get_i18n_string(actual.tested.i18n_key, **actual.tested.variables)
        )
        status = Status.WRONG
    else:
        status = Status.CORRECT if expected.message == actual.message else Status.WRONG

    return EvaluationResult(
        result=StatusMessage(enum=status),
        readable_expected=expected.readable(),
        readable_actual=actual.readable(),
        messages=messages,
    )
