from clinterface import info, command, positional, option, switch, run

@command("A nice command")
def normal(what: option, should: switch):
    if should:
        print(what)

@command("An even nicer command")
def multiple(name, *files):
    print(name, len(files))

@command("A numbery command")
def add(a: positional(arg_type = int), b: positional(arg_type = int)):
    print(a + b)

run()