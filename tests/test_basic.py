def test_import():
    import s390x_auto_path
    assert hasattr(s390x_auto_path, '__version__')
