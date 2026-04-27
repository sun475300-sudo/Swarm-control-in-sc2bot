"""
Phase 653: mTLS Security Gateway for SC2 Bot Communications

Mutual TLS gateway providing secure, authenticated communication channels
for StarCraft II bot-to-server interactions. Manages certificate lifecycle,
enforces mutual authentication, and encrypts all traffic using TLS 1.3.
"""

import hashlib
import hmac
import logging
import os
import secrets
import struct
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Union

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & Constants
# ---------------------------------------------------------------------------


class CertStatus(Enum):
    ACTIVE = auto()
    REVOKED = auto()
    EXPIRED = auto()
    PENDING = auto()


class TLSVersion(Enum):
    TLS_1_2 = "TLSv1.2"
    TLS_1_3 = "TLSv1.3"


class CipherSuite(Enum):
    TLS_AES_128_GCM_SHA256 = "TLS_AES_128_GCM_SHA256"
    TLS_AES_256_GCM_SHA384 = "TLS_AES_256_GCM_SHA384"
    TLS_CHACHA20_POLY1305_SHA256 = "TLS_CHACHA20_POLY1305_SHA256"
    TLS_AES_128_CCM_SHA256 = "TLS_AES_128_CCM_SHA256"


class HandshakeState(Enum):
    IDLE = auto()
    CLIENT_HELLO = auto()
    SERVER_HELLO = auto()
    CERTIFICATE = auto()
    CERTIFICATE_VERIFY = auto()
    FINISHED = auto()
    ESTABLISHED = auto()
    FAILED = auto()


class ChannelState(Enum):
    CLOSED = auto()
    CONNECTING = auto()
    HANDSHAKE = auto()
    OPEN = auto()
    DRAINING = auto()
    ERROR = auto()


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class CertificateInfo:
    """X.509 certificate representation."""

    serial_number: str
    subject_cn: str
    issuer_cn: str
    not_before: float
    not_after: float
    public_key_hash: str
    status: CertStatus = CertStatus.ACTIVE
    is_ca: bool = False
    key_usage: list[str] = field(
        default_factory=lambda: ["digitalSignature", "keyEncipherment"]
    )
    san_entries: list[str] = field(default_factory=list)
    fingerprint_sha256: str = ""
    raw_pem: str = ""

    @property
    def is_valid(self) -> bool:
        now = time.time()
        return (
            self.status == CertStatus.ACTIVE
            and self.not_before <= now <= self.not_after
        )

    @property
    def days_until_expiry(self) -> float:
        return max(0.0, (self.not_after - time.time()) / 86400.0)


@dataclass
class HandshakeRecord:
    """Record of a completed or failed TLS handshake."""

    client_cn: str
    server_cn: str
    timestamp: float
    state: HandshakeState
    tls_version: str
    cipher_suite: str
    duration_ms: float
    error: Optional[str] = None


@dataclass
class TrafficStats:
    """Encrypted traffic statistics for a channel."""

    bytes_sent: int = 0
    bytes_recv: int = 0
    records_sent: int = 0
    records_recv: int = 0
    handshakes_completed: int = 0
    handshakes_failed: int = 0
    last_activity: float = 0.0


# ---------------------------------------------------------------------------
# CertificateAuthority
# ---------------------------------------------------------------------------


