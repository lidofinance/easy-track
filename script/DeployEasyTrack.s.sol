// SPDX-FileCopyrightText: 2026 Lido <info@lido.fi>
// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.25;

import {EasyTrackScript} from "script/helpers/EasyTrackScript.sol";
import {Lido} from "script/helpers/Lido.sol";
import {
    IEasyTrack,
    IEVMScriptExecutor,
    IRewardProgramsRegistry
} from "test/foundry/interfaces/EasyTrack.sol";
import {IFinance, INodeOperatorsRegistry} from "test/foundry/interfaces/External.sol";

/// @notice `scripts/deploy.py`: Easy Track with the initial settings and its executor owned by
///         Voting, the five factories registered with their permissions, the reward programs
///         registry with its roles, and the admin role handed to Voting. `deploy` does it for a
///         deployer, `run` for the broadcaster with the addresses read from the environment, and
///         records the deployment.
contract DeployEasyTrack is EasyTrackScript {
    /// @dev The environment `scripts/deploy.py` reads
    struct Params {
        /// @dev `LEGO_PROGRAM_VAULT`, the program `TopUpLegoProgram` pays
        address legoProgramVault;
        /// @dev `LEGO_COMMITTEE_MULTISIG`, the trusted caller of `TopUpLegoProgram`
        address legoCommitteeMultisig;
        /// @dev `REWARD_PROGRAMS_MULTISIG`, the trusted caller of the reward programs factories
        address rewardProgramsMultisig;
        /// @dev `PAUSE_ADDRESS`, granted `PAUSE_ROLE` next to Voting
        address pauseAddress;
    }

    struct Deployment {
        IEasyTrack easyTrack;
        address evmScriptExecutor;
        address increaseNodeOperatorStakingLimit;
        address topUpLegoProgram;
        IRewardProgramsRegistry rewardProgramsRegistry;
        address addRewardProgram;
        address removeRewardProgram;
        address topUpRewardPrograms;
    }

    /// @dev `utils/constants.py`, the settings Easy Track starts with
    uint256 public constant INITIAL_MOTION_DURATION = 72 hours;
    uint256 public constant INITIAL_MOTIONS_COUNT_LIMIT = 12;
    uint256 public constant INITIAL_OBJECTIONS_THRESHOLD = 50;

    function run() external {
        Lido.DAO memory dao = Lido.dao();
        Params memory params = Params({
            legoProgramVault: vm.envAddress("LEGO_PROGRAM_VAULT"),
            legoCommitteeMultisig: vm.envAddress("LEGO_COMMITTEE_MULTISIG"),
            rewardProgramsMultisig: vm.envAddress("REWARD_PROGRAMS_MULTISIG"),
            pauseAddress: vm.envAddress("PAUSE_ADDRESS")
        });

        vm.startBroadcast();
        Deployment memory deployment = deploy(msg.sender, params);
        vm.stopBroadcast();

        _record(dao, msg.sender, params, deployment);
    }

    /// @dev `deploy_easy_tracks`, as `deployer`, the account the calls come from and the admin
    ///      until the hand-over: the broadcaster under `run`, the script contract on a fork
    function deploy(address deployer, Params memory params)
        public
        returns (Deployment memory deployment)
    {
        Lido.DAO memory dao = Lido.dao();
        address registry = Lido.curatedRegistry(dao);

        deployment.easyTrack = IEasyTrack(
            _deployArtifact(
                "EasyTrack",
                abi.encode(
                    dao.ldo,
                    deployer,
                    INITIAL_MOTION_DURATION,
                    INITIAL_MOTIONS_COUNT_LIMIT,
                    INITIAL_OBJECTIONS_THRESHOLD
                )
            )
        );
        deployment.evmScriptExecutor =
            _deployArtifact("EVMScriptExecutor", abi.encode(dao.callsScript, deployment.easyTrack));
        IEVMScriptExecutor(deployment.evmScriptExecutor).transferOwnership(dao.voting);
        deployment.easyTrack.setEVMScriptExecutor(deployment.evmScriptExecutor);

        deployment.increaseNodeOperatorStakingLimit =
            _deployArtifact("IncreaseNodeOperatorStakingLimit", abi.encode(registry));
        deployment.topUpLegoProgram = _deployArtifact(
            "TopUpLegoProgram",
            abi.encode(params.legoCommitteeMultisig, dao.finance, params.legoProgramVault)
        );

        address[] memory roleHolders = _roleHolders(dao.voting, deployment.evmScriptExecutor);
        deployment.rewardProgramsRegistry = IRewardProgramsRegistry(
            _deployArtifact(
                "RewardProgramsRegistry", abi.encode(dao.voting, roleHolders, roleHolders)
            )
        );
        deployment.addRewardProgram = _deployArtifact(
            "AddRewardProgram",
            abi.encode(params.rewardProgramsMultisig, deployment.rewardProgramsRegistry)
        );
        deployment.removeRewardProgram = _deployArtifact(
            "RemoveRewardProgram",
            abi.encode(params.rewardProgramsMultisig, deployment.rewardProgramsRegistry)
        );
        deployment.topUpRewardPrograms = _deployArtifact(
            "TopUpRewardPrograms",
            abi.encode(
                params.rewardProgramsMultisig,
                deployment.rewardProgramsRegistry,
                dao.finance,
                dao.ldo
            )
        );

        _addEVMScriptFactories(dao, registry, deployment);
        _grantRoles(dao, params.pauseAddress, deployment.easyTrack);
        _transferAdminRole(deployer, dao.voting, deployment.easyTrack);
    }

    /// @dev `add_evm_script_factories`, in its order
    function _addEVMScriptFactories(
        Lido.DAO memory dao,
        address registry,
        Deployment memory deployment
    ) private {
        IEasyTrack easyTrack = deployment.easyTrack;
        bytes memory newImmediatePayment =
            _permission(dao.finance, IFinance.newImmediatePayment.selector);

        easyTrack.addEVMScriptFactory(
            deployment.increaseNodeOperatorStakingLimit,
            _permission(registry, INodeOperatorsRegistry.setNodeOperatorStakingLimit.selector)
        );
        easyTrack.addEVMScriptFactory(deployment.topUpLegoProgram, newImmediatePayment);
        easyTrack.addEVMScriptFactory(deployment.topUpRewardPrograms, newImmediatePayment);
        easyTrack.addEVMScriptFactory(
            deployment.addRewardProgram,
            _permission(
                address(deployment.rewardProgramsRegistry),
                IRewardProgramsRegistry.addRewardProgram.selector
            )
        );
        easyTrack.addEVMScriptFactory(
            deployment.removeRewardProgram,
            _permission(
                address(deployment.rewardProgramsRegistry),
                IRewardProgramsRegistry.removeRewardProgram.selector
            )
        );
    }

    /// @dev `grant_roles`: Voting may pause, unpause and cancel, the pause address may pause
    function _grantRoles(Lido.DAO memory dao, address pauseAddress, IEasyTrack easyTrack) private {
        easyTrack.grantRole(easyTrack.PAUSE_ROLE(), dao.voting);
        easyTrack.grantRole(easyTrack.UNPAUSE_ROLE(), dao.voting);
        easyTrack.grantRole(easyTrack.CANCEL_ROLE(), dao.voting);
        easyTrack.grantRole(easyTrack.PAUSE_ROLE(), pauseAddress);
    }

    /// @dev `transfer_admin_role`: Voting becomes the admin and the deployer stops being one
    function _transferAdminRole(address deployer, address voting, IEasyTrack easyTrack) private {
        bytes32 adminRole = easyTrack.DEFAULT_ADMIN_ROLE();

        easyTrack.grantRole(adminRole, voting);
        easyTrack.revokeRole(adminRole, deployer);
    }

    /// @dev `create_permission`: the target and the selector a factory's scripts may call
    function _permission(address target, bytes4 selector) private pure returns (bytes memory) {
        return abi.encodePacked(target, selector);
    }

    function _roleHolders(address voting, address executor)
        private
        pure
        returns (address[] memory holders)
    {
        holders = new address[](2);
        holders[0] = voting;
        holders[1] = executor;
    }

    function _record(
        Lido.DAO memory dao,
        address deployer,
        Params memory params,
        Deployment memory deployment
    ) private {
        _recordEasyTrack(dao, deployer, deployment);
        _recordFactories(dao, params, deployment);
    }

    function _recordEasyTrack(Lido.DAO memory dao, address deployer, Deployment memory deployment)
        private
    {
        _recordDeployment(
            dao,
            "EasyTrack",
            address(deployment.easyTrack),
            _args(
                _arg(dao.ldo),
                _arg(deployer),
                _arg(INITIAL_MOTION_DURATION),
                _arg(INITIAL_MOTIONS_COUNT_LIMIT),
                _arg(INITIAL_OBJECTIONS_THRESHOLD)
            )
        );
        _recordDeployment(
            dao,
            "EVMScriptExecutor",
            deployment.evmScriptExecutor,
            _args(_arg(dao.callsScript), _arg(address(deployment.easyTrack)))
        );
        _recordDeployment(
            dao,
            "IncreaseNodeOperatorStakingLimit",
            deployment.increaseNodeOperatorStakingLimit,
            _args(_arg(Lido.curatedRegistry(dao)))
        );
    }

    function _recordFactories(
        Lido.DAO memory dao,
        Params memory params,
        Deployment memory deployment
    ) private {
        string memory registry = _arg(address(deployment.rewardProgramsRegistry));
        string memory multisig = _arg(params.rewardProgramsMultisig);
        string memory roleHolders = _arg(_roleHolders(dao.voting, deployment.evmScriptExecutor));

        _recordDeployment(
            dao,
            "TopUpLegoProgram",
            deployment.topUpLegoProgram,
            _args(
                _arg(params.legoCommitteeMultisig), _arg(dao.finance), _arg(params.legoProgramVault)
            )
        );
        _recordDeployment(
            dao,
            "RewardProgramsRegistry",
            address(deployment.rewardProgramsRegistry),
            _args(_arg(dao.voting), roleHolders, roleHolders)
        );
        _recordDeployment(
            dao, "AddRewardProgram", deployment.addRewardProgram, _args(multisig, registry)
        );
        _recordDeployment(
            dao, "RemoveRewardProgram", deployment.removeRewardProgram, _args(multisig, registry)
        );
        _recordDeployment(
            dao,
            "TopUpRewardPrograms",
            deployment.topUpRewardPrograms,
            _args(multisig, registry, _arg(dao.finance), _arg(dao.ldo))
        );
    }
}
