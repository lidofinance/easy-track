#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o pipefail

RED='\033[0;31m'
ORANGE='\033[0;33m'
GREEN='\033[0;32m'
NC='\033[0m'

if [[ "${TRACE-0}" == "1" ]]; then
  set -o xtrace
fi

envs=(REMOTE_RPC ETHERSCAN_TOKEN CONFIG ETHERSCAN_API)

local_rpc_port=7776

_err() {
  local message=$1

  echo -e "${RED}Error:${NC} $message, aborting." >&2
  exit 1
}

for e in "${envs[@]}"; do
    [[ "${!e:+isset}" == "isset" ]] || { _err "${e} env var is required but is not set"; }
done

function start_fork() {
  local_fork_command=$(
    cat <<-_EOF_ | xargs | sed 's/ / /g'
    yarn ganache --chain.vmErrorsOnRPCResponse true
    --wallet.totalAccounts 10 --chain.chainId 1
    --fork.url ${REMOTE_RPC}
    --miner.blockGasLimit 92000000
    --server.host 127.0.0.1 --server.port ${local_rpc_port}
    --hardfork istanbul -d
_EOF_
  )

  echo "Starting local fork \"${local_fork_command}\""
  (nc -vz 127.0.0.1 $local_rpc_port) &>/dev/null && kill -SIGTERM "$(lsof -t -i:$local_rpc_port)"

  $local_fork_command 1>>./logs 2>&1 &
  fork_pid=$$
  echo "Ganache pid $fork_pid"

  sleep 10
}

echo "=========================================================="
./bytecode-verificator/bytecode_verificator.sh --solc-version 0.8.6 --remote-rpc-url $REMOTE_RPC --config-json $CONFIG --contract AddNodeOperators --etherscan-api-url $ETHERSCAN_API --local-ganache
echo "=========================================================="
./bytecode-verificator/bytecode_verificator.sh --solc-version 0.8.6 --remote-rpc-url $REMOTE_RPC --config-json $CONFIG --contract ActivateNodeOperators --etherscan-api-url $ETHERSCAN_API  --skip-compilation --local-ganache
echo "=========================================================="
./bytecode-verificator/bytecode_verificator.sh --solc-version 0.8.6 --remote-rpc-url $REMOTE_RPC --config-json $CONFIG --contract DeactivateNodeOperators --etherscan-api-url $ETHERSCAN_API  --skip-compilation --local-ganache
echo "=========================================================="
./bytecode-verificator/bytecode_verificator.sh --solc-version 0.8.6 --remote-rpc-url $REMOTE_RPC --config-json $CONFIG --contract SetVettedValidatorsLimits --etherscan-api-url $ETHERSCAN_API  --skip-compilation --local-ganache
echo "=========================================================="
./bytecode-verificator/bytecode_verificator.sh --solc-version 0.8.6 --remote-rpc-url $REMOTE_RPC --config-json $CONFIG --contract IncreaseVettedValidatorsLimit --etherscan-api-url $ETHERSCAN_API  --skip-compilation --local-ganache
echo "=========================================================="
./bytecode-verificator/bytecode_verificator.sh --solc-version 0.8.6 --remote-rpc-url $REMOTE_RPC --config-json $CONFIG --contract SetNodeOperatorNames --etherscan-api-url $ETHERSCAN_API  --skip-compilation --local-ganache
echo "=========================================================="
./bytecode-verificator/bytecode_verificator.sh --solc-version 0.8.6 --remote-rpc-url $REMOTE_RPC --config-json $CONFIG --contract SetNodeOperatorRewardAddresses --etherscan-api-url $ETHERSCAN_API  --skip-compilation --local-ganache
echo "=========================================================="
./bytecode-verificator/bytecode_verificator.sh --solc-version 0.8.6 --remote-rpc-url $REMOTE_RPC --config-json $CONFIG --contract ChangeNodeOperatorManagers --etherscan-api-url $ETHERSCAN_API --skip-compilation --local-ganache
echo "=========================================================="
./bytecode-verificator/bytecode_verificator.sh --solc-version 0.8.6 --remote-rpc-url $REMOTE_RPC --config-json $CONFIG --contract UpdateTargetValidatorLimits --etherscan-api-url $ETHERSCAN_API  --skip-compilation --local-ganache