# SC2 Bot - SaltStack State Files
# States: sc2bot.install, sc2bot.configure, sc2bot.service
# Pillar data and orchestration for deployment sequence

# ============================================
# sc2bot.install
# ============================================
sc2bot.install.system_deps:
  pkg.installed:
    - pkgs:
        - python3
        - python3-pip
        - python3-venv
        - docker.io
        - curl
        - git

sc2bot.install.user:
  user.present:
    - name: sc2bot
    - shell: /bin/bash
    - home: /opt/sc2bot
    - createhome: True
    - require:
        - pkg: sc2bot.install.system_deps

sc2bot.install.data_dir:
  file.directory:
    - name: /opt/sc2bot
    - user: sc2bot
    - group: sc2bot
    - mode: 755
    - makedirs: True
    - require:
        - user: sc2bot.install.user

sc2bot.install.venv:
  cmd.run:
    - name: python3 -m venv /opt/sc2bot/venv
    - runas: sc2bot
    - unless: test -f /opt/sc2bot/venv/bin/activate
    - require:
        - file: sc2bot.install.data_dir

sc2bot.install.python_deps:
  pip.installed:
    - pkgs:
        - burnysc2
        - aiohttp
        - prometheus-client
        - pyyaml
    - bin_env: /opt/sc2bot/venv
    - require:
        - cmd: sc2bot.install.venv

# ============================================
# sc2bot.configure
# ============================================
sc2bot.configure.config_file:
  file.managed:
    - name: /opt/sc2bot/config.yml
    - source: salt://sc2bot/files/config.yml.jinja
    - template: jinja
    - user: sc2bot
    - group: sc2bot
    - mode: 640
    - context:
        env:         {{ pillar.get('sc2bot:env', 'production') }}
        host:        {{ pillar.get('sc2bot:host', '127.0.0.1') }}
        port:        {{ pillar.get('sc2bot:port', 5678) }}
        realtime_id: {{ pillar.get('sc2bot:realtime_id', '') }}
        log_level:   {{ pillar.get('sc2bot:log_level', 'INFO') }}
    - require:
        - cmd: sc2bot.install.venv

sc2bot.configure.log_dir:
  file.directory:
    - name: /opt/sc2bot/logs
    - user: sc2bot
    - group: sc2bot
    - mode: 755
    - require:
        - file: sc2bot.install.data_dir

sc2bot.configure.replay_dir:
  file.directory:
    - name: /opt/sc2bot/replays
    - user: sc2bot
    - group: sc2bot
    - mode: 755

# ============================================
# sc2bot.service
# ============================================
sc2bot.service.systemd_unit:
  file.managed:
    - name: /etc/systemd/system/sc2bot.service
    - source: salt://sc2bot/files/sc2bot.service
    - user: root
    - group: root
    - mode: 644
    - require:
        - file: sc2bot.configure.config_file

sc2bot.service.daemon_reload:
  cmd.run:
    - name: systemctl daemon-reload
    - onchanges:
        - file: sc2bot.service.systemd_unit

sc2bot.service.enabled:
  service.running:
    - name: sc2bot
    - enable: True
    - watch:
        - file: sc2bot.configure.config_file
        - file: sc2bot.service.systemd_unit
    - require:
        - cmd: sc2bot.service.daemon_reload

# ============================================
# Orchestration: deploy sequence
# (run via: salt-run state.orch sc2bot.orchestrate)
# ============================================
# 1. install  → 2. configure  → 3. service
# salt '*' state.apply sc2bot.install
# salt '*' state.apply sc2bot.configure
# salt '*' state.apply sc2bot.service
