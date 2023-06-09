# Control Flow Graph Judge
This repository was made to allow educators to create control flow graph exercises for Dodona. Please note, this judge has a very specific application which may not suit your needs. Students will be given a set of assembly instructions, they will have to use this instructions in the CFG Builder to create a correct control flow graph.

## Exercise Structure
When building your own exercises, please follow the structure specified below. The `evaluation` folder is made available to the judge.

```
+-- exercise
|   +-- config.json               # Configuration of the exercise
|   +-- description              
|   |   +-- description.nl.md     # The description in Dutch
|   |   +-- description.en.md     # The description in English
|   |   +-- media
|   |   |   +-- some_image.png    # [optional] An image used in the description
|   |   +-- boilerplate
|   |       +-- boilerplate       # The original assemblycode
|   +-- evaluation
|       +-- evaluator.py           # File where the tests are created
|       +-- solution.json          # This will be the correct JSON code generated by the teacher
```
For creating your solution.json file you could create the control flow graph in the CFG Builder itself or use our automated CFG Builder tool (*see below*).
The evaluator.py file should contain all the tests you want the user to see. The ones you should definitely have are: cvg.correct_stippel(), cvg.correct_nodes() and cvg.correct_edges(). These check whether the lines are correctly dashed, whether the codeblocks are correct and whether the edges are correct.
You could use this structure in your evaluator.py file if you want the basic settings:
```
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

```



## Exercise Example
You could find an example exercise at https://github.com/wodsaegh/CVG-exe2

Running this code with one codeblock missing in your JSON file gives following output:
![image](https://user-images.githubusercontent.com/79666347/235501818-31bb99aa-ce1d-484a-b815-61c526267e37.png)

## AGCFG: Automatic Generation Control Flow Graph
**Disclaimer:** It will always be safer to generate your own control flow graphs. This tool does not 100% guarantee a correct solution. However, in most cases it will. 
This tool is designed for teachers who want to save some time and let an automatic tool generate their control flow graphs.
It works as follows:

0. Make sure you have angr([install](https://docs.angr.io/en/latest/getting-started/installing.html)) and the assemblers for your respective architecture installed. For AT&T and intel architecture it should be automatically installed on your linux device, for ARM run the following command:
```
sudo aptitude install binutils-arm-linux-gnueabihf
```
1. Put your assemblycode in a .s file
2. Run the following command in this folder:
```
python3 generate_CFG.py <inputfile.s> <architecture (att, ARM or intel)>
```
3. The generated solution will be present in the solution.json file.
4. Check your solution by copying it into our [CFG Checker tool](https://github.com/wodsaegh/cvg-judge/tree/main/CFG%20Checker)
5. Copy your solution.json file and put it in your exercise repository.
