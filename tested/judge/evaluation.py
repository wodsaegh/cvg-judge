import html
import logging
from enum import StrEnum, unique
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple

from tested.configs import Bundle
from tested.dodona import (
    AppendMessage,
    CloseContext,
    CloseJudgment,
    CloseTab,
    CloseTest,
    CloseTestcase,
    EscalateStatus,
    ExtendedMessage,
    Message,
    StartContext,
    StartJudgment,
    StartTab,
    StartTest,
    StartTestcase,
    Status,
    StatusMessage,
    Update,
)
from tested.evaluators import get_evaluator
from tested.internationalization import get_i18n_string
from tested.judge.collector import OutputManager, TestcaseCollector
from tested.judge.execution import ContextResult
from tested.languages.generator import (
    attempt_readable_input,
    convert_statement,
    get_readable_input,
)
from tested.testsuite import (
    Context,
    ExceptionOutput,
    ExceptionOutputChannel,
    ExitCodeOutputChannel,
    FileOutput,
    FileOutputChannel,
    FileUrl,
    IgnoredChannel,
    OutputChannel,
    SpecialOutputChannel,
    TextOutput,
    TextOutputChannel,
    ValueOutput,
    ValueOutputChannel,
)
from tested.utils import get_args, safe_del, safe_get

_logger = logging.getLogger(__name__)


@unique
class Channel(StrEnum):
    """
    The different output channels.
    """

    FILE = "file"
    EXCEPTION = "exception"
    STDOUT = "stdout"
    STDERR = "stderr"
    EXIT = "exit code"
    RETURN = "return"


def _evaluate_channel(
    bundle: Bundle,
    context_directory: Path,
    out: TestcaseCollector,
    channel: Channel,
    output: OutputChannel,
    actual: Optional[str],
    unexpected_status: Status = Status.WRONG,
    timeout: bool = False,
    memory: bool = False,
) -> Optional[bool]:
    """
    Evaluate the output on a given channel. This function will output the
    appropriate messages to start and end a new test in Dodona.

    Depending on the channel, the result might not be outputted to Dodona. For
    example, if an exit code is 0 and also expected to be 0, it will not be shown,
    as it is assumed to be an implicit test. There is currently no way to override
    this.

    If the actual result is None, this means something went wrong while executing
    the code (like a premature exit call). A message will be added and the channel
    will be shown, regardless of value.

    :param out: The output file for the judge.
    :param channel: The name of the channel being evaluated. Will be
                         displayed in Dodona.
    :param output: The output channel from the test case.
    :param actual: The actual output or None if the result is missing.
    :param bundle: The configuration bundle.
    :param context_directory: The directory in which the execution took place.

    :return: True if successful, otherwise False.
    """
    evaluator = get_evaluator(
        bundle, context_directory, output, unexpected_status=unexpected_status
    )
    # Run the evaluator.
    evaluation_result = evaluator(output, actual if actual else "")
    status = evaluation_result.result

    # Decide if we should show this channel or not.
    is_correct = status.enum == Status.CORRECT

    if not should_show(output, channel) and is_correct:
        return True

    expected: str
    if (
        not isinstance(output, get_args(SpecialOutputChannel))
        and not output.show_expected
        and not is_correct
    ):
        expected = ""
        evaluation_result.messages.append(
            ExtendedMessage(
                description=get_i18n_string("judge.evaluation.hidden_expected")
            )
        )
    else:
        expected = evaluation_result.readable_expected

    channel_test = (
        "return (String)"
        if (channel is Channel.RETURN and evaluation_result.is_multiline_string)
        else channel
    )

    out.add(StartTest(expected=expected, channel=channel_test))

    # Report any messages we received.
    for message in evaluation_result.messages:
        out.add(AppendMessage(message=message))

    # Report missing output
    if actual is None:
        out.add(AppendMessage(message=get_i18n_string("judge.evaluation.early-exit")))
    elif should_show(output, channel) and timeout and not is_correct:
        status.human = get_i18n_string("judge.evaluation.time-limit")
        status.enum = Status.TIME_LIMIT_EXCEEDED
        out.add(AppendMessage(message=status.human))
    elif should_show(output, channel) and memory and not is_correct:
        status.human = get_i18n_string("judge.evaluation.memory-limit")
        status.enum = Status.TIME_LIMIT_EXCEEDED
        out.add(AppendMessage(message=status.human))

    # Close the test.
    out.add(CloseTest(generated=evaluation_result.readable_actual, status=status))

    return is_correct


