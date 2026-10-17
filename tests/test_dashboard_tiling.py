"""Pure regression tests: conservative auto-tiling never changes card spacing."""
import os
import sys

sys.path.insert(0, os.getcwd())

from vitalux.dashboard_model import DEFAULT, GAP, ORDER, grid_pack, intersect, normalize_order


def check_layout(layout, columns):
    for key, (x, y, w, h) in layout.items():
        assert 0 <= x < columns and x + w <= columns, (key, layout)
        assert y >= 0 and w > 0 and h >= DEFAULT[key][3]
    for i, key in enumerate(layout):
        for other in list(layout)[i + 1:]:
            assert not intersect(layout[key], layout[other]), (key, other, layout)
    # DashboardBoard._frame: adjacent cards retain exactly the former GAP.
    for key, (x, y, w, h) in layout.items():
        for other, (ox, oy, ow, oh) in layout.items():
            if key != other and ox == x + w and oy == y:
                pixel_gap = round(ox * 100) - round(w * 100 + x * 100 - GAP)
                assert pixel_gap == GAP, (key, other, pixel_gap)


def run():
    # The normal dashboard must retain its original geometry without jitter.
    standard = grid_pack(ORDER, (), 12)
    assert standard == DEFAULT, (standard, DEFAULT)
    for cols in (3, 6, 12):
        check_layout(grid_pack(ORDER, (), cols), cols)
        check_layout(grid_pack(ORDER, ("gpu", "ram"), cols), cols)

    # Substantial holes close when previously adjacent cards are reordered.
    keys = ["hero", "graph_load", "cpu", "graph_net",
            "network", "drives", "gpu", "ram", "disk"]
    tiles = grid_pack(keys, (), 12)
    check_layout(tiles, 12)
    assert tiles["graph_load"][2] + tiles["cpu"][2] == 12, tiles
    assert tiles["cpu"][3] == tiles["graph_load"][3], tiles
    # At a narrower breakpoint a small one-cell vacancy remains unchanged.
    narrow = grid_pack(["graph_load", "cpu"], (), 6)
    assert narrow["graph_load"][2] == 3
    assert narrow["cpu"][2] == 2
    # A lonely 25%-width card may only double, rather than become huge.
    lone = grid_pack(["cpu"], (), 12)
    assert lone["cpu"][2] == 6

    # Existing persisted tile order, hidden cards and 14px spacing still work.
    custom = normalize_order(["cpu", "hero", "gpu"])
    assert custom[:3] == ["cpu", "hero", "gpu"]
    reflow = grid_pack(custom, ("graph_net", "drives"), 12)
    check_layout(reflow, 12)
    assert "graph_net" not in reflow and "drives" not in reflow
    assert grid_pack(keys, (), 12) == tiles  # deterministic drag preview
    print("Dashboard smart gap filling, fixed 14px spacing and legacy layout: OK")


if __name__ == "__main__":
    run()
