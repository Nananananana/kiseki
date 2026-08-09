"""パッケージが import できることを確認する。

値オブジェクトの実装は Issue #7 で追加する。
"""


def test_kiseki_package_is_importable() -> None:
    import kiseki

    assert kiseki is not None
