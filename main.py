"""24-Hour Weekly Pricing Clock generator.

Renders a polar chart showing peak/off-peak hours across all seven days
for a given timezone. Output: perfected_pricing_clock.png (300 DPI).
"""

import argparse
import subprocess
import zoneinfo
from datetime import datetime, timedelta

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# --- Configuration ---

# Peak windows are defined in UTC, Monday-Friday (UTC weekday), regardless of
# the chart's display timezone. 01:00-04:00 and 06:00-10:00 UTC -> hours 1-3, 6-9.
UTC_PEAK_HOURS = {1, 2, 3, 6, 7, 8, 9}
UTC_PEAK_WEEKDAYS = {0, 1, 2, 3, 4}  # datetime.weekday(): Monday=0 ... Sunday=6

PEAK_COLOR = '#EA4335'
OFF_PEAK_COLOR = '#34A853'

DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

BAR_HEIGHT = 0.95
DAY_LABEL_OFFSET = 1.82
DAY_LABEL_HOUR = 4
RMAX = 8.2
SLICE_EDGE_WIDTH = 1.2
HOURS_PER_DAY = 24
TEXT_COLOR = '#2C3E50'

TITLE_FONT_SIZE = 16
LABEL_FONT_SIZE = 12
DAY_LABEL_FONT_SIZE = 13
BORDER_WIDTH = 1.5
HOUR_LABEL_PAD = 12
HOUR_LABEL_VA = 'center'
HOUR_LABEL_HA = 'center'

FIG_SIZE = (10, 10)
DPI = 300

OUTPUT_FILENAME = 'perfected_pricing_clock.png'

# --- Animation Configuration ---

GIF_FILENAME = 'pricing_clock.gif'
GIF_FPS = 10
GIF_DPI = 100
GIF_INTERVAL_MS = 1000 // GIF_FPS

HIGHLIGHT_COLOR = '#FBBC05'
MARKER_COLOR = '#4285F4'
HIGHLIGHT_LINEWIDTH = 6
MARKER_LINEWIDTH = 3
HIGHLIGHT_MIN_ALPHA = 0.35
MARKER_MIN_ALPHA = 0.25

GIF_LOOP_FRAMES = 84

COMMON_TIMEZONES = [
    'America/Los_Angeles', 'America/Denver', 'America/Chicago',
    'America/New_York', 'America/Halifax', 'America/Tijuana',
    'America/Mexico_City', 'Europe/London', 'Europe/Berlin',
    'Europe/Moscow', 'Asia/Dubai', 'Asia/Kolkata',
    'Asia/Shanghai', 'Asia/Tokyo', 'Australia/Sydney', 'Pacific/Auckland',
    'UTC',
]


