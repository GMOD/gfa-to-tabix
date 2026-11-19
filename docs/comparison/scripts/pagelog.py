#!/usr/bin/env python3
"""pagelog.py SOURCE MOUNT LOG

Mounts a read-only copy of the directory SOURCE at MOUNT (FUSE, through
fusepy) and appends `path offset size` to LOG for every read the kernel asks
of it, with read-ahead off. A program that memory-maps a file under MOUNT
then shows each page it touches as a 4 KB read, which a syscall trace of the
program does not show.
"""
import os
import sys

from fuse import FUSE, Operations


class PageLog(Operations):
    def __init__(self, source, log):
        self.source = source
        self.log = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)

    def real(self, path):
        return os.path.join(self.source, path.lstrip("/"))

    def getattr(self, path, fh=None):
        st = os.lstat(self.real(path))
        return {k: getattr(st, k) for k in ("st_mode", "st_nlink", "st_size", "st_uid", "st_gid",
                                            "st_atime", "st_mtime", "st_ctime")}

    def readdir(self, path, fh):
        return [".", ".."] + os.listdir(self.real(path))

    def open(self, path, flags):
        return os.open(self.real(path), os.O_RDONLY)

    def read(self, path, size, offset, fh):
        os.write(self.log, f"{path}\t{offset}\t{size}\n".encode())
        return os.pread(fh, size, offset)

    def release(self, path, fh):
        os.close(fh)
        return 0


FUSE(PageLog(sys.argv[1], sys.argv[3]), sys.argv[2], foreground=True, ro=True, nothreads=True, max_readahead=0)
