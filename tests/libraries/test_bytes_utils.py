from brownie import reverts


def test_bytes24_at(bytes_utils_wrapper):
    short_word = "0x00112233445566778899aabbccddeeff"
    word = "0x00112233445566778899aabbccddeeff0102030405060708090a0b0c0d0f"
    # word too short start from zero position
    assert (
        bytes_utils_wrapper.bytes24At(short_word, 0)
        == "0x00112233445566778899aabbccddeeff0000000000000000"
    )
    # word too short start from non zero position
    assert (
        bytes_utils_wrapper.bytes24At(short_word, 4)
        == "0x445566778899aabbccddeeff000000000000000000000000"
    )

    # long word zero position
    assert (
        bytes_utils_wrapper.bytes24At(word, 0),
        "0x00112233445566778899aabbccddeeff0102030405060708",
    )

    # long word non zero position
    assert (
        bytes_utils_wrapper.bytes24At(word, 6),
        "0x66778899aabbccddeeff0102030405060708090a0b0c0d0f",
    )


def test_address_at(owner, bytes_utils_wrapper):
    address = owner.address
    word_with_bytes = "0x00112233" + address[2:] + "ddeeff"
    assert bytes_utils_wrapper.addressAt(address, 0) == address
    assert bytes_utils_wrapper.addressAt(word_with_bytes, 4) == address


def test_uint32_at(bytes_utils_wrapper):
    one = "0x00000001"
    zero = "0x00000000"
    empty = "0x"
    max_value = "0xffffffff"
    long_word = "0xffffff00000010eeee"
    assert bytes_utils_wrapper.uint32At(one, 0) == 1
    assert bytes_utils_wrapper.uint32At(zero, 0) == 0
    assert bytes_utils_wrapper.uint32At(empty, 0) == 0
    assert bytes_utils_wrapper.uint32At(max_value, 0) == 2 ** 32 - 1

    assert bytes_utils_wrapper.uint32At(long_word, 3) == 16


def test_uint256_at(bytes_utils_wrapper):
    one = "0x".ljust(65, "0") + "1"
    zero = "0x".ljust(66, "0")
    empty = "0x"
    max_value = "0x".ljust(66, "f")
    long_word = "0xaabbccdd".ljust(74, "f")

    assert bytes_utils_wrapper.uint256At(one, 0) == 1
    assert bytes_utils_wrapper.uint256At(zero, 0) == 0
    assert bytes_utils_wrapper.uint256At(empty, 0) == 0
    assert bytes_utils_wrapper.uint256At(max_value, 0) == 2 ** 256 - 1
    assert bytes_utils_wrapper.uint256At(long_word, 4) == 2 ** 256 - 1
