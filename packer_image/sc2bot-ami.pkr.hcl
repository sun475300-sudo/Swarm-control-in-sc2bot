# ============================================================================
# Phase 603: Packer - SC2 Bot AMI Builder
# ============================================================================
# HashiCorp Packer HCL configuration for building production-ready
# Amazon Machine Images (AMIs) for the SC2 Zerg Commander Bot.
#
# Features:
#   - Amazon EBS builder with gp3 volumes
#   - Python 3.11 + virtualenv for bot runtime
#   - SC2 bot dependencies (burnysc2, numpy, etc.)
#   - systemd service for bot auto-start
#   - Prometheus node_exporter for metrics
#   - Log rotation with logrotate
#   - Security hardening (fail2ban, UFW, SSH lockdown)
#   - Manifest post-processor for CI/CD integration
#
# Usage:
#   packer init sc2bot-ami.pkr.hcl
#   packer validate sc2bot-ami.pkr.hcl
#   packer build sc2bot-ami.pkr.hcl
#
# Override variables:
#   packer build -var="instance_type=c5.xlarge" -var="aws_region=ap-northeast-2" .
# ============================================================================

# ============================================================================
# Packer Settings & Required Plugins
# ============================================================================

packer {
  required_version = ">= 1.9.0"

  required_plugins {
    amazon = {
      version = ">= 1.3.0"
      source  = "github.com/hashicorp/amazon"
    }
  }
}

# ============================================================================
# Variables
# ============================================================================

variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS region where the AMI will be created."

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-\\d{1}$", var.aws_region))
    error_message = "aws_region must be a valid AWS region identifier (e.g., us-east-1)."
  }
}

variable "instance_type" {
  type        = string
  default     = "c5.2xlarge"
  description = "EC2 instance type used during AMI build. c5.2xlarge recommended for SC2 bot workloads."

  validation {
    condition     = contains(["t3.large", "t3.xlarge", "c5.xlarge", "c5.2xlarge", "c5.4xlarge", "m5.xlarge", "m5.2xlarge"], var.instance_type)
    error_message = "instance_type must be a supported type for SC2 bot builds."
  }
}

variable "ami_name_prefix" {
  type        = string
  default     = "sc2-zerg-commander-bot"
  description = "Prefix for the AMI name. Build timestamp is appended automatically."
}

variable "vpc_id" {
  type        = string
  default     = ""
  description = "VPC ID for the build instance. Leave empty to use default VPC."
}

variable "subnet_id" {
  type        = string
  default     = ""
  description = "Subnet ID for the build instance. Leave empty for auto-selection."
}

variable "bot_version" {
  type        = string
  default     = "1.0.0"
  description = "Semantic version of the SC2 bot being deployed."
}

variable "python_version" {
  type        = string
  default     = "3.11"
  description = "Python version to install for the bot runtime."
}

variable "source_ami_filter_name" {
  type        = string
  default     = "ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"
  description = "Name filter for the source AMI."
}

variable "source_ami_owners" {
  type        = list(string)
  default     = ["099720109477"] # Canonical (Ubuntu)
  description = "AWS account IDs that own the source AMI."
}

variable "ssh_username" {
  type        = string
  default     = "ubuntu"
  description = "SSH username for the build instance."
}

variable "volume_size" {
  type        = number
  default     = 50
  description = "Root EBS volume size in GB."
}

variable "sc2_map_pool" {
  type        = list(string)
  default     = ["AcropolisLE", "DiscoBloodbathLE", "EphemeronLE", "ThunderbirdLE", "TritonLE", "WintersGateLE", "WorldofSleepersLE"]
  description = "List of SC2 maps to pre-download for the bot."
}

variable "enable_gpu" {
  type        = bool
  default     = false
  description = "Whether to install GPU drivers (for ML-based bots)."
}

variable "environment" {
  type        = string
  default     = "production"
  description = "Deployment environment tag."

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "environment must be one of: development, staging, production."
  }
}