def evaluate_context_results(
    bundle: Bundle,
    context: Context,
    exec_results: Optional[ContextResult],
    compiler_results: Tuple[List[Message], Status],
    context_dir: Path,
    collector: OutputManager,
) -> Optional[Status]:
    """
    Evaluate the results for a single context.

    This function is called for each context of the test suite, even if there
    are no results for the context in question.

    :param bundle: The configuration bundle.
    :param context: The context to evaluate.
    :param exec_results: The results of evaluating the context.
    :param compiler_results: The compiler results.
    :param context_dir: The directory where the execution happened.
    :param collector: Where to put the output
    :return: A status if of interest to the caller.
    """

    # If the compiler results are not successful, there is no point in doing more,
    # so stop early.
    if compiler_results[1] != Status.CORRECT:
        readable_input = attempt_readable_input(bundle, context)
        collector.add(StartTestcase(description=readable_input))
        # Report all compiler messages.
        for message in compiler_results[0]:
            collector.add(AppendMessage(message=message))
        # Escalate the compiler status to every testcase.
        collector.add(EscalateStatus(status=StatusMessage(enum=compiler_results[1])))

        # Finish evaluation, since there is nothing we can do.
        collector.add(CloseTestcase(accepted=False))
        return compiler_results[1]

    # There must be execution if compilation succeeded.
    assert exec_results is not None

    # Split the basic output channels.
    stdout_ = exec_results.stdout.split(exec_results.separator)
    stderr_ = exec_results.stderr.split(exec_results.separator)
    exceptions = exec_results.exceptions.split(exec_results.separator)
    values = exec_results.results.split(exec_results.separator)

    # The first item should always be empty, since the separator must be printed
    # before the test suite runs. We remove the first item; for stdout and stderr
    # we only remove the first item if it is indeed empty. This is to keep error
    # messages present for debugging.

    deletions = (
        safe_del(stdout_, 0, lambda e: e == ""),
        safe_del(stderr_, 0, lambda e: e == ""),
        safe_del(exceptions, 0, lambda e: e == ""),
        safe_del(values, 0, lambda e: e == ""),
    )

    could_delete = all(deletions)

    # Add a message indicating there were missing values.
    missing_values = []
    if not could_delete:
        _logger.warning("Missing output in context testcase.")
        missing_values.append(
            AppendMessage(get_i18n_string("judge.evaluation.early-exit"))
        )
        missing_values.append(
            EscalateStatus(
                status=StatusMessage(
                    enum=Status.WRONG,
                    human=get_i18n_string("judge.evaluation.missing.output"),
                )
            )
        )
        # Recover stdout and stderr if present.
        if recovered := "\n".join(stdout_):
            missing_values.append(
                AppendMessage(
                    ExtendedMessage(
                        description="Standaarduitvoer was:\n" + recovered, format="code"
                    )
                )
            )
        if recovered := "\n".join(stderr_):
            missing_values.append(
                AppendMessage(
                    ExtendedMessage(
                        description="Standaardfout was:\n" + recovered, format="code"
                    )
                )
            )

    collectors = []
    inlined_files: Set[FileUrl] = set()

    # Begin processing the normal testcases.
    for i, testcase in enumerate(context.testcases):
        _logger.debug(f"Evaluating testcase {i}")

        readable_input, seen = get_readable_input(bundle, context.link_files, testcase)
        inlined_files = inlined_files.union(seen)
        t_col = TestcaseCollector(StartTestcase(description=readable_input))

        # Get the evaluators
        output = testcase.output

        # Get the values produced by the execution. If there are no values,
        # we use an empty string at this time. We handle missing output later.
        actual_stderr = safe_get(stderr_, i)
        actual_exception = safe_get(exceptions, i)
        actual_stdout = safe_get(stdout_, i)
        actual_value = safe_get(values, i)

        _evaluate_channel(
            bundle,
            context_dir,
            t_col,
            Channel.FILE,
            output.file,
            "",
            timeout=exec_results.timeout,
            memory=exec_results.memory,
        )
        _evaluate_channel(
            bundle,
            context_dir,
            t_col,
            Channel.STDERR,
            output.stderr,
            actual_stderr,
            timeout=exec_results.timeout and len(stderr_) == i + 1,
            memory=exec_results.memory and len(stderr_) == i + 1,
        )
        _evaluate_channel(
            bundle,
            context_dir,
            t_col,
            Channel.EXCEPTION,
            output.exception,
            actual_exception,
            unexpected_status=Status.RUNTIME_ERROR,
            timeout=exec_results.timeout and len(exceptions) == i + 1,
            memory=exec_results.memory and len(exceptions) == i + 1,
        )
        _evaluate_channel(
            bundle,
            context_dir,
            t_col,
            Channel.STDOUT,
            output.stdout,
            actual_stdout,
            timeout=exec_results.timeout and len(stdout_) == i + 1,
            memory=exec_results.memory and len(stdout_) == i + 1,
        )
        _evaluate_channel(
            bundle,
            context_dir,
            t_col,
            Channel.RETURN,
            output.result,
            actual_value,
            timeout=exec_results.timeout and len(values) == i + 1,
            memory=exec_results.memory and len(values) == i + 1,
        )

        # If this is the last testcase, do the exit channel.
        if i == len(context.testcases) - 1:
            _evaluate_channel(
                bundle,
                context_dir,
                t_col,
                Channel.EXIT,
                testcase.output.exit_code,
                str(exec_results.exit),
                timeout=exec_results.timeout,
                memory=exec_results.memory,
            )
        else:
            assert (
                testcase.output.exit_code == IgnoredChannel.IGNORED
            ), "Only the last testcase may check the exit code."

        # Add messages if there was no output.
        if missing_values:
            for u in missing_values:
                t_col.add(u)

        collectors.append(t_col)

    # Add file links
    non_inlined = set(context.link_files).difference(inlined_files)
    if non_inlined:
        _link_files_message(non_inlined, collector)

    # Add all testcases to collector
    for t_col in collectors:
        t_col.to_manager(collector, CloseTestcase())

    if exec_results.timeout:
        return Status.TIME_LIMIT_EXCEEDED
    if exec_results.memory:
        return Status.MEMORY_LIMIT_EXCEEDED
    return None