class CertificateAuthority:
    """
    Simulated Certificate Authority for issuing and managing X.509 certificates.
    Handles CA key generation, certificate signing, and revocation.
    """

    def __init__(self, ca_name: str = "SC2-Bot-CA", validity_days: int = 365):
        self.ca_name = ca_name
        self.validity_days = validity_days
        self._ca_cert: Optional[CertificateInfo] = None
        self._ca_private_key_hash: str = ""
        self._issued_certs: dict[str, CertificateInfo] = {}
        self._revoked_serials: set[str] = set()
        self._crl_number: int = 0
        self._serial_counter: int = 1000
        self._lock = threading.Lock()

        self._initialize_ca()
        logger.info("CertificateAuthority '%s' initialised", ca_name)

    def _initialize_ca(self) -> None:
        """Generate the root CA certificate and private key."""
        self._ca_private_key_hash = hashlib.sha256(secrets.token_bytes(32)).hexdigest()

        now = time.time()
        serial = self._next_serial()
        fingerprint = hashlib.sha256(
            f"{self.ca_name}:{serial}:{now}".encode()
        ).hexdigest()

        self._ca_cert = CertificateInfo(
            serial_number=serial,
            subject_cn=self.ca_name,
            issuer_cn=self.ca_name,
            not_before=now,
            not_after=now + self.validity_days * 86400,
            public_key_hash=hashlib.sha256(
                self._ca_private_key_hash.encode()
            ).hexdigest()[:40],
            status=CertStatus.ACTIVE,
            is_ca=True,
            key_usage=["keyCertSign", "cRLSign"],
            fingerprint_sha256=fingerprint,
            raw_pem=self._generate_pem_stub(self.ca_name, serial),
        )
        self._issued_certs[serial] = self._ca_cert

    def _next_serial(self) -> str:
        with self._lock:
            self._serial_counter += 1
            return f"{self._serial_counter:08X}"

    def issue_certificate(
        self,
        common_name: str,
        san_entries: Optional[list[str]] = None,
        validity_days: Optional[int] = None,
        key_usage: Optional[list[str]] = None,
    ) -> CertificateInfo:
        """Issue a new certificate signed by this CA."""
        if not self._ca_cert or not self._ca_cert.is_valid:
            raise RuntimeError("CA certificate is not valid")

        days = validity_days or self.validity_days
        now = time.time()
        serial = self._next_serial()
        priv_key = secrets.token_bytes(32)
        pub_key_hash = hashlib.sha256(priv_key).hexdigest()[:40]
        fingerprint = hashlib.sha256(
            f"{common_name}:{serial}:{now}".encode()
        ).hexdigest()

        cert = CertificateInfo(
            serial_number=serial,
            subject_cn=common_name,
            issuer_cn=self.ca_name,
            not_before=now,
            not_after=now + days * 86400,
            public_key_hash=pub_key_hash,
            status=CertStatus.ACTIVE,
            is_ca=False,
            key_usage=key_usage or ["digitalSignature", "keyEncipherment"],
            san_entries=san_entries or [common_name],
            fingerprint_sha256=fingerprint,
            raw_pem=self._generate_pem_stub(common_name, serial),
        )
        with self._lock:
            self._issued_certs[serial] = cert
        logger.info(
            "Certificate issued: CN=%s serial=%s (expires in %d days)",
            common_name,
            serial,
            days,
        )
        return cert

    def revoke_certificate(
        self, serial_number: str, reason: str = "unspecified"
    ) -> bool:
        """Revoke a certificate by serial number."""
        cert = self._issued_certs.get(serial_number)
        if not cert:
            logger.warning("Certificate %s not found for revocation", serial_number)
            return False
        if cert.is_ca:
            logger.error("Cannot revoke the CA certificate")
            return False
        cert.status = CertStatus.REVOKED
        self._revoked_serials.add(serial_number)
        self._crl_number += 1
        logger.info(
            "Certificate %s (CN=%s) revoked: %s", serial_number, cert.subject_cn, reason
        )
        return True

    def is_revoked(self, serial_number: str) -> bool:
        return serial_number in self._revoked_serials

    def verify_certificate(self, cert: CertificateInfo) -> tuple[bool, str]:
        """Verify a certificate against this CA."""
        if cert.issuer_cn != self.ca_name:
            return False, f"Unknown issuer: {cert.issuer_cn}"
        if cert.serial_number in self._revoked_serials:
            return False, "Certificate has been revoked"
        if not cert.is_valid:
            return False, "Certificate is expired or not yet valid"
        stored = self._issued_certs.get(cert.serial_number)
        if not stored:
            return False, "Certificate not found in issued list"
        if stored.fingerprint_sha256 != cert.fingerprint_sha256:
            return False, "Fingerprint mismatch"
        return True, "Valid"

    def get_crl(self) -> dict:
        """Return the Certificate Revocation List."""
        revoked = []
        for serial in self._revoked_serials:
            cert = self._issued_certs.get(serial)
            if cert:
                revoked.append(
                    {
                        "serial": serial,
                        "cn": cert.subject_cn,
                        "revoked_at": time.time(),
                    }
                )
        return {
            "issuer": self.ca_name,
            "crl_number": self._crl_number,
            "revoked_certificates": revoked,
        }

    def get_ca_cert(self) -> Optional[CertificateInfo]:
        return self._ca_cert

    def list_certificates(self) -> list[dict]:
        """List all issued certificates."""
        return [
            {
                "serial": cert.serial_number,
                "cn": cert.subject_cn,
                "status": cert.status.name,
                "days_until_expiry": round(cert.days_until_expiry, 1),
                "is_ca": cert.is_ca,
            }
            for cert in self._issued_certs.values()
        ]

    @staticmethod
    def _generate_pem_stub(cn: str, serial: str) -> str:
        b64_body = hashlib.sha512(f"{cn}:{serial}".encode()).hexdigest()
        lines = [b64_body[i : i + 64] for i in range(0, len(b64_body), 64)]
        return (
            "-----BEGIN CERTIFICATE-----\n"
            + "\n".join(lines)
            + "\n-----END CERTIFICATE-----"
        )


# ---------------------------------------------------------------------------
# CertManager
# ---------------------------------------------------------------------------


