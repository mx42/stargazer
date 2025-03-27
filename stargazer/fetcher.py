"""
Module fetching data from the GitHub API
"""

import requests


class InvalidCredentialsException(Exception):
    """
    Specific exception for invalid credentials (401)
    """

    pass


class MissingRepoException(Exception):
    """
    Specific exception for missing user or repo (404)
    """

    pass


class Fetcher:
    """
    Object centralizing fetching functions from GH API
    """

    def __init__(self, gh_token: str):
        """
        Constructor - setup GH config
        """
        self.gh_token = gh_token
        self.per_page = 30

        # TODO: Could use the `link` header to handle the pagination.

    def get_project_stars(self, user: str, repo: str, page: int = 1) -> list[str]:
        """
        Fetches the user names having starred a repo.

        :param user: repository owner
        :param repo: repository name
        :param page: page number (defaults at 1)

        :return: list of user names (string)

        :raises: InvalidCredentialsException if the authentication is missing
        :raises: MissingRepoException if the user or repo doesn't match existing resources
        :raises: RuntimeError if any other error occurs from the request
        """
        res = requests.get(
            f"https://api.github.com/repos/{user}/{repo}/stargazers?per_page={self.per_page}&page={page}",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.gh_token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        if res.status_code == 200:
            items = [item["login"] for item in res.json()]
            if len(items) == self.per_page:
                items.extend(self.get_project_stars(user, repo, page + 1))
            return items
        elif res.status_code == 401:
            raise InvalidCredentialsException()
        elif res.status_code == 404:
            raise MissingRepoException()
        raise RuntimeError(f"Unexpected HTTP Code: {res.status_code}")

    def get_user_stars(self, user, page: int = 1) -> list[str]:
        """
        Fetches the stars of an user

        :param user: user name
        :param page: page number (defaults at 1)

        :return: list of repos (string)

        :raises: InvalidCredentialsException if the authentication is missing
        :raises: MissingRepoException if the user or repo doesn't match existing resources
        :raises: RuntimeError if any other error occurs from the request
        """
        res = requests.get(
            f"https://api.github.com/users/{user}/starred?per_page={self.per_page}&page={page}",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.gh_token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        if res.status_code == 200:
            items = [item["full_name"] for item in res.json()]
            if len(items) == self.per_page:
                items.extend(self.get_user_stars(user, page + 1))
            return items
        elif res.status_code == 401:
            raise InvalidCredentialsException()
        elif res.status_code == 404:
            raise MissingRepoException()
        raise RuntimeError(f"Unexpected HTTP Code: {res.status_code}")
