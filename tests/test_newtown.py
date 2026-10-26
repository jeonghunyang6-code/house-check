from collector.newtown import ZONES
from collector.regions import REGIONS


def test_zones_well_formed():
    assert len({z.code for z in ZONES}) == len(ZONES)
    for z in ZONES:
        assert z.region_code in REGIONS and z.source.startswith("https://") and z.members
        assert (z.stage, z.stage_no) in {("선도지구", 0), ("구역지정", 1), ("조합설립", 3)}
        assert all(m.startswith(z.region_code[:4]) for m in z.members)
