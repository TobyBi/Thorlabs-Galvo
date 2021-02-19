import numpy as np

# Voltage range of the DAC
DAC_RANGE =         [0, 5]
# Resolution of DAC voltage range in bits
DAC_BITS =          12
# Number of bits Labjack DAC can be set to
DAC_SET_BITS =      16
# DAC voltage steps
VOLTAGE_LEVELS =    np.linspace(
    DAC_RANGE[0], DAC_RANGE[1], num=2**DAC_BITS, endpoint=True
    )
# Converts positions to μm
POSITION_UNIT_PREFIX = 1e6
# Full length range of DAC in m
CALIBRATION = {
    "x": 12.37e-3, # 12.684e-3 for other galvo 2021.01.19
    "z": 12.5e-3   # 13.24e-3 for other galvo 2021.01.19
}
# Provides "slope" and "intercept" in voltage = slope*pos + intercept for both
# axes
POSITION_TO_VOLTAGE = {
    "x": {
        "slope": (
            -(DAC_RANGE[1] - DAC_RANGE[0])
            / CALIBRATION["x"] 
            / POSITION_UNIT_PREFIX),
        "intercept": DAC_RANGE[1]
    },
    "z": {
        "slope": (
            (DAC_RANGE[1] - DAC_RANGE[0])
            /CALIBRATION["z"]
            /POSITION_UNIT_PREFIX),
        "intercept": DAC_RANGE[1]/2
    }
}
# The calibration is assuming that the origin can be set at exactly the centre 
# of the rod in the z direction. We cannot so this is a correction to set the 
# height 
#                  ---------------------------------------------
#                  |
#                  |
#                  |
#                  | <- z=0 should be here
#                  | <- but it's most likely here
#                  |
#                  |
#                  ---------------------------------------------
# Alters the equation to:
#   voltage = slope * (pos + correction) + intercept
POSITION_CENTRE_CORRECTION = {
    "x": 0 / POSITION_UNIT_PREFIX, 
    "z": 0 / POSITION_UNIT_PREFIX
    }

class Point():
    def __init__(self, axis: str, pos : float=None, voltage: float=None):
        """
        A single axis point in space representing beam position directed by Galvo.

        Parameters
        ----------
        axis : str
            Dimension of the point, related to the Galvo axis.
        pos : float, optional
            Absolute position of the point in μm, by default None.
        voltage : float, optional
            Absolute voltage of the point in Volts, by default None.

        Raises
        ------
        ValueError
            Axis/coordinate has to be either "x" or "z".
            Must have at least either an input position or voltage.

        Examples
        --------
        >>> p = Point("x", pos=1400)
        >>> print(p.pos)
        1399.9999999999998
        >>> print(p.bit)
        58120
        >>> print(p.voltage)
        4.434114793856104

        Notes
        -----
        Implementation of a Point in only a single dimension because Points in 
        one dimension DOES NOT interact with another dimension except when 
        moving the Galvo mirror diagonally (in two dimensions at once).

        TODO: handle different speeds.
        """
        if axis not in ["x", "z"]:
            raise ValueError("Axis should be 'x' or 'z'.")
        if pos == None and voltage == None:
            raise ValueError("Either pos or voltage should not be None.")

        self._axis = axis

        if pos != None:
            self._pos = self._position_limits(pos)
            # converting position to voltage
            self._voltage = self.pos_to_volt(self._axis, self._pos)
        elif voltage != None:
            self._voltage = self._voltage_limits(voltage)
            # converting voltage to position
            self._pos = self.volt_to_pos(self._axis, self._voltage)

    def __add__(self, other_point):
        """Adds two Points, position and voltage, from the same axis."""
        if self._axis != other_point._axis:
            raise ValueError("Adding two points in different axes.")
        new_pos = self.pos + other_point.pos
        return Point(self._axis, pos=new_pos)

    def __sub__(self, other_point):
        """Substracts two Points, position and voltage, from the same axis."""
        if self._axis != other_point._axis:
            raise ValueError("Subtracting two points from different axes.")
        new_pos = self.pos - other_point.pos
        return Point(self._axis, pos=new_pos)

    @property
    def pos(self) -> float:
        """Return position of point in μm."""
        return self._pos

    @property
    def voltage(self) -> float:
        """Return voltage of point in Volts."""
        return self._voltage

    @property
    def bit(self) -> int:
        """
        Return the closest bit corresponding to the closest position.

        Returns
        -------
        middle_bit : int
            Bit corresponding to closest voltage/position to input.

        Notes
        -----
        Finding closest bit from voltage with 12 bits of resolution, then 
        increasing the resolution to 16 bits to coarsen by 4 bits before 
        finding the middle bit.
        """
        # closest bit from voltage in 12bit levels, upshifted to 16bit
        closest_bit = abs(VOLTAGE_LEVELS - self.voltage).argmin() << (DAC_SET_BITS - DAC_BITS)
        # coarsening by 4 bits, and setting to the middle step
        middle_bit = self._binary_coarsen(closest_bit, DAC_SET_BITS - DAC_BITS)
        return middle_bit

    @staticmethod
    def volt_to_pos(axis: str, volt: float) -> float:
        """Return voltage to position conversion."""
        new_pos = (
            (volt -  POSITION_TO_VOLTAGE[axis]["intercept"]) 
            / POSITION_TO_VOLTAGE[axis]["slope"]
            )
        return new_pos

    @staticmethod
    def pos_to_volt(axis: str, pos: float) -> float:
        """Return position to voltage conversion."""
        new_volt = (
            POSITION_TO_VOLTAGE[axis]["slope"]
            *(pos + POSITION_CENTRE_CORRECTION[axis])
            + POSITION_TO_VOLTAGE[axis]["intercept"]
            )
        return new_volt

    @staticmethod
    def _voltage_limits(volt: float) -> float:
        """Return voltages within DAC range limits."""
        if volt < min(DAC_RANGE):
            return min(DAC_RANGE)
        elif volt > max(DAC_RANGE):
            return max(DAC_RANGE)
        else:
            return volt

    def _position_limits(self, pos: float) -> float:
        """Return positions within allowed DAC voltage range."""
        set_voltage = self.pos_to_volt(self._axis, pos)
        set_voltage = self._voltage_limits(set_voltage)

        set_pos = self.volt_to_pos(self._axis, set_voltage)
        return set_pos

    @staticmethod
    def _replace_any_bit(val: int, pos: int, new_bit: int) -> int:
        """Replace bit at position (starting at 0) with new bit.

        Helper function for Point._binary_coarsen

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
        >>> Point._replace_any_bit(10, 2, 0)
        8
        """
        part1 = val & (~1 << pos)       # replaces bit at pos with 0
        part2 = new_bit << pos          # shifts new_bit to pos
        replaced = part1 | part2        # replaces 0 with new_bit at pos
        return replaced

    @staticmethod
    def _binary_coarsen(val: int, coarsen: int) -> int:
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
        >>> Point._binary_coarsen(192830999, 4)
        192831000
        """
        if coarsen == 4:
            # special case to coarsen by 4 for speediness
            # 8 is "1000" in binary
            coarsened = ((val >> 4) << 4) | 8     
        else:
            for k in range(coarsen):
                if k < (coarsen - 1):
                    # replace every LSB from coarsen amount by 0
                    coarsened = self._replace_any_bit(val, k, 0)  
                else:
                    # replace coarsen amount pos by 1
                    coarsened = self._replace_any_bit(val, k, 1)
        return coarsened
