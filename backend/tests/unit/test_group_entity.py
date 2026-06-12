from domain.entities.group import Group


def test_group_defaults_have_none_id():
    g = Group(name="MIS")
    assert g.id is None
    assert g.created_at is None


def test_group_stores_name():
    g = Group(name="HR", id=1)
    assert g.name == "HR"
    assert g.id == 1
