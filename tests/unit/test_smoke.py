"""Verify that the package can be imported.

Value objects are added in issue #7.
"""


def test_kiseki_package_is_importable() -> None:
    import kiseki

    assert kiseki is not None
