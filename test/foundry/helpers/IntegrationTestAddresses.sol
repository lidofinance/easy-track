// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {Vm} from "forge-std/Vm.sol";

/// @notice Reader of `integration-test-addresses-<chain>.yaml`, the payout deployments the Brownie
///         suite parametrizes its payouts fixtures over, in the block style the file is written
///         in: the top-level `easytrack`, then a key per suite holding its shared contracts and its
///         `instances`, each a `- name:` line followed by its contracts. As `get_single_token_config`
///         and `get_multi_token_config` of `utils/deployed_addresses.py` do, a missing file or an
///         empty instance list yields the one synthetic `default` instance, which deploys
///         everything fresh.
library IntegrationTestAddresses {
    /// @dev A payout setup of a suite. A zero contract is deployed fresh.
    struct Instance {
        string name;
        address registry;
        address addAllowedRecipient;
        address removeAllowedRecipient;
        address topUpAllowedRecipients;
    }

    /// @dev A suite's shared contracts and its instances
    struct Suite {
        address easyTrack;
        address factory;
        address builder;
        address tokensRegistry;
        Instance[] instances;
    }

    /// @dev python: the `{"name": "default"}` instance of a chain without instances
    string internal constant DEFAULT_INSTANCE = "default";

    /// @dev The key of the line that opens an instance
    string private constant INSTANCE_KEY = "- name";

    Vm private constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    /// @dev The suite under `key` of `file`, `single_token` or `multi_token`
    function load(string memory file, string memory key)
        internal
        view
        returns (Suite memory suite)
    {
        if (vm.exists(file)) {
            _read(suite, vm.split(vm.readFile(file), "\n"), key);
        }

        if (suite.instances.length == 0) {
            suite.instances = new Instance[](1);
            suite.instances[0].name = DEFAULT_INSTANCE;
        }
    }

    function _read(Suite memory suite, string[] memory lines, string memory key) private pure {
        suite.instances = new Instance[](_countInstances(lines, key));

        bool inSuite;
        uint256 instancesSeen;
        for (uint256 index; index < lines.length; ++index) {
            string memory line = vm.trim(lines[index]);
            if (_isSkipped(line)) {
                continue;
            }

            (string memory lineKey, string memory value) = _keyValue(line);

            if (_isTopLevel(lines[index])) {
                inSuite = _equals(lineKey, key);
                instancesSeen = 0;
                if (_equals(lineKey, "easytrack")) {
                    suite.easyTrack = vm.parseAddress(value);
                }
                continue;
            }

            if (!inSuite) {
                continue;
            }

            if (_equals(lineKey, INSTANCE_KEY)) {
                suite.instances[instancesSeen].name = value;
                ++instancesSeen;
                continue;
            }

            if (bytes(value).length == 0) {
                continue;
            }

            if (instancesSeen == 0) {
                _setSuiteContract(suite, lineKey, vm.parseAddress(value));
            } else {
                _setInstanceContract(
                    suite.instances[instancesSeen - 1], lineKey, vm.parseAddress(value)
                );
            }
        }
    }

    function _countInstances(string[] memory lines, string memory key)
        private
        pure
        returns (uint256 count)
    {
        bool inSuite;
        for (uint256 index; index < lines.length; ++index) {
            string memory line = vm.trim(lines[index]);
            if (_isSkipped(line)) {
                continue;
            }

            (string memory lineKey,) = _keyValue(line);

            if (_isTopLevel(lines[index])) {
                inSuite = _equals(lineKey, key);
                continue;
            }

            if (inSuite && _equals(lineKey, INSTANCE_KEY)) {
                ++count;
            }
        }
    }

    function _setSuiteContract(Suite memory suite, string memory key, address value) private pure {
        if (_equals(key, "factory")) {
            suite.factory = value;
        } else if (_equals(key, "builder")) {
            suite.builder = value;
        } else if (_equals(key, "tokens_registry")) {
            suite.tokensRegistry = value;
        } else {
            revert(string.concat("unknown suite key: ", key));
        }
    }

    function _setInstanceContract(Instance memory instance, string memory key, address value)
        private
        pure
    {
        if (_equals(key, "registry")) {
            instance.registry = value;
        } else if (_equals(key, "add_allowed_recipient")) {
            instance.addAllowedRecipient = value;
        } else if (_equals(key, "remove_allowed_recipient")) {
            instance.removeAllowedRecipient = value;
        } else if (_equals(key, "top_up_allowed_recipients")) {
            instance.topUpAllowedRecipients = value;
        } else {
            revert(string.concat("unknown instance key: ", key));
        }
    }

    /// @dev A blank line or a comment
    function _isSkipped(string memory trimmed) private pure returns (bool) {
        return bytes(trimmed).length == 0 || bytes(trimmed)[0] == "#";
    }

    /// @dev A line without indentation, before trimming
    function _isTopLevel(string memory raw) private pure returns (bool) {
        return bytes(raw)[0] != " ";
    }

    /// @dev `key: "value"` split at the colon, the value without its quotes, empty for `key:`
    function _keyValue(string memory line)
        private
        pure
        returns (string memory key, string memory value)
    {
        uint256 colon = vm.indexOf(line, ":");
        if (colon == type(uint256).max) {
            return (line, "");
        }

        key = _slice(line, 0, colon);
        value = vm.trim(_slice(line, colon + 1, bytes(line).length));

        bytes memory raw = bytes(value);
        if (raw.length >= 2 && raw[0] == '"' && raw[raw.length - 1] == '"') {
            value = _slice(value, 1, raw.length - 1);
        }
    }

    function _slice(string memory text, uint256 start, uint256 end)
        private
        pure
        returns (string memory)
    {
        bytes memory raw = bytes(text);
        bytes memory out = new bytes(end - start);
        for (uint256 index = start; index < end; ++index) {
            out[index - start] = raw[index];
        }

        return string(out);
    }

    function _equals(string memory a, string memory b) private pure returns (bool) {
        return keccak256(bytes(a)) == keccak256(bytes(b));
    }
}
