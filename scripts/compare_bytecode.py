from brownie import web3

log_color_diff = "\x1b[6;30;42m"
log_color_default = "\x1b[0m"
bytes_per_line = 32
line_length = bytes_per_line * 2
format_line_length = max(line_length, 40)


def compare(orig_address, comparing_address):
    orig_code = web3.eth.get_code(orig_address).hex()[2:]
    comparing_code = web3.eth.get_code(comparing_address).hex()[2:]
    print(
        "          {0:<{2}}    {1:<{2}}\n".format(
            orig_address, comparing_address, format_line_length
        )
    )

    for i in range(max(len(orig_code), len(comparing_code)) // line_length + 1):
        code_line = orig_code[i * line_length : (i + 1) * line_length]
        comparing_code_line = comparing_code[i * line_length : (i + 1) * line_length]
        is_equal = code_line == comparing_code_line
        if is_equal:
            print(
                "{0:>5}     {1:<{4}} {2:<4} {3:<{4}}".format(
                    i, code_line, "", comparing_code_line, format_line_length
                )
            )
        else:
            color_flag = False
            log_code = ""
            log_comparing_code = ""
            for byte_ind in range(bytes_per_line):
                orig_byte = code_line[byte_ind * 2 : (byte_ind + 1) * 2]
                comparing_byte = comparing_code_line[byte_ind * 2 : (byte_ind + 1) * 2]
                if orig_byte == comparing_byte and color_flag:
                    color_flag = False
                    log_code = log_code + log_color_default
                    log_comparing_code = log_comparing_code + log_color_default
                elif orig_byte != comparing_byte and not color_flag:
                    color_flag = True
                    log_code = log_code + log_color_diff
                    log_comparing_code = log_comparing_code + log_color_diff

                log_code = log_code + orig_byte
                log_comparing_code = log_comparing_code + co

            log_code = log_code + log_color_default
            log_comparing_code = log_comparing_code + log_color_default

            print(
                "{0:>5}     {1:<{4}} {2:<4} {3:<{4}}".format(
                    i, log_code, "neq", log_comparing_code, format_line_length
                )
            )
    print(
        f"\n\nBytecode at addresses {orig_address} and {comparing_address} is {'NOT' if orig_code != comparing_code else ''} equal\n\n"
    )
