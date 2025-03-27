"""
Module fetching data from the GitHub API
"""

import aiohttp
import asyncio
import logging
import os
import requests

if os.getenv("TESTING"):
    BASE_URL = "http://localhost:8080/"
else:
    BASE_URL = "https://api.github.com/"


class InvalidCredentialsException(Exception):
    """
    Specific exception for invalid credentials (401)
    """

    pass


class MissingRepoException(Exception):
    """
    Specific exception for missing user or repo (404)
    """

    # TODO Add repo as attribute
    pass


class Fetcher:
    """
    Object centralizing fetching functions from GH API
    """

    def __init__(self, gh_token: str, max_parallel: int):
        """
        Constructor - setup GH config

        :param gh_token: Github API token
        :param max_parallel: Maximum parallel queries
        """
        # Number of elements per page to fetch - GH default is 30
        self.per_page = 30

        # Maximum number of parallel queries
        self.max_parallel = max_parallel

        self.logger = logging.getLogger(__name__)

        # Query headers
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {gh_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        # Queue for parallelising the users stars
        self.users_queue = []

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
            f"{BASE_URL}repos/{user}/{repo}/stargazers?per_page={self.per_page}&page={page}",
            headers=self.headers,
        )
        if res.status_code == 200:
            # This is clearly not really strong against change in remote schema but whatever
            items = [item["login"] for item in res.json()]
            if len(items) == self.per_page:
                # TODO: Could use the `link` header to handle pagination. -> more boilerplate but 1 less query on some occurrences
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
            f"{user}/starred?per_page={self.per_page}&page={page}"
        ) as res:
            if res.status == 200:
                items = [item["full_name"] for item in await res.json()]
                if len(items) == self.per_page:
                    _, followup = await self.get_user_stars(session, user, page + 1)
                    items.extend(followup)
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

    async def run_queued_users_fetch(
        self, base_url=f"{BASE_URL}users/"
    ) -> dict[str, list[str]]:
        """
        Run async queries to fetch user stars from the api

        :param base_url: Base URL for possible override

        :return: dict of users -> list of repos
        """
        connector = aiohttp.TCPConnector(limit=self.max_parallel)
        async with aiohttp.ClientSession(
            headers=self.headers,
            connector=connector,
            base_url=base_url,
        ) as session:
            tasks = []
            for user in self.users_queue:
                tasks.append(self.get_user_stars(session, user))
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            return responses

    def get_queued_users_stars(self) -> (dict[str, list[str]], list[Exception]):
        """
        Fetches queued users stars from the API
        """
        if not self.users_queue:
            return {}, []
        resp = asyncio.new_event_loop().run_until_complete(
            self.run_queued_users_fetch()
        )
        response = {}
        errors = []
        for entry in resp:
            if isinstance(entry, Exception):
                errors.append(entry)
                continue
            user, repos = entry
            response[user] = repos
        return response, errors
