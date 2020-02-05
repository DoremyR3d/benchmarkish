from typing import List

from benchmarkish import *


def trim_array(arr: List, mean: float) -> List:
    if mean == 0:
        return arr
    if mean < 0:
        mean *= -1
    if mean >= 0.5:
        logger.info("Won't trim an array over 49%")
        return arr
    l_arr = len(arr)
    if l_arr == 0:
        return arr
    l_trim = int(l_arr * (2 * mean))
    if l_trim % 2:
        n_remove = int((l_trim - 1) / 2)
        n_err = 1
    else:
        n_remove = int(l_trim / 2)
        n_err = 0
    s_arr = sorted(arr)
    s_arr = s_arr[n_remove:(len(s_arr) - n_remove)]
    if n_err:
        s_arr[0] = (s_arr[0] / 2) + (s_arr[len(s_arr) - 1] / 2)
        del s_arr[len(s_arr) - 1]
    return s_arr


class PsRunInfo:
    environ = {}

    def __init__(self, index: int):
        self.index = index
        self.cpu_percent = []
        self.mem_percent = []
        self._trim_cpu_percent = 0
        self._trimmed_cpu_percent = None
        self._trim_mem_percent = 0
        self._trimmed_mem_percent = None
        self.last_cpu_times = None
        self.totaltime = None
        self.environ = None

    def add_cpu_perc(self, cpuperc):
        self.cpu_percent.append(cpuperc)
        self._trimmed_cpu_percent = None

    def avg_cpu_perc(self):
        return sum(self.cpu_percent) / len(self.cpu_percent)

    def trimmed_avg_cpu_perc(self, trim: float):
        if trim == 0:
            return self.avg_cpu_perc()
        if trim < 0:
            trim *= -1
        if trim >= 0.5:
            logger.info("Won't trim over 49%")
            return self.avg_cpu_perc()
        if self._trim_cpu_percent == trim and self._trimmed_cpu_percent:
            return sum(self._trimmed_cpu_percent) / len(self._trimmed_cpu_percent)
        self._trim_cpu_percent = trim
        self._trimmed_cpu_percent = trim_array(self.cpu_percent, trim)
        return sum(self._trimmed_cpu_percent) / len(self._trimmed_cpu_percent)

    def max_cpu_perc(self):
        return max(self.cpu_percent)

    def max_trimmed_cpu_perc(self, trim: float):
        if trim == 0:
            return self.max_cpu_perc()
        if trim < 0:
            trim *= -1
        if trim >= 0.5:
            logger.info("Won't trim over 49%")
            return self.max_cpu_perc()
        if self._trim_cpu_percent == trim and self._trimmed_cpu_percent:
            return max(self._trimmed_cpu_percent)
        self._trim_cpu_percent = trim
        self._trimmed_cpu_percent = trim_array(self.cpu_percent, trim)
        return max(self._trimmed_cpu_percent)

    def add_mem_perc(self, memperc):
        self.mem_percent.append(memperc)
        self._trimmed_mem_percent = None

    def avg_mem_perc(self):
        return sum(self.mem_percent) / len(self.mem_percent)

    def trimmed_avg_mem_perc(self, trim: float):
        if trim == 0:
            return self.avg_mem_perc()
        if trim < 0:
            trim *= -1
        if trim >= 0.5:
            logger.info("Won't trim over 49%")
            return self.avg_mem_perc()
        if self._trim_mem_percent == trim and self._trimmed_mem_percent:
            return sum(self._trimmed_mem_percent) / len(self._trimmed_mem_percent)
        self._trim_mem_percent = trim
        self._trimmed_mem_percent = trim_array(self.mem_percent, trim)
        return sum(self._trimmed_mem_percent) / len(self._trimmed_mem_percent)

    def max_mem_perc(self):
        return max(self.cpu_percent)

    def max_trimmed_mem_perc(self, trim: float):
        if trim == 0:
            return self.max_mem_perc()
        if trim < 0:
            trim *= -1
        if trim >= 0.5:
            logger.info("Won't trim over 49%")
            return self.max_mem_perc()
        if self._trim_mem_percent == trim and self._trimmed_mem_percent:
            return max(self._trimmed_mem_percent)
        self._trim_mem_percent = trim
        self._trimmed_mem_percent = trim_array(self.mem_percent, trim)
        return max(self._trimmed_mem_percent)

    def merge_environ(self):
        PsRunInfo.environ.update(self.environ)
        del self.environ
