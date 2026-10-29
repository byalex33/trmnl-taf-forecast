
"""Decode aviationweather.gov TAF JSON for Liquid templates."""
from datetime import datetime, timezone


def _ts(epoch):
    if not epoch:
        return ""
    try:
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc).strftime("%d/%H%Mz")
    except (ValueError, TypeError, OSError):
        return str(epoch)


def _vis(v):
    if v is None:
        return "—"
    if v in ("6+", "P6SM", "CAVOK"):
        return str(v)
    try:
        f = float(v)
        if f >= 6:
            return "6+"
        if f < 1:
            return f"{f:.2f}SM"
        return f"{f:.1f}SM"
    except (TypeError, ValueError):
        return str(v)


def _wind(fc):
    wdir = fc.get("wdir")
    wspd = fc.get("wspd")
    wgst = fc.get("wgst")
    if wdir is None and wspd is None:
        return "—"
    if str(wdir).upper() == "VRB":
        base = f"VRB{int(wspd or 0):02d}KT"
    else:
        try:
            base = f"{int(wdir):03d}{int(wspd or 0):02d}KT"
        except (TypeError, ValueError):
            base = f"{wdir}{wspd}KT"
    if wgst:
        base = base.replace("KT", f"G{int(wgst)}KT")
    return base


def _clouds(clouds):
    if not clouds:
        return "—"
    parts = []
    for c in clouds:
        cover = c.get("cover") or ""
        base = c.get("base")
        typ = c.get("type")
        if cover in ("NSC", "NCD", "CLR", "SKC"):
            parts.append(cover)
        elif base is None:
            parts.append(cover)
        else:
            try:
                parts.append(f"{cover}{int(base/100):03d}" + (typ or ""))
            except (TypeError, ValueError):
                parts.append(f"{cover}{base}")
    return " ".join(parts) if parts else "—"


def _period(fc):
    change = fc.get("fcstChange") or "BASE"
    prob = fc.get("probability")
    label = change
    if prob:
        label = f"PROB{prob} {change}" if change and change != "BASE" else f"PROB{prob}"
    wx = fc.get("wxString") or "NSW"
    if wx == "NSW":
        wx = "—"
    return {
        "label": label,
        "from": _ts(fc.get("timeFrom")),
        "to": _ts(fc.get("timeTo")),
        "wind": _wind(fc),
        "vis": _vis(fc.get("visib")),
        "clouds": _clouds(fc.get("clouds") or []),
        "wx": wx,
    }


def run(input):
    # Array responses arrive under data; single object at root
    rows = input.get("data") if isinstance(input.get("data"), list) else None
    if rows is None:
        if isinstance(input, list):
            rows = input
        elif input.get("icaoId") or input.get("rawTAF"):
            rows = [input]
        else:
            rows = []

    stations = []
    for row in rows:
        periods = [_period(fc) for fc in (row.get("fcsts") or [])]
        stations.append({
            "icao": row.get("icaoId") or "",
            "name": row.get("name") or "",
            "raw": row.get("rawTAF") or "",
            "issued": (row.get("issueTime") or "")[:16].replace("T", " ") + "Z" if row.get("issueTime") else "",
            "periods": periods,
        })

    primary = stations[0] if stations else {
        "icao": "—", "name": "", "raw": "No TAF", "issued": "", "periods": []
    }
    return {
        "icao": primary["icao"],
        "name": primary["name"],
        "raw": primary["raw"],
        "issued": primary["issued"],
        "periods": primary["periods"],
        "stations": stations,
        "station_count": len(stations),
    }