class CertManager:
    """
    Manages certificate lifecycle including generation, rotation, storage,
    and expiry monitoring for SC2 bot clients and servers.
    """

    def __init__(self, ca: CertificateAuthority, rotation_threshold_days: float = 30.0):
        self.ca = ca
        self.rotation_threshold_days = rotation_threshold_days
        self._client_certs: dict[str, CertificateInfo] = {}
        self._server_certs: dict[str, CertificateInfo] = {}
        self._rotation_history: list[dict] = []
        self._pinned_fingerprints: dict[str, str] = {}
        self._lock = threading.Lock()
        logger.info(
            "CertManager initialised (rotation_threshold=%.0f days)",
            rotation_threshold_days,
        )

    def create_client_cert(
        self, client_id: str, san_entries: Optional[list[str]] = None
    ) -> CertificateInfo:
        """Create and store a client certificate."""
        cn = f"sc2-bot-client-{client_id}"
        cert = self.ca.issue_certificate(cn, san_entries=san_entries)
        with self._lock:
            self._client_certs[client_id] = cert
            self._pinned_fingerprints[client_id] = cert.fingerprint_sha256
        logger.info("Client cert created: %s", cn)
        return cert

    def create_server_cert(
        self, server_id: str, san_entries: Optional[list[str]] = None
    ) -> CertificateInfo:
        """Create and store a server certificate."""
        cn = f"sc2-server-{server_id}"
        sans = san_entries or [cn, f"{server_id}.sc2.local"]
        cert = self.ca.issue_certificate(cn, san_entries=sans)
        with self._lock:
            self._server_certs[server_id] = cert
            self._pinned_fingerprints[server_id] = cert.fingerprint_sha256
        logger.info("Server cert created: %s", cn)
        return cert

    def rotate_certificate(
        self, entity_id: str, is_client: bool = True
    ) -> Optional[CertificateInfo]:
        """Rotate a certificate by issuing a new one and revoking the old."""
        store = self._client_certs if is_client else self._server_certs
        old_cert = store.get(entity_id)
        if not old_cert:
            logger.warning("No existing cert for '%s' to rotate", entity_id)
            return None

        # Issue replacement
        new_cert = (
            self.create_client_cert(entity_id)
            if is_client
            else self.create_server_cert(entity_id)
        )

        # Revoke old
        self.ca.revoke_certificate(old_cert.serial_number, reason="superseded")

        self._rotation_history.append(
            {
                "entity_id": entity_id,
                "old_serial": old_cert.serial_number,
                "new_serial": new_cert.serial_number,
                "rotated_at": time.time(),
            }
        )
        logger.info(
            "Certificate rotated for '%s': %s -> %s",
            entity_id,
            old_cert.serial_number,
            new_cert.serial_number,
        )
        return new_cert

    def check_expiring(self, threshold_days: Optional[float] = None) -> list[dict]:
        """Find certificates approaching expiry."""
        threshold = threshold_days or self.rotation_threshold_days
        expiring: list[dict] = []
        all_certs = list(self._client_certs.items()) + list(self._server_certs.items())
        for eid, cert in all_certs:
            if cert.is_valid and cert.days_until_expiry <= threshold:
                expiring.append(
                    {
                        "entity_id": eid,
                        "cn": cert.subject_cn,
                        "serial": cert.serial_number,
                        "days_remaining": round(cert.days_until_expiry, 1),
                    }
                )
        return expiring

    def auto_rotate_expiring(self) -> list[str]:
        """Automatically rotate all certificates near expiry."""
        expiring = self.check_expiring()
        rotated: list[str] = []
        for entry in expiring:
            eid = entry["entity_id"]
            is_client = eid in self._client_certs
            result = self.rotate_certificate(eid, is_client=is_client)
            if result:
                rotated.append(eid)
        if rotated:
            logger.info("Auto-rotated %d certificates", len(rotated))
        return rotated

    def verify_pinning(self, entity_id: str, cert: CertificateInfo) -> bool:
        """Verify a certificate matches its pinned fingerprint."""
        pinned = self._pinned_fingerprints.get(entity_id)
        if not pinned:
            logger.warning("No pinned fingerprint for '%s'", entity_id)
            return False
        match = pinned == cert.fingerprint_sha256
        if not match:
            logger.warning("Pin verification FAILED for '%s'", entity_id)
        return match

    def get_client_cert(self, client_id: str) -> Optional[CertificateInfo]:
        return self._client_certs.get(client_id)

    def get_server_cert(self, server_id: str) -> Optional[CertificateInfo]:
        return self._server_certs.get(server_id)

    def get_rotation_history(self) -> list[dict]:
        return list(self._rotation_history)

    def get_stats(self) -> dict:
        return {
            "client_certs": len(self._client_certs),
            "server_certs": len(self._server_certs),
            "pinned_entries": len(self._pinned_fingerprints),
            "rotations_performed": len(self._rotation_history),
        }


