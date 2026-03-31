# HashiCorp Vault HCL Policy for SC2 Bot
# Secret management and API key protection for the SC2 Zerg AI bot.
# Apply with: vault policy write sc2bot sc2bot-policy.hcl

# ─── KV Secrets: SC2 Bot Application Secrets ─────────────────────────────────

# Full CRUD access to all sc2bot secrets
path "secret/sc2bot/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

# Read-only access to shared sc2bot config (ladder tokens, API keys)
path "secret/sc2bot/config" {
  capabilities = ["read", "list"]
}

# SC2 API credentials - read only for the bot process
path "secret/sc2bot/api-keys" {
  capabilities = ["read"]
}

# Ladder credentials (sc2ai.net token)
path "secret/sc2bot/ladder" {
  capabilities = ["read"]
}

# Discord webhook secrets
path "secret/sc2bot/discord" {
  capabilities = ["read"]
}

# Deny access to production secrets from non-prod identities
path "secret/sc2bot/prod/*" {
  capabilities = ["deny"]
}

# ─── KV v2 (versioned) Secrets ────────────────────────────────────────────────

path "secret/data/sc2bot/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/metadata/sc2bot/*" {
  capabilities = ["list", "read", "delete"]
}

path "secret/destroy/sc2bot/*" {
  capabilities = ["update"]
}

# ─── Database: Dynamic Credentials for Replay DB ──────────────────────────────

# Request dynamic PostgreSQL credentials for replay database
path "database/creds/sc2bot-role" {
  capabilities = ["read"]
}

# Read-only role for analytics queries
path "database/creds/sc2bot-readonly-role" {
  capabilities = ["read"]
}

# Allow renewing database leases
path "database/renew/*" {
  capabilities = ["update"]
}

# Allow revoking own database credentials
path "database/revoke/*" {
  capabilities = ["update"]
}

# ─── PKI: Certificate Issuance for SC2 Bot TLS ────────────────────────────────

# Issue TLS certificates for sc2bot services
path "pki/issue/sc2bot-cert" {
  capabilities = ["create", "update"]
}

# Read CA certificate chain
path "pki/cert/ca" {
  capabilities = ["read"]
}

# Read CRL
path "pki/crl" {
  capabilities = ["read"]
}

# Intermediate CA for sc2bot domain
path "pki_int/issue/sc2bot-cert" {
  capabilities = ["create", "update"]
}

path "pki_int/cert/ca_chain" {
  capabilities = ["read"]
}

# ─── Auth: Token Self-Management ──────────────────────────────────────────────

# Allow the sc2bot to look up its own token
path "auth/token/lookup-self" {
  capabilities = ["read"]
}

# Allow renewing own token
path "auth/token/renew-self" {
  capabilities = ["update"]
}

# Allow revoking own token (graceful shutdown)
path "auth/token/revoke-self" {
  capabilities = ["update"]
}

# ─── System: Health and Seal Status ───────────────────────────────────────────

# Allow reading Vault health (for readiness probes)
path "sys/health" {
  capabilities = ["read", "sudo"]
}

# Read seal status
path "sys/seal-status" {
  capabilities = ["read"]
}

# ─── Transit: Encryption-as-a-Service ────────────────────────────────────────

# Encrypt/decrypt replay data at rest
path "transit/encrypt/sc2bot-key" {
  capabilities = ["update"]
}

path "transit/decrypt/sc2bot-key" {
  capabilities = ["update"]
}

path "transit/keys/sc2bot-key" {
  capabilities = ["read"]
}
