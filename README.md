Stargazer
=========

This project provides an API to fetch "star-neighbors" of a given GitHub project.
A star-neighbor is a project having at least 1 common star-gazer with the current project.

API Usage:

```
GET /repos/<user>/<repo>/starneighbours
```

Answers with:

```
[
  {
    "repo": "<repoA>",
    "stargazers": ["userA", "userB"]
  },
  {
    "repo": "<repoB>",
    "stargazers": ["userA"]
  }
]
```

Usage
-----
The API runs using Flask, and stores a local cache using DuckDB.

You can install the dependencies using `uv` or `pip`, and run `api` or `stargazer/main.py`.

Please note that the Flask runner shouldn't be used in a "production" environment, rather use nginx or gunicorn for example.

You need to provide a GitHub Token to be able to fetch data from the API.
Please set it up in a `GH_TOKEN` environment variable, or pass it as a `gh_token` header parameter to your queries.
You can create a token at https://github.com/settings/tokens.

Architecture
------------

The code architecture is pretty simple, there's the API endpoint, a "Cacher" to store local cache, and a "Fetcher" to pull data from GitHub.

```
.
├── .envrc             => EnvRC configuration to auto-load env variables & Nix
├── Dockerfile         => Dockerfile to run the app in a container
├── devenv.*           => DevEnv files
├── pyproject.toml     => Python standard project configuration
├── README.md          => This readme!
├── stargazer
│   ├── cacher.py      => Code dealing with the caching part
│   ├── fetcher.py     => Code dealing with the fetching part
│   ├── __init__.py
│   └── main.py        => Main API entry-point
└── uv.lock            => Lockfile for UV
```

Next Steps
----------
* Add tests
* Add parallelism
* Add authentication
Adding some basic auth should be doable quite quickly using flask-security for example.
Actually, since this is a GitHub project, I wonder if one can't "just" create a GitHub App and use the user's tokens to access the API, directly.
Maybe even use GH Pages to publish it? I've never used it, I'm not sure it's possible to have server-side processing, to be further explored.
