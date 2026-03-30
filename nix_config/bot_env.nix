# Nix expression for a reproducible SC2 Zerg bot development environment.
# Run with: nix-shell bot_env.nix
# Or: nix develop (if using flakes wrapper)

{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  name = "sc2-zerg-bot-env";

  buildInputs = with pkgs; [
    # Python runtime and core tooling
    python311
    python311Packages.pip
    python311Packages.virtualenv

    # SC2 bot library dependencies (installed via pip inside venv)
    python311Packages.aiohttp
    python311Packages.numpy
    python311Packages.loguru

    # C++ acceleration module build tools
    cmake
    ninja
    gcc13
    clang_16
    pkg-config

    # Protocol Buffers for SC2 API communication
    protobuf

    # Database tooling for battle statistics
    sqlite
    postgresql_15

    # Utilities
    git
    jq
    curl
    gnumake
  ];

  shellHook = ''
    echo "SC2 Zerg Bot Dev Environment (Nix)"
    echo "======================================"

    # Create and activate Python virtual environment
    if [ ! -d ".venv" ]; then
      python3 -m venv .venv
      echo "Created .venv"
    fi
    source .venv/bin/activate

    # Install Python SC2 library if not present
    if ! python -c "import sc2" 2>/dev/null; then
      pip install --quiet burnysc2 loguru aiohttp
      echo "Installed python-sc2 (burnysc2) and deps"
    fi

    export SC2_BOT_ROOT="$(pwd)"
    export SC2PATH="$HOME/StarCraftII"
    echo "SC2PATH = $SC2PATH"
    echo "Ready. Run: python run.py --race Zerg"
  '';
}
