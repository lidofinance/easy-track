import pytest


@pytest.fixture(scope="session", params=range(4))
def bytes_24_at_testcases(request):
    short_word = "0x00112233445566778899aabbccddeeff"
    word = "0x00112233445566778899aabbccddeeff0102030405060708090a0b0c0d0f"
    return [
        # word too short start from zero position
        (short_word, 0, "0x00112233445566778899aabbccddeeff0000000000000000"),
        # word too short start from non zero position
        (short_word, 4, "0x445566778899aabbccddeeff000000000000000000000000"),
        # long word zero position
        (word, 0, "0x00112233445566778899aabbccddeeff0102030405060708"),
        # long word non zero position
        (word, 6, "0x66778899aabbccddeeff0102030405060708090a0b0c0d0f"),
    ][request.param]


@pytest.fixture(scope="session", params=range(2))
def address_at_testcases(owner, request):
    address = owner.address
    word_with_bytes = "0x00112233" + address[2:] + "ddeeff"
    return [(address, 0, address), (word_with_bytes, 4, address)][request.param]


@pytest.fixture(scope="session", params=range(5))
def uint32_at_testcases(owner, request):
    one = "0x00000001"
    zero = "0x00000000"
    empty = "0x"
    max_value = "0xffffffff"
    long_word = "0xffffff00000010eeee"

    return [
        (one, 0, 1),
        (zero, 0, 0),
        (empty, 0, 0),
        (max_value, 0, 2 ** 32 - 1),
        (long_word, 3, 16),
    ][request.param]


@pytest.fixture(scope="session", params=range(5))
def uint256_at_testcases(owner, request):
    one = "0x".ljust(65, "0") + "1"
    zero = "0x".ljust(66, "0")
    empty = "0x"
    max_value = "0x".ljust(66, "f")
    long_word = "0xaabbccdd".ljust(74, "f")

    return [
        (one, 0, 1),
        (zero, 0, 0),
        (empty, 0, 0),
        (max_value, 0, 2 ** 256 - 1),
        (long_word, 4, 2 ** 256 - 1),
    ][request.param]


def test_bytes24_at(bytes_utils_wrapper, bytes_24_at_testcases):
    source, location, result = bytes_24_at_testcases
    assert bytes_utils_wrapper.bytes24At(source, location) == result


def test_address_at(bytes_utils_wrapper, address_at_testcases):
    source, location, result = address_at_testcases
    assert bytes_utils_wrapper.addressAt(source, location) == result


def test_uint32_at(bytes_utils_wrapper, uint32_at_testcases):
    source, location, result = uint32_at_testcases
    assert bytes_utils_wrapper.uint32At(source, location) == result


def test_uint256_at(bytes_utils_wrapper, uint256_at_testcases):
    source, location, result = uint256_at_testcases
    assert bytes_utils_wrapper.uint256At(source, location) == result