# ---------------------------------------------------------------------------
# TLSConfig
# ---------------------------------------------------------------------------


class TLSConfig:
    """
    TLS configuration including protocol version, cipher suites,
    and handshake parameters for SC2 bot communication.
    """

    def __init__(
        self,
        min_version: TLSVersion = TLSVersion.TLS_1_3,
        max_version: TLSVersion = TLSVersion.TLS_1_3,
        require_client_cert: bool = True,
    ):
        self.min_version = min_version
        self.max_version = max_version
        self.require_client_cert = require_client_cert
        self.cipher_suites: list[CipherSuite] = [
            CipherSuite.TLS_AES_256_GCM_SHA384,
            CipherSuite.TLS_CHACHA20_POLY1305_SHA256,
            CipherSuite.TLS_AES_128_GCM_SHA256,
        ]
        self.session_timeout_sec: int = 3600
        self.max_early_data_size: int = 16384
        self.enable_ocsp_stapling: bool = True
        self.enable_sct: bool = True
        self.alpn_protocols: list[str] = ["sc2-bot/1.0", "h2", "http/1.1"]
        self.session_ticket_keys: list[bytes] = []
        self._rotate_session_keys()
        logger.info(
            "TLSConfig created (min=%s, max=%s, mTLS=%s)",
            min_version.value,
            max_version.value,
            require_client_cert,
        )

    def _rotate_session_keys(self) -> None:
        """Generate new session ticket encryption keys."""
        self.session_ticket_keys = [secrets.token_bytes(32) for _ in range(3)]

    def set_cipher_suites(self, suites: list[CipherSuite]) -> None:
        """Set allowed cipher suites in preference order."""
        self.cipher_suites = suites
        logger.info("Cipher suites updated: %s", [s.value for s in suites])

    def negotiate_version(self, client_versions: list[str]) -> Optional[TLSVersion]:
        """Negotiate the highest mutually supported TLS version."""
        preferred = [TLSVersion.TLS_1_3, TLSVersion.TLS_1_2]
        for ver in preferred:
            if ver.value in client_versions:
                if self._version_gte(ver, self.min_version):
                    return ver
        return None

    def negotiate_cipher(self, client_suites: list[str]) -> Optional[CipherSuite]:
        """Negotiate a cipher suite with the client."""
        for suite in self.cipher_suites:
            if suite.value in client_suites:
                return suite
        return None

    def negotiate_alpn(self, client_protos: list[str]) -> Optional[str]:
        """Negotiate an ALPN protocol."""
        for proto in self.alpn_protocols:
            if proto in client_protos:
                return proto
        return None

    @staticmethod
    def _version_gte(a: TLSVersion, b: TLSVersion) -> bool:
        order = {TLSVersion.TLS_1_2: 0, TLSVersion.TLS_1_3: 1}
        return order.get(a, 0) >= order.get(b, 0)

    def to_dict(self) -> dict:
        return {
            "min_version": self.min_version.value,
            "max_version": self.max_version.value,
            "require_client_cert": self.require_client_cert,
            "cipher_suites": [s.value for s in self.cipher_suites],
            "session_timeout_sec": self.session_timeout_sec,
            "alpn_protocols": self.alpn_protocols,
            "ocsp_stapling": self.enable_ocsp_stapling,
        }


# ---------------------------------------------------------------------------
# mTLSGateway
# ---------------------------------------------------------------------------


