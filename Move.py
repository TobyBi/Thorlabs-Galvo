import numpy as np

try:
    from .Position import Point, DAC_SET_BITS
except ImportError:
    from Position import Point, DAC_SET_BITS

# Maximum movement speed in μm/s
MAX_SPEED = 10e3

class Move():
    """
    Determines a sequence of bits between two points in space given an
    initial and final position.

    Also determines the time in seconds required to step through the bit
    sequence.

    Parameters
    ----------
    axis : str
        Coordinate or axis of movement.
    pos_init : float
        Init position in μm.
    pos_final : float
        Final position in μm.
    speed : float
        Speed in μm/s.

    Attributes
    ----------
    t
    bits

    Examples
    --------
    >>> move = Move("x", 1000, 2000, 100)
    >>> move.t
    >>> move.bits
    """
    def __init__(
        self, axis: str, pos_init: float, pos_final: float, speed: float):
        """Inits a Move object."""
        self._axis = axis
        self._point_init = Point(axis, pos_init)
        self._point_final = Point(axis, pos_final)
        self._speed = speed

    @property
    def t(self) -> float:
        """Return movement time in seconds, if speed=0μm/s then t=0s."""
        try:
            _t = abs(self._point_init.pos - self._point_final.pos) / self._speed
        except ZeroDivisionError:
            _t = 0
        return _t

    @property
    def bits(self) -> np.array:
        """
        Return array of bits for every point between initial and final.

        Returns
        -------
        array of ints

        Notes
        -----
        If speed=0μm/s, return array of length 1.
        """
        if self._point_init.bit < self._point_final.bit:
            bin_steps = np.arange(
                self._point_init.bit, self._point_final.bit + 1, DAC_SET_BITS
                )
        else:
            # if point_init is greater than point_final, then switch np.arange
            # start and stop then reverse array
            bin_steps = np.arange(
                self._point_final.bit, self._point_init.bit + 1, DAC_SET_BITS
                )[::-1]
        return bin_steps

    @staticmethod
    def speed_limits(spd: float) -> float:
        """
        Limits an input speed (in μm/s) to between 0 and 10k μm/s.

        Parameters
        ----------
        spd : float
            Speed in μm/s.

        Returns
        -------
        float
        """
        if spd < 0:
            return 0
        elif spd > MAX_SPEED:
            return MAX_SPEED
        else:
            return spd

class MoveMultiDim():
    """
    Constant speed movement for multiple dimensions/axes.

    Parameters
    ----------
    axis : iterable
        Multiple axes for movement.
    pos_init : dict
        Initial positions in microns for all axes, where key-value is
        axis-position.
    pos_final : dict
        Final positions in microns for all axes, where key-value is
        axis-position.
    speed : float
        Speed in both axes in μm/s (not hypotenuse speed).

    Attributes
    ----------
    t
    bits

    Raises
    ------
    TypeError
        Input axis must be an iterable and not a string

    Examples
    --------
    >>> move = MoveMultiDim(["x", "z"], {"x": 0, "z": 0}, {"x": 3000, "z": 5000}, 1000)
    >>> move.t
    >>> move.bits
    """
    def __init__(self, axis, pos_init: dict, pos_final: dict, speed: float):
        """Inits a MoveMultiDim object."""
        try:
            if not isinstance(axis, str):
                iter(axis)
            else:
                raise TypeError
        except TypeError:
            raise TypeError("Argument axes must be an iterable and not a string")
        else:
            self._axis = axis
        self._speed = speed
        self._t = 0

        self._moves = {}
        for ax in self.axis:
            self._moves[ax] = Move(
                ax, pos_init[ax], pos_final[ax], self._speed
                )

            # set movement time to the longest time out of all axes
            if self._moves[ax].t > self._t:
                self._t = self._moves[ax].t

    @property
    def t(self) -> float:
        """Return longest time for movement for all axes in seconds."""
        return self._t

    @property
    def bits(self) -> dict:
        """Return bit array for all axes."""
        _bits = {}
        for ax in self.axis:
            _bits[ax] = self._moves[ax].bits
        return _bits


if __name__ == "__main__":
    m = Move("x", 0, 0, 100)
    print(len(m.bits), m.bits[0], m.bits[-1])
    print(m.bits)
    print(m.t)

    m2 = MoveMultiDim(["x", "z"], {"x": 0, "z": 0}, {"x": 3000, "z": 3000}, 500)
    m3 = list(m2.bits.values())
    print(m3)