variable "prometheus_node_exporter_version" {
  type        = string
  default     = "1.7.0"
  description = "Version of Prometheus node_exporter to install."
}

# ============================================================================
# Local Variables
# ============================================================================

locals {
  build_timestamp = formatdate("YYYYMMDD-hhmmss", timestamp())
  ami_name        = "${var.ami_name_prefix}-${var.bot_version}-${local.build_timestamp}"

  common_tags = {
    Name          = local.ami_name
    Project       = "SC2-Zerg-Commander-Bot"
    Environment   = var.environment
    BotVersion    = var.bot_version
    PythonVersion = var.python_version
    BuildDate     = local.build_timestamp
    ManagedBy     = "packer"
    Phase         = "603"
  }

  bot_user        = "sc2bot"
  bot_home        = "/opt/sc2bot"
  bot_venv        = "/opt/sc2bot/venv"
  bot_log_dir     = "/var/log/sc2bot"
  sc2_maps_dir    = "/opt/sc2bot/maps"
  systemd_service = "sc2bot.service"
}

# ============================================================================
# Source: Amazon EBS Builder
# ============================================================================

source "amazon-ebs" "sc2bot" {
  region        = var.aws_region
  instance_type = var.instance_type
  ami_name      = local.ami_name
  ami_description = "SC2 Zerg Commander Bot v${var.bot_version} - Production AMI built on ${local.build_timestamp}"

  # Source AMI filter - latest Ubuntu 22.04 LTS
  source_ami_filter {
    filters = {
      name                = var.source_ami_filter_name
      root-device-type    = "ebs"
      virtualization-type = "hvm"
      architecture        = "x86_64"
    }
    owners      = var.source_ami_owners
    most_recent = true
  }

  # Network configuration
  vpc_id    = var.vpc_id != "" ? var.vpc_id : null
  subnet_id = var.subnet_id != "" ? var.subnet_id : null
  associate_public_ip_address = true

  # SSH configuration
  ssh_username         = var.ssh_username
  ssh_timeout          = "10m"
  ssh_agent_auth       = false
  temporary_key_pair_type = "ed25519"

  # EBS volume configuration
  launch_block_device_mappings {
    device_name           = "/dev/sda1"
    volume_size           = var.volume_size
    volume_type           = "gp3"
    iops                  = 3000
    throughput            = 125
    delete_on_termination = true
    encrypted             = true
  }

  # AMI configuration
  ami_virtualization_type = "hvm"
  ena_support             = true
  force_deregister        = true
  force_delete_snapshot   = true

  # Tags
  tags = local.common_tags

  run_tags = merge(local.common_tags, {
    Name = "packer-builder-${local.ami_name}"
  })

  snapshot_tags = local.common_tags
}

# ============================================================================
# Build Configuration
# ============================================================================

