from sys      import argv
from argparse import ArgumentParser
from inspect  import signature, _empty, Parameter

class info:
    progname = argv[0]
    description = ''

class positional:
    def __init__(self, /, *, default = _empty, arg_type = str, allowed = _empty):
        self.default = default
        self.type = arg_type
        self.allowed = allowed

class option:
    def __init__(self, /, *, arg_count = '?', alias = None, default = _empty, arg_type = str):
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
        baked_args = []
        for param in signature(f).parameters.values():
            cmd_names = ""
            kwargs = {}

            param_specs = positional() if param._annotation == _empty else param._annotation if isinstance(param._annotation, (positional, option, switch)) else param._annotation()
            if isinstance(param_specs, positional):
                cmd_names = [param.name]
                kwargs = {'type': param_specs.type}
                if param.kind == Parameter.VAR_POSITIONAL: 
                    kwargs['nargs'] = '+'
                    kwargs['help'] = '(Multiple arguments)'
                if param_specs.default != _empty: kwargs['default'] = param_specs.default
                if param_specs.allowed != _empty: kwargs['choices'] = param_specs.allowed
            elif isinstance(param_specs, option):
                cmd_names = [f'--{param.name}', f'-{param_specs.alias}'] if param_specs.alias else [f'--{param.name}']
                kwargs = {'nargs': param_specs.arg_count, 'type': param_specs.type, 'dest': param.name}
                if param_specs.default != _empty:
                    kwargs['default'] = param_specs.default
                    kwargs['metavar'] = f'{cmd_names[0].lstrip("-").upper()} (default: {param_specs.default})'
            elif isinstance(param_specs, switch):
                cmd_names = [f'--{param.name}', f'-{param_specs.alias}'] if param_specs.alias else [f'--{param.name}']
                kwargs = {'action': 'store_true', 'default': False, 'dest': param.name}
                
            baked_args.append((cmd_names, kwargs))
        available_commands[f.__name__] = (f, desc, baked_args)
        return f
    return decorator

def run():
    global available_commands
    command_line_arguments = argv[1:]
    if not command_line_arguments or command_line_arguments[0] not in available_commands:
        command_line_arguments = ['--help']

    cmd_parser = ArgumentParser(prog = info.progname, description = info.description)
    subparsers = cmd_parser.add_subparsers(metavar = '')
    for command_name, (command, command_desc, baked_args) in available_commands.items():
        subparser = subparsers.add_parser(command_name, help = command_desc)
        for parser_cmd_names, parser_cmd_kwargs in baked_args:
            subparser.add_argument(*parser_cmd_names, **parser_cmd_kwargs)
        def call_appropriate_command(funcname):
            func, _, _ = available_commands[funcname]
            params = signature(func).parameters.values()
            def inner(namespace):
                args = []
                kwargs = {}
                namespace = vars(namespace)
                for param in params:
                    param_specs = positional() if param._annotation == _empty else param._annotation if isinstance(param._annotation, (positional, option, switch)) else param._annotation()
                    if not isinstance(param_specs, positional):
                        kwargs[param.name] = namespace[param.name]
                    elif isinstance(namespace[param.name], list):
                        args += namespace[param.name]
                    else:
                        args.append(namespace[param.name])
                func(*args, **kwargs)
            return inner
        subparser.set_defaults(_func_to_call_ = call_appropriate_command(command_name))
    
    def global_help():
        print('Available sub-commands:')
        print('\n'.join([f'  {cmd_name} - {cmd_desc}' for cmd_name, (_, cmd_desc, _) in available_commands.items()]))
        print('Pass -h or --help to a sub-command to learn more')
    cmd_parser.print_help = global_help
    namespace = cmd_parser.parse_args(command_line_arguments)
    namespace._func_to_call_(namespace)