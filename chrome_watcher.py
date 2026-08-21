from __future__ import annotations

import ctypes
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path


TH32CS_SNAPPROCESS = 0x00000002
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
CREATE_NO_WINDOW = 0x08000000


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


def is_process_running(executable_name: str) -> bool:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32FirstW.restype = wintypes.BOOL
    kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32NextW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == INVALID_HANDLE_VALUE:
        return False
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(entry)
    target = executable_name.casefold()
    try:
        if not kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
            return False
        while True:
            if entry.szExeFile.casefold() == target:
                return True
            if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                return False
    finally:
        kernel32.CloseHandle(snapshot)


def run() -> None:
    frozen = bool(getattr(sys, "frozen", False))
    project_root = Path(sys.executable).resolve().parent if frozen else Path(__file__).resolve().parent
    main_command = (
        [str(project_root / "otp_autofill.exe")]
        if frozen
        else [sys.executable, str(project_root / "main.py")]
    )
    otp_process: subprocess.Popen[bytes] | None = None

    while True:
        chrome_running = is_process_running("chrome.exe")
        otp_running = otp_process is not None and otp_process.poll() is None
        if chrome_running and not otp_running:
            otp_process = subprocess.Popen(
                main_command,
                cwd=project_root,
                creationflags=CREATE_NO_WINDOW,
            )
        elif not chrome_running and otp_running:
            otp_process.terminate()
            try:
                otp_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                otp_process.kill()
            otp_process = None
        time.sleep(3)


if __name__ == "__main__":
    run()
