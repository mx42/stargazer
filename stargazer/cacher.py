"""
Cache layer to possibly reduce a bit the load on GH API.

Implemented using DuckDB because it's convenient and reasonably fast.
Probably a solution involving GraphQL would have been relevant.
"""

import duckdb
import logging

INIT_SQL = """
    create table if not exists repo_stars (owner STRING, repo STRING, starred_by STRING, cached_at TIMESTAMP);
    create table if not exists users_stars (user STRING, starred_repo STRING, cached_at TIMESTAMP);
"""


class Cacher:
    """
    Cache layer access object
    """

    def __init__(self, database: str | None, max_age_d: int, fetcher):
        """
        Constructor - initializes DuckDB connection.

        :param database: database file for duckdb - if None, operates in-memory
        :param max_age_d: max age to cache data for, in days
        :param fetcher: fetcher reference
        """
        # Database file initialization
        if database:
            self.conn = duckdb.connect(database)
        else:
            self.conn = duckdb.connect()
        self.conn.sql(INIT_SQL)
        # TODO: Clean-up old data? Currently data is just filtered out, it might become a mess after some weeks of using it.
        # Also: maybe we can pull all the data in memory... depends on volume.

        # Max cache age to keep
        self.max_age_d = max_age_d

        # Fetcher object
        self.fetcher = fetcher

        self.logger = logging.getLogger(__name__)

    def __del__(self):
        """
        Destructor - closes DuckDB connection.
        """
        self.conn.close()

    def get_project_stars(self, user: str, repo: str) -> list[str]:
        """
        Returns the users having starred a project
        Tries to fetch it from the cache, otherwise polls GitHub API to get it.

        :param user: repository owner
        :param repo: repository name

        :return: list of users (as string)
        """
        res = self.conn.sql(
            f"""select starred_by
            from repo_stars
            where owner = '{user}'
                and repo = '{repo}'
                and cached_at > current_localtimestamp() - INTERVAL {self.max_age_d} DAY
            """
        ).fetchall()
        if not len(res):
            res = self.fetcher.get_project_stars(user, repo)
            for entry in res:
                # TODO: Could send the rows as chunks, need to benchmark duckdb's capabilities.
                self.conn.execute(
                    "insert into repo_stars values (?, ?, ?, current_localtimestamp())",
                    [user, repo, entry],
                )
        else:
            res = [entry[0] for entry in res]
        return res

    def get_user_stars(self, user: str) -> list[str]:
        """
        Returns the stars of an user
        Tries to fetch it from the cache, otherwise adds it to a list to be polled from GitHub API.

        :param user: user to fetch stars

        :return: list of starred repositories
        """
        res = self.conn.sql(
            f"""select starred_repo
            from users_stars
            where user = '{user}'
            and cached_at > current_localtimestamp() - INTERVAL {self.max_age_d} DAY
            """
        ).fetchall()
        if not len(res):
            self.fetcher.add_user_to_queue(user)
            res = []
        else:
            res = [entry[0] for entry in res]
        return res

    def get_users_stars_from_api(self) -> dict[str, list[str]]:
        """
        Fetches the users stars we couldn't find in cache from the api, and cache it

        :return: list of starred repositories
        """
        result, errors = self.fetcher.get_queued_users_stars()
        for user, starred in result.items():
            for entry in starred:
                # TODO: Should chunk/batch insert queries. To be benchmarked
                self.conn.execute(
                    "insert into users_stars values (?, ?, current_localtimestamp())",
                    [user, entry],
                )
        if errors:
            types = {}
            for error in errors:
                if type(error) not in types:
                    types[type(error)] = 0
                types[type(error)] += 1
            raise RuntimeError(
                f"Caught some exceptions fetching the users stars: {str(types)}"
            )
        return result

    def get_starneighbors(self, user: str, repo: str) -> list[dict]:
        """
        Returns the star-neighbors of a given repository

        :param user: repository owner
        :param repo: repository name

        :return: List of dict with key repo (string) and key stargazers (list of strings)
        """
        starneighbors = {}
        for starrer in self.get_project_stars(user, repo):
            repos = self.get_user_stars(starrer)
            for starred_repo in repos:
                if starred_repo not in starneighbors:
                    starneighbors[starred_repo] = []
                starneighbors[starred_repo].append(starrer)
        for starrer, repos in self.get_users_stars_from_api().items():
            for starred_repo in repos:
                if starred_repo not in starneighbors:
                    starneighbors[starred_repo] = []
                starneighbors[starred_repo].append(starrer)
        starneighbors.pop(f"{user}/{repo}", None)
        starneighbors = [{"repo": k, "stargazers": v} for k, v in starneighbors.items()]
        return starneighbors
