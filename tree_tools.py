from collections.abc import Iterable


def _slot_to_dict(obj):
    return {slot: getattr(obj, slot) for slot in obj.__slots__}


def dict_extract(key, var, debug=False, depth=0):
    """
    fdsj
    """
    if isinstance(key, str):
        key = [key]
    if hasattr(var, "items") or hasattr(var, "__slots__"):
        if hasattr(var, "items"):
            iterable = var.items()
        elif hasattr(var, "__slots__"):
            iterable = _slot_to_dict(var).items()
        for k, v in iterable:
            if debug:
                print()
            if k in key:
                if debug:
                    print()
                yield v
            if isinstance(v, dict):
                yield from dict_extract(key, v, debug=debug, depth=depth + 1)
            elif isinstance(v, Iterable):
                for d in v:
                    yield from dict_extract(key, d, debug=debug, depth=depth + 1)
            elif hasattr(v, "__slots__"):
                yield from dict_extract(key, _slot_to_dict(v), debug=debug, depth=depth + 1)
    else:
        if debug:
            print()


def dict_modify(key, var, func, debug=False, depth=0):
    """
    fdsj
    """
    if isinstance(key, str):
        key = [key]
    if hasattr(var, "items") or hasattr(var, "__slots__"):
        if hasattr(var, "items"):
            iterable = var.items()
        elif hasattr(var, "__slots__"):
            iterable = _slot_to_dict(var).items()
        for k, v in iterable:
            if debug:
                print(" " * depth, "k is ", k, "and v is a", type(v))
            if k in key:
                if debug:
                    print(" " * depth, "found", k)
                var[k] = func(v)
            if isinstance(v, dict):
                v = dict_modify(key, v, func, debug=debug, depth=depth + 1)
            elif isinstance(v, Iterable):
                for d in v:
                    v = dict_modify(key, d, func, debug=debug, depth=depth + 1)
            elif hasattr(v, "__slots__"):
                v = dict_modify(key, _slot_to_dict(v), func, debug=debug, depth=depth + 1)
    else:
        if debug:
            print(" " * depth, type(var), "does not have an items or a __slots__ attribute", var)
    return var
