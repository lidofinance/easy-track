// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {Test} from "forge-std/Test.sol";
import {IntegrationTestAddresses} from "test/foundry/helpers/IntegrationTestAddresses.sol";

/// @notice The reader of `integration-test-addresses-<chain>.yaml` over inline text. Needs no fork.
contract IntegrationTestAddressesTest is Test {
    string internal constant SINGLE_TOKEN = "single_token";
    string internal constant MULTI_TOKEN = "multi_token";
    string internal constant MISSING_FILE = "integration-test-addresses-none.yaml";

    address internal constant EASY_TRACK = address(0xE1);
    address internal constant FACTORY = address(0xF1);
    address internal constant BUILDER = address(0xB1);
    address internal constant TOKENS_REGISTRY = address(0xC1);
    address internal constant REGISTRY = address(0x11);
    address internal constant ADD_ALLOWED_RECIPIENT = address(0x12);
    address internal constant REMOVE_ALLOWED_RECIPIENT = address(0x13);
    address internal constant TOP_UP_ALLOWED_RECIPIENTS = address(0x14);
    address internal constant SECOND_REGISTRY = address(0x21);
    address internal constant MULTI_TOKEN_FACTORY = address(0xF2);
    address internal constant MULTI_TOKEN_REGISTRY = address(0x31);

    function test_ReadsSuiteContractsAndInstances() external pure {
        IntegrationTestAddresses.Suite memory suite =
            IntegrationTestAddresses.parse(_file(), SINGLE_TOKEN);

        assertEq(suite.easyTrack, EASY_TRACK, "easyTrack");
        assertEq(suite.factory, FACTORY, "factory");
        assertEq(suite.builder, BUILDER, "builder");
        assertEq(suite.tokensRegistry, address(0), "tokensRegistry");
        assertEq(suite.instances.length, 2, "instances");

        IntegrationTestAddresses.Instance memory first = suite.instances[0];
        assertEq(first.name, "LOL stETH", "first.name");
        assertEq(first.registry, REGISTRY, "first.registry");
        assertEq(first.addAllowedRecipient, ADD_ALLOWED_RECIPIENT, "first.addAllowedRecipient");
        assertEq(
            first.removeAllowedRecipient, REMOVE_ALLOWED_RECIPIENT, "first.removeAllowedRecipient"
        );
        assertEq(
            first.topUpAllowedRecipients, TOP_UP_ALLOWED_RECIPIENTS, "first.topUpAllowedRecipients"
        );

        IntegrationTestAddresses.Instance memory second = suite.instances[1];
        assertEq(second.name, "LEGO LDO", "second.name");
        assertEq(second.registry, SECOND_REGISTRY, "second.registry");
        assertEq(second.addAllowedRecipient, address(0), "second.addAllowedRecipient");
        assertEq(second.removeAllowedRecipient, address(0), "second.removeAllowedRecipient");
        assertEq(second.topUpAllowedRecipients, address(0), "second.topUpAllowedRecipients");
    }

    function test_ReadsSuiteAfterAnother() external pure {
        IntegrationTestAddresses.Suite memory suite =
            IntegrationTestAddresses.parse(_file(), MULTI_TOKEN);

        assertEq(suite.easyTrack, EASY_TRACK, "easyTrack");
        assertEq(suite.factory, MULTI_TOKEN_FACTORY, "factory");
        assertEq(suite.builder, address(0), "builder");
        assertEq(suite.tokensRegistry, TOKENS_REGISTRY, "tokensRegistry");
        assertEq(suite.instances.length, 1, "instances");
        assertEq(suite.instances[0].name, "LEGO stablecoins", "name");
        assertEq(suite.instances[0].registry, MULTI_TOKEN_REGISTRY, "registry");
    }

    // python: try_load_deployed_contract
    function test_ReadsLocalAsOmitted() external pure {
        IntegrationTestAddresses.Suite memory suite =
            IntegrationTestAddresses.parse(_localFile(), SINGLE_TOKEN);

        assertEq(suite.easyTrack, address(0), "easyTrack");
        assertEq(suite.factory, address(0), "factory");
        assertEq(suite.builder, address(0), "builder");
        assertEq(suite.instances.length, 1, "instances");
        assertEq(suite.instances[0].name, "fresh", "name");
        assertEq(suite.instances[0].registry, address(0), "registry");
        assertEq(suite.instances[0].topUpAllowedRecipients, address(0), "topUpAllowedRecipients");
    }

    function test_ReadsSuiteWithoutInstancesAsDefaultInstance() external pure {
        IntegrationTestAddresses.Suite memory suite =
            IntegrationTestAddresses.parse(_noInstancesFile(), SINGLE_TOKEN);

        assertEq(suite.easyTrack, EASY_TRACK, "easyTrack");
        assertEq(suite.factory, FACTORY, "factory");
        assertEq(suite.instances.length, 1, "instances");
        assertEq(suite.instances[0].name, IntegrationTestAddresses.DEFAULT_INSTANCE, "name");
        assertEq(suite.instances[0].registry, address(0), "registry");
    }

    function test_ReadsMissingFileAsDefaultInstance() external view {
        IntegrationTestAddresses.Suite memory suite =
            IntegrationTestAddresses.load(MISSING_FILE, SINGLE_TOKEN);

        assertEq(suite.easyTrack, address(0), "easyTrack");
        assertEq(suite.factory, address(0), "factory");
        assertEq(suite.instances.length, 1, "instances");
        assertEq(suite.instances[0].name, IntegrationTestAddresses.DEFAULT_INSTANCE, "name");
        assertEq(suite.instances[0].registry, address(0), "registry");
    }

    /// @dev Both suites: the single-token one with an instance naming every contract and one with
    ///      the add factory empty and the rest absent, the multi-token one with no builder
    function _file() private pure returns (string memory) {
        return string.concat(
            "easytrack: \"0x00000000000000000000000000000000000000e1\"\n",
            "\n",
            "# the suites\n",
            "single_token:\n",
            "  factory: \"0x00000000000000000000000000000000000000f1\"\n",
            "  builder: \"0x00000000000000000000000000000000000000b1\"\n",
            "  instances:\n",
            "    - name: LOL stETH\n",
            "      registry: \"0x0000000000000000000000000000000000000011\"\n",
            "      add_allowed_recipient: \"0x0000000000000000000000000000000000000012\"\n",
            "      remove_allowed_recipient: \"0x0000000000000000000000000000000000000013\"\n",
            "      top_up_allowed_recipients: \"0x0000000000000000000000000000000000000014\"\n",
            "\n",
            "    - name: LEGO LDO\n",
            "      registry: \"0x0000000000000000000000000000000000000021\"\n",
            "      add_allowed_recipient:\n",
            "\n",
            "multi_token:\n",
            "  factory: \"0x00000000000000000000000000000000000000f2\"\n",
            "  tokens_registry: \"0x00000000000000000000000000000000000000c1\"\n",
            "  instances:\n",
            "    - name: LEGO stablecoins\n",
            "      registry: \"0x0000000000000000000000000000000000000031\"\n"
        );
    }

    /// @dev python: the `"local"` entries, every contract to be deployed fresh
    function _localFile() private pure returns (string memory) {
        return string.concat(
            "easytrack: \"local\"\n",
            "single_token:\n",
            "  factory: \"local\"\n",
            "  builder: \"local\"\n",
            "  instances:\n",
            "    - name: fresh\n",
            "      registry: \"local\"\n",
            "      top_up_allowed_recipients: \"local\"\n"
        );
    }

    /// @dev A suite listing its shared contracts and no instances
    function _noInstancesFile() private pure returns (string memory) {
        return string.concat(
            "easytrack: \"0x00000000000000000000000000000000000000e1\"\n",
            "single_token:\n",
            "  factory: \"0x00000000000000000000000000000000000000f1\"\n"
        );
    }
}
