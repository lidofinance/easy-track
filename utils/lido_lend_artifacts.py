"""Strict reader for immutable Lido Lend deployment artifacts."""

from pathlib import Path

from eth_abi import encode
from web3 import Web3

try:
    import tomllib
except ImportError:
    import tomli as tomllib


MARKET_PARAMS_ABI_TYPE = "(address,address,address,address,uint256)"
METADATA_FIELDS = ("deployment", "chain_id", "config_hash")
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
PROTOCOL_FIELDS = (
    "deployment",
    "network",
    "chain_id",
    "config_hash",
    "core",
    "owner_facade",
    "irm_router",
    "adaptive_curve_irm",
    "builder",
    "risk_steward_dashboard",
    "agent",
    "evm_script_executor",
)
MARKET_FIELDS = (
    "name",
    "id",
    "loan_token",
    "collateral_token",
    "oracle",
    "irm",
    "lltv",
    "guardian_signals",
    "builder",
    "controller",
    "vault",
    "circuit_breaker",
)
CURVE_FIELDS = (
    "curve_steepness",
    "adjustment_speed",
    "target_utilization",
    "initial_rate_at_target",
    "min_rate_at_target",
    "max_rate_at_target",
    "max_borrow_rate",
)


def _read_toml(path, label):
    if not path.is_file():
        raise ValueError(f"{label} does not exist: {path}")
    with path.open("rb") as stream:
        return tomllib.load(stream)


def _as_int(value):
    return int(value, 0) if isinstance(value, str) else int(value)


def _metadata_value(metadata, field):
    if field not in metadata:
        raise ValueError(f"artifact metadata has no {field}")
    return _as_int(metadata[field]) if field == "chain_id" else metadata[field]


def _require_fields(value, fields, label):
    missing = [field for field in fields if field not in value]
    if missing:
        raise ValueError(f"{label} is missing fields: {', '.join(missing)}")


def _require_metadata(artifact, expected_kind, path, expected=None):
    metadata = artifact.get("artifact", {})
    if metadata.get("kind") != expected_kind:
        raise ValueError(f"not a {expected_kind} artifact: {path}")
    for field in METADATA_FIELDS:
        value = _metadata_value(metadata, field)
        if expected is not None and value != _metadata_value(expected, field):
            raise ValueError(f"{path} belongs to a different {field}")
    return metadata


def _linked_artifacts(root, directory, expected_kind, section):
    result = {}
    artifacts_dir = root / directory
    if not artifacts_dir.is_dir():
        return result
    for path in sorted(artifacts_dir.glob("*.toml")):
        artifact = _read_toml(path, f"{expected_kind} artifact")
        _require_metadata(artifact, expected_kind, path)
        value = artifact.get(section, {})
        _require_fields(value, ("name", "address"), f"{path}:{section}")
        name = value.get("name")
        if name != path.stem:
            raise ValueError(f"{path}: {section}.name {name!r} does not match the file name")
        if name in result:
            raise ValueError(f"duplicate {expected_kind} artifact name: {name}")
        result[name] = (path, artifact)
    return result


def _market_id(market):
    params = (
        market["loan_token"],
        market["collateral_token"],
        market["oracle"],
        market["irm"],
        _as_int(market["lltv"]),
    )
    return Web3.keccak(encode([MARKET_PARAMS_ABI_TYPE], [params])).hex()


