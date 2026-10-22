"""Time and date awareness service for GDR-AI and Aarushi.
Provides reliable dynamic time retrieval, timezone comparisons, duration arithmetic,
and midnight-crossing calculations.
"""

from datetime import datetime, date, time, timedelta
import re
from typing import Dict, Any, Optional, Tuple
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

COMMON_TZ_ALIASES = {
    "delhi": "Asia/Kolkata",
    "india": "Asia/Kolkata",
    "ist": "Asia/Kolkata",
    "kolkata": "Asia/Kolkata",
    "mumbai": "Asia/Kolkata",
    "london": "Europe/London",
    "uk": "Europe/London",
    "gmt": "GMT",
    "utc": "UTC",
    "new york": "America/New_York",
    "ny": "America/New_York",
    "est": "America/New_York",
    "california": "America/Los_Angeles",
    "sf": "America/Los_Angeles",
    "pst": "America/Los_Angeles",
    "tokyo": "Asia/Tokyo",
    "japan": "Asia/Tokyo",
    "singapore": "Asia/Singapore",
    "dubai": "Asia/Dubai",
    "sydney": "Australia/Sydney",
    "berlin": "Europe/Berlin",
    "paris": "Europe/Paris",
}


def resolve_timezone(tz_name: Optional[str] = None) -> ZoneInfo:
    """Resolve human timezone string or alias to a valid ZoneInfo."""
    if not tz_name:
        return ZoneInfo("Asia/Kolkata")
    
    clean = tz_name.strip().lower()
    if clean in COMMON_TZ_ALIASES:
        return ZoneInfo(COMMON_TZ_ALIASES[clean])
    
    try:
        return ZoneInfo(tz_name)
    except Exception:
        # Fallback to Asia/Kolkata default
        return ZoneInfo("Asia/Kolkata")