def _link_files_message(
    link_files: Iterable[FileUrl], collector: Optional[OutputManager] = None
) -> Optional[AppendMessage]:
    link_list = ", ".join(
        f'<a href="{link_file.url}" class="file-link" target="_blank">'
        f'<span class="code">{html.escape(link_file.name)}</span></a>'
        for link_file in link_files
    )
    file_list_str = get_i18n_string(
        "judge.evaluation.files", count=len(link_files), files=link_list
    )
    description = f"<div class='contains-file''><p>{file_list_str}</p></div>"
    message = ExtendedMessage(description=description, format="html")
    if collector is not None:
        collector.add(AppendMessage(message=message))
        return None
    else:
        return AppendMessage(message=message)


def should_show(test: OutputChannel, channel: Channel) -> bool:
    """
    Determine if the channel should be shown, without accounting for the actual
    value. This function answers the question: "Assuming the actual value is
    correct, should we show this output channel?".

    :param test: The output for the channel from the test suite.
    :param channel: The channel.

    :return: True if the channel should be shown, false otherwise.
    """
    if channel == Channel.EXIT:
        if test == IgnoredChannel.IGNORED:
            return False
        assert isinstance(test, get_args(ExitCodeOutputChannel))
        return test.value != 0
    elif channel in (Channel.STDOUT, Channel.STDERR):
        assert isinstance(test, get_args(TextOutput))
        # We don't show the channel if the output is nothing or ignored.
        return not isinstance(test, get_args(SpecialOutputChannel))
    elif channel == Channel.FILE:
        assert isinstance(test, get_args(FileOutput))
        # We don't show the channel if we ignore the channel.
        return not isinstance(test, IgnoredChannel)
    elif channel == Channel.RETURN:
        assert isinstance(test, get_args(ValueOutput))
        # We don't show the channel if we ignore it or expect no result.
        return not isinstance(test, get_args(SpecialOutputChannel))
    elif channel == Channel.EXCEPTION:
        assert isinstance(test, get_args(ExceptionOutput))
        return not isinstance(test, get_args(SpecialOutputChannel))
    else:
        raise AssertionError(f"Unknown channel {channel}")


