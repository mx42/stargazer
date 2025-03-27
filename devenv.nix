{ pkgs, lib, config, inputs, ... }:

{
  # https://devenv.sh/basics/
  # https://devenv.sh/packages/
  packages = [ pkgs.uv ];

  # https://devenv.sh/languages/
  languages.python = {
    enable = true;
    version = "3.13";
    uv.enable = true;
    uv.sync.enable = true;
    uv.package = pkgs.uv;
  };

  enterShell = ''
  '';

  processes = {
  };
    # api.exec = "export TESTING=1 && uv run api";

  # https://devenv.sh/services/
  services = {
    # nginx = {
    #   enable = true;
    #   httpConfig = ''{
    #     server {
    #       listen 8080;
    #       location / {
    #         return 200 "Hello, world!";
    #       }
    #     }
    #   }'';
    # };
  };

  containers = {
    test = {
      name = "stargazer-test";
      startupCommand = "export TESTING=1 && uv sync && uv run api";
    };
  };

  # https://devenv.sh/tasks/
  # tasks = {
  #   "myproj:setup".exec = "mytool build";
  #   "devenv:enterShell".after = [ "myproj:setup" ];
  # };

  # https://devenv.sh/tests/
    # wait_for_port 8080
  enterTest = ''
    export TESTING=1 && uv run api &
    wait_for_port 5000
    uv run pytest
  '';

  # https://devenv.sh/git-hooks/
  git-hooks.hooks = {
    black.enable = true;
    ruff.enable = true;
  };

  # See full reference at https://devenv.sh/reference/options/
}
