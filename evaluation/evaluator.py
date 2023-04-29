from validators.checks import HtmlSuite, TestSuite, ChecklistItem, BoilerplateTestSuite, Check
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


class CVGSuite(BoilerplateTestSuite):
    """TestSuite that does HTML validation by default"""
    allow_warnings: bool
    solution_content: str

    cont_nodes: list
    cont_edges: list

    sol_nodes: list
    sol_edges: list
    succes_tests: bool

    def __init__(self, content: str, solution: str, check_recommended: bool = True, allow_warnings: bool = True, abort: bool = True, check_minimal: bool = False):
        super().__init__("CVG", content, check_recommended, check_minimal)

        content = ast.literal_eval(content)
        # print(content)
        self.cont_nodes = content["nodes"]
        self.cont_edges = content["edges"]

        solution_content: str = solution
        self.sol_nodes = solution_content["nodes"]
        self.sol_edges = solution_content["edges"]
        self.succes_tests = True

    def return_true(self) -> Check:
        def _inner(_: BeautifulSoup) -> bool:
            return True
        return Check(_inner)

    def return_false(self) -> Check:
        def _inner(_: BeautifulSoup) -> bool:
            return False
        return Check(_inner)

    def compare_nodeslength(self) -> Check:

        def _inner(_: BeautifulSoup) -> bool:

            if (self.succes_tests != False):
                self.succes_tests = len(self.sol_nodes) == len(self.cont_nodes)
            return (len(self.sol_nodes) == len(self.cont_nodes))
        return Check(_inner)

    def compare_edgeslength(self) -> Check:

        def _inner(_: BeautifulSoup) -> bool:
            if (self.succes_tests != False):
                self.succes_tests = len(self.sol_edges) == len(self.cont_edges)
            return (len(self.sol_edges) == len(self.cont_edges))
        return Check(_inner)

    def correct_nodes(self) -> Check:

        def _inner(_: BeautifulSoup) -> bool:
            self.cont_nodes.sort()
            self.sol_nodes.sort()
            if (self.succes_tests != False):
                self.succes_tests = (self.cont_nodes == self.sol_nodes)
            return (self.cont_nodes == self.sol_nodes)

        return Check(_inner)

    def correct_edges(self) -> Check:

        def _inner(_: BeautifulSoup) -> bool:
            # 0: from , #1: to , #2 : dashes
            user_edges = []
            sol_edges = []
            for i, edge in enumerate(self.cont_edges):
                temp_edge = [0, 0, 0]
                temp_edge[0] = edge["from"]
                temp_edge[1] = edge["to"]
                temp_edge[2] = edge["dashes"]
                user_edges.append(temp_edge)

            for i, edge in enumerate(self.sol_edges):
                temp_edge = [0, 0, 0]
                temp_edge[0] = edge["from"]
                temp_edge[1] = edge["to"]
                temp_edge[2] = edge["dashes"]
                sol_edges.append(temp_edge)
            user_edges.sort()
            sol_edges.sort()
            if len(user_edges) != len(sol_edges):
                return False
            for i in range(len(user_edges)):
                if user_edges[i][0] != sol_edges[i][0] or user_edges[i][1] != sol_edges[i][1]:
                    self.succes_tests == False
                    return False
            return True

        return Check(_inner)

    def correct_stippel(self) -> Check:

        def _inner(_: BeautifulSoup) -> bool:
            # 0: from , #1: to , #2 : dashes
            user_edges = []
            sol_edges = []
            for i, edge in enumerate(self.cont_edges):
                temp_edge = [0, 0, 0]
                temp_edge[0] = edge["from"]
                temp_edge[1] = edge["to"]
                temp_edge[2] = edge["dashes"]
                user_edges.append(temp_edge)

            for i, edge in enumerate(self.sol_edges):
                temp_edge = [0, 0, 0]
                temp_edge[0] = edge["from"]
                temp_edge[1] = edge["to"]
                temp_edge[2] = edge["dashes"]
                sol_edges.append(temp_edge)
            user_edges.sort()
            sol_edges.sort()
            if len(user_edges) != len(sol_edges):
                self.succes_tests == False
                return False
            for i in range(len(user_edges)):
                if user_edges[i][0] != sol_edges[i][0] or user_edges[i][1] != sol_edges[i][1] or user_edges[i][2] != sol_edges[i][2]:
                    self.succes_tests == False
                    return False
            return True

        return Check(_inner)

    def correct_CVG(self) -> Check:
        def _inner(_: BeautifulSoup) -> bool:
            return self.succes_tests

        return Check(_inner)
