import pytest

from tests.client import make_client


@pytest.fixture(scope="session")
def client():
    with make_client() as c:
        yield c
