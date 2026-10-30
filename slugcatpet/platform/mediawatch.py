"""媒体监视：系统里有没有别的程序在放声音（用来判断"用户是不是在听歌"）。

照 platform/envwatch.py 的模式：一个 QTimer 轮询，间隔 1s，连续两次结果一致才切换。

只走 WASAPI 的 IAudioSessionManager2 枚举音频会话，读每个会话的状态和进程名，
不读波形：多数机器的音频驱动不暴露 IAudioMeterInformation（本机实测 E_NOINTERFACE），
所以只能知道"有没有在响"，拿不到音量和节拍。摇摆只能按固定拍子走。

拿不到任何信息时静默降级成"没在放歌"，不抛错、不影响别的模块。
"""

from __future__ import annotations

import ctypes
import os
from ctypes import POINTER, Structure, byref, c_int, c_uint, c_ulong, c_void_p, oledll, windll

from PySide6.QtCore import QObject, QTimer, Signal

POLL_MS = 1000
DEBOUNCE_POLLS = 2  # 连续这么多次判断一致才切换，照 envwatch 的做法

# IAudioSessionControl::GetState
SESSION_INACTIVE, SESSION_ACTIVE, SESSION_EXPIRED = 0, 1, 2

# 默认排除：这些在响多半是开会/来消息，不是听歌。设置里可改。
# 注意浏览器不在里面——很多人就是用浏览器听歌的。
DEFAULT_BLOCKLIST = (
    "wemeetapp.exe",  # 腾讯会议
    "dingtalk.exe",  # 钉钉
    "feishu.exe",  # 飞书
    "lark.exe",
    "ms-teams.exe",  # Teams
    "teams.exe",
    "zoom.exe",
    "wechat.exe",  # 微信
    "wechatappex.exe",
    "wxwork.exe",  # 企业微信
    "discord.exe",
    "qq.exe",
    "telegram.exe",
    "slack.exe",
)

_ole32 = windll.ole32
_kernel32 = windll.kernel32
oledll.ole32.IIDFromString.restype = c_ulong

_CLSCTX_ALL = 23
_PROCESS_QUERY_LIMITED = 0x1000
_MAX_SESSIONS = 32  # 会话数上限，防止异常时死循环


