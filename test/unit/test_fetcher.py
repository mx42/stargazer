import aiohttp
import pytest

from urllib.parse import urlparse, parse_qsl

from unittest.mock import patch, Mock, AsyncMock
from stargazer.fetcher import Fetcher, InvalidCredentialsException, MissingRepoException


def get_project_stars_page_mock(raw_url, headers):
    # Validate passed headers
    assert headers.get("Accept") == "application/vnd.github+json"
    assert headers.get("Authorization") == "Bearer token"
    assert "X-GitHub-Api-Version" in headers

    url = urlparse(raw_url)
    qs = dict(parse_qsl(url.query))

    assert "my_user" in url.path
    assert "my_repo" in url.path

    assert "per_page" in qs
    assert "page" in qs

    start = int(qs["per_page"]) * (int(qs["page"]) - 1)
    end = max(7, start + int(qs["per_page"]))

    res = []
    for n in range(start, end):
        res.append({"login": f"star{n}"})
    result = Mock()
    result.status_code = 200
    result.json.return_value = res
    return result


@patch("stargazer.fetcher.requests.get")
def test_get_project_stars_paginates(get_mock):
    # With
    tested = Fetcher("token", max_parallel=2)
    tested.per_page = 3
    get_mock.side_effect = get_project_stars_page_mock

    # When
    res = tested.get_project_stars(user="my_user", repo="my_repo")

    # Then
    get_mock.assert_called()
    assert res == [f"star{n}" for n in range(0, 7)]


@patch("stargazer.fetcher.requests.get")
def test_get_project_stars_raises_on_status_401(get_mock):
    # With
    tested = Fetcher("token", max_parallel=2)
    tested.per_page = 3
    res_object = Mock()
    res_object.status_code = 401
    res_object.json.side_effect = NotImplementedError("shouldn't get there")
    get_mock.return_value = res_object

    # When/Then
    with pytest.raises(expected_exception=InvalidCredentialsException):
        tested.get_project_stars(user="my_user", repo="my_repo")


@patch("stargazer.fetcher.requests.get")
def test_get_project_stars_raises_on_status_404(get_mock):
    # With
    tested = Fetcher("token", max_parallel=2)
    tested.per_page = 3
    res_object = Mock()
    res_object.status_code = 404
    res_object.json.side_effect = NotImplementedError("shouldn't get there")
    get_mock.return_value = res_object

    # When/Then
    with pytest.raises(expected_exception=MissingRepoException):
        tested.get_project_stars(user="my_user", repo="my_repo")


@patch("stargazer.fetcher.requests.get")
def test_get_project_stars_raises_on_status_other(get_mock):
    # With
    tested = Fetcher("token", max_parallel=2)
    tested.per_page = 3
    res_object = Mock()
    res_object.status_code = 500
    res_object.json.side_effect = NotImplementedError("shouldn't get there")
    get_mock.return_value = res_object

    # When/Then
    with pytest.raises(expected_exception=RuntimeError):
        tested.get_project_stars(user="my_user", repo="my_repo")


def get_user_stars_page_mock(raw_url):

    url = urlparse(raw_url)
    qs = dict(parse_qsl(url.query))

    assert "my_user" in url.path

    assert "per_page" in qs
    assert "page" in qs

    start = int(qs["per_page"]) * (int(qs["page"]) - 1)
    end = max(7, start + int(qs["per_page"]))

    res = []
    for n in range(start, end):
        res.append({"full_name": f"repo{n}"})
    result = Mock()
    result.status = 200
    result.json.return_value = res
    return result


@pytest.mark.skip(reason="to be fixed...")
@pytest.mark.asyncio
async def test_get_user_stars_paginate():
    # With
    tested = Fetcher("token", max_parallel=2)
    tested.per_page = 3

    mock_response = AsyncMock()
    mock_response.__aenter__.side_effect = get_user_stars_page_mock
    mock_response.__aexit__.return_value = None

    expected = [f"repo{n}" for n in range(0, 7)]

    with patch("aiohttp.ClientSession.get", return_value=mock_response):
        async with aiohttp.ClientSession() as session:
            response = await tested.get_user_stars(session, user="my_user")
            assert response == expected


@pytest.mark.skip(reason="to be implemented - figure out how to properly test async")
def test_get_user_stars_raises_on_status_401():
    pass


@pytest.mark.skip(reason="to be implemented - figure out how to properly test async")
def test_get_user_stars_raises_on_status_404():
    pass


@pytest.mark.skip(reason="to be implemented - figure out how to properly test async")
def test_get_user_stars_raises_on_status_other():
    pass


@pytest.mark.skip(reason="to be implemented - figure out how to properly test async")
def test_add_user_to_queue_gets_processed_with_get_queued_users_stars():
    # mock fetcher.get_user_stars
    # call add user several times
    # call run_queued_users_fetch
    # check calls
    pass


@pytest.mark.skip(reason="to be implemented - figure out how to properly test async")
def test_run_queued_users_fetch_returns_exceptions():
    pass


@pytest.mark.skip(reason="to be implemented")
def test_get_queued_users_stars_split_results_and_exceptions():
    pass
