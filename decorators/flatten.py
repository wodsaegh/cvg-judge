from inspect import getfullargspec
from utils.flatten import flatten_queue


def flatten_varargs(func):
    """
    Decorator used to modify a function's arguments and flatten a variable
    amount of Checks into one List, can also take nested Iterables (maps, generators, ...)
    """
    argspec = getfullargspec(func)

    # No varargs argument to flatten
    if argspec.varargs is None:
        return func

    def wrapper(*args, **kwargs):
        args = list(args)

        # Cut out the normal arguments & only leave varargs behind
        # then flatten them into a single list
        varargs = flatten_queue(args[len(argspec.args):])
        args = args[:len(argspec.args)] + varargs

        return func(*args, **kwargs)

    return wrapper
