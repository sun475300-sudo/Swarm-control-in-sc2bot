# Phase 654: SBOM Generator for SC2 Bot Supply Chain Security
# Software Bill of Materials generator for SC2 bot dependencies

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# ============================================================
# Constants & Known Vulnerability Database (mock)
# ============================================================

SPDX_VERSION = "SPDX-2.3"
CYCLONEDX_VERSION = "1.5"
SBOM_TOOL_NAME = "SC2-SBOM-Generator"
SBOM_TOOL_VERSION = "0.654.0"

# License compatibility matrix (simplified)
LICENSE_COMPATIBILITY: Dict[str, Set[str]] = {
    "MIT": {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "Unlicense"},
    "Apache-2.0": {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC"},
    "GPL-3.0-only": {"GPL-3.0-only", "GPL-3.0-or-later", "AGPL-3.0-only"},
    "GPL-2.0-only": {"GPL-2.0-only", "GPL-2.0-or-later", "LGPL-2.1-only"},
    "LGPL-2.1-only": {
        "MIT",
        "Apache-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "LGPL-2.1-only",
    },
    "BSD-2-Clause": {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC"},
    "BSD-3-Clause": {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC"},
}

# SC2 bot typical dependency categories
SC2_DEPENDENCY_CATEGORIES = [
    "core_bot_framework",
    "machine_learning",
    "replay_analysis",
    "networking",
    "data_processing",
    "visualization",
    "testing",
    "deployment",
    "monitoring",
    "security",
]


# ============================================================
# Data Classes
# ============================================================


@dataclass
class Package:
    """Represents a software package in the dependency tree."""

    name: str
    version: str
    purl: str = ""  # Package URL (purl spec)
    license_id: str = "NOASSERTION"
    supplier: str = ""
    checksum_sha256: str = ""
    description: str = ""
    download_url: str = ""
    direct: bool = True
    category: str = "general"
    dependencies: List[str] = field(default_factory=list)  # names of deps
    file_path: str = ""

    def __post_init__(self) -> None:
        if not self.purl:
            self.purl = f"pkg:pypi/{self.name}@{self.version}"
        if not self.checksum_sha256:
            raw = f"{self.name}-{self.version}-{self.download_url}"
            self.checksum_sha256 = hashlib.sha256(raw.encode()).hexdigest()

    @property
    def identifier(self) -> str:
        return f"{self.name}@{self.version}"

    def to_spdx_dict(self) -> Dict[str, Any]:
        return {
            "SPDXID": f"SPDXRef-Package-{self.name}-{self.version}",
            "name": self.name,
            "versionInfo": self.version,
            "packageUrl": self.purl,
            "licenseConcluded": self.license_id,
            "licenseDeclared": self.license_id,
            "supplier": (
                f"Organization: {self.supplier}" if self.supplier else "NOASSERTION"
            ),
            "downloadLocation": self.download_url or "NOASSERTION",
            "checksums": [
                {"algorithm": "SHA256", "checksumValue": self.checksum_sha256}
            ],
            "description": self.description,
            "externalRefs": [
                {
                    "referenceCategory": "PACKAGE-MANAGER",
                    "referenceType": "purl",
                    "referenceLocator": self.purl,
                }
            ],
        }

    def to_cyclonedx_dict(self) -> Dict[str, Any]:
        component: Dict[str, Any] = {
            "type": "library",
            "name": self.name,
            "version": self.version,
            "purl": self.purl,
            "hashes": [{"alg": "SHA-256", "content": self.checksum_sha256}],
        }
        if self.license_id != "NOASSERTION":
            component["licenses"] = [{"license": {"id": self.license_id}}]
        if self.supplier:
            component["supplier"] = {"name": self.supplier}
        if self.description:
            component["description"] = self.description
        return component


@dataclass
class Vulnerability:
    """Represents a known vulnerability (CVE) associated with a package."""

    cve_id: str
    package_name: str
    affected_versions: List[str] = field(default_factory=list)
    fixed_version: str = ""
    severity: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL
    cvss_score: float = 0.0
    description: str = ""
    references: List[str] = field(default_factory=list)
    published_date: str = ""
    exploitable: bool = False

    @property
    def cvss_severity(self) -> str:
        if self.cvss_score >= 9.0:
            return "CRITICAL"
        elif self.cvss_score >= 7.0:
            return "HIGH"
        elif self.cvss_score >= 4.0:
            return "MEDIUM"
        else:
            return "LOW"

    def affects_version(self, version: str) -> bool:
        if not self.affected_versions:
            return True
        return version in self.affected_versions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cve_id": self.cve_id,
            "package": self.package_name,
            "severity": self.severity,
            "cvss_score": self.cvss_score,
            "description": self.description,
            "fixed_version": self.fixed_version,
            "exploitable": self.exploitable,
        }


@dataclass
class SBOMDocument:
    """Represents a complete SBOM document in either SPDX or CycloneDX format."""

    doc_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "SC2-Bot-SBOM"
    version: str = "1.0"
    created: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    creator_tool: str = f"{SBOM_TOOL_NAME}/{SBOM_TOOL_VERSION}"
    packages: List[Package] = field(default_factory=list)
    vulnerabilities: List[Vulnerability] = field(default_factory=list)
    license_conflicts: List[Dict[str, str]] = field(default_factory=list)
    relationships: List[Dict[str, str]] = field(default_factory=list)

    @property
    def total_packages(self) -> int:
        return len(self.packages)

    @property
    def direct_packages(self) -> List[Package]:
        return [p for p in self.packages if p.direct]

    @property
    def transitive_packages(self) -> List[Package]:
        return [p for p in self.packages if not p.direct]

    @property
    def critical_vulns(self) -> List[Vulnerability]:
        return [v for v in self.vulnerabilities if v.severity == "CRITICAL"]

    @property
    def high_vulns(self) -> List[Vulnerability]:
        return [v for v in self.vulnerabilities if v.severity == "HIGH"]

    def add_package(self, pkg: Package) -> None:
        self.packages.append(pkg)

    def add_vulnerability(self, vuln: Vulnerability) -> None:
        self.vulnerabilities.append(vuln)

    def add_relationship(
        self, source: str, target: str, rel_type: str = "DEPENDS_ON"
    ) -> None:
        self.relationships.append(
            {
                "source": source,
                "target": target,
                "type": rel_type,
            }
        )

    def to_spdx(self) -> Dict[str, Any]:
        """Generate SPDX 2.3 JSON format."""
        doc: Dict[str, Any] = {
            "spdxVersion": SPDX_VERSION,
            "dataLicense": "CC0-1.0",
            "SPDXID": "SPDXRef-DOCUMENT",
            "name": self.name,
            "documentNamespace": f"https://sc2bot.dev/spdx/{self.doc_id}",
            "creationInfo": {
                "created": self.created,
                "creators": [f"Tool: {self.creator_tool}"],
                "licenseListVersion": "3.19",
            },
            "packages": [p.to_spdx_dict() for p in self.packages],
            "relationships": [],
        }
        for rel in self.relationships:
            spdx_src = f"SPDXRef-Package-{rel['source']}"
            spdx_tgt = f"SPDXRef-Package-{rel['target']}"
            doc["relationships"].append(
                {
                    "spdxElementId": spdx_src,
                    "relatedSpdxElement": spdx_tgt,
                    "relationshipType": rel["type"],
                }
            )
        # Document describes root
        doc["relationships"].append(
            {
                "spdxElementId": "SPDXRef-DOCUMENT",
                "relatedSpdxElement": "SPDXRef-Package-sc2-commander-bot-1.0.0",
                "relationshipType": "DESCRIBES",
            }
        )
        return doc

    def to_cyclonedx(self) -> Dict[str, Any]:
        """Generate CycloneDX 1.5 JSON format."""
        doc: Dict[str, Any] = {
            "bomFormat": "CycloneDX",
            "specVersion": CYCLONEDX_VERSION,
            "serialNumber": f"urn:uuid:{self.doc_id}",
            "version": 1,
            "metadata": {
                "timestamp": self.created,
                "tools": [{"name": SBOM_TOOL_NAME, "version": SBOM_TOOL_VERSION}],
                "component": {
                    "type": "application",
                    "name": self.name,
                    "version": self.version,
                },
            },
            "components": [p.to_cyclonedx_dict() for p in self.packages],
            "dependencies": [],
        }
        # Build dependency graph
        dep_map: Dict[str, List[str]] = {}
        for rel in self.relationships:
            src = rel["source"]
            tgt = rel["target"]
            if src not in dep_map:
                dep_map[src] = []
            dep_map[src].append(tgt)
        for src, deps in dep_map.items():
            doc["dependencies"].append({"ref": src, "dependsOn": deps})
        # Vulnerability section
        if self.vulnerabilities:
            doc["vulnerabilities"] = []
            for vuln in self.vulnerabilities:
                entry: Dict[str, Any] = {
                    "id": vuln.cve_id,
                    "description": vuln.description,
                    "ratings": [
                        {
                            "score": vuln.cvss_score,
                            "severity": vuln.severity.lower(),
                            "method": "CVSSv3",
                        }
                    ],
                    "affects": [{"ref": vuln.package_name}],
                }
                if vuln.references:
                    entry["references"] = [{"url": r} for r in vuln.references]
                doc["vulnerabilities"].append(entry)
        return doc

    def summary(self) -> Dict[str, Any]:
        license_set: Set[str] = set()
        category_counts: Dict[str, int] = {}
        for p in self.packages:
            license_set.add(p.license_id)
            cat = p.category
            category_counts[cat] = category_counts.get(cat, 0) + 1
        return {
            "document_id": self.doc_id,
            "total_packages": self.total_packages,
            "direct_dependencies": len(self.direct_packages),
            "transitive_dependencies": len(self.transitive_packages),
            "unique_licenses": sorted(license_set),
            "category_breakdown": category_counts,
            "total_vulnerabilities": len(self.vulnerabilities),
            "critical_vulnerabilities": len(self.critical_vulns),
            "high_vulnerabilities": len(self.high_vulns),
            "license_conflicts": len(self.license_conflicts),
        }


# ============================================================
# Dependency Scanner
# ============================================================


class DependencyScanner:
    """Scans project dependencies: direct and transitive."""

    def __init__(self, project_root: str = ".") -> None:
        self.project_root = Path(project_root)
        self.packages: Dict[str, Package] = {}
        self._visited: Set[str] = set()

    def scan_requirements_file(self, filepath: str) -> List[Package]:
        """Parse a requirements.txt-style file for direct dependencies."""
        packages: List[Package] = []
        path = Path(filepath)
        if not path.exists():
            return packages
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                name, version = self._parse_requirement_line(line)
                if name:
                    pkg = Package(name=name, version=version, direct=True)
                    packages.append(pkg)
                    self.packages[pkg.identifier] = pkg
        return packages

    def scan_setup_py(self, filepath: str) -> List[Package]:
        """Extract install_requires from setup.py (simple pattern match)."""
        packages: List[Package] = []
        path = Path(filepath)
        if not path.exists():
            return packages
        content = path.read_text(encoding="utf-8")
        in_requires = False
        for line in content.splitlines():
            stripped = line.strip()
            if "install_requires" in stripped:
                in_requires = True
                continue
            if in_requires:
                if stripped.startswith("]"):
                    in_requires = False
                    continue
                cleaned = stripped.strip("'\",")
                if cleaned:
                    name, version = self._parse_requirement_line(cleaned)
                    if name:
                        pkg = Package(name=name, version=version, direct=True)
                        packages.append(pkg)
                        self.packages[pkg.identifier] = pkg
        return packages

    def scan_pyproject_toml(self, filepath: str) -> List[Package]:
        """Basic pyproject.toml dependency extraction."""
        packages: List[Package] = []
        path = Path(filepath)
        if not path.exists():
            return packages
        content = path.read_text(encoding="utf-8")
        in_deps = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped == "dependencies = [" or stripped == "dependencies = [":
                in_deps = True
                continue
            if in_deps:
                if stripped.startswith("]"):
                    in_deps = False
                    continue
                cleaned = stripped.strip("\"',")
                if cleaned:
                    name, version = self._parse_requirement_line(cleaned)
                    if name:
                        pkg = Package(name=name, version=version, direct=True)
                        packages.append(pkg)
                        self.packages[pkg.identifier] = pkg
        return packages

    def resolve_transitive(
        self,
        direct_pkgs: List[Package],
        known_tree: Optional[Dict[str, List[str]]] = None,
    ) -> List[Package]:
        """Resolve transitive dependencies given a dependency tree mapping."""
        if known_tree is None:
            known_tree = {}
        transitive: List[Package] = []
        queue = [p.name for p in direct_pkgs]
        visited: Set[str] = {p.name for p in direct_pkgs}

        while queue:
            current = queue.pop(0)
            child_names = known_tree.get(current, [])
            for child in child_names:
                if child not in visited:
                    visited.add(child)
                    pkg = Package(
                        name=child,
                        version="0.0.0",  # would be resolved by pip
                        direct=False,
                        category="transitive",
                    )
                    transitive.append(pkg)
                    self.packages[pkg.identifier] = pkg
                    queue.append(child)
        return transitive

    def build_dependency_tree(self) -> Dict[str, List[str]]:
        """Return adjacency list of dependency relationships."""
        tree: Dict[str, List[str]] = {}
        for ident, pkg in self.packages.items():
            tree[pkg.name] = pkg.dependencies[:]
        return tree

    def scan_all(self) -> List[Package]:
        """Scan all recognized dependency files in project root."""
        all_pkgs: List[Package] = []
        req_path = self.project_root / "requirements.txt"
        if req_path.exists():
            all_pkgs.extend(self.scan_requirements_file(str(req_path)))
        setup_path = self.project_root / "setup.py"
        if setup_path.exists():
            all_pkgs.extend(self.scan_setup_py(str(setup_path)))
        pyproject_path = self.project_root / "pyproject.toml"
        if pyproject_path.exists():
            all_pkgs.extend(self.scan_pyproject_toml(str(pyproject_path)))
        return all_pkgs

    @staticmethod
    def _parse_requirement_line(line: str) -> Tuple[str, str]:
        """Parse 'package>=version' into (name, version)."""
        for sep in ["==", ">=", "<=", "~=", "!=", ">", "<"]:
            if sep in line:
                parts = line.split(sep, 1)
                name = parts[0].strip().lower()
                version = parts[1].strip().split(",")[0].strip()
                return name, version
        name = line.strip().lower()
        if name and name[0].isalpha():
            return name, "0.0.0"
        return "", ""


# ============================================================
# Vulnerability Database (Mock CVE data)
# ============================================================


class VulnerabilityDatabase:
    """Mock CVE database for vulnerability matching."""

    def __init__(self) -> None:
        self.entries: List[Vulnerability] = []
        self._load_mock_data()

    def _load_mock_data(self) -> None:
        mock_vulns = [
            Vulnerability(
                cve_id="CVE-2024-35195",
                package_name="requests",
                affected_versions=["2.25.0", "2.25.1", "2.26.0", "2.27.0", "2.28.0"],
                fixed_version="2.31.0",
                severity="MEDIUM",
                cvss_score=5.6,
                description="Proxy credentials leaked via redirect in requests library",
            ),
            Vulnerability(
                cve_id="CVE-2024-3651",
                package_name="idna",
                affected_versions=["3.0", "3.1", "3.2", "3.3", "3.4", "3.5", "3.6"],
                fixed_version="3.7",
                severity="HIGH",
                cvss_score=7.5,
                description="Denial of service via resource consumption in IDNA processing",
            ),
            Vulnerability(
                cve_id="CVE-2023-44271",
                package_name="pillow",
                affected_versions=[
                    "9.0.0",
                    "9.1.0",
                    "9.2.0",
                    "9.3.0",
                    "9.4.0",
                    "9.5.0",
                ],
                fixed_version="10.0.1",
                severity="HIGH",
                cvss_score=7.5,
                description="Uncontrolled resource consumption in Pillow image processing",
            ),
            Vulnerability(
                cve_id="CVE-2024-28219",
                package_name="pillow",
                affected_versions=["10.0.0", "10.1.0", "10.2.0"],
                fixed_version="10.3.0",
                severity="CRITICAL",
                cvss_score=9.0,
                description="Buffer overflow in Pillow's _imagingcms module",
                exploitable=True,
            ),
            Vulnerability(
                cve_id="CVE-2023-45803",
                package_name="urllib3",
                affected_versions=["1.26.0", "1.26.1", "1.26.2", "2.0.0", "2.0.1"],
                fixed_version="2.0.7",
                severity="MEDIUM",
                cvss_score=4.2,
                description="Request body not stripped on redirect in urllib3",
            ),
            Vulnerability(
                cve_id="CVE-2024-22195",
                package_name="jinja2",
                affected_versions=[
                    "3.0.0",
                    "3.0.1",
                    "3.0.2",
                    "3.0.3",
                    "3.1.0",
                    "3.1.1",
                    "3.1.2",
                ],
                fixed_version="3.1.3",
                severity="MEDIUM",
                cvss_score=6.1,
                description="XSS via xmlattr filter in Jinja2 template engine",
            ),
            Vulnerability(
                cve_id="CVE-2024-0001",
                package_name="numpy",
                affected_versions=["1.24.0", "1.24.1", "1.24.2"],
                fixed_version="1.24.4",
                severity="LOW",
                cvss_score=3.1,
                description="Mock: Integer overflow in array indexing (simulated)",
            ),
            Vulnerability(
                cve_id="CVE-2024-0002",
                package_name="protobuf",
                affected_versions=["3.20.0", "3.20.1", "4.21.0"],
                fixed_version="4.25.0",
                severity="HIGH",
                cvss_score=7.8,
                description="Mock: Deserialization vulnerability in protobuf (simulated)",
                exploitable=True,
            ),
        ]
        self.entries.extend(mock_vulns)

    def lookup(self, package_name: str, version: str) -> List[Vulnerability]:
        """Find all known vulns for a package@version."""
        hits: List[Vulnerability] = []
        for v in self.entries:
            if v.package_name == package_name and v.affects_version(version):
                hits.append(v)
        return hits

    def lookup_all(self, packages: List[Package]) -> List[Vulnerability]:
        """Scan all packages against known vulnerabilities."""
        all_vulns: List[Vulnerability] = []
        for pkg in packages:
            found = self.lookup(pkg.name, pkg.version)
            all_vulns.extend(found)
        return all_vulns


# ============================================================
# License Compliance Checker
# ============================================================


class LicenseComplianceChecker:
    """Detect license conflicts in dependency graph."""

    def __init__(self, project_license: str = "MIT") -> None:
        self.project_license = project_license

    def check_compatibility(self, pkg_license: str) -> bool:
        """Check if a dependency license is compatible with the project license."""
        compatible = LICENSE_COMPATIBILITY.get(self.project_license, set())
        if not compatible:
            return True  # unknown project license, skip
        return pkg_license in compatible or pkg_license == "NOASSERTION"

    def find_conflicts(self, packages: List[Package]) -> List[Dict[str, str]]:
        """Find all license conflicts in the dependency set."""
        conflicts: List[Dict[str, str]] = []
        for pkg in packages:
            if pkg.license_id == "NOASSERTION":
                continue
            if not self.check_compatibility(pkg.license_id):
                conflicts.append(
                    {
                        "package": pkg.identifier,
                        "package_license": pkg.license_id,
                        "project_license": self.project_license,
                        "conflict": f"{pkg.license_id} is not compatible with {self.project_license}",
                    }
                )
        # Check inter-dependency conflicts
        licenses_in_use = [
            p.license_id for p in packages if p.license_id != "NOASSERTION"
        ]
        unique_licenses = set(licenses_in_use)
        for lic_a in unique_licenses:
            for lic_b in unique_licenses:
                if lic_a == lic_b:
                    continue
                compat_a = LICENSE_COMPATIBILITY.get(lic_a, set())
                if compat_a and lic_b not in compat_a:
                    conflict_key = tuple(sorted([lic_a, lic_b]))
                    entry = {
                        "license_a": conflict_key[0],
                        "license_b": conflict_key[1],
                        "conflict": f"{conflict_key[0]} and {conflict_key[1]} may be incompatible",
                    }
                    if entry not in conflicts:
                        conflicts.append(entry)
        return conflicts

    def generate_license_report(self, packages: List[Package]) -> Dict[str, Any]:
        """Generate a license compliance report."""
        license_counts: Dict[str, int] = {}
        for pkg in packages:
            lic = pkg.license_id
            license_counts[lic] = license_counts.get(lic, 0) + 1
        conflicts = self.find_conflicts(packages)
        return {
            "project_license": self.project_license,
            "total_packages": len(packages),
            "license_distribution": license_counts,
            "conflicts": conflicts,
            "compliant": len(conflicts) == 0,
        }


# ============================================================
# SBOM Generator (Main Orchestrator)
# ============================================================


class SBOMGenerator:
    """
    Main SBOM generator for SC2 bot supply chain security.
    Orchestrates scanning, vulnerability matching, license checking,
    and document generation in SPDX / CycloneDX formats.
    """

    def __init__(
        self,
        project_root: str = ".",
        project_license: str = "MIT",
        project_name: str = "SC2-Commander-Bot",
    ) -> None:
        self.project_root = project_root
        self.project_name = project_name
        self.scanner = DependencyScanner(project_root)
        self.vuln_db = VulnerabilityDatabase()
        self.license_checker = LicenseComplianceChecker(project_license)
        self.document: Optional[SBOMDocument] = None

    def _build_sc2_mock_dependencies(self) -> List[Package]:
        """Build a realistic mock dependency list for an SC2 bot project."""
        sc2_deps: List[Tuple[str, str, str, str, bool]] = [
            # (name, version, license, category, direct)
            ("burnysc2", "6.5.0", "MIT", "core_bot_framework", True),
            ("python-sc2", "5.0.12", "MIT", "core_bot_framework", True),
            ("numpy", "1.26.4", "BSD-3-Clause", "data_processing", True),
            ("scipy", "1.12.0", "BSD-3-Clause", "data_processing", True),
            ("torch", "2.2.0", "BSD-3-Clause", "machine_learning", True),
            ("tensorflow", "2.15.0", "Apache-2.0", "machine_learning", True),
            ("scikit-learn", "1.4.0", "BSD-3-Clause", "machine_learning", True),
            ("pandas", "2.2.0", "BSD-3-Clause", "data_processing", True),
            ("matplotlib", "3.8.3", "PSF-2.0", "visualization", True),
            ("protobuf", "4.25.2", "BSD-3-Clause", "networking", True),
            ("grpcio", "1.62.0", "Apache-2.0", "networking", True),
            ("aiohttp", "3.9.3", "Apache-2.0", "networking", True),
            ("requests", "2.31.0", "Apache-2.0", "networking", True),
            ("websockets", "12.0", "BSD-3-Clause", "networking", True),
            ("pillow", "10.2.0", "MIT-CMU", "data_processing", True),
            ("opencv-python", "4.9.0.80", "Apache-2.0", "data_processing", True),
            ("pyyaml", "6.0.1", "MIT", "data_processing", True),
            ("toml", "0.10.2", "MIT", "data_processing", True),
            ("click", "8.1.7", "BSD-3-Clause", "core_bot_framework", True),
            ("tqdm", "4.66.2", "MIT", "visualization", True),
            ("pytest", "8.0.2", "MIT", "testing", True),
            ("hypothesis", "6.98.0", "MPL-2.0", "testing", True),
            ("docker", "7.0.0", "Apache-2.0", "deployment", True),
            ("prometheus-client", "0.20.0", "Apache-2.0", "monitoring", True),
            ("cryptography", "42.0.4", "Apache-2.0", "security", True),
            # Transitive dependencies
            ("certifi", "2024.2.2", "MPL-2.0", "networking", False),
            ("charset-normalizer", "3.3.2", "MIT", "networking", False),
            ("idna", "3.6", "BSD-3-Clause", "networking", False),
            ("urllib3", "2.2.0", "MIT", "networking", False),
            ("six", "1.16.0", "MIT", "data_processing", False),
            ("setuptools", "69.1.0", "MIT", "core_bot_framework", False),
            ("wheel", "0.42.0", "MIT", "core_bot_framework", False),
            ("pip", "24.0", "MIT", "core_bot_framework", False),
            ("jinja2", "3.1.3", "BSD-3-Clause", "data_processing", False),
            ("markupsafe", "2.1.5", "BSD-3-Clause", "data_processing", False),
            ("attrs", "23.2.0", "MIT", "data_processing", False),
            ("multidict", "6.0.5", "Apache-2.0", "networking", False),
            ("yarl", "1.9.4", "Apache-2.0", "networking", False),
            ("frozenlist", "1.4.1", "Apache-2.0", "networking", False),
            ("aiosignal", "1.3.1", "Apache-2.0", "networking", False),
            ("async-timeout", "4.0.3", "Apache-2.0", "networking", False),
            ("typing-extensions", "4.9.0", "PSF-2.0", "core_bot_framework", False),
            ("filelock", "3.13.1", "Unlicense", "data_processing", False),
            ("sympy", "1.12", "BSD-3-Clause", "data_processing", False),
            ("networkx", "3.2.1", "BSD-3-Clause", "data_processing", False),
            ("fsspec", "2024.2.0", "BSD-3-Clause", "data_processing", False),
            ("mpmath", "1.3.0", "BSD-3-Clause", "data_processing", False),
            ("packaging", "24.0", "Apache-2.0", "core_bot_framework", False),
            ("pluggy", "1.4.0", "MIT", "testing", False),
            ("iniconfig", "2.0.0", "MIT", "testing", False),
            ("exceptiongroup", "1.2.0", "MIT", "testing", False),
            ("tomli", "2.0.1", "MIT", "data_processing", False),
            ("cffi", "1.16.0", "MIT", "security", False),
            ("pycparser", "2.21", "BSD-3-Clause", "security", False),
        ]
        packages: List[Package] = []
        for name, ver, lic, cat, direct in sc2_deps:
            pkg = Package(
                name=name,
                version=ver,
                license_id=lic,
                category=cat,
                direct=direct,
                supplier="PyPI",
                download_url=f"https://pypi.org/project/{name}/{ver}/",
                description=f"SC2 bot dependency: {name}",
            )
            packages.append(pkg)
            self.scanner.packages[pkg.identifier] = pkg
        return packages

    def _build_sc2_dependency_relationships(
        self, packages: List[Package]
    ) -> List[Tuple[str, str]]:
        """Build realistic dependency edges for SC2 bot packages."""
        edges: List[Tuple[str, str]] = [
            ("requests", "urllib3"),
            ("requests", "certifi"),
            ("requests", "charset-normalizer"),
            ("requests", "idna"),
            ("aiohttp", "multidict"),
            ("aiohttp", "yarl"),
            ("aiohttp", "frozenlist"),
            ("aiohttp", "aiosignal"),
            ("aiohttp", "async-timeout"),
            ("aiohttp", "attrs"),
            ("torch", "typing-extensions"),
            ("torch", "filelock"),
            ("torch", "sympy"),
            ("torch", "networkx"),
            ("torch", "fsspec"),
            ("torch", "jinja2"),
            ("jinja2", "markupsafe"),
            ("sympy", "mpmath"),
            ("pytest", "pluggy"),
            ("pytest", "iniconfig"),
            ("pytest", "exceptiongroup"),
            ("pytest", "packaging"),
            ("pytest", "tomli"),
            ("cryptography", "cffi"),
            ("cffi", "pycparser"),
            ("burnysc2", "protobuf"),
            ("burnysc2", "aiohttp"),
            ("burnysc2", "numpy"),
            ("tensorflow", "numpy"),
            ("tensorflow", "protobuf"),
            ("tensorflow", "grpcio"),
            ("scikit-learn", "numpy"),
            ("scikit-learn", "scipy"),
            ("pandas", "numpy"),
            ("matplotlib", "numpy"),
            ("matplotlib", "pillow"),
            ("opencv-python", "numpy"),
        ]
        pkg_names = {p.name for p in packages}
        return [(s, t) for s, t in edges if s in pkg_names and t in pkg_names]

    def generate(
        self, output_format: str = "both", use_mock: bool = True
    ) -> SBOMDocument:
        """
        Generate a full SBOM document.

        Args:
            output_format: 'spdx', 'cyclonedx', or 'both'
            use_mock: Use mock SC2 dependencies (True) or scan project (False)
        """
        # Phase 1: Scan dependencies
        if use_mock:
            packages = self._build_sc2_mock_dependencies()
        else:
            packages = self.scanner.scan_all()
            tree = self.scanner.build_dependency_tree()
            transitive = self.scanner.resolve_transitive(packages, tree)
            packages.extend(transitive)

        # Phase 2: Build SBOM document
        doc = SBOMDocument(name=self.project_name)
        for pkg in packages:
            doc.add_package(pkg)

        # Phase 3: Build relationships
        edges = self._build_sc2_dependency_relationships(packages)
        for src, tgt in edges:
            doc.add_relationship(src, tgt, "DEPENDS_ON")

        # Phase 4: Vulnerability scan
        vulns = self.vuln_db.lookup_all(packages)
        for v in vulns:
            doc.add_vulnerability(v)

        # Phase 5: License compliance
        conflicts = self.license_checker.find_conflicts(packages)
        doc.license_conflicts = conflicts

        self.document = doc
        return doc

    def export_spdx(self, filepath: str) -> str:
        """Export SBOM in SPDX JSON format."""
        if self.document is None:
            self.generate()
        assert self.document is not None
        spdx_data = self.document.to_spdx()
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(spdx_data, f, indent=2, ensure_ascii=False)
        return str(path.resolve())

    def export_cyclonedx(self, filepath: str) -> str:
        """Export SBOM in CycloneDX JSON format."""
        if self.document is None:
            self.generate()
        assert self.document is not None
        cdx_data = self.document.to_cyclonedx()
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cdx_data, f, indent=2, ensure_ascii=False)
        return str(path.resolve())

    def generate_security_report(self) -> Dict[str, Any]:
        """Generate a comprehensive security report for the SC2 bot."""
        if self.document is None:
            self.generate()
        assert self.document is not None
        doc = self.document

        vuln_by_severity: Dict[str, int] = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
        }
        for v in doc.vulnerabilities:
            sev = v.severity
            if sev in vuln_by_severity:
                vuln_by_severity[sev] += 1

        exploitable = [v for v in doc.vulnerabilities if v.exploitable]
        actionable = [
            {
                "cve": v.cve_id,
                "package": v.package_name,
                "severity": v.severity,
                "action": (
                    f"Upgrade to >= {v.fixed_version}" if v.fixed_version else "Monitor"
                ),
            }
            for v in doc.vulnerabilities
            if v.severity in ("CRITICAL", "HIGH")
        ]

        license_report = self.license_checker.generate_license_report(doc.packages)

        risk_score = 0.0
        risk_score += vuln_by_severity["CRITICAL"] * 10.0
        risk_score += vuln_by_severity["HIGH"] * 5.0
        risk_score += vuln_by_severity["MEDIUM"] * 2.0
        risk_score += vuln_by_severity["LOW"] * 0.5
        risk_score += len(doc.license_conflicts) * 3.0
        risk_score += len(exploitable) * 15.0
        max_score = 100.0
        normalized_risk = min(risk_score / max_score, 1.0)

        if normalized_risk < 0.2:
            risk_level = "LOW"
        elif normalized_risk < 0.5:
            risk_level = "MEDIUM"
        elif normalized_risk < 0.8:
            risk_level = "HIGH"
        else:
            risk_level = "CRITICAL"

        return {
            "report_id": str(uuid.uuid4()),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "project": self.project_name,
            "sbom_summary": doc.summary(),
            "vulnerability_summary": {
                "total": len(doc.vulnerabilities),
                "by_severity": vuln_by_severity,
                "exploitable_count": len(exploitable),
                "actionable_items": actionable,
            },
            "license_compliance": license_report,
            "supply_chain_risk": {
                "risk_score": round(risk_score, 2),
                "normalized": round(normalized_risk, 4),
                "risk_level": risk_level,
            },
            "recommendations": self._generate_recommendations(
                vuln_by_severity, exploitable, doc.license_conflicts
            ),
        }

    def _generate_recommendations(
        self,
        vuln_counts: Dict[str, int],
        exploitable: List[Vulnerability],
        conflicts: List[Dict[str, str]],
    ) -> List[str]:
        """Generate actionable recommendations based on findings."""
        recs: List[str] = []
        if vuln_counts.get("CRITICAL", 0) > 0:
            recs.append("URGENT: Patch all CRITICAL vulnerabilities immediately")
        if vuln_counts.get("HIGH", 0) > 0:
            recs.append(
                "HIGH PRIORITY: Address HIGH severity vulnerabilities within 7 days"
            )
        if exploitable:
            recs.append(
                f"WARNING: {len(exploitable)} exploitable vulnerability(ies) detected - "
                "prioritize these for immediate patching"
            )
        if conflicts:
            recs.append(
                f"LICENSE: {len(conflicts)} license conflict(s) found - "
                "review and resolve before distribution"
            )
        if vuln_counts.get("MEDIUM", 0) > 0:
            recs.append(
                "MEDIUM: Schedule patching of MEDIUM vulnerabilities within 30 days"
            )
        recs.append(
            "GENERAL: Enable automated dependency updates via Dependabot or Renovate"
        )
        recs.append("GENERAL: Run SBOM generation as part of CI/CD pipeline")
        recs.append("GENERAL: Pin all dependency versions for reproducible builds")
        return recs


