"""The fake profile repository honours the shared contract."""

import pytest

from kiseki.adapters.fake.profiles import FakeProfileRepository
from profile_contract import ProfileRepositoryContract


class TestFakeProfileRepository(ProfileRepositoryContract):
    @pytest.fixture
    def profiles(self) -> FakeProfileRepository:
        return FakeProfileRepository()
