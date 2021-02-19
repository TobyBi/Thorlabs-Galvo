import numpy as np

from helpers import binary_coarsen

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
            self._voltage = self.pos_to_volt(self._pos)
        elif voltage != None:
            self._voltage = self._voltage_limits(voltage)
            # converting voltage to position
            self._pos = self.volt_to_pos(self._voltage)

    def __add__(self, other_point: Point):
        """Adds two Points, position and voltage, from the same axis."""
        if self._axis != other_point._axis:
            raise ValueError("Adding two points in different axes.")
        new_pos = self.pos + other_point.pos
        return Point(self._axis, pos=new_pos)

    def __sub__(self, other_point: Point):
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
        middle_bit = binary_coarsen(closest_bit, DAC_SET_BITS - DAC_BITS)
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
        set_voltage = pos_to_volt(pos)
        set_voltage = self.voltage_limits(self._axis, set_voltage)

        set_pos = self.volt_to_pos(self._axis, set_voltage)
        return set_pos

if __name__ == "__main__":
    # testing instantiation 
    pnt1 = Point("x", 0)
    print(pnt1.pos, pnt1.voltage, pnt1.bit)

    pnt2 = Point("z", -1000)
    print(pnt2.pos, pnt2.voltage, pnt2.bit)

    # testing adding different axes
    try:
        pnt1 + pnt2
    except Exception as e:
        print(e)

    # testing adding
    pnt3 = Point("x", 1300)
    pnt4 = pnt1 + pnt3
    print(pnt4.pos, pnt4.voltage, pnt4.bit)

    # testing adding out of range
    pnt5 = pnt1 + Point("x", 14000)
    print(pnt5.pos, pnt5.voltage, pnt5.bit)
