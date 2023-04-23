"""translate judge output towards Dodona"""

from enum import Enum, auto
from typing import Dict

from dodona.dodona_command import ErrorType


class Translator:
    """a class for translating all user feedback
    The Translator class provides translations for a set of Text
    messages and for the Dodona error types.
    """

    class Language(Enum):
        """Language"""

        EN = auto()
        NL = auto()

    class Text(Enum):
        """Text message content enum"""

        MISSING_EVALUATION_FILE = auto()
        MISSING_CREATE_SUITE = auto()
        MISSING_SUITES = auto()
        TESTCASE_ABORTED = auto()
        TESTCASE_NO_LONGER_EVALUATED = auto()
        FAILED_TESTS = auto()
        INVALID_LANGUAGE_TRANSLATION = auto()
        INVALID_TESTSUITE_STUDENTS = auto()
        EVALUATION_FAILED = auto()
        # double char exceptions
        MISSING_OPENING_CHARACTER = auto()
        MISSING_CLOSING_CHARACTER = auto()
        # html exceptions
        MISSING_OPENING_TAG = auto()
        MISSING_CLOSING_TAG = auto()
        INVALID_TAG = auto()
        NO_SELF_CLOSING_TAG = auto()
        UNEXPECTED_TAG = auto()
        UNEXPECTED_CLOSING_TAG = auto()
        INVALID_ATTRIBUTE = auto()
        MISSING_REQUIRED_ATTRIBUTE = auto()
        DUPLICATE_ID = auto()
        AT_LEAST_ONE_CHAR = auto()
        NO_WHITESPACE = auto()
        NO_ABS_PATHS = auto()
        MISSING_RECOMMENDED_ATTRIBUTE = auto()
        AMBIGUOUS_XPATH = auto()
        # comparer text
        EMPTY_SUBMISSION = auto()
        TAGS_DIFFER = auto()
        ATTRIBUTES_DIFFER = auto()
        NOT_ALL_ATTRIBUTES_PRESENT = auto()
        CONTENTS_DIFFER = auto()
        AMOUNT_CHILDREN_DIFFER = auto()
        STYLES_DIFFER = auto()
        EXPECTED_COMMENT = auto()
        COMMENT_CORRECT_TEXT = auto()
        AT_LINE = auto()
        SIMILARITY = auto()
        # normal text
        ERRORS = auto()
        WARNINGS = auto()
        LOCATED_AT = auto()
        LINE = auto()
        POSITION = auto()
        SUBMISSION = auto()

    def __init__(self, language: Language):
        self.language = language

    @classmethod
    def from_str(cls, language: str) -> "Translator":
        """created a Translator instance
        If the language is not detected correctly or not supported
        the translator defaults to English (EN).
        :param language: Dodona language string "nl" or "en"
        :return: translator
        """
        if language == "nl":
            return cls(cls.Language.NL)

        # default value is EN
        return cls(cls.Language.EN)

    def human_error(self, error: ErrorType) -> str:
        """translate an ErrorType enum into a human-readable string
        :param error: ErrorType enum
        :return: translated human-readable string
        """
        return self.error_translations[self.language][error]

    def error_status(self, error: ErrorType, **kwargs) -> Dict[str, str]:
        """translate an ErrorType enum into a status object
        :param error: ErrorType enum
        :return: Dodona status object
        """
        return {
            "enum": error,
            "human": self.human_error(error).format(**kwargs),
        }

    def translate(self, message: Text, **kwargs) -> str:
        """translate a Text enum into a string
        :param message: Text enum
        :param kwargs: parameters for message
        :return: translated text
        """
        return self.text_translations[self.language][message].format(**kwargs)

    error_translations = {
        Language.EN: {
            ErrorType.INTERNAL_ERROR: "Internal error",
            ErrorType.COMPILATION_ERROR: "The code is not valid",
            ErrorType.MEMORY_LIMIT_EXCEEDED: "Memory limit exceeded",
            ErrorType.TIME_LIMIT_EXCEEDED: "Time limit exceeded",
            ErrorType.OUTPUT_LIMIT_EXCEEDED: "Output limit exceeded",
            ErrorType.RUNTIME_ERROR: "Crashed while testing",
            ErrorType.WRONG: "Test failed",
            ErrorType.WRONG_ANSWER: "{amount} tests failed",
            ErrorType.CORRECT: "All tests succeeded",
            ErrorType.CORRECT_ANSWER: "All tests succeeded",
        },
        Language.NL: {
            ErrorType.INTERNAL_ERROR: "Interne fout",
            ErrorType.COMPILATION_ERROR: "Ongeldige code",
            ErrorType.MEMORY_LIMIT_EXCEEDED: "Geheugenlimiet overschreden",
            ErrorType.TIME_LIMIT_EXCEEDED: "Tijdslimiet overschreden",
            ErrorType.OUTPUT_LIMIT_EXCEEDED: "Outputlimiet overschreden",
            ErrorType.RUNTIME_ERROR: "Gecrasht bij testen",
            ErrorType.WRONG: "Test gefaald",
            ErrorType.WRONG_ANSWER: "{amount} testen gefaald",
            ErrorType.CORRECT: "Alle testen geslaagd",
            ErrorType.CORRECT_ANSWER: "Alle testen geslaagd",
        },
    }

    text_translations = {
        Language.EN: {
            Text.MISSING_EVALUATION_FILE: "The evaluator.py and solution.html files are missing.",
            Text.MISSING_CREATE_SUITE: "The evaluator.py file does not implement the 'create_suites(content)' method.",
            Text.MISSING_SUITES: "The 'create_suites(content)' method in the evaluator.py-file did not return any evaluation suites.",
            Text.TESTCASE_ABORTED: "Evaluation was aborted because this test failed. All subsequent tests were not executed.",
            Text.TESTCASE_NO_LONGER_EVALUATED: "This test was not evaluated.",
            Text.FAILED_TESTS: "{amount} test(s) failed.",
            Text.INVALID_LANGUAGE_TRANSLATION: "Translation for language {language} has less items than the checklist ({translation} instead of {checklist}). Some items will use the default value.",
            Text.INVALID_TESTSUITE_STUDENTS: "Your submission could not be evaluated because of an error in the solution file.",
            Text.EVALUATION_FAILED: "This check could not be executed successfully. Make sure that the HTML in your submission is valid.",
            # double char exceptions
            Text.MISSING_OPENING_CHARACTER: "Missing opening character for",
            Text.MISSING_CLOSING_CHARACTER: "Missing closing character for",
            # html exceptions
            Text.MISSING_OPENING_TAG: "Missing opening HTML tag for",
            Text.MISSING_CLOSING_TAG: "Missing closing HTML tag for",
            Text.INVALID_TAG: "Invalid HTML tag",
            Text.NO_SELF_CLOSING_TAG: "The following tag is not a self-closing HTML tag",
            Text.UNEXPECTED_TAG: "Unexpected HTML tag",
            Text.UNEXPECTED_CLOSING_TAG: "The tag <{tag}> isn't supposed to have a closing tag, it's self-closing.",
            Text.INVALID_ATTRIBUTE: "Invalid attribute for",
            Text.MISSING_REQUIRED_ATTRIBUTE: "Missing required attribute(s) for",
            Text.DUPLICATE_ID: "Id '{id}' defined in tag <{tag}> is already defined",
            Text.AT_LEAST_ONE_CHAR: "The value of {attr} must be at least one character.",
            Text.NO_WHITESPACE: "The value of {attr} may not contain whitespace.",
            Text.NO_ABS_PATHS: "The src attribute may not contain an absolute path.",
            Text.MISSING_RECOMMENDED_ATTRIBUTE: "Missing recommended attribute(s) for",
            Text.AMBIGUOUS_XPATH: "We were unable to unambiguously locate this element. Make sure the submission is wrapped in a single root element.",
            # comparer text
            Text.EMPTY_SUBMISSION: "The submission is empty.",
            Text.TAGS_DIFFER: "Tags differ",
            Text.ATTRIBUTES_DIFFER: "Attributes differ",
            Text.NOT_ALL_ATTRIBUTES_PRESENT: "Not all minimal required attributes are present",
            Text.CONTENTS_DIFFER: "Contents differ",
            Text.AMOUNT_CHILDREN_DIFFER: "Amount of child elements differs",
            Text.STYLES_DIFFER: "CSS styling differs for element <{tag}>",
            Text.EXPECTED_COMMENT: "Expected a comment",
            Text.COMMENT_CORRECT_TEXT: "The comment does not have the correct text",
            Text.AT_LINE: "at line",
            Text.SIMILARITY: " similarity",
            # normal text
            Text.ERRORS: "Error(s)",
            Text.WARNINGS: "Warning(s)",
            Text.LOCATED_AT: "located at",
            Text.LINE: "line",
            Text.POSITION: "position",
            Text.SUBMISSION: "Submission"
        },
        Language.NL: {
            Text.MISSING_EVALUATION_FILE: "De evaluator.py en solution.html bestanden ontbreken.",
            Text.MISSING_CREATE_SUITE: "Het evaluator.py-bestand bevat de 'create_suites(content)'-methode niet.",
            Text.MISSING_SUITES: "De 'create_suites(content)'-methode in het evaluator.py-bestand returnde geen test suites.",
            Text.TESTCASE_ABORTED: "Het evalueren is onderbroken omdat deze test faalde. De hierop volgende tests werden niet uitgevoerd.",
            Text.TESTCASE_NO_LONGER_EVALUATED: "Deze test werd niet uitgevoerd.",
            Text.FAILED_TESTS: "{amount} test(en) gefaald.",
            Text.INVALID_LANGUAGE_TRANSLATION: "De vertaling voor {language} bevat minder elementen dan de checklist ({translation} in plaats van {checklist}). De default waarde zal worden gebruikt voor sommige items.",
            Text.INVALID_TESTSUITE_STUDENTS: "Jouw indiening kon niet geëvalueerd worden door een fout in het oplossingsbestand.",
            Text.EVALUATION_FAILED: "Deze test kon niet uitgevoerd worden. Controleer dat de HTML in de indiening geldig is.",
            # double char exceptions
            Text.MISSING_OPENING_CHARACTER: "Ontbrekend openend karakter voor",
            Text.MISSING_CLOSING_CHARACTER: "Ontbrekend sluitend karakter voor",
            # html exceptions
            Text.MISSING_OPENING_TAG: "Ontbrekende openende HTML-tag voor",
            Text.MISSING_CLOSING_TAG: "Ontbrekende sluitende HTML-tag voor",
            Text.INVALID_TAG: "Ongeldige HTML-tag",
            Text.NO_SELF_CLOSING_TAG: "De volgende HTML-tag is geen zelf-afsluitende HTML-tag",
            Text.UNEXPECTED_TAG: "Onverwachte HTML-tag",
            Text.UNEXPECTED_CLOSING_TAG: "De tag <{tag}> hoort geen sluitende tag te hebben, het is een zichzelf-afsluitende tag.",
            Text.INVALID_ATTRIBUTE: "Ongeldig attribuut voor",
            Text.MISSING_REQUIRED_ATTRIBUTE: "Ontbrekende vereiste attributen voor",
            Text.DUPLICATE_ID: "Id '{id}' gedefinieerd in tag <{tag}> is al gedefinieerd",
            Text.AT_LEAST_ONE_CHAR: "De waarde van {attr} moet minimaal 1 karakter lang zijn.",
            Text.NO_WHITESPACE: "De waarde van {attr} mag geen spaties bevatten.",
            Text.NO_ABS_PATHS: "Het attribuut src mag geen absoluut pad zijn.",
            Text.MISSING_RECOMMENDED_ATTRIBUTE: "Ontbrekende aanbevolen attributen voor",
            Text.AMBIGUOUS_XPATH: "Dit HTML-element kon niet ondubbelzinnig gevonden worden. Zorg dat er slechts één enkele omsluitende tag op het hoogste niveau van de indiening is.",
            # comparer text
            Text.EMPTY_SUBMISSION: "De indiening was leeg.",
            Text.TAGS_DIFFER: "Tags verschillen",
            Text.ATTRIBUTES_DIFFER: "Attributen verschillen",
            Text.NOT_ALL_ATTRIBUTES_PRESENT: "Niet alle minimaal vereiste attributen zijn aanwezig",
            Text.CONTENTS_DIFFER: "Inhoud (text) verschilt",
            Text.AMOUNT_CHILDREN_DIFFER: "Aantal kind elementen verschilt",
            Text.STYLES_DIFFER: "CSS-opmaak verschilt voor element <{tag}>",
            Text.EXPECTED_COMMENT: "Verwachte een comment",
            Text.COMMENT_CORRECT_TEXT: "De comment heeft niet de correcte tekst",
            Text.AT_LINE: "op regel",
            Text.SIMILARITY: "-gelijkaardigheid",
            # normal text
            Text.ERRORS: "Fout(en)",
            Text.WARNINGS: "Waarschuwing(en)",
            Text.LOCATED_AT: "gevonden op",
            Text.LINE: "regel",
            Text.POSITION: "positie",
            Text.SUBMISSION: "Indiening"
        }
    }
