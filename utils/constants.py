DEFAULT_NETWORK = "mainnet"


class NetworkConfig:
    """Configuration for a specific network"""
    def __init__(
        self,
        motion_duration: int,
        motions_count_limit: int,
        objections_threshold: int,
        validator_exit_fee_limit: int,
        max_group_share_limit_phase_1: int,
        max_default_tier_share_limit_phase_1: int,
        max_group_share_limit_phase_2_and_3: int,
        max_default_tier_share_limit_phase_2_and_3: int,
        st_vaults_committee: str,
        max_liquidity_fee_bp: int,
        max_reservation_fee_bp: int,
        max_infra_fee_bp: int,
    ):
        # General Easy Track settings
        self.motion_duration = motion_duration
        self.motions_count_limit = motions_count_limit
        self.objections_threshold = objections_threshold

        # Vaults factories settings
        self.validator_exit_fee_limit = validator_exit_fee_limit # maximum ETH value which can be spent to force validator exit (withdrawal fee)
        # Vaults factories settings for phases 1/2/3 - see https://research.lido.fi/t/lido-v3-design-implementation-proposal/10665
        self.max_group_share_limit_phase_1 = max_group_share_limit_phase_1 # max group share limit which can be set by easy track for phase 1
        self.max_default_tier_share_limit_phase_1 = max_default_tier_share_limit_phase_1 # max default tier share limit which can be set by easy track for phase 1
        self.max_group_share_limit_phase_2_and_3 = max_group_share_limit_phase_2_and_3 # max group share limit which can be set by easy track for phase 2 and 3
        self.max_default_tier_share_limit_phase_2_and_3 = max_default_tier_share_limit_phase_2_and_3 # max default tier share limit which can be set by easy track for phase 2 and 3
        self.st_vaults_committee = st_vaults_committee # address of the stVaults committee
        self.max_liquidity_fee_bp = max_liquidity_fee_bp # max liquidity fee basis points which can be set by easy track
        self.max_reservation_fee_bp = max_reservation_fee_bp # max reservation fee basis points which can be set by easy track
        self.max_infra_fee_bp = max_infra_fee_bp # max infra fee basis points which can be set by easy track


def get_network_config(network=DEFAULT_NETWORK):
    """Get configuration for the specified network"""
    if network == "mainnet" or network == "mainnet-fork":
        return NetworkConfig(
            motion_duration = 72 * 60 * 60,  # 72 hours
            motions_count_limit = 12,
            objections_threshold = 50,  # 0.5 %
            validator_exit_fee_limit = 100000000000000000,  # 0.1 ETH
            max_group_share_limit_phase_1 = 50_000 * 10 ** 18,
            max_default_tier_share_limit_phase_1 = 0,
            max_group_share_limit_phase_2_and_3 = 1_000_000 * 10 ** 18,
            max_default_tier_share_limit_phase_2_and_3 = 1_000_000 * 10 ** 18,
            st_vaults_committee = "0x18A1065c81b0Cc356F1b1C843ddd5E14e4AefffF",
            max_liquidity_fee_bp = 1000,
            max_reservation_fee_bp = 0,
            max_infra_fee_bp = 100,
        )

    if network == "hoodi" or network == "hoodi-fork":
        return NetworkConfig(
            motion_duration = 72 * 60 * 60,  # 72 hours
            motions_count_limit = 12,
            objections_threshold = 50,  # 0.5 %
            validator_exit_fee_limit = 100000000000000000,  # 0.1 ETH
            max_group_share_limit_phase_1 = 50_000 * 10 ** 18,
            max_default_tier_share_limit_phase_1 = 0,
            max_group_share_limit_phase_2_and_3 = 500_000 * 10 ** 18,
            max_default_tier_share_limit_phase_2_and_3 = 500_000 * 10 ** 18,
            st_vaults_committee = "0xeBe5948787Bb3a565F67ccD93cb85A91960c472a",
            max_liquidity_fee_bp = 1000,
            max_reservation_fee_bp = 0,
            max_infra_fee_bp = 100,
        )

    raise NameError(
        f"""Unknown network "{network}". Supported networks: mainnet, mainnet-fork, hoodi, hoodi-fork"""
    )


# Backward compatibility - deprecated constants
# Use get_network_config() instead
INITIAL_MOTION_DURATION = 72 * 60 * 60  # 72 hours
INITIAL_MOTIONS_COUNT_LIMIT = 12
INITIAL_OBJECTIONS_THRESHOLD = 50  # 0.5 %
