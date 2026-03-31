# OPA Rego Policy: SC2 Bot Role-Based Access Control
# Package: sc2bot.authz
# Enforces RBAC for replay access, API endpoints, and admin operations.
# Evaluate with: opa eval -d sc2bot-rbac.rego -i input.json "data.sc2bot.authz.allow"

package sc2bot.authz

import future.keywords.if
import future.keywords.in
import future.keywords.every

# ─── Default Deny ────────────────────────────────────────────────────────────

default allow := false
default deny := false

# ─── Role Definitions ────────────────────────────────────────────────────────

# Role hierarchy: admin > player > viewer
roles := {
    "admin": {
        "permissions": [
            "replay:read", "replay:write", "replay:delete", "replay:share",
            "bot:start", "bot:stop", "bot:configure", "bot:restart",
            "ladder:read", "ladder:write", "ladder:admin",
            "stats:read", "stats:export",
            "user:read", "user:write", "user:delete",
            "system:read", "system:configure",
        ],
    },
    "player": {
        "permissions": [
            "replay:read", "replay:write", "replay:share",
            "bot:start", "bot:stop",
            "ladder:read", "ladder:write",
            "stats:read",
            "user:read",
        ],
    },
    "viewer": {
        "permissions": [
            "replay:read",
            "ladder:read",
            "stats:read",
            "user:read",
        ],
    },
    "guest": {
        "permissions": [
            "replay:read",
            "ladder:read",
        ],
    },
}

# ─── Helper: Role Lookup ──────────────────────────────────────────────────────

# Get the role of the requesting user
user_role(user_id) := role if {
    some user in data.users
    user.id == user_id
    role := user.role
}

# Check whether a user has a specific permission via their role
has_permission(user_id, permission) if {
    role := user_role(user_id)
    permission in roles[role].permissions
}

# ─── Allow Rules ─────────────────────────────────────────────────────────────

# Allow admin: full access to everything
allow if {
    user_role(input.user.id) == "admin"
    not is_system_endpoint
}

# Allow admin access to system endpoints
allow if {
    user_role(input.user.id) == "admin"
    is_system_endpoint
}

# Allow player: access to player-scoped permissions
allow if {
    user_role(input.user.id) == "player"
    permission_required := required_permission(input.method, input.resource)
    has_permission(input.user.id, permission_required)
    not exceeds_rate_limit(input.user.id)
}

# Allow viewer: read-only access
allow if {
    user_role(input.user.id) == "viewer"
    permission_required := required_permission(input.method, input.resource)
    permission_required in ["replay:read", "ladder:read", "stats:read", "user:read"]
    has_permission(input.user.id, permission_required)
    not exceeds_rate_limit(input.user.id)
}

# Allow guest: public read access to replays and ladder
allow if {
    user_role(input.user.id) == "guest"
    input.method == "GET"
    input.resource in ["replays", "ladder"]
}

# ─── Deny Rules ──────────────────────────────────────────────────────────────

# Deny unauthorized replay access (accessing another player's private replay)
deny if {
    input.resource == "replays"
    input.action == "read"
    replay := data.replays[input.resource_id]
    replay.visibility == "private"
    replay.owner_id != input.user.id
    user_role(input.user.id) != "admin"
}

# Deny deletion of replays by non-owners (unless admin)
deny if {
    input.resource == "replays"
    input.method == "DELETE"
    replay := data.replays[input.resource_id]
    replay.owner_id != input.user.id
    user_role(input.user.id) != "admin"
}

# Deny access during maintenance window (unless admin)
deny if {
    data.system.maintenance_mode == true
    user_role(input.user.id) != "admin"
}

# Deny banned users
deny if {
    some user in data.users
    user.id == input.user.id
    user.status == "banned"
}

# Deny if rate limit exceeded
deny if {
    exceeds_rate_limit(input.user.id)
}

# ─── Rate Limiting ────────────────────────────────────────────────────────────

# Rate limit config per role (requests per minute)
rate_limits := {
    "admin":  1000,
    "player": 200,
    "viewer": 60,
    "guest":  20,
}

exceeds_rate_limit(user_id) if {
    role := user_role(user_id)
    limit := rate_limits[role]
    current_requests := data.rate_counters[user_id].requests_last_minute
    current_requests > limit
}

# ─── Resource-to-Permission Mapping ──────────────────────────────────────────

required_permission(method, resource) := permission if {
    method == "GET"
    permission := concat(":", [resource_base(resource), "read"])
}

required_permission(method, resource) := permission if {
    method in ["POST", "PUT", "PATCH"]
    permission := concat(":", [resource_base(resource), "write"])
}

required_permission(method, resource) := permission if {
    method == "DELETE"
    permission := concat(":", [resource_base(resource), "delete"])
}

resource_base("replays")     := "replay"
resource_base("bots")        := "bot"
resource_base("ladder")      := "ladder"
resource_base("stats")       := "stats"
resource_base("users")       := "user"
resource_base("system")      := "system"

# ─── Helper Predicates ────────────────────────────────────────────────────────

is_system_endpoint if {
    input.resource in ["system", "config", "health", "metrics"]
}

is_read_method if {
    input.method == "GET"
}

is_write_method if {
    input.method in ["POST", "PUT", "PATCH", "DELETE"]
}

# ─── Decision Log Metadata ────────────────────────────────────────────────────

decision_info := {
    "user_id":    input.user.id,
    "user_role":  user_role(input.user.id),
    "resource":   input.resource,
    "method":     input.method,
    "allowed":    allow,
    "denied":     deny,
    "timestamp":  input.timestamp,
}
