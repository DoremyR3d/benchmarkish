import argparse

from benchmarkish.main import execute_benchmarkish


def resolve_args():
    p = argparse.ArgumentParser(description="Command line utility that executes a command, watches over the created "
                                            "process collecting memory and cpu usage and creates report using the "
                                            "collected data. Everything is collected in the current working directory "
                                            "splitting the results according to process and os, including anything "
                                            "the command prints on stdout/stderr")
    p.add_argument('command', type=str,
                   help="The command to be executed. Accepts anything legal for the default system interpreter")
    p.add_argument('-n', type=int, required=True,
                   help="The number of times the command must be executed")
    p.add_argument('--testname', '-t', type=str,
                   help="Assigns a name to the test executed")
    p.add_argument('--envname', '-e', type=str,
                   help="Appends a custom string to the os name. e.g.: Linux_envname")
    p.add_argument('--pname', '-p', type=str, required=True,
                   help="Gives a custom name to the benchmark, instead of using the command's first token")
    p.add_argument('--append', '-a', default=False, action='store_true',
                   help="If a compatible report exists, it is extended and not replaced. Every time specifier is "
                        "appended to the test name, and not the report file name")
    p.add_argument('--xlsx', default=False, action='store_true',
                   help="If specified, it generates a xlsx report file (requires openpyxl)")
    p.add_argument('--json', default=False, action='store_true',
                   help="If specified, it generates a json report file")
    p.add_argument('-postcmd', type=str,
                   help="After every run executes another command, which isn't benchmarked")
    p.add_argument('--postfailfast', default=False, action='store_true',
                   help="If specified, it makes the benchmark stop if the postcmd returns a non-zero value")
    p.add_argument('--failfast', default=False, action='store_true',
                   help="If specified, it makes the benchmark fail if the cmd returns a non-zero value")
    p.add_argument('--environ', default=False, action='store_true',
                   help="Dumps the environment variables of the watched process in the report")
    p.add_argument('--trim', type=int, default=10,
                   help="Define which percentage of the results to trim to elaborate the trimmed stats")
    p.add_argument('--details', default=False, action='store_true',
                   help="Dumps informations specific to every single run inside the report")
    return vars(p.parse_args())


def main():
    argv = resolve_args()
    execute_benchmarkish(
        argv['command'], argv['n'], argv['pname'], argv['testname'], argv['envname'], argv['append'], argv['xlsx'],
        argv['json'], argv['postcmd'], argv['failfast'], argv['postfailfast'], argv['environ'], argv['trim'],
        argv['details']
    )


if __name__ == '__main__':
    main()
