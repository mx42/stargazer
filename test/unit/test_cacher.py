from unittest.mock import Mock

from stargazer.cacher import Cacher
from stargazer.fetcher import MissingRepoException


def test_cacher_grabs_project_stars_from_database_first():
    # With
    mocked_fetcher = Mock()
    tested = Cacher(database=None, max_age_d=1, fetcher=mocked_fetcher)
    tested.conn.sql(
        """
        insert into repo_stars values ('owner1', 'repo1', 'starrer1', current_localtimestamp()),
        ('owner1', 'repo1', 'starrer2', current_localtimestamp()),
        ('owner2', 'repo2', 'starrer3', current_localtimestamp())
        """
    )

    # When
    result = tested.get_project_stars("owner1", "repo1")

    # Then
    assert result == ["starrer1", "starrer2"]
    mocked_fetcher.assert_not_called()


def test_cacher_grabs_project_stars_from_api_and_cache_it():
    # With
    mocked_fetcher = Mock()
    mocked_fetcher.get_project_stars.return_value = ["starrer1", "starrer2"]
    tested = Cacher(database=None, max_age_d=1, fetcher=mocked_fetcher)

    # When
    result = tested.get_project_stars("owner2", "repo2")

    # Then
    assert result == ["starrer1", "starrer2"]
    mocked_fetcher.get_project_stars.assert_called_with("owner2", "repo2")
    in_db = tested.conn.sql(
        """
        select owner, repo, starred_by from repo_stars where owner = 'owner2' and repo = 'repo2'
        """
    ).fetchall()
    assert in_db == [
        ("owner2", "repo2", "starrer1"),
        ("owner2", "repo2", "starrer2"),
    ]


def test_cacher_grabs_ignores_old_database_project_stars():
    # With
    mocked_fetcher = Mock()
    mocked_fetcher.get_project_stars.return_value = ["starrer2", "starrer3"]
    tested = Cacher(database=None, max_age_d=1, fetcher=mocked_fetcher)
    tested.conn.sql(
        """
        insert into repo_stars values ('owner3', 'repo3', 'starrer1', current_localtimestamp() - INTERVAL 2 DAY)
        """
    )

    # When
    result = tested.get_project_stars("owner3", "repo3")

    # Then
    assert result == ["starrer2", "starrer3"]
    mocked_fetcher.get_project_stars.assert_called_with("owner3", "repo3")
    in_db = tested.conn.sql(
        """
        select owner, repo, starred_by from repo_stars where owner = 'owner3' and repo = 'repo3'
        """
    ).fetchall()
    assert in_db == [
        ("owner3", "repo3", "starrer1"),
        ("owner3", "repo3", "starrer2"),
        ("owner3", "repo3", "starrer3"),
    ]


def test_cacher_grabs_user_stars_from_database_first():
    # With
    mocked_fetcher = Mock()
    tested = Cacher(database=None, max_age_d=1, fetcher=mocked_fetcher)
    tested.conn.sql(
        """
        insert into users_stars values ('user1', 'starred1', current_localtimestamp()),
        ('user1', 'starred2', current_localtimestamp()),
        ('user2', 'starred3', current_localtimestamp())
        """
    )

    # When
    result = tested.get_user_stars("user1")

    # Then
    assert result == ["starred1", "starred2"]
    mocked_fetcher.assert_not_called()


def test_cacher_queue_users_if_missing_data():
    # With
    mocked_fetcher = Mock()
    tested = Cacher(database=None, max_age_d=1, fetcher=mocked_fetcher)

    # When
    result = tested.get_user_stars("user2")

    # Then
    assert result == []
    mocked_fetcher.add_user_to_queue.assert_called_with("user2")
    in_db = tested.conn.sql(
        """
        select starred_repo from users_stars where user = 'user2'
        """
    ).fetchall()
    assert in_db == []


