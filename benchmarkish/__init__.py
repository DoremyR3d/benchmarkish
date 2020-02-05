def _default_logger():
    import logging
    import datetime
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


try:
    if not logger:
        logger = _default_logger()
        logger.info("Initialized default logger")
except NameError:
    logger = _default_logger()
    logger.info("Initialized default logger")

RUNS_L = "RUNS"
TRIM_L = "TRIM%"
MEANCPU_L = "AVG CPU%"
T_MEANCPU_L = "TR.AVG CPU%"
MAXCPU_L = "MAX CPU%"
T_MAXCPU_L = "TR.MAX CPU%"
MEANMEM_L = "AVG MEM"
T_MEANMEM_L = "TR.AVG MEM"
MAXMEM_L = "MAX MEM"
T_MAXMEM_L = "TR.MAX MEM"
CPUTIME_L = "USER CPUt"
SYSCPUTIME_L = "SYS CPUt"
MEANTIME_L = "AVG TIME"
MAXTIME_L = "MAX TIME"
MINTIME_L = "MIN TIME"
MIDTIME_L = "MEDIAN TIME"
PROCENV_L = "ENVIRONMENT"
ENV_L = "SYSTEM SPECS"

RUNS_I = "entries"
TRIM_I = "trim"
MEANCPU_I = "avg_cpu"
T_MEANCPU_I = "trimmed_avg_cpu"
MAXCPU_I = "max_cpu"
T_MAXCPU_I = "max_trimmed_cpu"
MEANMEM_I = "avg_mem"
T_MEANMEM_I = "trimmed_avg_mem"
MAXMEM_I = "max_mem"
T_MAXMEM_I = "max_trimmed_mem"
CPUTIME_I = "user_cput"
SYSCPUTIME_I = "system_cput"
TIME_I = "time"
MEANTIME_I = "total_time"
MAXTIME_I = "max_time"
MINTIME_I = "min_time"
MIDTIME_I = "mid_time"
DETAILS_I = "details"
PROCENV_I = "environ"
ENV_I = "envstats"

OS_I = "OS"
OSVERSION_I = "OS VERSION"
OSRELEASE_I = "OS RELEASE"
OSARCHITECTURE_I = "OS ARCHITECTURE"
MACHINETYPE_I = "MACHINE TYPE"
PHYCORES_I = "PHYSICAL CORES"
LOGCORES_I = "LOGICAL CORES"
STARTCPU_I = "USAGE PERCENTAGE @STARTUP"
RAWMEM_I = "RAW TOTAL MEMORY"
TOTALMEM_I = "TOTAL MEMORY"
AVAILABLEMEM_I = "AVAILABLE MEMORY @STARTUP"
