// SPDX-License-Identifier: GPL-2.0-or-later
pragma solidity 0.8.36;

import {DeployWethWsteth} from "../deployment/mainnet/DeployWethWsteth.s.sol";
import {MarketPlan} from "../deployment/DeploymentTypes.sol";

// Compiled from script/ci/ in the lending checkout.
contract DeployFirstMarket is DeployWethWsteth {
    function _deploymentPlan() internal pure override returns (MarketPlan memory plan) {
        address[] memory guardians = new address[](1);
        guardians[0] = 0x1011E8a0668da8bbED925cB5A6DA5aa128C2BB5E;
        plan = _wethWstethPlan(guardians);
        plan.name = "weth-wsteth";
        plan.guardianGroup = keccak256(bytes(plan.name));
    }
}

contract DeploySecondMarket is DeployWethWsteth {
    function _deploymentPlan() internal pure override returns (MarketPlan memory plan) {
        address[] memory guardians = new address[](1);
        guardians[0] = 0x1011E8a0668da8bbED925cB5A6DA5aa128C2BB5E;
        plan = _wethWstethPlan(guardians);
        plan.name = "weth-wsteth-secondary";
        plan.guardianGroup = keccak256(bytes(plan.name));
        plan.market.lltv = 0.94e18;
    }
}
