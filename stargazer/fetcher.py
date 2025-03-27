"""
Module fetching data from the GitHub API
"""

import aiohttp
import asyncio
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
        self.per_page = 30
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {gh_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self.users_queue = []

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
            headers=self.headers,
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

    async def get_user_stars(
        self, session: aiohttp.ClientSession, user: str, page: int = 1
    ) -> (str, list[str]):
        """
        Fetches the stars of an user

        :param user: user name
        :param page: page number (defaults at 1)

        :return: list of repos (string)

        :raises: InvalidCredentialsException if the authentication is missing
        :raises: MissingRepoException if the user or repo doesn't match existing resources
        :raises: RuntimeError if any other error occurs from the request
        """
        async with session.get(
            f"https://api.github.com/users/{user}/starred?per_page={self.per_page}&page={page}",
            headers=self.headers,
        ) as res:
            if res.status == 200:
                items = [item["full_name"] for item in await res.json()]
                if len(items) == self.per_page:
                    items.extend(await self.get_user_stars(session, user, page + 1))
                return user, items
            elif res.status == 401:
                raise InvalidCredentialsException()
            elif res.status == 404:
                raise MissingRepoException()
            raise RuntimeError(f"Unexpected HTTP Code: {res.status}")

    def add_user_to_queue(self, user: str) -> None:
        """
        Adds an user to the queue to poll its stars on the API later.

        :param user: user name to fetch stars from
        """
        self.users_queue.append(user)

    async def run_queued_users_fetch(self) -> dict[str, list[str]]:
        """
        Run async queries to fetch user stars from the api
        """
        async with aiohttp.ClientSession() as session:
            tasks = []
            for user in self.users_queue:
                tasks.append(self.get_user_stars(session, user))
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            return responses

    def get_queued_users_stars(self) -> dict[str, list[str]]:
        """
        Fetches queued users stars from the API
        """
        resp = asyncio.new_event_loop().run_until_complete(
            self.run_queued_users_fetch()
        )
        response = {}
        for entry in resp:
            if isinstance(entry, Exception):
                raise entry
            user, repos = entry
            response[user] = repos
        return response