def load_lido_lend_artifacts(directory, require_exit_books=False):
    """Load and cross-check one immutable Lido Lend deployment directory."""
    root = Path(directory).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Lido Lend artifacts directory does not exist: {root}")

    protocol_path = root / "protocol.toml"
    protocol_artifact = _read_toml(protocol_path, "protocol artifact")
    metadata = _require_metadata(protocol_artifact, "protocol-deployment", protocol_path)
    protocol = protocol_artifact.get("protocol", {})
    _require_fields(protocol, PROTOCOL_FIELDS, f"{protocol_path}:protocol")
    for field in METADATA_FIELDS:
        if _metadata_value(protocol, field) != _metadata_value(metadata, field):
            raise ValueError(f"protocol and artifact metadata disagree on {field}")

    oracle_artifacts = _linked_artifacts(root, "oracles", "oracle", "oracle")
    guardian_artifacts = _linked_artifacts(root, "guardians", "guardian-signals", "guardian_signals")
    for path, artifact in oracle_artifacts.values():
        _require_metadata(artifact, "oracle", path, metadata)
    for path, artifact in guardian_artifacts.values():
        _require_metadata(artifact, "guardian-signals", path, metadata)

    markets_dir = root / "markets"
    market_paths = sorted(markets_dir.glob("*.toml")) if markets_dir.is_dir() else []
    if not market_paths:
        raise ValueError(f"deployment has no market artifacts: {markets_dir}")

    markets = {}
    market_ids = set()
    for path in market_paths:
        artifact = _read_toml(path, "market artifact")
        _require_metadata(artifact, "market-deployment", path, metadata)
        market = artifact.get("market", {})
        _require_fields(market, MARKET_FIELDS, f"{path}:market")
        _require_fields(artifact.get("curve", {}), CURVE_FIELDS, f"{path}:curve")
        name = market.get("name")
        if name != path.stem:
            raise ValueError(f"{path}: market.name {name!r} does not match the file name")
        if name in markets:
            raise ValueError(f"duplicate market artifact name: {name}")
        if market.get("builder", "").lower() != protocol.get("builder", "").lower():
            raise ValueError(f"market {name!r}: builder does not match protocol artifact")
        if market.get("irm", "").lower() != protocol.get("irm_router", "").lower():
            raise ValueError(f"market {name!r}: IRM does not match protocol artifact")
        pausers = artifact.get("roles", {}).get("pausers", [])
        circuit_breaker = market.get("circuit_breaker", ZERO_ADDRESS)
        if not pausers or circuit_breaker.lower() != pausers[0].lower():
            raise ValueError(f"market {name!r}: CircuitBreaker must be the first pauser")
        derived_id = _market_id(market)
        if derived_id.lower() != market.get("id", "").lower():
            raise ValueError(f"market {name!r}: artifact id does not match its market params")
        if derived_id.lower() in market_ids:
            raise ValueError(f"duplicate market id: {derived_id}")
        market_ids.add(derived_id.lower())

        oracle_name = market.get("oracle_artifact", "")
        if oracle_name:
            if oracle_name not in oracle_artifacts:
                raise ValueError(f"market {name!r}: missing oracle artifact {oracle_name!r}")
            oracle = oracle_artifacts[oracle_name][1]["oracle"]
            if oracle["address"].lower() != market["oracle"].lower():
                raise ValueError(f"market {name!r}: oracle artifact address mismatch")

        guardian_name = market.get("guardian_group", "")
        if guardian_name:
            if guardian_name not in guardian_artifacts:
                raise ValueError(f"market {name!r}: missing GuardianSignals artifact {guardian_name!r}")
            guardian = guardian_artifacts[guardian_name][1]["guardian_signals"]
            if guardian["address"].lower() != market["guardian_signals"].lower():
                raise ValueError(f"market {name!r}: GuardianSignals artifact address mismatch")

        markets[name] = artifact

    exit_books_path = root / "exit-books.toml"
    exit_books_artifact = None
    if exit_books_path.is_file():
        exit_books_artifact = _read_toml(exit_books_path, "exit books artifact")
        _require_metadata(exit_books_artifact, "exit-books-deployment", exit_books_path, metadata)
        _require_fields(
            exit_books_artifact.get("exit_books", {}),
            ("morpho", "erc4626"),
            f"{exit_books_path}:exit_books",
        )
    elif require_exit_books:
        raise ValueError(f"exit books artifact does not exist: {exit_books_path}")

    return {
        "root": root,
        "metadata": metadata,
        "protocol": protocol_artifact,
        "markets": markets,
        "oracles": {name: artifact for name, (_, artifact) in oracle_artifacts.items()},
        "guardians": {name: artifact for name, (_, artifact) in guardian_artifacts.items()},
        "exit_books": exit_books_artifact,
    }