class mTLSGateway:
    """
    Mutual TLS gateway that enforces authenticated, encrypted communication
    between SC2 bot clients and game servers.
    """

    def __init__(
        self,
        ca: CertificateAuthority,
        cert_manager: CertManager,
        tls_config: Optional[TLSConfig] = None,
        listen_addr: str = "0.0.0.0",
        listen_port: int = 8443,
    ):
        self.ca = ca
        self.cert_manager = cert_manager
        self.tls_config = tls_config or TLSConfig()
        self.listen_addr = listen_addr
        self.listen_port = listen_port

        self._server_cert: Optional[CertificateInfo] = None
        self._active_sessions: dict[str, dict] = {}
        self._handshake_log: list[HandshakeRecord] = []
        self._traffic_stats = TrafficStats()
        self._running = False
        self._lock = threading.Lock()
        self._blocked_fingerprints: set[str] = set()
        self._rate_limits: dict[str, list[float]] = defaultdict(list)
        self._rate_limit_max: int = 100
        self._rate_limit_window: float = 60.0
        logger.info("mTLSGateway created (%s:%d)", listen_addr, listen_port)

    def initialize(self, server_id: str = "gateway-primary") -> bool:
        """Initialize the gateway with a server certificate."""
        self._server_cert = self.cert_manager.create_server_cert(
            server_id,
            san_entries=[
                f"sc2-server-{server_id}",
                f"{server_id}.sc2.local",
                "localhost",
            ],
        )
        logger.info("Gateway initialised with cert CN=%s", self._server_cert.subject_cn)
        return True

    def start(self) -> bool:
        """Start the mTLS gateway."""
        if not self._server_cert:
            logger.error("Gateway not initialised: no server certificate")
            return False
        self._running = True
        logger.info("mTLS gateway started on %s:%d", self.listen_addr, self.listen_port)
        return True

    def stop(self) -> None:
        """Stop the gateway and close all sessions."""
        self._running = False
        session_count = len(self._active_sessions)
        self._active_sessions.clear()
        logger.info("mTLS gateway stopped (%d sessions closed)", session_count)

    def perform_handshake(
        self, client_cert: CertificateInfo, client_hello: Optional[dict] = None
    ) -> HandshakeRecord:
        """
        Perform a mutual TLS handshake with a client.
        Validates client certificate and negotiates session parameters.
        """
        start_time = time.time()
        hello = client_hello or {}

        # Rate limiting
        client_key = client_cert.subject_cn
        if not self._check_rate_limit(client_key):
            record = HandshakeRecord(
                client_cn=client_cert.subject_cn,
                server_cn=self._server_cert.subject_cn if self._server_cert else "",
                timestamp=start_time,
                state=HandshakeState.FAILED,
                tls_version="",
                cipher_suite="",
                duration_ms=0.0,
                error="Rate limit exceeded",
            )
            self._handshake_log.append(record)
            self._traffic_stats.handshakes_failed += 1
            return record

        # Check blocked fingerprints
        if client_cert.fingerprint_sha256 in self._blocked_fingerprints:
            record = HandshakeRecord(
                client_cn=client_cert.subject_cn,
                server_cn=self._server_cert.subject_cn if self._server_cert else "",
                timestamp=start_time,
                state=HandshakeState.FAILED,
                tls_version="",
                cipher_suite="",
                duration_ms=(time.time() - start_time) * 1000,
                error="Blocked fingerprint",
            )
            self._handshake_log.append(record)
            self._traffic_stats.handshakes_failed += 1
            return record

        # Verify client certificate
        valid, reason = self.ca.verify_certificate(client_cert)
        if not valid:
            record = HandshakeRecord(
                client_cn=client_cert.subject_cn,
                server_cn=self._server_cert.subject_cn if self._server_cert else "",
                timestamp=start_time,
                state=HandshakeState.FAILED,
                tls_version="",
                cipher_suite="",
                duration_ms=(time.time() - start_time) * 1000,
                error=f"Certificate verification failed: {reason}",
            )
            self._handshake_log.append(record)
            self._traffic_stats.handshakes_failed += 1
            logger.warning(
                "Handshake failed for %s: %s", client_cert.subject_cn, reason
            )
            return record

        # Negotiate TLS version
        client_versions = hello.get("tls_versions", [TLSVersion.TLS_1_3.value])
        tls_version = self.tls_config.negotiate_version(client_versions)
        if not tls_version:
            record = HandshakeRecord(
                client_cn=client_cert.subject_cn,
                server_cn=self._server_cert.subject_cn if self._server_cert else "",
                timestamp=start_time,
                state=HandshakeState.FAILED,
                tls_version="",
                cipher_suite="",
                duration_ms=(time.time() - start_time) * 1000,
                error="No common TLS version",
            )
            self._handshake_log.append(record)
            self._traffic_stats.handshakes_failed += 1
            return record

        # Negotiate cipher suite
        client_suites = hello.get(
            "cipher_suites", [CipherSuite.TLS_AES_256_GCM_SHA384.value]
        )
        cipher = self.tls_config.negotiate_cipher(client_suites)
        if not cipher:
            record = HandshakeRecord(
                client_cn=client_cert.subject_cn,
                server_cn=self._server_cert.subject_cn if self._server_cert else "",
                timestamp=start_time,
                state=HandshakeState.FAILED,
                tls_version=tls_version.value,
                cipher_suite="",
                duration_ms=(time.time() - start_time) * 1000,
                error="No common cipher suite",
            )
            self._handshake_log.append(record)
            self._traffic_stats.handshakes_failed += 1
            return record

        # Generate session
        session_id = secrets.token_hex(16)
        master_secret = secrets.token_bytes(48)
        duration_ms = (time.time() - start_time) * 1000

        with self._lock:
            self._active_sessions[session_id] = {
                "client_cn": client_cert.subject_cn,
                "client_serial": client_cert.serial_number,
                "tls_version": tls_version.value,
                "cipher_suite": cipher.value,
                "master_secret_hash": hashlib.sha256(master_secret).hexdigest(),
                "created_at": time.time(),
                "last_activity": time.time(),
                "bytes_transferred": 0,
            }

        record = HandshakeRecord(
            client_cn=client_cert.subject_cn,
            server_cn=self._server_cert.subject_cn if self._server_cert else "",
            timestamp=start_time,
            state=HandshakeState.ESTABLISHED,
            tls_version=tls_version.value,
            cipher_suite=cipher.value,
            duration_ms=duration_ms,
        )
        self._handshake_log.append(record)
        self._traffic_stats.handshakes_completed += 1
        logger.info(
            "Handshake OK: %s <-> %s (%s, %s) in %.1f ms",
            client_cert.subject_cn,
            self._server_cert.subject_cn if self._server_cert else "?",
            tls_version.value,
            cipher.value,
            duration_ms,
        )
        return record

    def _check_rate_limit(self, client_key: str) -> bool:
        """Check if a client is within rate limits."""
        now = time.time()
        window = self._rate_limit_window
        attempts = self._rate_limits[client_key]
        self._rate_limits[client_key] = [t for t in attempts if now - t < window]
        if len(self._rate_limits[client_key]) >= self._rate_limit_max:
            return False
        self._rate_limits[client_key].append(now)
        return True

    def block_fingerprint(self, fingerprint: str) -> None:
        """Block a certificate fingerprint from connecting."""
        self._blocked_fingerprints.add(fingerprint)
        logger.info("Fingerprint blocked: %s...", fingerprint[:16])

    def close_session(self, session_id: str) -> bool:
        """Close an active session."""
        with self._lock:
            if session_id in self._active_sessions:
                del self._active_sessions[session_id]
                return True
        return False

    def get_active_sessions(self) -> list[dict]:
        """Return all active sessions."""
        return [
            {"session_id": sid, **info} for sid, info in self._active_sessions.items()
        ]

    def get_handshake_log(self, limit: int = 50) -> list[dict]:
        """Return recent handshake records."""
        return [
            {
                "client_cn": r.client_cn,
                "server_cn": r.server_cn,
                "state": r.state.name,
                "tls_version": r.tls_version,
                "cipher_suite": r.cipher_suite,
                "duration_ms": round(r.duration_ms, 2),
                "error": r.error,
            }
            for r in self._handshake_log[-limit:]
        ]

    def get_traffic_stats(self) -> dict:
        return {
            "bytes_sent": self._traffic_stats.bytes_sent,
            "bytes_recv": self._traffic_stats.bytes_recv,
            "handshakes_completed": self._traffic_stats.handshakes_completed,
            "handshakes_failed": self._traffic_stats.handshakes_failed,
            "active_sessions": len(self._active_sessions),
        }


