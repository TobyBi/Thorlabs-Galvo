def replace_any_bit(val: int, pos: int, new_bit: int) -> int:
    """Replace bit at position (starting at 0) with new bit.

    Parameters
    ----------
    val : int
        Integer to have bit replaced.
    pos : int
        Position to replace starting at 0 from LSB (right).
    new_bit : int
        0 or 1.

    Returns
    -------
    replaced : int
        Integer with changed bit.

    Examples
    --------
    >>> replace_any_bit(10, 2, 0)
    8
    """
    part1 = val & (~1 << pos)       # replaces bit at pos with 0
    part2 = new_bit << pos          # shifts new_bit to pos
    replaced = part1 | part2             # replaces 0 with new_bit at pos
    return replaced

def binary_coarsen(val: int, coarsen: int) -> int:
    """Coarsen binary value by any integer amount and set to middle bit.

    Parameters
    ----------
    val : int
        Integer to coarsen, unsigned.
    coarsen : int
        Bit value to coarsen by.

    Returns
    -------
    val : int
        Coarsened value.

    Examples
    --------
    >>> binary_coarsen(192830999, 4)
    192831000
    """
    if coarsen == 4:
        # special case to coarsen by 4 for speediness
        coarsened = ((val >> 4) << 4) | 8     # 8 is "1000" in binary
    else:
        for k in range(coarsen):
            if k < (coarsen - 1):
                # replace every LSB from coarsen amount by 0
                coarsened = replace_any_bit(val, k, 0)    
            else:
                # replace coarsen amount pos by 1
                coarsened = replace_any_bit(val, k, 1)    

    return coarsened

# def binary_coarsen_4bits(val):
#     """
#     Coarsen binary value by 4 bits and set to the middle bit

#     Parameters
#     ----------
#     val : int
#         Int to coarsen

#     Returns
#     -------
#     ans : int
#         val coarsened by 4 bits 
#     """
#     ans = ((val >> 4) << 4) | 8     # 8 is "1000" in binary
#     return ans