def get_system_timezone():
    try:
        path = subprocess.run(['readlink', '/etc/localtime'], capture_output=True, text=True, timeout=5)
        if path.returncode == 0 and path.stdout.strip():
            tz_name = path.stdout.strip()
            if tz_name.startswith('/var/db/timezone/zoneinfo/'):
                tz_name = tz_name.split('/var/db/timezone/zoneinfo/')[-1]
            elif tz_name.startswith('/usr/share/zoneinfo/'):
                tz_name = tz_name.split('/usr/share/zoneinfo/')[-1]
            return zoneinfo.ZoneInfo(tz_name)
    except Exception:
        pass
    try:
        result = subprocess.run(['systemsetup', '-gettimezone'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            tz_name = result.stdout.strip().split(': ')[-1]
            return zoneinfo.ZoneInfo(tz_name)
    except Exception:
        pass
    try:
        return datetime.now().astimezone().tzinfo
    except Exception:
        return zoneinfo.ZoneInfo('UTC')


def select_timezone():
    system_tz = get_system_timezone()
    default_name = str(system_tz)

    print(f"System timezone detected: {default_name}")
    print("\nCommon timezones:")
    for i, tz_name in enumerate(COMMON_TIMEZONES, 1):
        marker = " (default)" if tz_name == default_name else ""
        print(f"  {i}. {tz_name}{marker}")
    print(f"  {len(COMMON_TIMEZONES) + 1}. Enter custom timezone")
    print("  Enter to accept default")

    choice = input(f"Select timezone [1-{len(COMMON_TIMEZONES) + 1}]: ").strip()

    if choice == '' or choice == str(len(COMMON_TIMEZONES) + 1):
        return system_tz

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(COMMON_TIMEZONES):
            return zoneinfo.ZoneInfo(COMMON_TIMEZONES[idx])
        return system_tz
    except ValueError:
        pass

    try:
        return zoneinfo.ZoneInfo(choice)
    except zoneinfo.ZoneInfoNotFoundError:
        return system_tz


def compute_hour_angles():
    angles = np.linspace(0, 2 * np.pi, HOURS_PER_DAY, endpoint=False)
    width = 2 * np.pi / HOURS_PER_DAY
    return angles, width


def setup_axes(figsize=FIG_SIZE):
    fig, ax = plt.subplots(figsize=figsize, subplot_kw={'projection': 'polar'})
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.set_rmax(RMAX)
    return fig, ax


def compute_peak_grid(tz, reference_date=None):
    """For each (day_index, local_hour) cell, determine peak/off-peak by
    converting that local slot to UTC and testing it against the UTC-defined
    peak windows. A reference Monday-start week is used since DST can shift
    which local hours map to the UTC peak windows across the year."""
    if reference_date is None:
        reference_date = datetime.now(tz).date()
    monday = reference_date - timedelta(days=reference_date.weekday())

    grid = [[False] * HOURS_PER_DAY for _ in DAYS]
    for day_index in range(len(DAYS)):
        local_date = monday + timedelta(days=day_index)
        for hour in range(HOURS_PER_DAY):
            local_dt = datetime(local_date.year, local_date.month, local_date.day,
                                 hour, tzinfo=tz)
            utc_dt = local_dt.astimezone(zoneinfo.ZoneInfo('UTC'))
            grid[day_index][hour] = (utc_dt.weekday() in UTC_PEAK_WEEKDAYS
                                      and utc_dt.hour in UTC_PEAK_HOURS)
    return grid


def get_slice_color(day_index, hour, peak_grid):
    return PEAK_COLOR if peak_grid[day_index][hour] else OFF_PEAK_COLOR


def render_rings(ax, angles, width, peak_grid):
    for i, day in enumerate(DAYS):
        radii = i + 1

        for hour in range(HOURS_PER_DAY):
            color = get_slice_color(i, hour, peak_grid)

            ax.bar(angles[hour], BAR_HEIGHT, width=width, bottom=radii, align='edge',
                   color=color, edgecolor='white', linewidth=SLICE_EDGE_WIDTH)


def add_hour_labels(ax, angles):
    hour_labels = [f"{h:02d}:00" for h in range(HOURS_PER_DAY)]
    ax.set_xticks(angles)
    ax.tick_params(axis='x', pad=HOUR_LABEL_PAD)
    ax.set_rlabel_position(32.5)
    ax.set_xticklabels(hour_labels, fontsize=LABEL_FONT_SIZE, fontweight='bold', color=TEXT_COLOR,
                       va=HOUR_LABEL_VA, ha=HOUR_LABEL_HA)


def add_day_labels(ax, angles):
    for i, day in enumerate(DAYS):
        ax.text(angles[DAY_LABEL_HOUR], i + DAY_LABEL_OFFSET, day,
                fontsize=DAY_LABEL_FONT_SIZE,
                fontweight='bold',
                color=TEXT_COLOR,
                va='center',
                ha='center')


def finalize_axes(ax):
    ax.set_yticklabels([])
    ax.grid(False)

    # ax.spines['polar'].set_color('#000000')
    # ax.spines['polar'].set_linewidth(BORDER_WIDTH)
    # ax.spines['polar'].set_visible(False)


def set_title(ax, tz_name):
    ax.set_title(f"24-Hour Weekly Pricing Clock\n{tz_name}\n",
                 fontsize=TITLE_FONT_SIZE, fontweight='bold', color=TEXT_COLOR)
    # ax.grid(True)


def save_and_show(fig, show=True, filename=OUTPUT_FILENAME):
    fig.savefig(filename, dpi=DPI)
    if show:
        plt.show()


def generate_chart(tz=None, show=True, filename=OUTPUT_FILENAME):
    tz = select_timezone() if tz is None else tz

    angles, width = compute_hour_angles()
    fig, ax = setup_axes()
    peak_grid = compute_peak_grid(tz)
    render_rings(ax, angles, width, peak_grid)
    add_hour_labels(ax, angles)
    add_day_labels(ax, angles)
    finalize_axes(ax)
    set_title(ax, str(tz))
    save_and_show(fig, show, filename)


def get_current_day_hour(tz):
    now = datetime.now(tz)
    return now.strftime('%A'), now.hour


def create_day_highlight(ax, day_index):
    theta = np.linspace(0, 2 * np.pi, 400)
    radius = day_index + 1 + BAR_HEIGHT + 0.08
    line, = ax.plot(theta, np.full_like(theta, radius),
                    color=HIGHLIGHT_COLOR, linewidth=HIGHLIGHT_LINEWIDTH,
                    alpha=0.0, zorder=3)
    return line


def create_time_marker(ax, angles, width, hour):
    theta = angles[hour] + width / 2
    inner, outer = 0.4, RMAX - 0.25
    line, = ax.plot([theta, theta], [inner, outer],
                    color=MARKER_COLOR, linewidth=MARKER_LINEWIDTH,
                    alpha=0.0, zorder=3)
    dot, = ax.plot([theta], [outer], marker='o',
                   color=MARKER_COLOR, markersize=8,
                   alpha=0.0, zorder=4)
    return line, dot


def update_animation(frame, highlight, marker_line, marker_dot):
    pulse = abs(np.sin(2 * np.pi * frame / GIF_LOOP_FRAMES))
    h_alpha = HIGHLIGHT_MIN_ALPHA + (1.0 - HIGHLIGHT_MIN_ALPHA) * pulse
    m_alpha = MARKER_MIN_ALPHA + (1.0 - MARKER_MIN_ALPHA) * (1.0 - pulse)

    highlight.set_alpha(h_alpha)
    marker_line.set_alpha(m_alpha)
    marker_dot.set_alpha(m_alpha)
    return highlight, marker_line, marker_dot


def render_animation(tz, show=True, filename=GIF_FILENAME):
    angles, width = compute_hour_angles()
    fig, ax = setup_axes()
    peak_grid = compute_peak_grid(tz)
    render_rings(ax, angles, width, peak_grid)
    add_hour_labels(ax, angles)
    add_day_labels(ax, angles)
    finalize_axes(ax)
    set_title(ax, str(tz))

    day_name, hour = get_current_day_hour(tz)
    day_index = DAYS.index(day_name)
    highlight = create_day_highlight(ax, day_index)
    marker_line, marker_dot = create_time_marker(ax, angles, width, hour)

    animation = FuncAnimation(fig, update_animation, frames=GIF_LOOP_FRAMES,
                              fargs=(highlight, marker_line, marker_dot),
                              interval=GIF_INTERVAL_MS, blit=True)
    animation.save(filename, writer='pillow', fps=GIF_FPS, dpi=GIF_DPI)
    if show:
        plt.show()


def parse_args():
    parser = argparse.ArgumentParser(description="24-Hour Weekly Pricing Clock")
    parser.add_argument('--tz', help='timezone key (default: system timezone)')
    parser.add_argument('--animate', action='store_true', help='render animated GIF instead of static PNG')
    parser.add_argument('--headless', action='store_true', help='do not open a display window')
    return parser.parse_args()


def main():
    args = parse_args()
    tz = select_timezone() if args.tz is None else zoneinfo.ZoneInfo(args.tz)
    if args.animate:
        render_animation(tz, show=not args.headless)
    else:
        generate_chart(tz, show=not args.headless)


if __name__ == '__main__':
    main()
