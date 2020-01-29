import subprocess
import datetime
import sys
import time
import logging
import platform
import shlex
import os
import argparse
from collections import OrderedDict, namedtuple
from typing import Dict, Any, List

import psutil
# import openpyxl


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
    return vars(p.parse_args())


class PsRunInfo:
    environ = {}

    def __init__(self, index: int):
        self.index = index
        self.cpu_percent = []
        self.mem_percent = []
        self.last_cpu_times = None
        self.totaltime = None
        self.environ = None

    def add_cpu_perc(self, cpuperc):
        self.cpu_percent.append(cpuperc)

    def avg_cpu_perc(self):
        return sum(self.cpu_percent) / len(self.cpu_percent)

    def max_cpu_perc(self):
        return max(self.cpu_percent)

    def add_mem_perc(self, memperc):
        self.mem_percent.append(memperc)

    def avg_mem_perc(self):
        return sum(self.mem_percent) / len(self.mem_percent)

    def max_mem_perc(self):
        return max(self.cpu_percent)

    def merge_environ(self):
        PsRunInfo.environ.update(self.environ)
        del self.environ


def get_size(nbytes, suffix="B"):
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if nbytes < factor:
            return f"{nbytes:.2f}{unit}{suffix}"
        nbytes /= factor
    # This shouldn't happen on real systems, but you can never be sure
    return f"{nbytes:.2f}{unit}{suffix}"


def collect_envdata(argmap: Dict[str, Any]):
    udict = OrderedDict()

    # platform info
    uname = platform.uname()
    udict['OS'] = uname.system
    udict['OS VERSION'] = uname.version
    udict['OS RELEASE'] = uname.release
    udict['OS ARCHITECTURE'] = " ".join(platform.architecture())
    udict['MACHINE TYPE'] = uname.machine

    # cpu info
    udict['PHYSICAL CORES'] = psutil.cpu_count(logical=False)
    udict['LOGICAL CORES'] = psutil.cpu_count(logical=True)
    udict['USAGE PERCENTAGE @STARTUP'] = psutil.cpu_percent(interval=1.0)

    # mem info
    vmem = psutil.virtual_memory()
    udict['RAW TOTAL MEMORY'] = vmem.total
    udict['TOTAL MEMORY'] = get_size(vmem.total)
    udict['AVAILABLE MEMORY @STARTUP'] = get_size(vmem.available)

    # log dump
    logger.info('=' * 40 + " SPECS " + '=' * 40)
    for key, value in udict.items():
        logger.info(f"{key}: {value}")
    logger.info('=' * 87)

    argmap['envstats'] = udict


def collectdata(pid, info: PsRunInfo, collect_environ: bool = False):
    if not pid:
        logger.exception("nopid")
        return 1

    try:
        pswatcher = psutil.Process(pid)
    except:
        logger.exception("Couldn't collect data")
        return 1
    start = datetime.datetime.now()
    try:
        while 1:
            time.sleep(0.2)
            # Talking about WSL, as_dict throws KeyError there. We must take the slower approach
            info.add_cpu_perc(pswatcher.cpu_percent())
            info.add_mem_perc(pswatcher.memory_percent())
            info.last_cpu_times = pswatcher.cpu_times()
            if collect_environ:
                info.environ = pswatcher.environ()

            status = pswatcher.status()
            if status == psutil.STATUS_ZOMBIE:
                # Since we're running inside the popen context, the process WILL remain [DECEASED] on Linux
                # On Windows NoSuchProcess is thrown instead
                break
    except:
        logger.exception("Loop interrupted")

    end = datetime.datetime.now()
    info.totaltime = (end - start) / datetime.timedelta(seconds=1)
    return 0


def process_data(infos: List[PsRunInfo], vmem, is_environ):
    out = OrderedDict()
    Detail = namedtuple("Detail", ['avg_cpu', 'max_cpu', 'avg_mem', 'max_mem',
                                   'user_cput', 'system_cput', 'child_user_cput', 'child_system_cput', 'totaltime'])
    details = []
    entries = 0
    avgcpusum = 0
    maxcpusum = 0
    avgmemsum = 0
    maxmemsum = 0
    usercputsum = 0
    syscputsum = 0
    cusercputsum = 0
    csyscputsum = 0
    totaltimesum = 0
    for info in infos:
        try:
            # Extract
            avgcpu = info.avg_cpu_perc()
            maxcpu = info.max_cpu_perc()
            avgmem = info.avg_mem_perc()
            maxmem = info.max_mem_perc()
            totaltime = info.totaltime
            usercput = info.last_cpu_times.user
            syscput = info.last_cpu_times.system
            cusercput = info.last_cpu_times.children_user
            csyscput = info.last_cpu_times.children_system
        except:
            logger.exception("Processing failed. Loops continue")
            continue
        else:
            # Append
            details.append(Detail(f"{avgcpu}%", f"{maxcpu}%",
                                  get_size(avgmem * (vmem / 100)), get_size(maxmem * (vmem / 100)),
                                  usercput, syscput, cusercput, csyscput, f"{totaltime} s"))
            entries += 1
            avgcpusum += avgcpu
            maxcpusum += maxcpu
            avgmemsum += avgmem
            maxmemsum += maxmem
            usercputsum += usercput
            syscputsum += syscput
            cusercputsum += cusercput
            csyscputsum += csyscput
            totaltimesum += totaltime
            if is_environ:
                info.merge_environ()
    out['entries'] = entries
    out['avg_cpu'] = f"{avgcpusum / entries}%"
    out['max_cpu'] = f"{maxcpusum / entries}%"
    out['avg_mem'] = get_size((vmem / 100) * (avgmemsum / entries))
    out['max_mem'] = get_size((vmem / 100) * (maxmemsum / entries))
    out['user_cput'] = usercputsum / entries
    out['system_cput'] = syscputsum / entries
    out['child_user_cput'] = cusercputsum / entries
    out['child_system_cput'] = csyscputsum / entries
    out['total_time'] = f"{totaltimesum / entries} s"
    out['details'] = details
    out['environ'] = PsRunInfo.environ
    return out


