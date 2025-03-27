"""
API Entrypoint
"""

from flask import Flask
from flask_restx import Resource, Api, reqparse
import os
import re

from stargazer.fetcher import Fetcher, InvalidCredentialsException, MissingRepoException
from stargazer.cacher import Cacher

CACHE_MAX_AGE_DAYS = 7
CACHE_DATABASE_FILE = "cache.db"
GH_TOKEN = os.getenv("GH_TOKEN")

app = Flask("stargazer")
api = Api(app)


@api.route("/repos/<string:user>/<string:repo>/starneighbours")
class StarNeighbours(Resource):
    """
    Main route to fetch star neighbors for a given repo
    """

    @api.doc(params={"gh_token": "GitHub token override."})
    def get(self, user: str, repo: str):
        """
        GET /repos/<user>/<repo>/starneighbors handler

        Tries to get the star-neighbors for the given repository.
        Can fail with errors:
        - 400 if the repo owner or repo name does not match the expected pattern
        - 401 if the GH credentials are missing or invalid
        - 404 if the repo is not found on GH
        - 500 if any other error happens on GH side

        :param user: repository owner, should match pattern ^[A-Za-z0-9_.-]+$
        :param repo: repository name, should match pattern ^[A-Za-z0-9_.-]+$

        :return: dict, int for the payload and status code
        """
        parser = reqparse.RequestParser()
        parser.add_argument("gh_token", type=str, help="GitHub token override")
        args = parser.parse_args()
        token = args.get("gh_token", GH_TOKEN)

        if not re.match(r"^[A-Za-z0-9_.-]+$", user):
            return {
                "message": "Invalid username, should only contain letters, numbers, _, - and ."
            }, 400
        if not re.match(r"^[A-Za-z0-9_.-]+$", repo):
            return {
                "message": "Invalid repository, should only contain letters, numbers, _, - and ."
            }, 400
        try:
            fetcher = Fetcher(token)
            cacher = Cacher(CACHE_DATABASE_FILE, CACHE_MAX_AGE_DAYS, fetcher)
            starneighbors = cacher.get_starneighbors(user, repo)
            return starneighbors, 200
        except InvalidCredentialsException:
            return {"message": "Invalid credentials"}, 401
        except MissingRepoException:
            return {"message": "Repository or user not found"}, 404
        except RuntimeError:
            return {"message": "Unexpected error"}, 500


def main():
    app.run(debug=True)


if __name__ == "__main__":
    main()