class TimeService:
    """Authoritative time and date management engine."""

    def __init__(self, default_tz: str = "Asia/Kolkata"):
        self.default_tz = default_tz

    def get_current_time(self, tz_name: Optional[str] = None) -> Dict[str, Any]:
        """Return rich current time metadata for the given timezone."""
        zone = resolve_timezone(tz_name or self.default_tz)
        now = datetime.now(zone)
        utc_now = datetime.now(ZoneInfo("UTC"))
        
        offset = now.utcoffset()
        offset_hours = offset.total_seconds() / 3600.0 if offset else 0.0
        offset_sign = "+" if offset_hours >= 0 else "-"
        abs_h = int(abs(offset_hours))
        abs_m = int((abs(offset_hours) - abs_h) * 60)
        offset_str = f"{offset_sign}{abs_h:02d}:{abs_m:02d}"

        time_str_12h = now.strftime("%I:%M %p").lstrip("0")
        time_str_24h = now.strftime("%H:%M")
        date_str = now.strftime("%Y-%m-%d")
        day_of_week = now.strftime("%A")
        full_date_str = now.strftime("%B %d, %Y")
        
        hour = now.hour
        if hour < 5:
            phase = "late night"
        elif hour < 12:
            phase = "morning"
        elif hour < 17:
            phase = "afternoon"
        elif hour < 21:
            phase = "evening"
        else:
            phase = "night"

        summary = f"{day_of_week}, {full_date_str} at {time_str_12h} ({zone.key}, UTC{offset_str})"

        return {
            "iso": now.isoformat(),
            "date": date_str,
            "time_12h": time_str_12h,
            "time_24h": time_str_24h,
            "day_of_week": day_of_week,
            "timezone": zone.key,
            "utc_offset": offset_str,
            "utc_iso": utc_now.isoformat(),
            "time_phase": phase,
            "summary": summary,
        }

    @staticmethod
    def parse_time_string(time_str: str) -> time:
        """Parse varied time strings like '10:30 AM', '10:30am', '2:15 PM', '14:15', '9pm'."""
        cleaned = time_str.strip().upper()
        # Handle formats like '9 PM' or '9PM'
        m_simple = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?$", cleaned)
        if m_simple:
            h = int(m_simple.group(1))
            m = int(m_simple.group(2) or 0)
            ampm = m_simple.group(3)
            if ampm == "PM" and h < 12:
                h += 12
            elif ampm == "AM" and h == 12:
                h = 0
            return time(hour=h, minute=m)

        for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M", "%I %p", "%I%p"):
            try:
                dt = datetime.strptime(cleaned, fmt)
                return dt.time()
            except ValueError:
                continue

        raise ValueError(f"Unable to parse time string: '{time_str}'")

    def calculate_duration(
        self,
        time_a_str: str,
        time_b_str: str,
        base_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Calculate the duration between two times, correctly handling midnight crossings."""
        t_a = self.parse_time_string(time_a_str)
        t_b = self.parse_time_string(time_b_str)

        d = base_date or date.today()
        dt_a = datetime.combine(d, t_a)
        dt_b = datetime.combine(d, t_b)

        # If time_b is earlier than time_a, assume it crosses midnight into the next day
        crossed_midnight = False
        if dt_b < dt_a:
            dt_b += timedelta(days=1)
            crossed_midnight = True

        diff = dt_b - dt_a
        total_minutes = int(diff.total_seconds() // 60)
        hours = total_minutes // 60
        minutes = total_minutes % 60

        # Formatted natural English
        parts_en = []
        if hours > 0:
            parts_en.append(f"{hours} hour" + ("s" if hours != 1 else ""))
        if minutes > 0 or not parts_en:
            parts_en.append(f"{minutes} minute" + ("s" if minutes != 1 else ""))
        formatted_en = " and ".join(parts_en)

        # Formatted natural Hinglish
        parts_hi = []
        if hours > 0:
            parts_hi.append(f"{hours} ghante")
        if minutes > 0 or not parts_hi:
            parts_hi.append(f"{minutes} minute")
        formatted_hi = " ".join(parts_hi)

        return {
            "start_time": time_a_str,
            "end_time": time_b_str,
            "hours": hours,
            "minutes": minutes,
            "total_minutes": total_minutes,
            "crossed_midnight": crossed_midnight,
            "formatted_en": formatted_en,
            "formatted_hi": formatted_hi,
            "summary": f"{formatted_en} ({total_minutes} mins total)",
        }

    def compare_timezones(
        self,
        time_str: str,
        tz_from: str = "Asia/Kolkata",
        tz_to: str = "Europe/London",
        ref_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Compare a given time between two timezones and provide meeting planning context."""
        zone_from = resolve_timezone(tz_from)
        zone_to = resolve_timezone(tz_to)

        t = self.parse_time_string(time_str)
        d = ref_date or date.today()

        dt_from = datetime.combine(d, t, tzinfo=zone_from)
        dt_to = dt_from.astimezone(zone_to)

        # Calculate offset difference in hours
        offset_from = dt_from.utcoffset().total_seconds() / 3600.0  # type: ignore
        offset_to = dt_to.utcoffset().total_seconds() / 3600.0  # type: ignore
        diff_hours = offset_to - offset_from

        from_fmt = dt_from.strftime("%I:%M %p").lstrip("0")
        to_fmt = dt_to.strftime("%I:%M %p").lstrip("0")

        diff_sign = "+" if diff_hours >= 0 else "-"
        abs_dh = int(abs(diff_hours))
        abs_dm = int((abs(diff_hours) - abs_dh) * 60)
        diff_str = f"{diff_sign}{abs_dh}h {abs_dm}m" if abs_dm else f"{diff_sign}{abs_dh}h"

        explanation = (
            f"When it is {from_fmt} in {zone_from.key}, it will be {to_fmt} in {zone_to.key} "
            f"({zone_to.key} is {abs_dh} hours {abs_dm} minutes {'ahead of' if diff_hours > 0 else 'behind'} {zone_from.key})."
        )

        return {
            "from_time": from_fmt,
            "from_tz": zone_from.key,
            "to_time": to_fmt,
            "to_tz": zone_to.key,
            "difference_hours": diff_hours,
            "difference_formatted": diff_str,
            "target_date": dt_to.strftime("%Y-%m-%d"),
            "is_different_day": dt_to.date() != dt_from.date(),
            "explanation": explanation,
        }

    def time_until(self, target_datetime_str: str, tz_name: Optional[str] = None) -> Dict[str, Any]:
        """Calculate the remaining time until a specified future datetime/deadline."""
        zone = resolve_timezone(tz_name or self.default_tz)
        now = datetime.now(zone)

        # Attempt to parse target datetime
        dt_target = None
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d",
            "%I:%M %p",
            "%H:%M"
        ):
            try:
                parsed = datetime.strptime(target_datetime_str.strip(), fmt)
                if fmt in ("%I:%M %p", "%H:%M"):
                    # Time today
                    dt_target = datetime.combine(now.date(), parsed.time(), tzinfo=zone)
                    if dt_target < now:
                        dt_target += timedelta(days=1)
                else:
                    dt_target = parsed.replace(tzinfo=zone)
                break
            except ValueError:
                continue

        if not dt_target:
            raise ValueError(f"Could not parse target datetime: '{target_datetime_str}'")

        diff = dt_target - now
        total_seconds = diff.total_seconds()
        is_past = total_seconds < 0

        abs_sec = abs(total_seconds)
        days = int(abs_sec // 86400)
        hours = int((abs_sec % 86400) // 3600)
        minutes = int((abs_sec % 3600) // 60)

        parts = []
        if days > 0:
            parts.append(f"{days} day" + ("s" if days != 1 else ""))
        if hours > 0:
            parts.append(f"{hours} hour" + ("s" if hours != 1 else ""))
        if minutes > 0 or not parts:
            parts.append(f"{minutes} minute" + ("s" if minutes != 1 else ""))
        duration_str = ", ".join(parts)

        summary = f"{duration_str} {'ago' if is_past else 'remaining'}"

        return {
            "target_datetime": dt_target.isoformat(),
            "is_past": is_past,
            "days": days,
            "hours": hours,
            "minutes": minutes,
            "total_seconds": total_seconds,
            "summary": summary,
        }


_TIME_SERVICE = None


def get_time_service() -> TimeService:
    global _TIME_SERVICE
    if _TIME_SERVICE is None:
        _TIME_SERVICE = TimeService()
    return _TIME_SERVICE

