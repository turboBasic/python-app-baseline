import app


def test_package_imports() -> None:
    assert app.__name__ == "app"
