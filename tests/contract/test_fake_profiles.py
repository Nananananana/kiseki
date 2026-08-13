"""The fake profile repository honours the shared contract."""

from kiseki.adapters.fake.profiles import FakeProfileRepository
from kiseki.ports.profiles import ProfileRepository
from profile_contract import ProfileRepositoryContract


class TestFakeProfileRepository(ProfileRepositoryContract):
    def make_repository(self) -> ProfileRepository:
        return FakeProfileRepository()
