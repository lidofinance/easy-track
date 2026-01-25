# Easy Track Brownie Development Container

Devcontainer for running Brownie tests on the Easy Track project.

## Architecture

- **Platform**: `linux/amd64` (even on ARM64 hosts)
  - Required for prebuilt `solc 0.8.6` binary
  - Avoids slow source compilation on ARM64

- **Tools**: Python 3.10, Poetry 1.8.2, Node.js 18, Hardhat

- **Dependencies**: Installed during image build (cached until lock files change)

## Running Tests

### Local (No Fork)

```bash
brownie test
```

### Mainnet Fork

The container has `MAINNET_RPC_URL=http://host.docker.internal:8545` by default.

**Option A: Local RPC**

Start an RPC on your host machine:
```bash
anvil --host 0.0.0.0 --port 8545 --fork-url https://eth.drpc.org
```

Then in the container:
```bash
brownie test --network mainnet-fork
```

**Option B: Remote RPC**

```bash
export MAINNET_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
brownie test --network mainnet-fork
```

## Rebuilding

After changing `pyproject.toml`, `poetry.lock`, `package.json`, or `package-lock.json`:

1. `Cmd+Shift+P` / `Ctrl+Shift+P`
2. Run **"Dev Containers: Rebuild Container"**