build {
  name    = "sc2bot-ami"
  sources = ["source.amazon-ebs.sc2bot"]

  # ========================================================================
  # Provisioner 1: System Update & Base Packages
  # ========================================================================
  provisioner "shell" {
    inline = [
      "echo '=========================================='",
      "echo 'Phase 603: SC2 Bot AMI Build Starting'",
      "echo '=========================================='",
      "echo 'Bot Version: ${var.bot_version}'",
      "echo 'Python Version: ${var.python_version}'",
      "echo 'Environment: ${var.environment}'",
      "echo ''",

      # Wait for cloud-init to finish
      "echo '[1/10] Waiting for cloud-init to complete...'",
      "sudo cloud-init status --wait",

      # System update
      "echo '[2/10] Updating system packages...'",
      "sudo apt-get update -qq",
      "sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -qq",

      # Install base dependencies
      "echo '[3/10] Installing base dependencies...'",
      "sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \\",
      "  build-essential \\",
      "  software-properties-common \\",
      "  apt-transport-https \\",
      "  ca-certificates \\",
      "  curl \\",
      "  wget \\",
      "  git \\",
      "  jq \\",
      "  unzip \\",
      "  htop \\",
      "  iotop \\",
      "  sysstat \\",
      "  net-tools \\",
      "  dnsutils \\",
      "  vim \\",
      "  tmux \\",
      "  tree \\",
      "  ncdu \\",
      "  awscli"
    ]
    max_retries = 3
  }

  # ========================================================================
  # Provisioner 2: Python 3.11 Installation & Virtual Environment
  # ========================================================================
  provisioner "shell" {
    inline = [
      "echo '[4/10] Installing Python ${var.python_version}...'",

      # Add deadsnakes PPA for Python 3.11
      "sudo add-apt-repository -y ppa:deadsnakes/ppa",
      "sudo apt-get update -qq",
      "sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \\",
      "  python${var.python_version} \\",
      "  python${var.python_version}-venv \\",
      "  python${var.python_version}-dev \\",
      "  python${var.python_version}-distutils",

      # Set Python 3.11 as default python3
      "sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python${var.python_version} 1",
      "sudo update-alternatives --set python3 /usr/bin/python${var.python_version}",

      # Verify Python installation
      "python3 --version",
      "echo 'Python ${var.python_version} installed successfully.'",

      # Create bot user and directories
      "echo 'Creating bot user and directories...'",
      "sudo useradd --system --create-home --home-dir ${local.bot_home} --shell /bin/bash ${local.bot_user}",
      "sudo mkdir -p ${local.bot_home}/{src,config,data,replays,maps,logs}",
      "sudo mkdir -p ${local.bot_log_dir}",

      # Create virtual environment
      "echo 'Creating Python virtual environment...'",
      "sudo python3 -m venv ${local.bot_venv}",
      "sudo ${local.bot_venv}/bin/pip install --upgrade pip setuptools wheel",
    ]
    max_retries = 2
  }

  # ========================================================================
  # Provisioner 3: SC2 Bot Dependencies
  # ========================================================================
  provisioner "shell" {
    inline = [
      "echo '[5/10] Installing SC2 bot dependencies...'",

      # Create requirements file
      "cat <<'REQUIREMENTS' | sudo tee ${local.bot_home}/requirements.txt",
      "# SC2 Bot Core",
      "burnysc2>=6.5.0",
      "sc2>=0.12.0",
      "",
      "# Data Processing",
      "numpy>=1.24.0",
      "scipy>=1.11.0",
      "pandas>=2.0.0",
      "",
      "# Machine Learning (optional, for ML-based decisions)",
      "scikit-learn>=1.3.0",
      "torch>=2.0.0; '${var.enable_gpu}' == 'true'",
      "",
      "# Async & Networking",
      "aiohttp>=3.9.0",
      "websockets>=12.0",
      "",
      "# Monitoring & Metrics",
      "prometheus-client>=0.19.0",
      "psutil>=5.9.0",
      "",
      "# Configuration",
      "pyyaml>=6.0",
      "python-dotenv>=1.0.0",
      "pydantic>=2.5.0",
      "",
      "# Logging",
      "structlog>=23.2.0",
      "python-json-logger>=2.0.0",
      "",
      "# Utilities",
      "click>=8.1.0",
      "rich>=13.7.0",
      "tenacity>=8.2.0",
      "REQUIREMENTS",

      # Install Python dependencies
      "sudo ${local.bot_venv}/bin/pip install -r ${local.bot_home}/requirements.txt",

      # Verify key packages
      "sudo ${local.bot_venv}/bin/python -c \"import sc2; print(f'python-sc2 version: {sc2.__version__}')\"",
      "echo 'SC2 bot dependencies installed successfully.'"
    ]
    max_retries = 2
    timeout     = "15m"
  }

  # ========================================================================
  # Provisioner 4: Copy Bot Source Code
  # ========================================================================
  provisioner "file" {
    source      = "../"
    destination = "/tmp/sc2bot-source"
  }

  provisioner "shell" {
    inline = [
      "echo '[6/10] Deploying bot source code...'",

      # Copy bot source files (excluding unnecessary files)
      "sudo rsync -av --exclude='.git' \\",
      "  --exclude='__pycache__' \\",
      "  --exclude='*.pyc' \\",
      "  --exclude='.env' \\",
      "  --exclude='node_modules' \\",
      "  --exclude='*.md' \\",
      "  --exclude='packer_image' \\",
      "  /tmp/sc2bot-source/ ${local.bot_home}/src/",

      # Create bot configuration
      "cat <<'BOTCONFIG' | sudo tee ${local.bot_home}/config/bot_config.yaml",
      "# SC2 Zerg Commander Bot Configuration",
      "# Auto-generated by Packer build - Phase 603",
      "",
      "bot:",
      "  name: \"Zerg Commander\"",
      "  version: \"${var.bot_version}\"",
      "  race: zerg",
      "  environment: ${var.environment}",
      "",
      "game:",
      "  realtime: false",
      "  step_time: 0.1",
      "  map_pool:",
      "%{ for map in var.sc2_map_pool ~}",
      "    - \"${map}\"",
      "%{ endfor ~}",
      "",
      "strategy:",
      "  default_build_order: hatch_first",
      "  aggression_level: 50",
      "  expansion_priority: standard",
      "  scout_mode: overlord",
      "",
      "performance:",
      "  max_actions_per_frame: 24",
      "  decision_interval_frames: 4",
      "  cache_size: 1000",
      "",
      "logging:",
      "  level: INFO",
      "  file: /var/log/sc2bot/bot.log",
      "  max_size_mb: 100",
      "  backup_count: 5",
      "  json_format: true",
      "",
      "metrics:",
      "  enabled: true",
      "  port: 9101",
      "  endpoint: /metrics",
      "",
      "replays:",
      "  save: true",
      "  directory: ${local.bot_home}/replays",
      "  max_stored: 100",
      "BOTCONFIG",

      # Set ownership
      "sudo chown -R ${local.bot_user}:${local.bot_user} ${local.bot_home}",
      "sudo chmod -R 750 ${local.bot_home}",
      "sudo chown -R ${local.bot_user}:${local.bot_user} ${local.bot_log_dir}",

      # Clean up temp files
      "sudo rm -rf /tmp/sc2bot-source",
      "echo 'Bot source code deployed successfully.'"
    ]
  }

  # ========================================================================
  # Provisioner 5: systemd Service Configuration
  # ========================================================================
  provisioner "shell" {
    inline = [
      "echo '[7/10] Configuring systemd service...'",

      # Create systemd service file
      "cat <<'SYSTEMD' | sudo tee /etc/systemd/system/${local.systemd_service}",
      "[Unit]",
      "Description=SC2 Zerg Commander Bot",
      "Documentation=https://github.com/sc2-zerg-commander",
      "After=network-online.target",
      "Wants=network-online.target",
      "",
      "[Service]",
      "Type=simple",
      "User=${local.bot_user}",
      "Group=${local.bot_user}",
      "WorkingDirectory=${local.bot_home}/src",
      "ExecStartPre=${local.bot_venv}/bin/python -c \"import sc2; print('SC2 lib OK')\"",
      "ExecStart=${local.bot_venv}/bin/python -m run_bot --config ${local.bot_home}/config/bot_config.yaml",
      "ExecReload=/bin/kill -HUP $MAINPID",
      "Restart=on-failure",
      "RestartSec=10",
      "StartLimitBurst=5",
      "StartLimitIntervalSec=60",
      "",
      "# Resource limits",
      "LimitNOFILE=65536",
      "LimitNPROC=4096",
      "MemoryMax=8G",
      "CPUQuota=400%",
      "",
      "# Security hardening",
      "NoNewPrivileges=yes",
      "ProtectSystem=strict",
      "ProtectHome=yes",
      "ReadWritePaths=${local.bot_home}/replays ${local.bot_home}/data ${local.bot_log_dir}",
      "PrivateTmp=yes",
      "ProtectKernelTunables=yes",
      "ProtectKernelModules=yes",
      "ProtectControlGroups=yes",
      "",
      "# Logging",
      "StandardOutput=journal",
      "StandardError=journal",
      "SyslogIdentifier=sc2bot",
      "",
      "# Environment",
      "Environment=PYTHONUNBUFFERED=1",
      "Environment=SC2BOT_ENV=${var.environment}",
      "Environment=SC2BOT_VERSION=${var.bot_version}",
      "EnvironmentFile=-${local.bot_home}/config/.env",
      "",
      "[Install]",
      "WantedBy=multi-user.target",
      "SYSTEMD",

      # Enable the service (don't start yet - no game to connect to)
      "sudo systemctl daemon-reload",
      "sudo systemctl enable ${local.systemd_service}",
      "echo 'systemd service configured and enabled.'"
    ]
  }

  # ========================================================================
  # Provisioner 6: Prometheus Node Exporter
  # ========================================================================
  provisioner "shell" {
    inline = [
      "echo '[8/10] Installing Prometheus node_exporter v${var.prometheus_node_exporter_version}...'",

      # Download and install node_exporter
      "cd /tmp",
      "wget -q https://github.com/prometheus/node_exporter/releases/download/v${var.prometheus_node_exporter_version}/node_exporter-${var.prometheus_node_exporter_version}.linux-amd64.tar.gz",
      "tar xzf node_exporter-${var.prometheus_node_exporter_version}.linux-amd64.tar.gz",
      "sudo mv node_exporter-${var.prometheus_node_exporter_version}.linux-amd64/node_exporter /usr/local/bin/",
      "rm -rf node_exporter-*",

      # Create node_exporter user
      "sudo useradd --system --no-create-home --shell /bin/false node_exporter || true",

      # Create systemd service for node_exporter
      "cat <<'NODEEXP' | sudo tee /etc/systemd/system/node_exporter.service",
      "[Unit]",
      "Description=Prometheus Node Exporter",
      "After=network.target",
      "",
      "[Service]",
      "Type=simple",
      "User=node_exporter",
      "Group=node_exporter",
      "ExecStart=/usr/local/bin/node_exporter \\",
      "  --collector.cpu \\",
      "  --collector.diskstats \\",
      "  --collector.filesystem \\",
      "  --collector.loadavg \\",
      "  --collector.meminfo \\",
      "  --collector.netdev \\",
      "  --collector.stat \\",
      "  --collector.time \\",
      "  --collector.processes \\",
      "  --collector.systemd \\",
      "  --web.listen-address=:9100",
      "Restart=on-failure",
      "RestartSec=5",
      "",
      "[Install]",
      "WantedBy=multi-user.target",
      "NODEEXP",

      "sudo systemctl daemon-reload",
      "sudo systemctl enable node_exporter.service",
      "echo 'Prometheus node_exporter installed successfully.'"
    ]
  }

  # ========================================================================
  # Provisioner 7: Log Rotation Setup
  # ========================================================================
  provisioner "shell" {
    inline = [
      "echo '[9/10] Configuring log rotation...'",

      # SC2 Bot log rotation
      "cat <<'LOGROTATE' | sudo tee /etc/logrotate.d/sc2bot",
      "${local.bot_log_dir}/*.log {",
      "    daily",
      "    rotate 14",
      "    compress",
      "    delaycompress",
      "    missingok",
      "    notifempty",
      "    create 0640 ${local.bot_user} ${local.bot_user}",
      "    sharedscripts",
      "    postrotate",
      "        systemctl reload ${local.systemd_service} > /dev/null 2>&1 || true",
      "    endscript",
      "}",
      "LOGROTATE",

      # Replay file cleanup (keep last 100, rotate weekly)
      "cat <<'REPLAYCLEAN' | sudo tee /etc/cron.weekly/sc2bot-replay-cleanup",
      "#!/bin/bash",
      "# SC2 Bot Replay Cleanup - Keep last 100 replays",
      "REPLAY_DIR=${local.bot_home}/replays",
      "MAX_REPLAYS=100",
      "if [ -d \"$REPLAY_DIR\" ]; then",
      "    REPLAY_COUNT=$(find \"$REPLAY_DIR\" -name '*.SC2Replay' | wc -l)",
      "    if [ \"$REPLAY_COUNT\" -gt \"$MAX_REPLAYS\" ]; then",
      "        find \"$REPLAY_DIR\" -name '*.SC2Replay' -printf '%T@ %p\\n' | \\",
      "            sort -n | head -n $(($REPLAY_COUNT - $MAX_REPLAYS)) | \\",
      "            awk '{print $2}' | xargs rm -f",
      "        echo \"Cleaned up $(($REPLAY_COUNT - $MAX_REPLAYS)) old replays.\"",
      "    fi",
      "fi",
      "REPLAYCLEAN",
      "sudo chmod +x /etc/cron.weekly/sc2bot-replay-cleanup",

      "echo 'Log rotation configured.'"
    ]
  }

  # ========================================================================
  # Provisioner 8: Security Hardening
  # ========================================================================
  provisioner "shell" {
    inline = [
      "echo '[10/10] Applying security hardening...'",

      # ---- fail2ban ----
      "sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq fail2ban",

      "cat <<'FAIL2BAN' | sudo tee /etc/fail2ban/jail.local",
      "[DEFAULT]",
      "bantime  = 3600",
      "findtime = 600",
      "maxretry = 5",
      "backend  = systemd",
      "",
      "[sshd]",
      "enabled = true",
      "port    = ssh",
      "filter  = sshd",
      "logpath = /var/log/auth.log",
      "maxretry = 3",
      "bantime  = 7200",
      "FAIL2BAN",

      "sudo systemctl enable fail2ban",

      # ---- UFW Firewall ----
      "sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ufw",

      # Default deny incoming, allow outgoing
      "sudo ufw default deny incoming",
      "sudo ufw default allow outgoing",

      # Allow SSH
      "sudo ufw allow 22/tcp comment 'SSH'",

      # Allow Prometheus metrics endpoints
      "sudo ufw allow 9100/tcp comment 'Prometheus node_exporter'",
      "sudo ufw allow 9101/tcp comment 'SC2 bot metrics'",

      # Allow SC2 game port range (if hosting)
      "sudo ufw allow 8168/tcp comment 'SC2 game port'",

      # Enable UFW (non-interactive)
      "echo 'y' | sudo ufw enable",
      "sudo ufw status verbose",

      # ---- SSH Hardening ----
      "sudo sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config",
      "sudo sed -i 's/#PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config",
      "sudo sed -i 's/#MaxAuthTries.*/MaxAuthTries 3/' /etc/ssh/sshd_config",
      "sudo sed -i 's/#ClientAliveInterval.*/ClientAliveInterval 300/' /etc/ssh/sshd_config",
      "sudo sed -i 's/#ClientAliveCountMax.*/ClientAliveCountMax 2/' /etc/ssh/sshd_config",
      "sudo sed -i 's/X11Forwarding yes/X11Forwarding no/' /etc/ssh/sshd_config",

      # ---- Kernel Hardening ----
      "cat <<'SYSCTL' | sudo tee /etc/sysctl.d/99-sc2bot-security.conf",
      "# Disable IP forwarding",
      "net.ipv4.ip_forward = 0",
      "",
      "# Disable source routing",
      "net.ipv4.conf.all.accept_source_route = 0",
      "net.ipv4.conf.default.accept_source_route = 0",
      "",
      "# Enable SYN flood protection",
      "net.ipv4.tcp_syncookies = 1",
      "",
      "# Disable ICMP redirects",
      "net.ipv4.conf.all.accept_redirects = 0",
      "net.ipv4.conf.default.accept_redirects = 0",
      "net.ipv4.conf.all.send_redirects = 0",
      "",
      "# Log martian packets",
      "net.ipv4.conf.all.log_martians = 1",
      "",
      "# Disable IPv6 if not needed",
      "net.ipv6.conf.all.disable_ipv6 = 1",
      "net.ipv6.conf.default.disable_ipv6 = 1",
      "",
      "# Increase file descriptor limits",
      "fs.file-max = 65536",
      "",
      "# Optimize for network performance (SC2 game connections)",
      "net.core.somaxconn = 1024",
      "net.ipv4.tcp_max_syn_backlog = 1024",
      "net.core.netdev_max_backlog = 5000",
      "SYSCTL",

      "sudo sysctl --system",

      # ---- Automatic Security Updates ----
      "sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq unattended-upgrades",
      "sudo dpkg-reconfigure -f noninteractive unattended-upgrades",

      "echo 'Security hardening applied successfully.'"
    ]
  }

  # ========================================================================
  # Provisioner 9: Final Cleanup & Validation
  # ========================================================================
  provisioner "shell" {
    inline = [
      "echo '=========================================='",
      "echo 'Final validation and cleanup'",
      "echo '=========================================='",

      # Validate Python environment
      "echo 'Validating Python environment...'",
      "sudo -u ${local.bot_user} ${local.bot_venv}/bin/python --version",
      "sudo -u ${local.bot_user} ${local.bot_venv}/bin/pip list --format=columns | head -20",

      # Validate systemd services
      "echo 'Validating systemd services...'",
      "sudo systemctl is-enabled ${local.systemd_service}",
      "sudo systemctl is-enabled node_exporter.service",
      "sudo systemctl is-enabled fail2ban.service",

      # Validate firewall
      "echo 'Validating firewall rules...'",
      "sudo ufw status",

      # Validate directories
      "echo 'Validating directory structure...'",
      "ls -la ${local.bot_home}/",
      "ls -la ${local.bot_home}/src/ | head -10",
      "ls -la ${local.bot_home}/config/",

      # Disk usage report
      "echo 'Disk usage report...'",
      "df -h /",
      "du -sh ${local.bot_home}/",

      # Cleanup
      "echo 'Cleaning up...'",
      "sudo apt-get autoremove -y -qq",
      "sudo apt-get clean",
      "sudo rm -rf /var/lib/apt/lists/*",
      "sudo rm -rf /tmp/*",
      "sudo rm -rf /var/tmp/*",

      # Clear logs for clean AMI
      "sudo journalctl --vacuum-time=1s",
      "sudo find /var/log -type f -name '*.log' -exec truncate -s 0 {} \\;",

      # Clear bash history
      "history -c",
      "cat /dev/null > ~/.bash_history",

      "echo '=========================================='",
      "echo 'SC2 Bot AMI Build Complete!'",
      "echo 'AMI Name: ${local.ami_name}'",
      "echo 'Bot Version: ${var.bot_version}'",
      "echo 'Environment: ${var.environment}'",
      "echo '=========================================='",
    ]
  }

  # ========================================================================
  # Post-Processor: Manifest Generation
  # ========================================================================
  post-processor "manifest" {
    output     = "sc2bot-ami-manifest.json"
    strip_path = true

    custom_data = {
      bot_version    = var.bot_version
      python_version = var.python_version
      environment    = var.environment
      instance_type  = var.instance_type
      region         = var.aws_region
      build_date     = local.build_timestamp
      phase          = "603"
    }
  }

  # ========================================================================
  # Post-Processor: Checksum for AMI verification
  # ========================================================================
  post-processor "checksum" {
    checksum_types = ["sha256"]
    output         = "sc2bot-ami-{{.ChecksumType}}.checksum"
  }
}
