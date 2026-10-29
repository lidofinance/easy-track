set dotenv-load

anvil_host := env_var_or_default("ANVIL_IP_ADDR", "127.0.0.1")
anvil_port := env_var_or_default("ANVIL_PORT", "8545")
anvil_rpc_url := "http://" + anvil_host + ":" + anvil_port
disable_code_size_limit := if env_var_or_default("DISABLE_CODE_SIZE_LIMIT", "") != "" { "--disable-code-size-limit" } else { "" }

# The chain to fork, `mainnet` or `hoodi`, and its RPC variable, as in .env.sample.
chain := env_var_or_default("CHAIN", "hoodi")
chain_rpc_env := uppercase(chain) + "_RPC_URL"
chain_rpc_url := env_var_or_default(chain_rpc_env, "")

# Start a local anvil fork of <CHAIN>_RPC_URL (reuses one already running on the port).
make-fork *args:
    @if nc -z -w 1 {{anvil_host}} {{anvil_port}} > /dev/null 2>&1; \
        then just _warn "anvil process is already running at {{anvil_rpc_url}}. Make sure it's connected to the right network and in the right state."; \
        elif [ -z "{{chain_rpc_url}}" ]; then just _warn "{{chain_rpc_env}} is not set"; exit 1; \
        else exec anvil -f "{{chain_rpc_url}}" --host {{anvil_host}} --port {{anvil_port}} --config-out localhost.json {{disable_code_size_limit}} --timeout 90000 {{args}}; \
    fi

# Run the unit tests.
test *args:
    forge test {{args}}

# Build the contracts, the artifacts the scenario tests deploy fresh factories from.
build:
    forge build

# Run the scenario tests on the anvil fork when one is up, else on <CHAIN>_RPC_URL, see test/foundry/README.md.
test-scenario *args: build
    FOUNDRY_PROFILE=scenario forge test --fork-url "$(just _rpc-url)" -vvv --show-progress --summary --detailed {{args}}

# Run a Foundry script of script/ on the same RPC, a dry run unless --broadcast is passed, see README.md.
script name *args: build
    FOUNDRY_PROFILE=scenario forge script script/{{name}}.s.sol --rpc-url "$(just _rpc-url)" {{args}}

# Format the Foundry tests and scripts. contracts/ is frozen, see [fmt] in foundry.toml.
fmt *args:
    forge fmt test/foundry script {{args}}

# The RPC of the forking recipes: the anvil on the port, else <CHAIN>_RPC_URL.
_rpc-url:
    @if nc -z -w 1 {{anvil_host}} {{anvil_port}} > /dev/null 2>&1; then echo "{{anvil_rpc_url}}"; \
        elif [ -n "{{chain_rpc_url}}" ]; then echo "{{chain_rpc_url}}"; \
        else just _warn "no anvil at {{anvil_rpc_url}} and {{chain_rpc_env}} is not set"; exit 1; \
    fi

_warn message:
    @tput setaf 3 && printf "[WARNING]" && tput sgr0 && echo " {{message}}" >&2
