import statistics
from collections import OrderedDict, namedtuple
from typing import List

from benchmarkish import *
from benchmarkish.model import PsRunInfo
from benchmarkish.format import get_size


def process_data(infos: List[PsRunInfo], vmem, trim, is_detailed, is_environ):
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
            travgcpu = info.trimmed_avg_cpu_perc(trim)
            maxcpu = info.max_cpu_perc()
            maxtrcpu = info.max_trimmed_cpu_perc(trim)
            avgmem = info.avg_mem_perc()
            travgmem = info.trimmed_avg_mem_perc(trim)
            maxmem = info.max_mem_perc()
            maxtrmem = info.max_trimmed_mem_perc(trim)
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
            maxtrcpusum +=maxtrcpu
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
    out[TRIM_I] = trim
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