# ---------------------------------------------------------------------------
# SecureChannel
# ---------------------------------------------------------------------------


class SecureChannel:
    """
    Encrypted communication channel for SC2 bot data transfer.
    Handles record-layer encryption, replay data, and API calls.
    """

    MAX_RECORD_SIZE = 16384  # TLS record limit

    def __init__(
        self,
        gateway: mTLSGateway,
        client_cert: CertificateInfo,
        channel_name: str = "default",
    ):
        self.gateway = gateway
        self.client_cert = client_cert
        self.channel_name = channel_name
        self._state = ChannelState.CLOSED
        self._session_id: Optional[str] = None
        self._cipher_suite: Optional[CipherSuite] = None
        self._sequence_number: int = 0
        self._send_buffer: list[bytes] = []
        self._recv_buffer: list[bytes] = []
        self._encryption_key: bytes = b""
        self._stats = TrafficStats()
        self._lock = threading.Lock()
        logger.info(
            "SecureChannel '%s' created for %s", channel_name, client_cert.subject_cn
        )

    def open(self) -> bool:
        """Open the channel by performing an mTLS handshake."""
        self._state = ChannelState.HANDSHAKE
        record = self.gateway.perform_handshake(self.client_cert)

        if record.state != HandshakeState.ESTABLISHED:
            self._state = ChannelState.ERROR
            logger.error(
                "Channel '%s' handshake failed: %s", self.channel_name, record.error
            )
            return False

        self._encryption_key = secrets.token_bytes(32)
        self._sequence_number = 0
        self._state = ChannelState.OPEN
        self._stats.handshakes_completed += 1

        # Retrieve session id from gateway
        sessions = self.gateway.get_active_sessions()
        for sess in sessions:
            if sess.get("client_cn") == self.client_cert.subject_cn:
                self._session_id = sess.get("session_id")
                break

        logger.info(
            "SecureChannel '%s' opened (cipher=%s)",
            self.channel_name,
            record.cipher_suite,
        )
        return True

    def close(self) -> None:
        """Close the channel gracefully."""
        if self._state == ChannelState.OPEN and self._session_id:
            self.gateway.close_session(self._session_id)
        self._state = ChannelState.CLOSED
        self._encryption_key = b""
        logger.info("SecureChannel '%s' closed", self.channel_name)

    def send(self, data: bytes) -> int:
        """Encrypt and send data through the channel."""
        if self._state != ChannelState.OPEN:
            raise RuntimeError(f"Channel not open (state={self._state.name})")

        total_sent = 0
        offset = 0
        while offset < len(data):
            chunk = data[offset : offset + self.MAX_RECORD_SIZE]
            encrypted = self._encrypt_record(chunk)
            self._send_buffer.append(encrypted)
            total_sent += len(chunk)
            offset += len(chunk)
            self._sequence_number += 1
            self._stats.records_sent += 1

        self._stats.bytes_sent += total_sent
        self._stats.last_activity = time.time()
        return total_sent

    def recv(self, max_size: int = 65536) -> bytes:
        """Receive and decrypt data from the channel."""
        if self._state != ChannelState.OPEN:
            raise RuntimeError(f"Channel not open (state={self._state.name})")

        if not self._recv_buffer:
            return b""

        with self._lock:
            encrypted = self._recv_buffer.pop(0)
        plaintext = self._decrypt_record(encrypted)
        self._stats.bytes_recv += len(plaintext)
        self._stats.records_recv += 1
        self._stats.last_activity = time.time()
        return plaintext[:max_size]

    def send_sc2_command(self, command: str, payload: dict) -> dict:
        """Send an SC2 bot command through the encrypted channel."""
        import json

        message = json.dumps(
            {
                "type": "sc2_command",
                "command": command,
                "payload": payload,
                "timestamp": time.time(),
                "sequence": self._sequence_number,
            }
        ).encode("utf-8")
        sent = self.send(message)
        return {
            "status": "sent",
            "command": command,
            "bytes": sent,
            "sequence": self._sequence_number,
        }

    def send_replay_data(self, replay_path: str, chunk_size: int = 8192) -> dict:
        """Send SC2 replay data through the encrypted channel."""
        # Simulate replay file content
        replay_data = hashlib.sha512(replay_path.encode()).digest() * 16
        total_sent = 0
        chunks = 0
        offset = 0
        while offset < len(replay_data):
            chunk = replay_data[offset : offset + chunk_size]
            self.send(chunk)
            total_sent += len(chunk)
            chunks += 1
            offset += chunk_size

        return {
            "replay_path": replay_path,
            "total_bytes": total_sent,
            "chunks": chunks,
            "encrypted": True,
        }

    def inject_recv(self, data: bytes) -> None:
        """Inject data into the receive buffer (for simulation/testing)."""
        encrypted = self._encrypt_record(data)
        with self._lock:
            self._recv_buffer.append(encrypted)

    def _encrypt_record(self, plaintext: bytes) -> bytes:
        """Encrypt a TLS record using the session key (simulated AEAD)."""
        nonce = struct.pack(">Q", self._sequence_number)
        tag_input = self._encryption_key + nonce + plaintext
        tag = hashlib.sha256(tag_input).digest()[:16]
        # Simulated encryption: XOR with key-derived stream
        key_stream = hashlib.sha256(self._encryption_key + nonce).digest()
        encrypted = bytes(
            p ^ key_stream[i % len(key_stream)] for i, p in enumerate(plaintext)
        )
        return nonce + tag + encrypted

    def _decrypt_record(self, record: bytes) -> bytes:
        """Decrypt a TLS record (simulated AEAD)."""
        nonce = record[:8]
        tag = record[8:24]
        ciphertext = record[24:]
        key_stream = hashlib.sha256(self._encryption_key + nonce).digest()
        plaintext = bytes(
            c ^ key_stream[i % len(key_stream)] for i, c in enumerate(ciphertext)
        )
        return plaintext

    @property
    def state(self) -> ChannelState:
        return self._state

    def get_stats(self) -> dict:
        return {
            "channel_name": self.channel_name,
            "state": self._state.name,
            "client_cn": self.client_cert.subject_cn,
            "bytes_sent": self._stats.bytes_sent,
            "bytes_recv": self._stats.bytes_recv,
            "records_sent": self._stats.records_sent,
            "records_recv": self._stats.records_recv,
            "sequence_number": self._sequence_number,
        }


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------


