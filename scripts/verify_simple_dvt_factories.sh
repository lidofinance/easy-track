#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o pipefail

if [[ "${TRACE-0}" == "1" ]]; then
  set -o xtrace
fi

envs=(REMOTE_RPC)

for e in "${envs[@]}"; do
    [[ "${!e:+isset}" == "isset" ]] || { _err "${e} env var is required but is not set"; }
done

./bytecode-verificator/bytecode_verificator.sh --solc-version 0.8.6 --remote-rpc-url $REMOTE_RPC --config-json ../deployed-holesky.json --contract AddNodeOperators --etherscan-api-url https://holesky.etherscan.io/api
./bytecode-verificator/bytecode_verificator.sh --solc-version 0.8.6 --remote-rpc-url $REMOTE_RPC --config-json ../deployed-holesky.json --contract ActivateNodeOperators --etherscan-api-url https://holesky.etherscan.io/api
./bytecode-verificator/bytecode_verificator.sh --solc-version 0.8.6 --remote-rpc-url $REMOTE_RPC --config-json ../deployed-holesky.json --contract DeactivateNodeOperators --etherscan-api-url https://holesky.etherscan.io/api
./bytecode-verificator/bytecode_verificator.sh --solc-version 0.8.6 --remote-rpc-url $REMOTE_RPC --config-json ../deployed-holesky.json --contract SetVettedValidatorsLimits --etherscan-api-url https://holesky.etherscan.io/api
./bytecode-verificator/bytecode_verificator.sh --solc-version 0.8.6 --remote-rpc-url $REMOTE_RPC --config-json ../deployed-holesky.json --contract SetNodeOperatorNames --etherscan-api-url https://holesky.etherscan.io/api
./bytecode-verificator/bytecode_verificator.sh --solc-version 0.8.6 --remote-rpc-url $REMOTE_RPC --config-json ../deployed-holesky.json --contract SetNodeOperatorRewardAddresses --etherscan-api-url https://holesky.etherscan.io/api
./bytecode-verificator/bytecode_verificator.sh --solc-version 0.8.6 --remote-rpc-url $REMOTE_RPC --config-json ../deployed-holesky.json --contract ChangeNodeOperatorManagers --etherscan-api-url https://holesky.etherscan.io/api
./bytecode-verificator/bytecode_verificator.sh --solc-version 0.8.6 --remote-rpc-url $REMOTE_RPC --config-json ../deployed-holesky.json --contract UpdateTargetValidatorLimits --etherscan-api-url https://holesky.etherscan.io/api