def test_cacher_queue_users_if_old_data():
    # With
    mocked_fetcher = Mock()
    tested = Cacher(database=None, max_age_d=1, fetcher=mocked_fetcher)
    tested.conn.sql(
        """
        insert into users_stars values ('user3', 'starred1', current_localtimestamp() - INTERVAL 2 DAY),
        ('user3', 'starred2', current_localtimestamp() - INTERVAL 2 DAY),
        """
    )

    # When
    result = tested.get_user_stars("user3")

    # Then
    assert result == []
    mocked_fetcher.add_user_to_queue.assert_called_with("user3")
    in_db = tested.conn.sql(
        """
        select starred_repo from users_stars where user = 'user3'
        """
    ).fetchall()
    assert in_db == [("starred1",), ("starred2",)]


def test_cacher_grabs_queued_batches_from_api():
    # With
    mocked_fetcher = Mock()
    mocked_fetcher.get_queued_users_stars.return_value = {
        "user1": ["starred1", "starred2"],
        "user2": ["starred1", "starred3"],
    }, None
    tested = Cacher(database=None, max_age_d=1, fetcher=mocked_fetcher)
    in_db = tested.conn.sql(
        """
        select user, starred_repo from users_stars where user = 'user3'
        """
    ).fetchall()
    assert in_db == []

    # When
    result = tested.get_users_stars_from_api()

    # Then
    assert result == {
        "user1": ["starred1", "starred2"],
        "user2": ["starred1", "starred3"],
    }
    mocked_fetcher.get_queued_users_stars.assert_called()
    in_db = tested.conn.sql(
        """
        select user, starred_repo from users_stars
        """
    ).fetchall()
    assert in_db == [
        ("user1", "starred1"),
        ("user1", "starred2"),
        ("user2", "starred1"),
        ("user2", "starred3"),
    ]


def test_cacher_raises_fetcher_errors():
    # With
    mocked_fetcher = Mock()
    mocked_fetcher.get_queued_users_stars.return_value = {
        "user1": ["starred1", "starred2"],
        "user2": ["starred1", "starred3"],
    }, [MissingRepoException()]
    tested = Cacher(database=None, max_age_d=1, fetcher=mocked_fetcher)
    in_db = tested.conn.sql(
        """
        select user, starred_repo from users_stars where user = 'user3'
        """
    ).fetchall()
    assert in_db == []

    # When
    import pytest

    with pytest.raises(expected_exception=RuntimeError):
        tested.get_users_stars_from_api()

    # Then
    mocked_fetcher.get_queued_users_stars.assert_called()
    in_db = tested.conn.sql(
        """
        select user, starred_repo from users_stars
        """
    ).fetchall()
    assert in_db == [
        ("user1", "starred1"),
        ("user1", "starred2"),
        ("user2", "starred1"),
        ("user2", "starred3"),
    ]


def test_cacher_get_starneighbors_aggregates_data():
    # With
    mocked_fetcher = Mock()
    mocked_fetcher.get_project_stars.return_value = ["starrer1", "starrer3"]
    mocked_fetcher.get_queued_users_stars.return_value = {}, []
    tested = Cacher(database=None, max_age_d=1, fetcher=mocked_fetcher)
    tested.conn.sql(
        """
        insert into users_stars values
            ('starrer1', 'owner1/repo1', current_localtimestamp()),
            ('starrer1', 'owner2/repo1', current_localtimestamp()), -- <-
            ('starrer1', 'owner2/repo2', current_localtimestamp()), -- <-
            ('starrer2', 'owner2/repo2', current_localtimestamp()),
            ('starrer3', 'owner1/repo1', current_localtimestamp()),
            ('starrer3', 'owner2/repo2', current_localtimestamp()), -- <-
            ('starrer3', 'owner3/repo3', current_localtimestamp()), -- <-
        """
    )

    # When
    result = tested.get_starneighbors("owner1", "repo1")

    # Then
    assert result == [
        {"repo": "owner2/repo1", "stargazers": ["starrer1"]},
        {"repo": "owner2/repo2", "stargazers": ["starrer1", "starrer3"]},
        {"repo": "owner3/repo3", "stargazers": ["starrer3"]},
    ]
