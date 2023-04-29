from validators.checks import HtmlSuite, TestSuite, ChecklistItem, BoilerplateTestSuite, Check, CVGSuite
from bs4 import BeautifulSoup
from utils.file_loaders import json_loader
import json
import numpy as np
import ast


def create_suites(content: str, solution: str) -> list[TestSuite]:
    cvg = CVGSuite(content, solution)
    cvg.make_item("Vergelijk het aantal codeblokken",
                  cvg.compare_nodeslength())
    cvg.make_item("Vergelijk het aantal pijlen", cvg.compare_edgeslength())
    cvg.make_item("Vergelijk de nodes", cvg.correct_nodes())
    cvg.make_item("Vergelijk de edges", cvg.correct_edges())
    cvg.make_item("Vergelijk de stippel", cvg.correct_stippel())
    cvg.make_item("Juiste CVG", cvg.correct_CVG())

    return [cvg]
