# Vault Agent configuration for SC2 Bot
# Provides auto-auth with Kubernetes service account and secret templating.
# Run with: vault agent -config=agent.hcl

# ─── Vault Connection ─────────────────────────────────────────────────────────

vault {
  address = "https://vault.sc2bot-system.svc.cluster.local:8200"

  # Retry on connection failure
  retry {
    num_retries = 5
    min_backoff = "1s"
    max_backoff = "30s"
  }

  # TLS configuration
  tls_skip_verify = false
  ca_cert         = "/var/run/secrets/vault/ca.crt"
}

# ─── Auto-Auth: Kubernetes Method ─────────────────────────────────────────────

auto_auth {
  method "kubernetes" {
    mount_path = "auth/kubernetes"

    config {
      role           = "sc2bot-role"
      token_path     = "/var/run/secrets/kubernetes.io/serviceaccount/token"
      jwt_ttl        = "10m"
    }
  }

  sink "file" {
    config {
      path  = "/vault/agent/token"
      mode  = 0400
    }
  }
}

# ─── Cache ────────────────────────────────────────────────────────────────────

cache {
  use_auto_auth_token = true

  # In-memory cache for frequently accessed secrets
  persist "kubernetes" {
    path                   = "/vault/agent/cache"
    keep_after_import      = true
    exit_on_err            = false
    service_account_token_file = "/var/run/secrets/kubernetes.io/serviceaccount/token"
  }
}

# ─── API Proxy Listener ───────────────────────────────────────────────────────

listener "tcp" {
  address       = "127.0.0.1:8007"
  tls_disable   = true
}

# ─── Secret Templates ─────────────────────────────────────────────────────────

template {
  source      = "/vault/templates/sc2bot-env.ctmpl"
  destination = "/vault/secrets/sc2bot.env"
  perms       = 0400
  command     = "/bin/sh -c 'kill -SIGHUP $(cat /app/sc2bot.pid) 2>/dev/null || true'"

  error_on_missing_key = true

  wait {
    min = "2s"
    max = "10s"
  }
}

template {
  source      = "/vault/templates/db-credentials.ctmpl"
  destination = "/vault/secrets/db.env"
  perms       = 0400
  command     = "/bin/sh -c 'kill -SIGHUP $(cat /app/sc2bot.pid) 2>/dev/null || true'"
}

template {
  source      = "/vault/templates/tls-cert.ctmpl"
  destination = "/vault/secrets/tls/sc2bot.crt"
  perms       = 0444
}

template {
  source      = "/vault/templates/tls-key.ctmpl"
  destination = "/vault/secrets/tls/sc2bot.key"
  perms       = 0400
}

# ─── Logging ──────────────────────────────────────────────────────────────────

log_level  = "info"
log_format = "json"

pid_file = "/vault/agent/vault-agent.pid"
