import pywintypes
import win32con
import win32file

import io
import msvcrt
from typing import Union


class Win32Error(Exception):
    def __init__(self, err_code: int, message: Union[str, None] = None):
        super().__init__(message or f"Error {hex(err_code)}")
        self.code = err_code


def _get_fd(fd: Union[int, io.IOBase]):
    if isinstance(fd, int):
        return fd
    else:
        return fd.fileno()


def lock(fd: Union[int, io.IOBase]):
    status = pywintypes.OVERLAPPED()
    status.hEvent = 0

    win32file.LockFileEx(msvcrt.get_osfhandle(_get_fd(fd)), win32con.LOCKFILE_EXCLUSIVE_LOCK, 0, -0x10000, status)


def unlock(fd: Union[int, io.IOBase]):
    status = pywintypes.OVERLAPPED
    status.hEvent = 0
    win32file.UnlockFile(msvcrt.get_osfhandle(_get_fd(fd)), 0, -0x10000, status)
