"""The in-memory fakes must satisfy the same contract as the real thing."""

import pytest
from kiseki.adapters.memory.repositories import (
    InMemoryAnchorRepository,
    InMemoryOutingRepository,
    InMemoryPhotoRepository,
)
from repository_contract import (
    AnchorRepositoryContract,
    OutingRepositoryContract,
    PhotoRepositoryContract,
)


class TestInMemoryPhotoRepository(PhotoRepositoryContract):
    @pytest.fixture
    def photos(self) -> InMemoryPhotoRepository:
        return InMemoryPhotoRepository()


class TestInMemoryOutingRepository(OutingRepositoryContract):
    @pytest.fixture
    def outings(self) -> InMemoryOutingRepository:
        return InMemoryOutingRepository()


class TestInMemoryAnchorRepository(AnchorRepositoryContract):
    @pytest.fixture
    def anchors(self) -> InMemoryAnchorRepository:
        return InMemoryAnchorRepository()
