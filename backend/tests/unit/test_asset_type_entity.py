from domain.entities.asset_type import AssetType


def test_asset_type_has_name():
    at = AssetType(name="SaaS")
    assert at.name == "SaaS"
    assert at.id is None


def test_asset_type_with_id():
    at = AssetType(name="ERP", id=1)
    assert at.id == 1
