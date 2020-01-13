from sys      import argv
from argparse import ArgumentParser
from inspect  import signature, _empty, Parameter

class positional:
    def __init__(self, /, *, default = _empty, arg_type = str, allowed = _empty):
        self.default = default
        self.type = arg_type
        self.allowed = allowed

class option:
    def __init__(self, /, *, arg_count = '?', alias = None, default = None, arg_type = str):
        self.arg_count = '*' if isinstance(arg_count, int) and arg_count < 0 else arg_count
        self.alias = alias
        self.default = default
        self.type = arg_type

class switch:
    def __init__(self, /, *, alias = None):
        self.alias = alias

available_commands = {}
def command(desc, /):
    def decorator(f):
        cmd_parser = ArgumentParser(prog = f.__name__, description = desc)
        for param in signature(f).parameters.values():
            cmd_names = ""
            kwargs = {}

            param_specs = param._annotation if param._annotation != _empty else positional()
            if isinstance(param_specs, positional):
                cmd_names = [param.name]
                kwargs = {'nargs': '?' if param.kind != Parameter.VAR_POSITIONAL else '*', 'type': param_specs.type}
                if param_specs.default != _empty: kwargs['default'] = param_specs.default
                if param_specs.allowed != _empty: kwargs['choices'] = param_specs.allowed
            elif isinstance(param_specs, option):
                cmd_names = [f'--{param.name}', f'-{param_specs.alias}'] if param_specs.alias else [f'--{param.name}']
                kwargs = {'nargs': param_specs.arg_count, 'default': param_specs.default, 'type': param_specs.type, 'dest': param.name}
            elif isinstance(param_specs, switch):
                cmd_names = [f'--{param.name}', f'-{param_specs.alias}'] if param_specs.alias else [f'--{param.name}']
                kwargs = {'nargs': 0, 'action': 'store_true', 'default': False, 'dest': param.name}
                
            cmd_parser.add_argument(*cmd_names, **kwargs)
        available_commands[f.__name__] = cmd_parser
        return f
    return decorator


@command("A nice command")
def help(abba: positional(arg_type = int), beachboi, *args, oblaty: option(alias = 'o', default = 'jerozolima')):
    pass

def run():
    if not argv:
        pass

    cmd_name, *cmd_args = argv[1:]
    print(available_commands[cmd_name].parse_args(cmd_args))

run()