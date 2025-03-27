"""
Cache layer to possibly reduce a bit the load on GH API.

Implemented using DuckDB because it's convenient and reasonably fast.
Probably a solution involving GraphQL would have been relevant.
"""

import duckdb


class Cacher:
    """
    Cache layer access object
    """

    def __init__(self, database: str, max_age_d: int, fetcher):
        """
        Constructor - initializes DuckDB connection.

        :param database: database file for duckdb
        :param max_age_d: max age to cache data for, in days
        :param fetcher: fetcher reference
        """
        self.conn = duckdb.connect(database)
        self.conn.sql(
            """
            create table if not exists repo_stars (owner STRING, repo STRING, starred_by STRING, cached_at TIMESTAMP);
            create table if not exists users_stars (user STRING, starred_repo STRING, cached_at TIMESTAMP);
            """
        )
        # TODO: Clean-up old data? Currently data is just filtered out, it might become a mess after some weeks of using it.
        self.max_age_d = max_age_d
        self.fetcher = fetcher

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
                self.conn.sql(
                    f"insert into repo_stars values ('{user}', '{repo}', '{entry}', current_localtimestamp())"
                )
        else:
            res = [entry[0] for entry in res]
        return res

    def get_user_stars(self, user: str) -> list[str]:
        """
        Returns the stars of an user
        Tries to fetch it from the cache, otherwise polls GitHub API to get it.

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
            res = self.fetcher.get_user_stars(user)
            for entry in res:
                self.conn.sql(
                    f"insert into users_stars values ('{user}', '{entry}', current_localtimestamp())"
                )
        else:
            res = [entry[0] for entry in res]
        return res

    def get_starneighbors(self, user: str, repo: str) -> list[dict]:
        """
        Returns the star-neighbors of a given repository

        :param user: repository owner
        :param repo: repository name

        :return: List of dict with key repo (string) and key stargazers (list of strings)
        """
        starrers = self.get_project_stars(user, repo)
        starneighbors = {}
        for starrer in starrers:
            starred = self.get_user_stars(starrer)
            for star in starred:
                if star not in starneighbors:
                    starneighbors[star] = []
                starneighbors[star].append(starrer)
        starneighbors.pop(f"{user}/{repo}", None)
        starneighbors = [{"repo": k, "stargazers": v} for k, v in starneighbors.items()]
        return starneighbors
