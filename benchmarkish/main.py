import datetime
import os
import platform
import shlex
import statistics
import subprocess
import sys
import time
from collections import OrderedDict, namedtuple
from typing import List

import psutil

from benchmarkish import *
from benchmarkish.format import get_size
from benchmarkish.model import PsRunInfo
from benchmarkish.report import report_json, report_logger, report_xlsx


def collect_envdata():
    udict = OrderedDict()

    # platform info
    uname = platform.uname()
    udict[OS_I] = uname.system
    udict[OSVERSION_I] = uname.version
    udict[OSRELEASE_I] = uname.release
    udict[OSARCHITECTURE_I] = " ".join(platform.architecture())
    udict[MACHINETYPE_I] = uname.machine

    # cpu info
    udict[PHYCORES_I] = psutil.cpu_count(logical=False)
    udict[LOGCORES_I] = psutil.cpu_count(logical=True)
    udict[STARTCPU_I] = psutil.cpu_percent(interval=1.0)

    # mem info
    vmem = psutil.virtual_memory()
    udict[RAWMEM_I] = vmem.total
    udict[TOTALMEM_I] = get_size(vmem.total)
    udict[AVAILABLEMEM_I] = get_size(vmem.available)

    # log dump
    logger.info('=' * 40 + " SPECS " + '=' * 40)
    for key, value in udict.items():
        logger.info(f"{key}: {value}")
    logger.info('=' * 87)

    return udict


def collectdata(pid, info: PsRunInfo, collect_environ: bool = False):
    if not pid:
        logger.exception("nopid")
        return 1

    try:
        pswatcher = psutil.Process(pid)
    except KeyboardInterrupt as ki:
        raise ki
    except Exception:
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
                logger.info("Zombie process, loop interrupted")
                break
    except KeyboardInterrupt as ki:
        raise ki
    except psutil.NoSuchProcess:
        logger.info("No such process, loop interrupted")
    except Exception:
        logger.exception("Loop interrupted")

    end = datetime.datetime.now()
    info.totaltime = (end - start) / datetime.timedelta(seconds=1)
    return 0


def process_data(infos: List[PsRunInfo], vmem, trimvalue, is_detailed, is_environ):
    out = OrderedDict()
    Detail = namedtuple("Detail", [MEANCPU_I, T_MEANCPU_I, MAXCPU_I, T_MAXCPU_I, MEANMEM_I, T_MEANMEM_I,
                                   MAXMEM_I, T_MAXMEM_I, CPUTIME_I, SYSCPUTIME_I, TIME_I])
    details = []
    entries = 0
    avgcpusum = 0
    travgcpusum = 0
    maxcpusum = 0
    maxtrcpusum = 0
    avgmemsum = 0
    travgmemsum = 0
    maxmemsum = 0
    maxtrmemsum = 0
    usercputsum = 0
    syscputsum = 0
    timelist = []
    totaltimesum = 0
    for info in infos:
        try:
            # Extract
            avgcpu = info.avg_cpu_perc()
            travgcpu = info.trimmed_avg_cpu_perc(trimvalue)
            maxcpu = info.max_cpu_perc()
            maxtrcpu = info.max_trimmed_cpu_perc(trimvalue)
            avgmem = info.avg_mem_perc()
            travgmem = info.trimmed_avg_mem_perc(trimvalue)
            maxmem = info.max_mem_perc()
            maxtrmem = info.max_trimmed_mem_perc(trimvalue)
            totaltime = info.totaltime
            usercput = info.last_cpu_times.user
            syscput = info.last_cpu_times.system
        except KeyboardInterrupt as ki:
            raise ki
        except Exception:
            logger.exception("Processing failed. Loops continue")
            continue
        else:
            # Append
            details.append(Detail(f"{avgcpu:.2f}%", f"{travgcpu:.2f}%", f"{maxcpu:.2f}%", f"{maxtrcpu:.2f}%",
                                  get_size(avgmem * (vmem / 100)), get_size(travgmem * (vmem / 100)),
                                  get_size(maxmem * (vmem / 100)), get_size(maxtrmem * (vmem / 100)),
                                  usercput, syscput, f"{totaltime:.2f} s"))
            entries += 1
            avgcpusum += avgcpu
            travgcpusum += travgcpu
            maxcpusum += maxcpu
            maxtrcpusum += maxtrcpu
            avgmemsum += avgmem
            travgmemsum += travgmem
            maxmemsum += maxmem
            maxtrmemsum += maxtrmem
            usercputsum += usercput
            syscputsum += syscput
            totaltimesum += totaltime
            timelist.append(totaltime)
            if is_environ:
                info.merge_environ()
    out[RUNS_I] = entries
    out[TRIM_I] = trimvalue
    out[MEANCPU_I] = f"{(avgcpusum / entries):.2f}%"
    out[T_MEANCPU_I] = f"{(travgcpusum / entries):.2f}%"
    out[MAXCPU_I] = f"{(maxcpusum / entries):.2f}%"
    out[T_MAXCPU_I] = f"{maxtrcpusum / entries}%"
    out[MEANMEM_I] = get_size((vmem / 100) * (avgmemsum / entries))
    out[T_MEANMEM_I] = get_size((vmem / 100) * (travgmemsum / entries))
    out[MAXMEM_I] = get_size((vmem / 100) * (maxmemsum / entries))
    out[T_MAXMEM_I] = get_size((vmem / 100) * (maxtrmemsum / entries))
    out[CPUTIME_I] = usercputsum / entries
    out[SYSCPUTIME_I] = syscputsum / entries
    out[MEANTIME_I] = f"{(totaltimesum / entries):.2f} s"
    out[MAXTIME_I] = f"{max(timelist):.2f} s"
    out[MINTIME_I] = f"{min(timelist):.2f} s"
    out[MIDTIME_I] = f"{statistics.median(timelist):.2f} s"
    out[DETAILS_I] = details if is_detailed else []
    out[PROCENV_I] = PsRunInfo.environ
    return out


