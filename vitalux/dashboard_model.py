"""Grid positions are stored independently of Qt and window dimensions."""
from copy import deepcopy

TITLES = {
    'hero':'Distribution & Systemdaten', 'cpu':'Prozessor', 'gpu':'Grafik',
    'ram':'Arbeitsspeicher', 'disk':'System-Laufwerk',
    'graph_load':'Auslastung', 'graph_net':'Netzwerk-Verlauf',
    'network':'Netzwerk', 'drives':'Laufwerke',
}
ORDER = tuple(TITLES)
# 12-column native widths and all non-hero sizes stay unchanged. The
# hero is one row shorter; its empty padding is compressed instead of its
# internal logo, typography or information-chip dimensions. The chips are
# always a single indivisible parent tile.
DEFAULT = {
    'hero': (0,0,12,8),
    'cpu': (0,8,3,8), 'gpu': (3,8,3,8),
    'ram': (6,8,3,8), 'disk': (9,8,3,8),
    'graph_load': (0,16,6,11), 'graph_net': (6,16,6,11),
    'network': (0,27,6,8), 'drives': (6,27,6,8),
}
MINSPAN = {'hero': (6,8), 'cpu': (3,6), 'gpu': (3,6), 'ram': (3,6),
           'disk': (3,6), 'graph_load': (4,7), 'graph_net': (4,7),
           'network': (4,5), 'drives': (4,5)}
PITCH = 35
GAP = 14


def clean_layout(data):
    """Reject invalid persisted data without losing valid user positions."""
    out = {k: tuple(v) for k, v in DEFAULT.items()}
    if not isinstance(data, dict):
        return out
    for key in ORDER:
        value = data.get(key)
        if not isinstance(value, (list, tuple)) or len(value) != 4 or not all(type(x) is int for x in value):
            continue
        x,y,w,h = value
        mw,mh = MINSPAN[key]
        if 0 <= x < 12 and 0 <= y <= 500 and mw <= w <= 12 and mh <= h <= 35 and x+w <= 12:
            out[key] = (x,y,w,h)
    return out


def intersect(a,b):
    ax,ay,aw,ah = a; bx,by,bw,bh = b
    return ax < bx+bw and bx < ax+aw and ay < by+bh and by < ay+ah


def settle(positions, anchored=None):
    """Push colliding tiles down while preserving their preferred x positions."""
    positions = deepcopy(positions)
    result = {}
    if anchored in positions:
        result[anchored] = positions[anchored]
    for key in sorted((k for k in positions if k != anchored), key=lambda k: (positions[k][1],positions[k][0], ORDER.index(k))):
        x,y,w,h = positions[key]
        while any(intersect((x,y,w,h), other) for other in result.values()):
            y += 1
            if y > 1000:
                break
        result[key] = (x,y,w,h)
    return result




def compact(positions):
    """Repack remaining tiles after hiding/showing, preserving visual reading order."""
    result = {}
    for key in sorted(positions, key=lambda k:(positions[k][1],positions[k][0], ORDER.index(k))):
        _,_,w,h = positions[key]
        y = 0
        while True:
            found = False
            for x in range(13-w):
                slot = (x,y,w,h)
                if not any(intersect(slot, other) for other in result.values()):
                    result[key] = slot
                    found = True
                    break
            if found: break
            y += 1
            if y > 1000:raise RuntimeError('No free grid space')
    return result


def normalize_order(saved=None, legacy=None):
    """Preserve previous user sequence; migrate placements without keeping sizes."""
    if isinstance(saved, (list, tuple)):
        known = [key for key in saved if key in ORDER]
        if len(known) == len(set(known)) and known:
            return known + [key for key in ORDER if key not in known]
    source = clean_layout(legacy)
    return sorted(ORDER, key=lambda key: (source[key][1],source[key][0],ORDER.index(key)))


def grid_pack(order, hidden=(), columns=12):
    """Reading-order packing on fixed-size tiles. Never overlaps or resizes.

    Each next card goes to the right, or starts a new row if it will not fit.
    A row grows to the height of its tallest default-sized card. This is
    deterministic, so the saved order is stable and small windows can reflow.
    """
    cols = int(columns)
    if cols not in (3, 6, 12):
        raise ValueError('Unsupported column count')
    hidden = set(hidden)
    layout = {}
    x = y = row_height = 0
    for key in order:
        if key not in DEFAULT or key in hidden:
            continue
        native_w, native_h = DEFAULT[key][2:]
        width = cols if key == 'hero' else min(cols, max(1,round(native_w*cols/12)))
        if x and x+width > cols:
            x = 0
            y += row_height
            row_height = 0
        layout[key] = (x,y,width,native_h)
        x += width
        row_height = max(row_height,native_h)
        if x >= cols:
            x = 0
            y += row_height
            row_height = 0
    return layout


def move_order(order, key, index):
    """Pure insertion without duplicate keys or arbitrary pixel coordinates."""
    source = [k for k in order if k != key]
    if key not in order:
        return list(order)
    source.insert(max(0,min(len(source),int(index))),key)
    return source
