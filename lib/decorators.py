
from contextlib import closing
from functools import wraps
from pymysql import connect

from settings import DATABASE as db_config


def database_conn(func):
    """Provides db cursor for decorated func."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        db = connect(host=db_config['host'],
                             user=db_config['username'],
                             passwd=db_config['password'],
                             db=db_config['database'])
        with closing(db.cursor()) as cursor:
            result = func(cursor, *args, **kwargs)
        return result
    return wrapper


def memoize(func):
    """Simple caching decorator.

    Puts result of the call to decorated function into
    dictionary with key equals to positional args
    supplied to function. Next call with the same
    args will result in cache lookup instead of real
    function call. Will not work with unhashable
    positional args.

    Adopted from here:
    https://wiki.python.org/moin/PythonDecoratorLibrary#Memoize
    """
    cache = {}

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            if args not in cache:
                cache[args] = func(*args, **kwargs)
            return cache[args]
        except TypeError:
            return func(*args, **kwargs)

    return wrapper
