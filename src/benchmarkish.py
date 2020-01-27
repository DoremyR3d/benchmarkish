import subprocess
import datetime
import time
import logging
import platform
import sys
import os
from collections import OrderedDict

import psutil
import openpyxl
from openpyxl.styles import Font
from openpyxl.worksheet.worksheet import Worksheet


class PsRunInfo:

    def __init__(self, index: int):
        self.index = index
        self.cpu_percent = []
        self.mem_percent = []
        self.last_cpu_times = None
        self.totaltime = None

    def add_cpu_perc(self, cpuperc):
        self.cpu_percent.append(cpuperc)

    def add_mem_perc(self, memperc):
        self.mem_percent.append(memperc)


def getsize(nbytes, suffix="B"):
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if nbytes < factor:
            return f"{nbytes:.2f}{unit}{suffix}"
        nbytes /= factor
    # This shouldn't happen on real systems, but you can never be sure
    return f"{nbytes:.2f}{unit}{suffix}"


def initialreport(log: logging.Logger, ws: Worksheet):
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
    # WSL doesn't support cpu_freq, and it works like crap on windows
    # cpufreq = psutil.cpu_freq()
    # udict['MAX TOTAL FREQUENCY'] = f"{cpufreq.max:.2f} Mhz"
    # udict['MIN TOTAL FREQUENCY'] = f"{cpufreq.min:.2f} Mhz"

    # mem info
    vmem = psutil.virtual_memory()
    udict['TOTAL MEMORY'] = getsize(vmem.total)
    udict['AVAILABLE MEMORY @STARTUP'] = getsize(vmem.available)

    # log dump
    log.info('='*40 + " SPECS " + '='*40)
    for key, value in udict.items():
        log.info(f"{key}: {value}")
    log.info('='*87)

    # wb write
    rownum = 2
    for key, value in udict.items():
        label = ws.cell(rownum, 1, key)
        label.font = Font(bold=True)
        _ = ws.cell(rownum, 2, value)
        rownum += 1

    # FIXME Return value
    pass


def collectdata(pid, info: PsRunInfo):
    if not pid:
        print("nopid")
        return

    try:
        print("init collect")
        pswatcher = psutil.Process(pid)
    except:
        # FIXME collect except data
        print("err")
        return
    start = datetime.datetime.now()
    try:
        # while psstatus == psutil.STATUS_RUNNING:
        # For some weird reason WSL starts everything in sleeping, and so the loop is never executed
        # Since that condition was never false before an exception occured on Windows, let's take a "pythonic" approach
        while 1:
            # Talking about WSL, as_dict throws KeyError there. We must take the slower approach
            print(pswatcher.cpu_percent())
            print(pswatcher.memory_percent())
            print(pswatcher.cpu_times)
            status = pswatcher.status()
            print(status)
            if status == psutil.STATUS_ZOMBIE:
                break
            time.sleep(1)
    except:
        # FIXME collect except data
        logger.exception("interrupt")
    end = datetime.datetime.now()
    info.totaltime = f"{(end - start) / datetime.timedelta(milliseconds=1)} ms"

    pass


def writedata(info: PsRunInfo):

    pass


def log_init():
    # # logger
    out = logging.getLogger()
    out.setLevel(logging.INFO)
    # FIXME logname
    fh = logging.FileHandler(f'{sys.argv[0]}.{datetime.date.today().strftime("%d%m%y")}.log')
    fh.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    out.addHandler(fh)
    out.addHandler(ch)
    return out


if __name__ == '__main__':
    # FIXME
    #   - args
    #   - for loop
    #   - stdout/stderr redirect
    #   - logging
    #   - reporting
    #   - setup.py

    # FIXME Proper args init
    proc = sys.argv[1]
    procname = os.path.split(proc)[1]
    # FIXME split dumplog and dumpxlsx - better to work on the sheet at the end then this split thing
    # Turns out that machine type and architecture are meaningless stats to get. You have to hope that in the
    # process environ is stored the architecture if you want that info
    # The side note is, shared drives do exist, so it makes sense to register the system name
    system_name = platform.uname().system
    folder_prefix = f"{system_name}/{procname}"
    os.makedirs(folder_prefix, exist_ok=True)

    # logger
    logger = log_init()
    # FIXME add time
    wb_name = folder_prefix + f"/{procname}.{datetime.date.today().strftime('%d%m%y')}.xlsx"
    workbook = openpyxl.Workbook()
    if workbook.active:
        ws_summary = workbook.active
        ws_summary.title = "SUMMARY"
    else:
        ws_summary = workbook.create_sheet("SUMMARY")
    initialreport(logger, ws_summary)

    with subprocess.Popen(sys.argv[1]) as subp:
        runinfo = PsRunInfo(0)
        collectdata(subp.pid, runinfo)
    writedata(runinfo)
    workbook.save(wb_name)
    print("over")
