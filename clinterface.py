from sys        import argv
from os         import mkdir, environ, remove, name as osname
from os.path    import join, exists, basename, splitext
from argparse   import ArgumentParser
from inspect    import signature, _empty, Parameter
from PyInquirer import style_from_dict, Token, prompt, Validator, ValidationError
from dill       import dump, load
from colorama    import Fore, Style, init as colinit
from pyfiglet    import Figlet

class info:
    progname = splitext(basename(argv[0]))[0]
    description = ''
    app_data_dir = join(environ['APPDATA'], progname) if osname == 'nt' else join(environ['HOME'], '.config', progname)

if not exists(info.app_data_dir): 
    mkdir(info.app_data_dir)

class lock:
    @staticmethod
    def locks_dir():
        return join(info.app_data_dir, 'locks')

    def __init__(self, name):
        self.filename = f'{name}.lock'
    
    def create(self):
        open(join(lock.locks_dir(), self.filename))

    def check(self):
        return exists(join(lock.locks_dir(), self.filename))

    def delete(self):
        remove(join(lock.locks_dir(), self.filename))

if not exists(lock.locks_dir()): 
    mkdir(lock.locks_dir())

class persistence:
    @staticmethod
    def vars_dir():
        return join(info.app_data_dir, 'vars')

    def __init__(self, name):
        self.filename = f'{name}.info'
    
    def save(self, obj):
        dump(obj, open(join(persistence.vars_dir(), self.filename), 'wb'))

    def load(self):
        return load(open(join(persistence.vars_dir(), self.filename), 'rb'))

    def ask(self, prompt, **kwargs):
        if new_value := ask_input(prompt, **kwargs):
            self.save(new_value)

if not exists(persistence.vars_dir()): 
    mkdir(persistence.vars_dir())

class positional:
    def __init__(self, /, *, default = _empty, arg_type = str, allowed = _empty):
        self.default = default
        self.type = arg_type
        self.allowed = allowed

    def parse_arg(self, param):
        cmd_names = [param.name]
        kwargs = {'type': self.type}
        if param.kind == Parameter.VAR_POSITIONAL: 
            kwargs['nargs'] = '+'
            kwargs['help'] = '(Multiple arguments)'
        if self.default != _empty: kwargs['default'] = self.default
        if self.allowed != _empty: kwargs['choices'] = self.allowed
        return cmd_names, kwargs

class option:
    def __init__(self, /, *, arg_count = '?', alias = None, default = _empty, arg_type = str):
        self.arg_count = '*' if isinstance(arg_count, int) and arg_count < 0 else arg_count
        self.alias = alias
        self.default = default
        self.type = arg_type

    def parse_arg(self, param):
        cmd_names = [f'--{param.name}', f'-{self.alias}'] if self.alias else [f'--{param.name}']
        kwargs = {'nargs': self.arg_count, 'type': self.type, 'dest': param.name}
        if self.default != _empty:
            kwargs['default'] = self.default
            kwargs['metavar'] = f'{cmd_names[0].lstrip("-").upper()} (default: {self.default})'
        return cmd_names, kwargs

class switch:
    def __init__(self, /, *, alias = None):
        self.alias = alias

    def parse_arg(self, param):
        cmd_names = [f'--{param.name}', f'-{self.alias}'] if self.alias else [f'--{param.name}']
        kwargs = {'action': 'store_true', 'default': False, 'dest': param.name}
        return cmd_names, kwargs

def get_param_type(param):
    annotation = param._annotation
    if annotation == _empty: return positional()
    elif hasattr(annotation, 'parse_args'): return annotation
    else: return annotation()

available_commands = {}
def command(desc, /):
    def decorator(f):
        params = f.__params__ if hasattr(f, '__params__') else signature(f).parameters.values()
        baked_args = [get_param_type(param).parse_arg(param) for param in params]

        global available_commands
        available_commands[f.__name__] = (f, desc, baked_args)
        return f
    return decorator

init_locks = []
def init_command(desc, /):
    def decorator(f):
        lockfile = join(lock.locks_dir(), f'{f.__name__}')
        def call_and_lock(*args, **kwargs):
            print_title()
            f(*args, **kwargs)
            open(lockfile, 'w')
        init_locks.append(lockfile)
        call_and_lock.__name__ = f.__name__
        call_and_lock.__params__ = signature(f).parameters.values()
        command(desc)(call_and_lock)
        return call_and_lock
    return decorator

def run():
    for init_lock in init_locks:
        if not exists(init_lock) and '-h' not in argv and '--help' not in argv and argv[1] != basename(init_lock):
            print(f'New environment. Please run "{info.progname} {basename(init_lock)}" first!')
            return

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
            params = func.__params__ if hasattr(func, '__params__') else signature(func).parameters.values()
            def inner(namespace):
                args = []
                kwargs = {}
                namespace = vars(namespace)
                for param in params:
                    param_specs = get_param_type(param)
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

def print_title():
    colinit(convert = True)
    print(Fore.RED + Style.BRIGHT + Figlet(font = 'slant').renderText(' * * * dev * * * ') + Style.RESET_ALL)

def ask(questions_data):
    style = style_from_dict({
        Token.QuestionMark: '#E91E63 bold',
        Token.Selected: '#673AB7 bold',
        Token.Instruction: '',
        Token.Answer: '#2196f3 bold',
        Token.Question: '',
    })
    return prompt(questions_data, style = style)

def ask_input(prompt, /, *, default = '', blacklist = []):
    class BlacklistValidator(Validator):
        def validate(self, document):
            for blacklisted in blacklist:
                if blacklisted in document.text:
                    raise ValidationError(message = f'Invalid token "{blacklisted}"!', cursor_position = len(document.text))

    answer = ask({'type': 'input', 'message': prompt, 'name': 'var', 'default': default, 'validate': BlacklistValidator})
    return answer['var'] if 'var' in answer else ''

def ask_list(prompt, choicelist, /):
    return ask({'type': 'list', 'message': prompt, 'name': 'var', 'choices': choicelist})['var']

def ask_confirm(prompt, /, *, default = True):
    return ask({'type': 'confirm', 'message': prompt, 'name': 'var', 'default': default})['var']