# ============================================================
# Demo
# ============================================================


def demo() -> None:
    """Demonstrate SBOM generation for SC2 bot supply chain security."""
    print("=" * 70)
    print("Phase 654: SBOM Generator for SC2 Bot Supply Chain Security")
    print("=" * 70)

    generator = SBOMGenerator(
        project_name="SC2-Commander-Bot",
        project_license="MIT",
    )

    # --- Generate SBOM ---
    print("\n[1] Generating SBOM with mock SC2 bot dependencies...")
    doc = generator.generate(use_mock=True)
    summary = doc.summary()
    print(f"    Total packages: {summary['total_packages']}")
    print(f"    Direct deps:    {summary['direct_dependencies']}")
    print(f"    Transitive:     {summary['transitive_dependencies']}")
    print(f"    Unique licenses: {', '.join(summary['unique_licenses'][:8])}...")

    # --- SPDX Format ---
    print("\n[2] SPDX 2.3 Format Output")
    spdx_data = doc.to_spdx()
    print(f"    SPDX Version:    {spdx_data['spdxVersion']}")
    print(f"    Document Name:   {spdx_data['name']}")
    print(f"    Package count:   {len(spdx_data['packages'])}")
    print(f"    Relationships:   {len(spdx_data['relationships'])}")

    # --- CycloneDX Format ---
    print("\n[3] CycloneDX 1.5 Format Output")
    cdx_data = doc.to_cyclonedx()
    print(f"    BOM Format:      {cdx_data['bomFormat']}")
    print(f"    Spec Version:    {cdx_data['specVersion']}")
    print(f"    Components:      {len(cdx_data['components'])}")
    vuln_count = len(cdx_data.get("vulnerabilities", []))
    print(f"    Vulnerabilities: {vuln_count}")

    # --- Vulnerability Scan ---
    print("\n[4] Vulnerability Scan Results")
    print(f"    Total vulnerabilities: {len(doc.vulnerabilities)}")
    for v in doc.vulnerabilities:
        marker = " [EXPLOITABLE]" if v.exploitable else ""
        print(
            f"    - {v.cve_id} ({v.severity}, CVSS {v.cvss_score}): "
            f"{v.package_name}{marker}"
        )

    # --- License Compliance ---
    print("\n[5] License Compliance Check")
    license_report = generator.license_checker.generate_license_report(doc.packages)
    print(f"    Project license: {license_report['project_license']}")
    print(f"    Compliant: {license_report['compliant']}")
    print(f"    License distribution:")
    for lic, count in sorted(
        license_report["license_distribution"].items(), key=lambda x: -x[1]
    )[:6]:
        print(f"      {lic}: {count}")
    if license_report["conflicts"]:
        print(f"    Conflicts found: {len(license_report['conflicts'])}")
        for c in license_report["conflicts"][:3]:
            conflict_desc = c.get("conflict", "unknown")
            print(f"      - {conflict_desc}")

    # --- Security Report ---
    print("\n[6] Supply Chain Security Report")
    report = generator.generate_security_report()
    risk = report["supply_chain_risk"]
    print(f"    Risk Score:  {risk['risk_score']} / 100")
    print(f"    Risk Level:  {risk['risk_level']}")
    print(f"    Normalized:  {risk['normalized']:.2%}")

    print("\n[7] Recommendations")
    for i, rec in enumerate(report["recommendations"], 1):
        print(f"    {i}. {rec}")

    # --- Category Breakdown ---
    print("\n[8] Dependency Category Breakdown")
    cats = summary.get("category_breakdown", {})
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        bar = "#" * count
        print(f"    {cat:25s} [{count:2d}] {bar}")

    print("\n" + "=" * 70)
    print("Phase 654 demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    demo()

# Phase 654: SBOM registered