def demo() -> None:
    """Demonstrate mTLS security gateway for SC2 bot communications."""
    print("=" * 70)
    print("Phase 653: mTLS Security Gateway for SC2 Bot Communications")
    print("=" * 70)

    # 1. Certificate Authority
    print("\n[1] Certificate Authority")
    ca = CertificateAuthority("SC2-Bot-Root-CA", validity_days=730)
    ca_cert = ca.get_ca_cert()
    print(f"  CA: {ca_cert.subject_cn} (serial={ca_cert.serial_number})")
    print(f"  Expires in: {ca_cert.days_until_expiry:.0f} days")

    # 2. CertManager
    print("\n[2] Certificate Management")
    cm = CertManager(ca, rotation_threshold_days=30)
    client1 = cm.create_client_cert("bot-alpha", san_entries=["bot-alpha.sc2.local"])
    client2 = cm.create_client_cert("bot-beta")
    server1 = cm.create_server_cert(
        "game-server-1", san_entries=["gs1.sc2.local", "localhost"]
    )
    print(
        f"  Client 'bot-alpha': CN={client1.subject_cn}, "
        f"serial={client1.serial_number}"
    )
    print(
        f"  Client 'bot-beta':  CN={client2.subject_cn}, "
        f"serial={client2.serial_number}"
    )
    print(f"  Server 'game-server-1': CN={server1.subject_cn}")
    print(f"  CertManager stats: {cm.get_stats()}")

    # Pin verification
    pin_ok = cm.verify_pinning("bot-alpha", client1)
    print(f"  Pin verification for bot-alpha: {pin_ok}")

    # 3. TLSConfig
    print("\n[3] TLS Configuration")
    tls_cfg = TLSConfig(require_client_cert=True)
    ver = tls_cfg.negotiate_version(["TLSv1.2", "TLSv1.3"])
    cipher = tls_cfg.negotiate_cipher(
        [
            "TLS_AES_256_GCM_SHA384",
            "TLS_CHACHA20_POLY1305_SHA256",
        ]
    )
    print(f"  Negotiated version: {ver.value if ver else 'None'}")
    print(f"  Negotiated cipher:  {cipher.value if cipher else 'None'}")
    print(f"  Config: {tls_cfg.to_dict()}")

    # 4. mTLS Gateway
    print("\n[4] mTLS Gateway")
    gw = mTLSGateway(ca, cm, tls_cfg, listen_port=8443)
    gw.initialize("gateway-primary")
    gw.start()

    # Successful handshakes
    hs1 = gw.perform_handshake(
        client1,
        {
            "tls_versions": ["TLSv1.3"],
            "cipher_suites": ["TLS_AES_256_GCM_SHA384"],
        },
    )
    print(
        f"  Handshake bot-alpha: state={hs1.state.name}, "
        f"cipher={hs1.cipher_suite}, duration={hs1.duration_ms:.2f}ms"
    )

    hs2 = gw.perform_handshake(client2)
    print(f"  Handshake bot-beta:  state={hs2.state.name}")

    # Revoke and try again
    ca.revoke_certificate(client2.serial_number, reason="compromised")
    hs3 = gw.perform_handshake(client2)
    print(
        f"  Handshake bot-beta (revoked): state={hs3.state.name}, " f"error={hs3.error}"
    )

    # Certificate rotation
    print("\n  Rotating bot-beta certificate...")
    new_beta = cm.rotate_certificate("bot-beta", is_client=True)
    if new_beta:
        hs4 = gw.perform_handshake(new_beta)
        print(f"  Handshake bot-beta (new cert): state={hs4.state.name}")

    print(f"  Traffic stats: {gw.get_traffic_stats()}")
    print(f"  Handshake log entries: {len(gw.get_handshake_log())}")

    # 5. SecureChannel
    print("\n[5] Secure Channel Communication")
    channel = SecureChannel(gw, client1, channel_name="sc2-data")
    opened = channel.open()
    print(f"  Channel opened: {opened}, state={channel.state.name}")

    if opened:
        # Send SC2 command
        cmd_result = channel.send_sc2_command(
            "build_order",
            {
                "race": "Zerg",
                "build": "12pool",
                "supply": 12,
            },
        )
        print(f"  Command sent: {cmd_result}")

        # Send replay data
        replay_result = channel.send_replay_data("/replays/game_001.SC2Replay")
        print(
            f"  Replay transfer: {replay_result['total_bytes']} bytes, "
            f"{replay_result['chunks']} chunks, "
            f"encrypted={replay_result['encrypted']}"
        )

        # Simulate recv
        channel.inject_recv(b'{"status":"ok","game_id":42}')
        response = channel.recv()
        print(f"  Received response: {len(response)} bytes")

        print(f"  Channel stats: {channel.get_stats()}")
        channel.close()

    # CRL
    print("\n[6] Certificate Revocation List")
    crl = ca.get_crl()
    print(f"  CRL number: {crl['crl_number']}")
    print(f"  Revoked certs: {len(crl['revoked_certificates'])}")
    for entry in crl["revoked_certificates"]:
        print(f"    - {entry['cn']} (serial={entry['serial']})")

    # All certs
    print("\n[7] All Issued Certificates")
    for cert_info in ca.list_certificates():
        print(
            f"    {cert_info['cn']:40s} status={cert_info['status']:8s} "
            f"expires_in={cert_info['days_until_expiry']} days"
        )

    gw.stop()

    print("\n" + "=" * 70)
    print("Phase 653: mTLS Security Gateway demo complete")
    print("=" * 70)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    demo()

# Phase 653: mTLS registered
