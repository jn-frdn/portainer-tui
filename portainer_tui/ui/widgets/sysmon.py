"""System monitor bar widget."""

from __future__ import annotations

import time

import psutil
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


def _color(pct: float) -> str:
    if pct >= 80:
        return "red"
    if pct >= 60:
        return "yellow"
    return "green"


def _fmt_rate(bps: float) -> str:
    if bps >= 1_073_741_824:
        return f"{bps / 1_073_741_824:.1f} GB/s"
    if bps >= 1_048_576:
        return f"{bps / 1_048_576:.1f} MB/s"
    if bps >= 1024:
        return f"{bps / 1024:.1f} KB/s"
    return f"{bps:.0f} B/s"


class SystemMonitor(Widget):
    """Compact 1-line system resource monitor."""

    DEFAULT_CSS = """
    SystemMonitor {
        height: 1;
        background: $panel;
        padding: 0 1;
    }
    SystemMonitor Static {
        width: 1fr;
        height: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        psutil.cpu_percent(interval=None)  # prime the CPU counter
        net = psutil.net_io_counters()
        self._prev_net = (net.bytes_sent, net.bytes_recv)
        self._prev_time = time.monotonic()

    def compose(self) -> ComposeResult:
        yield Static("", id="sysmon-text")

    def on_mount(self) -> None:
        self._refresh_stats()
        self.set_interval(2.0, self._refresh_stats)

    def _refresh_stats(self) -> None:
        now = time.monotonic()
        elapsed = now - self._prev_time
        if elapsed <= 0:
            elapsed = 1.0

        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        net = psutil.net_io_counters()

        sent_rate = (net.bytes_sent - self._prev_net[0]) / elapsed
        recv_rate = (net.bytes_recv - self._prev_net[1]) / elapsed
        self._prev_net = (net.bytes_sent, net.bytes_recv)
        self._prev_time = now

        cpu_c = _color(cpu)
        mem_c = _color(mem.percent)
        swap_c = _color(swap.percent)

        mem_used = mem.used / 1_073_741_824
        mem_total = mem.total / 1_073_741_824
        swap_used = swap.used / 1_073_741_824
        swap_total = swap.total / 1_073_741_824

        text = (
            f" CPU [{cpu_c}]{cpu:4.1f}%[/]   "
            f"MEM [{mem_c}]{mem_used:.1f}/{mem_total:.1f} GB  {mem.percent:.0f}%[/]   "
            f"SWAP [{swap_c}]{swap_used:.1f}/{swap_total:.1f} GB  {swap.percent:.0f}%[/]   "
            f"NET ↑ {_fmt_rate(sent_rate)}  ↓ {_fmt_rate(recv_rate)}"
        )
        self.query_one("#sysmon-text", Static).update(text)