def report_logger(results: dict):
    logger.info('=' * 39 + ' RESULTS ' + '=' * 39)
    logger.info(f"RUNS: {results['entries']}")
    logger.info(f"AVERAGE CPU USAGE: {results['avg_cpu']}")
    logger.info(f"MAX CPU USAGE: {results['max_cpu']}")
    logger.info(f"AVERAGE MEMORY USAGE: {results['avg_mem']}")
    logger.info(f"MAX MEMORY USAGE: {results['max_mem']}")
    logger.info(f"CPU TIME (USER): {results['user_cput']}")
    logger.info(f"CPU TIME (SYSTEM): {results['system_cput']}")
    logger.info(f"CPU TIME (CHILD_USER): {results['child_user_cput']}")
    logger.info(f"CPU TIME (CHILD_SYSTEM): {results['child_system_cput']}")
    logger.info(f"AVERAGE RUN DURATION: {results['total_time']}")
    logger.info('=' * 39 + ' DETAILS ' + '=' * 39)
    logger.info(f"{results['details']}")
    logger.info("{results['environ']}")


def report_json(results: dict, fpname: str):
    import json
    with open(fpname, mode='w') as t:
        json.dump(results, t)


def log_init():
    out = logging.getLogger()
    out.setLevel(logging.INFO)
    fh = logging.FileHandler(f'benchmarkish.{datetime.datetime.today().strftime("%d%m%yT%H%M%S")}.log')
    fh.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s -| %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    out.addHandler(fh)
    out.addHandler(ch)
    return out


if __name__ == '__main__':
    # FIXME
    #   - reporting
    #   - setup.py

    argv = resolve_args()
    logger = log_init()
    collect_envdata(argv)

    start_time = datetime.datetime.today()
    cmd = argv.get('command')
    if sys.platform != 'win32':
        cmd = list(shlex.shlex(cmd, punctuation_chars=True))
        if cmd[0].endswith('"'):
            cmd[0] = cmd[0].replace('"', "")
        if cmd[0].endswith("'"):
            cmd[0] = cmd[0].replace("'", "")
    print(cmd)
    procname = argv.get('pname')
    postcmd = argv.get('postcmd')
    if postcmd and sys.platform != 'win32':
        postcmd = list(shlex.shlex(postcmd, punctuation_chars=True))

    # create directory structure
    folder_prefix = f"{argv['envstats']['OS']}/{procname}" if not argv['envname'] \
        else f"{argv['envstats']['OS']}_{argv['envname']}/{procname}"
    os.makedirs(folder_prefix, exist_ok=True)

    runinfos = []
    for i in range(0, argv['n']):
        runinfo = PsRunInfo(i)
        try:
            with open(f'{folder_prefix}/{procname}.{start_time.strftime("%y%m%dT%H%M%S")}.{i}.out', mode='w') as out:
                with subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT) as subp:
                    failed = collectdata(subp.pid, runinfo, argv['environ'])
                if failed:
                    if argv.get('failfast'):
                        logger.error(f"Process returned {failed}. Ending the benchmark")
                        break
                    else:
                        continue
                print(runinfo.mem_percent)
                print(runinfo.cpu_percent)
                runinfos.append(runinfo)
                if postcmd:
                    out.write('='*39 + " POSTCMD " + '='*39 + '\n')
                    runret = subprocess.run(postcmd, stdout=out, stderr=subprocess.STDOUT)
                    if argv.get('postfailfast') and runret.returncode:
                        logger.error(f"Post command returned {runret.returncode}. Ending the benchmark")
                        break
        except:
            logger.exception("Can't open the process")

    report = process_data(runinfos, argv['envstats']['RAW TOTAL MEMORY'], argv['environ'])
    report_logger(report)
    if argv['json']:
        report_json(report, f'{folder_prefix}/{procname}.{start_time.strftime("%y%m%dT%H%M%S")}.json')
