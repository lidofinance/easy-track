from brownie import accounts, chain
from typing import Tuple, Sequence
from utils.lido import contracts as get_contracts

MAX_ITERATIONS = 1000

# https://github.com/lidofinance/dual-governance/blob/main/contracts/libraries/ExecutableProposals.sol#L27
PROPOSAL_STATUS = {
    "not_exist": 0,
    "submitted": 1,
    "scheduled": 2,
    "executed": 3,
    "cancelled": 4,
}

# https://github.com/lidofinance/dual-governance/blob/main/contracts/libraries/DualGovernanceStateMachine.sol#L35
DUAL_GOVERNANCE_STATE = {
    "normal": 1,
    "veto_signalling": 2,
    "veto_signalling_deactivation": 3,
    "veto_cooldown": 4,
    "rage_quit": 5,
}


def submit_proposals(items: Sequence[Tuple[Sequence[Tuple[str, str]], str]]) -> Sequence[Tuple[str, str]]:
    proposal_list = []
    contracts = get_contracts()

    for call_script, description in items:
        proposal_calldata = []

        for address, calldata in call_script:
            proposal_calldata.append((address, 0, calldata))

        proposal_list.append(
            (
                contracts.dual_governance.address,
                contracts.dual_governance.submitProposal.encode_input(
                    proposal_calldata, description
                ),
            )
        )
    return proposal_list


def process_proposals(proposal_ids):
    contracts = get_contracts()
    proposals_to_be_processed = list(proposal_ids)
    stranger = accounts[0]

    after_submit_delay = contracts.emergency_protected_timelock.getAfterSubmitDelay()
    after_schedule_delay = contracts.emergency_protected_timelock.getAfterScheduleDelay()

    submitted_proposals = []
    scheduled_proposals = []

    for proposal_id in proposals_to_be_processed:
        (_, _, _, _, proposal_status) = contracts.emergency_protected_timelock.getProposalDetails(proposal_id)
        if proposal_status == PROPOSAL_STATUS["submitted"]:
            submitted_proposals.append(proposal_id)
            proposals_to_be_processed.remove(proposal_id)
        elif proposal_status == PROPOSAL_STATUS["scheduled"]:
            scheduled_proposals.append(proposal_id)
            proposals_to_be_processed.remove(proposal_id)
        elif proposal_status in [PROPOSAL_STATUS["cancelled"], PROPOSAL_STATUS["executed"]]:
            proposals_to_be_processed.remove(proposal_id)

    if len(submitted_proposals):
        chain.sleep(after_submit_delay + 1)

        first_proposal_id = submitted_proposals[0]
        iterations = 0
        while not contracts.dual_governance.canScheduleProposal(first_proposal_id):
            wait_for_normal_state(stranger)
            iterations += 1
            if iterations > MAX_ITERATIONS:
                raise Exception(f"Unable to schedule the proposal. ({first_proposal_id})")

        for proposal_id in submitted_proposals:
            contracts.dual_governance.scheduleProposal(proposal_id, {"from": stranger})
            scheduled_proposals.append(proposal_id)

    if len(scheduled_proposals):
        chain.sleep(after_schedule_delay + 1)

        for proposal_id in scheduled_proposals:
            contracts.emergency_protected_timelock.execute(proposal_id, {"from": stranger})
            (_, _, _, _, proposal_status) = contracts.emergency_protected_timelock.getProposalDetails(proposal_id)
            assert proposal_status == PROPOSAL_STATUS["executed"], f"Proposal {proposal_id} execution failed"

    if len(proposals_to_be_processed):
        raise Exception(f"Unable to process proposals: {proposals_to_be_processed}. Proposals are already processed or cancelled.")


def process_pending_proposals():
    contracts = get_contracts()
    last_proposal_id = contracts.emergency_protected_timelock.getProposalsCount()

    if is_proposal_executed(last_proposal_id):
        return
    
    current_proposal_id = last_proposal_id
    while is_proposal_executed(current_proposal_id):
        current_proposal_id -= 1
        if current_proposal_id == 1:
            break
    
    process_proposals(list(range(current_proposal_id, last_proposal_id + 1)))


def wait_for_normal_state(stranger):
    contracts = get_contracts()
    # https://github.com/lidofinance/dual-governance/blob/main/contracts/interfaces/IDualGovernance.sol#L15
    state_details = contracts.dual_governance.getStateDetails()

    effective_state = state_details[0]
    persisted_state_entered_at = state_details[2]
    veto_signalling_activated_at = state_details[3]
    veto_signalling_duration = state_details[7]

    if effective_state == DUAL_GOVERNANCE_STATE["rage_quit"]:
        raise Exception("Dual Governance is in Rage Quit state. Unable to process proposals.")

    if effective_state == DUAL_GOVERNANCE_STATE["veto_signalling"]:
        remaining_time = veto_signalling_activated_at + veto_signalling_duration - chain.time()
        if remaining_time > 0:
            chain.sleep(remaining_time + 1)

    if effective_state == DUAL_GOVERNANCE_STATE["veto_signalling_deactivation"]:
        # https://github.com/lidofinance/dual-governance/blob/main/contracts/ImmutableDualGovernanceConfigProvider.sol#L98
        config = contracts.dual_governance_config_provider.getDualGovernanceConfig()
        veto_signalling_deactivation_max_duration = config[4]

        remaining_time = persisted_state_entered_at + veto_signalling_deactivation_max_duration - chain.time()

        if remaining_time > 0:
            chain.sleep(remaining_time + 1)
        
    contracts.dual_governance.activateNextState({"from": stranger})


def is_proposal_executed(proposal_id: int) -> bool:
    contracts = get_contracts()
    (_, _, _, _, proposal_status) = contracts.emergency_protected_timelock.getProposalDetails(proposal_id)
    return proposal_status == PROPOSAL_STATUS["executed"]