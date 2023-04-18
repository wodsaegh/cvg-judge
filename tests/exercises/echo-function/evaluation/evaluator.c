#include <string.h>
#include <stdbool.h>

#include "evaluation_result.h"

EvaluationResult* evaluate(char* actual) {
    bool result = !strcmp("correct", actual);
    EvaluationResult* r = create_result(1);
    r->result = result;
    r->readableExpected = "correct";
    r->readableActual = actual;
    r->messages[0] = create_message("Hallo", NULL, NULL);
    return r;
}