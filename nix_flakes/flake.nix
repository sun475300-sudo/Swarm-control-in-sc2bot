# Phase 564: Nix Flakes
# SC2 Bot reproducible development environment with Nix

{
  description = "SC2 Zerg Bot — reproducible build with Nix flakes";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    poetry2nix = {
      url = "github:nix-community/poetry2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, poetry2nix }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        inherit (poetry2nix.lib.mkPoetry2Nix { inherit pkgs; })
          mkPoetryApplication mkPoetryEnv;

        # ─────────────────────────────────────────
        # Python environment
        # ─────────────────────────────────────────

        pythonEnv = pkgs.python311.withPackages (ps: with ps; [
          numpy
          scipy
          torch
          # sc2  # uncomment when available
          pytest
          pytest-asyncio
          black
          ruff
          mypy
        ]);

        # ─────────────────────────────────────────
        # Bot application package
        # ─────────────────────────────────────────

        sc2bot = mkPoetryApplication {
          projectDir = self;
          preferWheels = true;
          overrides = pkgs.poetry2nix.defaultPoetryOverrides.extend (
            final: prev: {
              sc2 = prev.sc2.overridePythonAttrs (old: {
                buildInputs = (old.buildInputs or []) ++ [ pkgs.protobuf ];
              });
            }
          );
        };

        # ─────────────────────────────────────────
        # Docker image
        # ─────────────────────────────────────────

        dockerImage = pkgs.dockerTools.buildLayeredImage {
          name = "sc2-zerg-bot";
          tag = "latest";
          contents = [ sc2bot pkgs.python311 ];
          config = {
            Cmd = [ "${sc2bot}/bin/sc2bot" ];
            Env = [
              "PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python"
              "PYTHONUNBUFFERED=1"
            ];
            ExposedPorts = { "8080/tcp" = {}; };
          };
        };

      in {
        # ─────────────────────────────────────────
        # Packages
        # ─────────────────────────────────────────

        packages = {
          default    = sc2bot;
          sc2bot     = sc2bot;
          docker     = dockerImage;
        };

        # ─────────────────────────────────────────
        # Apps
        # ─────────────────────────────────────────

        apps = {
          default = flake-utils.lib.mkApp { drv = sc2bot; };
          bot = {
            type = "app";
            program = "${sc2bot}/bin/sc2bot";
          };
          train = {
            type = "app";
            program = "${sc2bot}/bin/sc2bot-train";
          };
        };

        # ─────────────────────────────────────────
        # Dev shell
        # ─────────────────────────────────────────

        devShells.default = pkgs.mkShell {
          buildInputs = [
            pythonEnv
            pkgs.git
            pkgs.curl
            pkgs.jq
            pkgs.docker
            pkgs.kubectl
            pkgs.helm
            pkgs.protobuf
            pkgs.nodejs_20
            pkgs.cargo
            pkgs.rustc
          ];

          shellHook = ''
            echo "SC2 Bot dev environment loaded"
            echo "Python: $(python --version)"
            export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
            export PYTHONPATH="$PWD:$PYTHONPATH"

            # Auto-activate venv if present
            if [ -d .venv ]; then
              source .venv/bin/activate
              echo "Venv activated"
            fi
          '';

          PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION = "python";
          NIX_PATH = "nixpkgs=${nixpkgs}";
        };

        # ─────────────────────────────────────────
        # Checks (CI)
        # ─────────────────────────────────────────

        checks = {
          inherit sc2bot;

          test = pkgs.runCommand "sc2bot-tests" {
            buildInputs = [ pythonEnv ];
          } ''
            cd ${self}
            export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
            python -m pytest tests/ -x -q --tb=short
            touch $out
          '';

          lint = pkgs.runCommand "sc2bot-lint" {
            buildInputs = [ pythonEnv ];
          } ''
            cd ${self}
            ruff check . --exclude .venv
            touch $out
          '';
        };

        # ─────────────────────────────────────────
        # NixOS module
        # ─────────────────────────────────────────

        nixosModules.sc2bot = { config, lib, pkgs, ... }: {
          options.services.sc2bot = {
            enable = lib.mkEnableOption "SC2 Zerg Bot service";
            port   = lib.mkOption { type = lib.types.port; default = 8080; };
            race   = lib.mkOption { type = lib.types.str;  default = "zerg"; };
          };

          config = lib.mkIf config.services.sc2bot.enable {
            systemd.services.sc2bot = {
              description = "SC2 Zerg Bot";
              wantedBy = [ "multi-user.target" ];
              serviceConfig = {
                ExecStart = "${sc2bot}/bin/sc2bot "
                  + "--race ${config.services.sc2bot.race} "
                  + "--port ${toString config.services.sc2bot.port}";
                Restart = "always";
                RestartSec = 5;
                Environment = [
                  "PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python"
                ];
              };
            };

            networking.firewall.allowedTCPPorts = [ config.services.sc2bot.port ];
          };
        };
      }
    );
}
