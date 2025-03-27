def test_get_project_stars_paginates():
    # create fetcher
    # override per_page -> 3
    # mock requests, page 1 = return 3 elements
    #   page 2 = return 3 elements
    #   page 3 = return 1 element
    #
    pass


def test_get_project_stars_raises_on_status_401():
    pass


def test_get_project_stars_raises_on_status_404():
    pass


def test_get_project_stars_raises_on_status_other():
    pass


def test_get_user_stars_paginate():
    # TODO: Check how this can be tested :x
    pass


def test_get_user_stars_raises_on_status_401():
    pass


def test_get_user_stars_raises_on_status_404():
    pass


def test_get_user_stars_raises_on_status_other():
    pass


def test_add_user_to_queue_gets_processed_with_get_queued_users_stars():
    # mock fetcher.get_user_stars
    # call add user several times
    # call run_queued_users_fetch
    # check calls
    pass


def test_run_queued_users_fetch_returns_exceptions():
    pass


def test_get_queued_users_stars_split_results_and_exceptions():
    pass
