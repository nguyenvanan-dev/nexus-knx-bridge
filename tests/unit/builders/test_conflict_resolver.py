import pytest
from core.builders.conflict_resolver import ConflictResolver

def test_conflict_resolver():
    resolver = ConflictResolver()
    assert hasattr(resolver, 'resolve')
