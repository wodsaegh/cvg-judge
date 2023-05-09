from validators.checks import HtmlSuite, TestSuite, ChecklistItem, BoilerplateTestSuite, Check, CVGSuite
from bs4 import BeautifulSoup
from utils.file_loaders import json_loader
import json
import numpy as np
import ast


def create_suites(content: str, solution: str) -> list[TestSuite]:
    cvg = CVGSuite(content, solution)
    cvg.make_item("Het aantal codeblokken is juist",
                  cvg.compare_nodeslength())
    cvg.make_item("De codeblokken zijn juist ingevuld", cvg.correct_nodes())
    cvg.make_item("Het aantal pijlen is juist", cvg.compare_edgeslength())
    cvg.make_item("De pijlen staan in de juiste richting", cvg.correct_edges())
    cvg.make_item("Er staat een doorvalpad waar een doorvalpad moet staan en een sprong waar een sprong moet staan", cvg.correct_stippel())
    cvg.make_item("De controleverloopgraaf is helemaal juist", cvg.correct_CVG())

    return [cvg]
