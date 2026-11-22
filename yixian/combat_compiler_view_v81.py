"""Private dependency injection for the frozen compiler chain.

No module in sys.modules or existing function globals is modified. Only Python
functions belonging to the explicit full_battle module graph are rebound. This
lets a new leaf resolve one documented admission gate while retaining every
ancestor check and keeping old entrypoints callable in the same process.
"""
from types import ModuleType, FunctionType


def compiler_modules(entry):
    found = {}
    pending = [entry]
    while pending:
        module = pending.pop()
        if module.__name__ in found:
            continue
        found[module.__name__] = module
        for value in vars(module).values():
            if isinstance(value, ModuleType) and (
                value.__name__ == 'yixian.full_battle'
                or value.__name__.startswith('yixian.full_battle_v')
            ):
                pending.append(value)
    return found


def isolated_compiler(entry, *, base_compile=None, runtime_bridge=None):
    originals = compiler_modules(entry)
    views = {name: ModuleType(name) for name in originals}
    namespaces = {id(vars(original)): vars(views[name]) for name, original in originals.items()}
    for name, original in originals.items():
        vars(views[name]).update(vars(original))
    functions = {}

    def rebind(value):
        if isinstance(value, ModuleType) and value.__name__ in originals:
            if originals[value.__name__] is not value:
                raise ValueError('Compiler module identity collision')
            return views[value.__name__]
        if isinstance(value, FunctionType) and id(value.__globals__) in namespaces:
            if value.__closure__ is not None:
                raise ValueError('A compiler closure requires an explicit migration')
            if id(value) not in functions:
                clone = FunctionType(value.__code__, namespaces[id(value.__globals__)],
                                     value.__name__, value.__defaults__)
                clone.__kwdefaults__ = value.__kwdefaults__.copy() if value.__kwdefaults__ else None
                clone.__annotations__ = value.__annotations__.copy()
                clone.__dict__.update(value.__dict__)
                clone.__module__ = value.__module__
                clone.__qualname__ = value.__qualname__
                functions[id(value)] = clone
            return functions[id(value)]
        return value

    for name, original in originals.items():
        vars(views[name]).update({key: rebind(value) for key, value in vars(original).items()})
    if base_compile is not None:
        views['yixian.full_battle'].compile_start = base_compile
    if runtime_bridge is not None:
        views['yixian.full_battle_v79r2'].BRIDGE = runtime_bridge
    return views[entry.__name__]