class _GUID(Structure):
    _fields_ = [
        ("Data1", c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]

    def __init__(self, s: str):
        if oledll.ole32.IIDFromString(s, byref(self)) != 0:
            raise ValueError(s)


_I_ENUMERATOR = "{BCDE0395-E52F-467C-8E3D-C4579291692E}"  # CLSID_MMDeviceEnumerator
_I_IMMDEVICE_ENUMERATOR = "{A95664D2-9614-4F35-A746-DE8DB63617E6}"
_I_SESSION_MANAGER2 = "{77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F}"
_I_SESSION_CONTROL2 = "{BFB7FF88-7239-4FC9-8FA2-07C950BE9C6D}"


def _vtable(ptr: c_void_p):
    return ctypes.cast(ptr, POINTER(POINTER(c_void_p)))[0]


def _fn(ptr: c_void_p, idx: int, restype, *argtypes):
    return ctypes.WINFUNCTYPE(restype, c_void_p, *argtypes)(_vtable(ptr)[idx])


def _release(ptr: c_void_p) -> None:
    """IUnknown::Release。每次轮询新建的会话对象都要还回去，不然会漏。"""
    if not ptr or not ptr.value:
        return
    try:
        _fn(ptr, 2, c_ulong)(ptr)
    except Exception:
        pass


def _exe_name(pid: int) -> str:
    """进程号 → exe 文件名（小写）；取不到返回空串。"""
    if pid <= 0:
        return ""
    try:
        _kernel32.OpenProcess.argtypes = [c_uint, c_int, c_uint]
        handle = _kernel32.OpenProcess(_PROCESS_QUERY_LIMITED, 0, pid)
        if not handle:
            return ""
        try:
            _kernel32.QueryFullProcessImageNameW.argtypes = [
                c_void_p,
                c_uint,
                ctypes.c_wchar_p,
                POINTER(c_uint),
            ]
            _kernel32.QueryFullProcessImageNameW.restype = c_int
            buf = ctypes.create_unicode_buffer(1024)
            size = c_uint(1024)
            if not _kernel32.QueryFullProcessImageNameW(handle, 0, buf, byref(size)):
                return ""
            return buf.value.replace("\\", "/").rsplit("/", 1)[-1].lower()
        finally:
            _kernel32.CloseHandle(handle)
    except Exception:
        return ""


class SessionProbe:
    """WASAPI 音频会话读取。COM 对象建一次一直复用，只有会话列表每次重取。

    任何一步失败都退化成"读不到"（available=False），不往外抛。
    """

    def __init__(self):
        self._enum = c_void_p()
        self._dev = c_void_p()
        self._mgr = c_void_p()
        self._ok = False
        self._setup()

    def _setup(self) -> None:
        try:
            _ole32.CoInitializeEx(None, 2)  # COINIT_APARTMENTTHREADED；Qt 已初始化时返回 S_FALSE，无害
        except Exception:
            pass
        try:
            cls, iid = _GUID(_I_ENUMERATOR), _GUID(_I_IMMDEVICE_ENUMERATOR)
            _ole32.CoCreateInstance.restype = c_ulong
            _ole32.CoCreateInstance.argtypes = [
                POINTER(_GUID),
                c_void_p,
                c_ulong,
                POINTER(_GUID),
                POINTER(c_void_p),
            ]
            if _ole32.CoCreateInstance(byref(cls), None, _CLSCTX_ALL, byref(iid), byref(self._enum)):
                return
            get_dev = _fn(self._enum, 4, c_ulong, c_uint, c_uint, POINTER(c_void_p))
            if get_dev(self._enum, 0, 0, byref(self._dev)):  # eRender=0, eConsole=0
                return
            activate = _fn(self._dev, 3, c_ulong, POINTER(_GUID), c_ulong, c_void_p, POINTER(c_void_p))
            if activate(self._dev, byref(_GUID(_I_SESSION_MANAGER2)), _CLSCTX_ALL, None, byref(self._mgr)):
                return
            self._ok = bool(self._mgr.value)
        except Exception:
            self._ok = False

    @property
    def available(self) -> bool:
        return self._ok

    def close(self) -> None:
        for p in (self._mgr, self._dev, self._enum):
            _release(p)
        self._mgr = self._dev = self._enum = c_void_p()
        self._ok = False

    def active_apps(self, skip_pid: int = 0) -> list[str]:
        """正在发声的进程名（小写 exe，已排除系统声音和自己）。"""
        if not self._ok:
            return []
        penum = c_void_p()
        try:
            get_enum = _fn(self._mgr, 5, c_ulong, POINTER(c_void_p))
            if get_enum(self._mgr, byref(penum)) or not penum.value:
                return []
            try:
                count = c_int(0)
                if _fn(penum, 3, c_ulong, POINTER(c_int))(penum, byref(count)):
                    return []
                out: list[str] = []
                for i in range(min(count.value, _MAX_SESSIONS)):
                    out.extend(self._read_one(penum, i, skip_pid))
                return out
            finally:
                _release(penum)
        except Exception:
            return []

    def _read_one(self, penum: c_void_p, idx: int, skip_pid: int) -> list[str]:
        ctl = c_void_p()
        try:
            if _fn(penum, 4, c_ulong, c_int, POINTER(c_void_p))(penum, idx, byref(ctl)) or not ctl.value:
                return []
            try:
                state = c_int(SESSION_INACTIVE)
                if _fn(ctl, 3, c_ulong, POINTER(c_int))(ctl, byref(state)):
                    return []
                if state.value != SESSION_ACTIVE:
                    return []  # 没在响，不用往下查进程
                ctl2 = c_void_p()
                try:
                    qi = _fn(ctl, 0, c_ulong, POINTER(_GUID), POINTER(c_void_p))
                    if qi(ctl, byref(_GUID(_I_SESSION_CONTROL2)), byref(ctl2)) or not ctl2.value:
                        return []
                    pid = c_uint(0)
                    if _fn(ctl2, 14, c_ulong, POINTER(c_uint))(ctl2, byref(pid)):
                        return []
                    if pid.value and pid.value == skip_pid:
                        return []
                    # IsSystemSoundsSession：S_OK(0) 表示是系统提示音
                    if _fn(ctl2, 15, c_ulong)(ctl2) == 0:
                        return []
                    name = _exe_name(pid.value)
                    return [name] if name else []
                finally:
                    _release(ctl2)
            finally:
                _release(ctl)
        except Exception:
            return []


class MediaWatcher(QObject):
    """轮询系统音频会话，判断"有没有别的程序在放声音"。

    只报 playing 的布尔变化（changed 信号），不报音量。
    """

    changed = Signal(bool)  # 有没有在放声音

    def __init__(self, blocklist=(), interval_ms: int = POLL_MS, parent=None):
        super().__init__(parent)
        self._block = {str(b).strip().lower() for b in blocklist if str(b).strip()}
        self._probe = SessionProbe()
        self._self_pid = os.getpid()
        self._playing = False
        self._streak = 0
        self._apps: list[str] = []
        self._timer = QTimer(self)
        self._timer.setInterval(min(interval_ms, 2000))
        self._timer.timeout.connect(self._on_poll)

    def start(self):
        self._timer.start()
        self._on_poll()

    def stop(self):
        self._timer.stop()

    def set_blocklist(self, names) -> None:
        self._block = {str(b).strip().lower() for b in names if str(b).strip()}
        self._streak = 0

    @property
    def available(self) -> bool:
        """这台机器能不能读到音频会话；False 时功能整体不可用。"""
        return self._probe.available

    @property
    def playing(self) -> bool:
        return self._playing

    @property
    def apps(self) -> list[str]:
        """正在发声的进程名（最近一次轮询）。"""
        return list(self._apps)

    def _on_poll(self):
        try:
            apps = self._probe.active_apps(skip_pid=self._self_pid)
        except Exception:
            apps = []
        self._apps = apps
        want = any(a not in self._block for a in apps)
        if want == self._playing:
            self._streak = 0
            return
        self._streak += 1
        if self._streak >= DEBOUNCE_POLLS:
            self._streak = 0
            self._playing = want
            self.changed.emit(want)