def guess_expected_value(bundle: Bundle, test: OutputChannel) -> str:
    """
    Try and get the expected value for an output channel. In some cases, such as
    a programmed or language specific evaluator, there will be no expected value
    available in the test suite. In that case, we use an empty string.

    :param bundle: Configuration bundle.
    :param test: The output channel.

    :return: A best effort attempt of the expected value.
    """
    if isinstance(test, get_args(SpecialOutputChannel)):
        return ""
    elif isinstance(test, TextOutputChannel):
        return test.get_data_as_string(bundle.config.resources)
    elif isinstance(test, FileOutputChannel):
        return test.get_data_as_string(bundle.config.resources)
    elif isinstance(test, ExceptionOutputChannel):
        return (
            test.exception.message
            if test.exception
            else get_i18n_string("judge.evaluation.dynamic")
        )
    elif isinstance(test, ValueOutputChannel):
        return (
            convert_statement(bundle, test.value)
            if test.value
            else get_i18n_string("judge.evaluation.dynamic")
        )
    elif isinstance(test, ExitCodeOutputChannel):
        return str(test.value)
    _logger.warn(f"Unknown output type {test}")
    return ""


def _add_channel(
    bundle: Bundle, output: OutputChannel, channel: Channel, updates: List[Update]
):
    """Add a channel to the output if it should be shown."""
    if should_show(output, channel):
        updates.append(
            StartTest(expected=guess_expected_value(bundle, output), channel=channel)
        )
        updates.append(
            CloseTest(
                generated="",
                status=StatusMessage(
                    enum=Status.NOT_EXECUTED,
                    human=get_i18n_string("judge.evaluation.missing.test"),
                ),
                accepted=False,
            )
        )


def prepare_evaluation(bundle: Bundle, collector: OutputManager):
    """
    Generate output depicting the expected test suite. This output will be shown if
    the normal execution terminates early for some reason. This function assumes
    the output is OK, but does not accept anything.

    :param bundle: The configuration bundle.
    :param collector: The output collector.
    """
    collector.prepare_judgment(StartJudgment())
    for i, tab in enumerate(bundle.suite.tabs):
        collector.prepare_tab(StartTab(title=tab.name, hidden=tab.hidden), i)

        for j, context in enumerate(tab.contexts):
            updates = []

            collector.prepare_context(
                StartContext(description=context.description), i, j
            )
            updates.append(
                AppendMessage(
                    message=get_i18n_string("judge.evaluation.missing.context")
                )
            )

            inlined_files: Set[FileUrl] = set()
            # Begin normal testcases.
            for t, testcase in enumerate(context.testcases):
                readable_input, seen = get_readable_input(
                    bundle, context.link_files, testcase
                )
                inlined_files = inlined_files.union(seen)
                updates.append(StartTestcase(description=readable_input))

                # Do the normal output channels.
                output = testcase.output
                _add_channel(bundle, output.stdout, Channel.STDOUT, updates)
                _add_channel(bundle, output.stderr, Channel.STDERR, updates)
                _add_channel(bundle, output.file, Channel.FILE, updates)
                _add_channel(bundle, output.exception, Channel.EXCEPTION, updates)
                _add_channel(bundle, output.result, Channel.RETURN, updates)

                # If last testcase, do exit code.
                if j == len(tab.contexts) - 1:
                    _add_channel(bundle, output.exit_code, Channel.EXIT, updates)

                updates.append(CloseTestcase(accepted=False))

            # Add file links
            non_inlined = set(context.link_files).difference(inlined_files)
            if non_inlined:
                updates.insert(0, _link_files_message(non_inlined))

            collector.prepare_context(updates, i, j)
            collector.prepare_context(CloseContext(accepted=False), i, j)
        collector.prepare_tab(CloseTab(), i)
    collector.prepare_judgment(CloseJudgment(accepted=False))
