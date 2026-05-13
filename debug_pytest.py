import pytest  # noqa: F401

from tests.core.test_abstract import test_serialization_context_summary

try:
    test_serialization_context_summary()
except Exception as e:
    print("FAILED", repr(e))
    import traceback

    traceback.print_exc()
