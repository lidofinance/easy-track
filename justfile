set dotenv-load

anvil_host := env_var_or_default("ANVIL_IP_ADDR", "127.0.0.1")
anvil_port := env_var_or_default("ANVIL_PORT", "8545")
anvil_rpc_url := "http://" + anvil_host + ":" + anvil_port
disable_code_size_limit := if env_var_or_default("DISABLE_CODE_SIZE_LIMIT", "") != "" { "--disable-code-size-limit" } else { "" }

# Start a local anvil fork (reuses one already running on the port).
make-fork *args:
    @if nc -z -w 1 {{anvil_host}} {{anvil_port}} > /dev/null 2>&1; \
        then just _warn "anvil process is already running at {{anvil_rpc_url}}. Make sure it's connected to the right network and in the right state."; \
        else exec anvil -f ${RPC_URL} --host {{anvil_host}} --port {{anvil_port}} --config-out localhost.json {{disable_code_size_limit}} --timeout 90000 {{args}}; \
    fi

# Run the deployed-factory scenario tests.
test-scenario *args:
    forge test --match-path 'test/foundry/scenario/**' \
        -vvv --show-progress --summary --detailed {{args}}

_warn message:
    @tput setaf 3 && printf "[WARNING]" && tput sgr0 && echo " {{message}}"
