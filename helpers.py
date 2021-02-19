def replace_any_bit(val, pos, new_bit):
    """
    Replace bit at position (starting at 0) with new bit in given value

    Parameters
    ----------
    val : int
        Int to have bit replaced
    pos : int
        Position to replace starting at 0 from LSB (right)
    new_bit : int
        0 or 1

    Returns
    -------
    ans : int
        result
    """
    part1 = (val & (~1 << pos))     # replaces bit at pos with 0
    part2 = (new_bit << pos)        # shifts new_bit to pos
    ans = part1 | part2             # replaces 0 with new_bit at pos
    return ans

def binary_coarsen(val, coarsen):
    """
    Coarsen binary value by any integer amount.

    Parameters
    ----------
    val : int
        Int to coarsen, unsigned
    coarsen : int
        bit value to coarsen by

    Returns
    -------
    val : int
        final value
    """
    if coarsen == 4:
        val = binary_coarsen_4bits(val)
    else:
        for k in range(coarsen):
            if k < (coarsen - 1):
                val = replace_any_bit(val, k, 0)    # replace every LSB from coarsen amount by 0
            else:
                val = replace_any_bit(val, k, 1)    # replace coarsen amount pos by 1

    return val

def binary_coarsen_4bits(val):
    """
    Coarsen binary value by 4 bits and set to the middle bit

    Parameters
    ----------
    val : int
        Int to coarsen

    Returns
    -------
    ans : int
        val coarsened by 4 bits 
    """
    ans = ((val >> 4) << 4) | 8     # 8 is "1000" in binary
    return ans