def execute_benchmarkish(
        command,
        execnum,
        processname,
        testname=None,
        envname=None,
        extendreport=False,
        xlsx=False,
        json=False,
        postcommand=None,
        failfast=False,
        postfailfast=False,
        fetchenviron=False,
        trim=10,
        gatherdetails=False
):
    envdata = collect_envdata()

    start_time = datetime.datetime.today()
    if sys.platform != 'win32':
        command = list(shlex.shlex(command, punctuation_chars=True))
        if command[0].endswith('"'):
            command[0] = command[0].replace('"', "")
        if command[0].endswith("'"):
            command[0] = command[0].replace("'", "")
    logger.info(f"Command to be executed: {command}")
    if testname:
        testname = f"{testname}_{start_time.strftime('%H%M%S')}" if extendreport else testname
    else:
        testname = start_time.strftime("%y%m%d%H%M%S")
    if postcommand and sys.platform != 'win32':
        postcommand = list(shlex.shlex(postcommand, punctuation_chars=True))

    if trim != 0:
        trim /= 100

    # create directory structure
    folder_prefix = f"{envdata[OS_I]}/{processname}" if not envname \
        else f"{envdata[OS_I]}_{envname}/{processname}"
    os.makedirs(folder_prefix, exist_ok=True)

    runinfos = []
    for i in range(0, execnum):
        runinfo = PsRunInfo(i)
        try:
            with open(f'{folder_prefix}/{processname}.{start_time.strftime("%y%m%d_%H%M%S")}.{i}.out', mode='w') as out:
                with subprocess.Popen(command, stdout=out, stderr=subprocess.STDOUT) as subp:
                    failed = collectdata(subp.pid, runinfo, fetchenviron)
                if failed:
                    if failfast:
                        logger.error(f"Process returned {failed}. Ending the benchmark")
                        break
                    else:
                        continue
                runinfos.append(runinfo)
                if postcommand:
                    out.write('=' * 39 + " POSTCMD " + '=' * 39 + '\n')
                    runret = subprocess.run(postcommand, stdout=out, stderr=subprocess.STDOUT)
                    if postfailfast and runret.returncode:
                        logger.error(f"Post command returned {runret.returncode}. Ending the benchmark")
                        break
        except KeyboardInterrupt as ki:
            raise ki
        except Exception:
            logger.exception("Can't open the process")

    report = process_data(runinfos, envdata[RAWMEM_I], trim, gatherdetails, fetchenviron)
    report_logger(report)
    if json:
        # Actually, do I really need to make an incremental json?
        report_json(report, f'{folder_prefix}/{processname}.{start_time.strftime("%y%m%d_%H%M%S")}.json', testname)
    if xlsx:
        report_xlsx(report, f'{folder_prefix}/{processname}', start_time, testname, extendreport, envdata)
