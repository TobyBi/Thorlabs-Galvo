"""
.. include:: ./README.md
"""

import warnings
import time
from copy import deepcopy

import numpy as np

SCALING = [0.5, 0.8, 1]

class GalvoDriver:
    """
    Interface to Thorlabs galvo driver controlling a single axis mirror

    Currently only supports use with LabJack.

    Parameters
    ----------
    axis : str
        Axis that the Galvo driver is controlling. Either "x" or "z"
    dac_name : str
        DAC output register name for LabJack
    pos_init : float, optional
        Initial position to set the mirror in microns
    open_labjack : bool, optional
        [description], by default False

    === UNUSED ===
    V_per_deg : float, optional
        Input voltage per degree moved. Controlled by the JP7 pin on the board (Fig 3.13 in the manual).
        The default is 0.5 but other valid options are 1  or 0.8
    beam_diameter : int or float, optional
        The input beam diameter in millimetres. The default is 8.

    TODO: add a logger?
    TODO: limiting inputs
    TODO: Public and private attribute for self.axis where I only write a @property so can only read self.axis and not write
    """
    def __init__(self, axis, dac_name, pos_init=0, open_labjack=False):
        """Inits a GalvoDriver object."""
        # if V_per_deg not in SCALING:
        #     raise ValueError("{0} is not a valid volts / degree scaling option must be in {1}.".format(
        #         V_per_deg, SCALING))

        if axis not in ["x", "z"]:
            raise ValueError("axis should be either 'x' (parallel to surface of rod) or 'z' (radially away from rod)")

         # axis of the galvo mirror the driver is controlling
        self.axis = axis                   
        self.dac_name = dac_name
        # volts / degree scaling set on the GalvoDriver card, converted to radians
        # self.scaling = V_per_deg * 180 / np.pi

        self.open_labjack = open_labjack

        # must initialise for point adding later
        self.__point = Point(self.axis, pos_init)
        self._point_history = [Point(self.axis, pos_init)]

        self.set_origin(pos_init)
        self.go_to(pos_init, 0)

    @property
    def pos(self) -> float:
        """Return the absolute position of the Galvo mirror in μm."""
        return self._pos

    @property
    def rel_pos(self) -> float:
        """Return the relative position to the origin in μm."""
        return self._rel_point.pos

    @property
    def pos_history(self) -> list:
        """Return the history of absolute positions in μm."""
        return [pnt.pos for pnt in self._point_history]

    def reset_pos(self):
        """Immediately reset position to origin."""
        self.go_to(0, 0)

    @property
    def origin(self) -> float:
        """Return the origin of galvo mirror in μm."""
        return self._origin.pos

    def set_origin(self, orig: float=None):
        """
        Set the origin of galvo mirror given a position in μm.

        The origin is set to absolute 0 μm if no arguments are passed.

        Parameters
        ----------
        orig : float
            Position in μm, by default None which sets the origin to 0 μm.

        Notes
        -----
        Not using setter decorators as using dictionary argument inputs is not
        aesthetically pleasing
        """
        if orig is None:
            self._origin = self._point
        else:
            self._origin = Point(self.axis, orig)

    def reset_origin(self):
        """Reset the origin to 0 μm without changing position."""
        self.set_origin(0)

    def go_to(self, new_pos: float, speed: float):
        """
        Go to relative position in μm from current position at μm/s.

        If speed > 0 μm/s then streams the position.

        Parameters
        ----------
        new_pos : float
            New position from origin in μm.
        speed : float
            Speed in μm/s.

        Returns
        -------
        tuple
            1 - position in μm of the mirror, calculated from reading the DAC.
            2 - time in s of movement given by the streaming statistics.

        Raises
        ------
        KeyboardInterrupt
            Moving stopped by user.
        """
        new_pos = new_pos + self.origin

        # move contains all bits between the two position
        move = Move(self.axis, self.pos, new_pos, speed)

        # movement with labjack, for other DAQs write another conditional
        if self.open_labjack:
            with self.open_labjack:
                # second condition of move.t == 0 is used when pos_init and pos_final are the same
                # but speed > 0 resulting in trying to stream when you can't
                if speed == 0 or move.t == 0:
                    # Updating DAC#_BINARY with bit of closest position
                    actual_t = 0
                    actual_V = self.open_labjack.updater.update(move.bits[-1])
                else:
                    self.open_labjack.streamer.stream_setup()
                    self.open_labjack.streamer.load_data(move.bits, "int")
                    actual_t = self.open_labjack.streamer.start_stream(move.t)
                    actual_V = self.open_labjack.updater.read()

            # reads the position (transformed from the voltage) where the mirror
            # is stopped
            # Also, within Streamer.start_stream sleeping occurs that blocks/holds execution
            # until the full stream has occurred, only then is the KeyboardInterrupt signal
            # handled
            # TODO: run laser and this on separate stream to be able to shutdown one immediately
            try:
                actual_V
            except NameError:
                # using new_pos because the stream is blocked until it's finished
                self._pos = new_pos
                actual_point = Point(self.axis, new_pos)
            else:
                actual_point = Point(self.axis, voltage=actual_V[self.dac_name])

            try:
                actual_t
            except NameError:
                actual_t = move.t

            # TODO: Might need to raise KeyboardInterrupt here?
        else:
            self._pos = new_pos
            actual_t = 0
            actual_point = Point(self.axis, self.pos)

        return actual_point.pos, actual_t

        # if self.open_labjack:
            # try:
            #     # second condition of move.t == 0 is used when pos_init and pos_final are the same
            #     # but speed > 0 resulting in trying to stream when you can't
            #     if speed == 0 or move.t == 0:
            #         # Updating DAC#_BINARY with bit of closest position
            #         actual_t = 0
            #         actual_V = self.open_labjack.updater.update(move.bits[-1])
            #     else:
            #         # Streaming bits between current position to new position
            #         self.open_labjack.streamer.stream_setup()
            #         self.open_labjack.streamer.load_data(move.bits, "int")
            #         actual_t = self.open_labjack.streamer.start_stream(move.t)
            #         actual_V = self.open_labjack.updater.read()
            # except KeyboardInterrupt:
            #     # reads the position (transformed from the voltage) where the mirror
            #     # is stopped
            #     # Also, within Streamer.start_stream sleeping occurs that blocks/holds execution
            #     # until the full stream has occurred, only then is the KeyboardInterrupt signal
            #     # handled
            #     # TODO: run laser and this on separate stream to be able to shutdown one immediately
            #     # TODO: context handler for lase
            #     # self.open_labjack.streamer.stop_stream()
            #     try:
            #         actual_V
            #     except NameError:
            #         actual_V = self.open_labjack.updater.read()

            #     try:
            #         actual_t
            #     except NameError:
            #         actual_t = move.t
            #     # using the stopped voltage to set the galvo position, even though this is the same
            #     # as new_pos as streaming is blocked until it finishes
            #     self._voltage = actual_V[self.dac_name]
            #     print("Stopping at {0} = {1}um!".format(self.axis, self.pos))
            #     # need to raise KeyboardInterrupt so that calling program above the stack can
            #     # also stop other processes
            #     raise KeyboardInterrupt("Moving stopped by user!")
            # else:
            #     # directly set private _pos attribute because method converts pos float to Point obj
            #     self._pos = new_pos
            # finally:
            #     actual_point = Point(self.axis, voltage=actual_V[self.dac_name])
        # else:
        #     self._pos = new_pos
        #     actual_t = 0
        #     actual_point = Point(self.axis, self.pos)

        # return actual_point.pos, actual_t

    #=======================================================
    # PRIVATE METHODS
    #=======================================================

    @property
    def _rel_point(self):
        """Return Point object relative to the origin."""
        return self._point - self._origin

    @property
    def _point(self):
        """Return absolute Point object."""
        return self.__point

    @_point.setter
    def _point(self, val):
        """Set the Point object where ``val`` should be a Point object."""
        self._point_history.append(deepcopy(self._point))
        self.__point = val

    @property
    def _pos(self):
        """Return absolute position in μm."""
        return self._point.pos

    @_pos.setter
    def _pos(self, val: float):
        """Set absolute position in μm."""
        self._point = Point(self.axis, val)

    @property
    def _voltage(self):
        """Return absolute voltage in V."""
        return self._point.voltage

    @_voltage.setter
    def _voltage(self, val: float):
        """Set absolute voltage in V."""
        self._point = Point(self.axis, voltage=val)

    def _revert_pos(self):
        """
        Revert to the most recent position, without sending command to DAQ

        UNUSED
        """
        temp_point = deepcopy(self._point)
        self._point = deepcopy(self._point_history[-1])
        self._point_history.append(temp_point)


class GalvoDrivers:
    """
    Combines multiple Thorlabs galvo drivers to simultaneously control them.

    Only supports use with LabJack.

    Parameters
    ----------
    axis : iterable of str
        Multiple axes of Galvo drivers to control simultaneously
    dac_name : dict
        Dict of DAC output register names for LabJack for each axis
    pos_init : dict
        Dict of initial positions to set the mirror of each axis in microns
    open_labjack : bool, optional
        LabJack object if it is connected physically, by default False.
        Make sure to add Updater and Streamer to LabJack object that have matching
        input and output registers

    Raises
    ------
    KeyError
        dac_name dict keys doesn't match the input axis
    KeyError
        pos_init dict keys doesn't match the input axis
    """
    def __init__(self, axis, dac_name: dict, pos_init: dict, open_labjack=False):
        """Inits a GalvoDrivers object."""
        self.axis = axis

        for ax in self.axis:
            try:
                dac_name[ax]
            except KeyError:
                raise KeyError("Input dac_name axes is missing '{0}'-axis".format(ax))

            try:
                pos_init[ax]
            except KeyError:
                raise KeyError("Input pos_init axes is missing '{0}'-axis".format(ax))

        self.dac_name = dac_name
        self.open_labjack = open_labjack

        self._galvos = {}
        for ax in self.axis:
            # using the Galvo objects for the axes as storage for points rather than
            # sending labjack/DAQ commands through them
            self._galvos[ax] = GalvoDriver(ax, self.dac_name[ax], pos_init=pos_init[ax], open_labjack=False)

        self.go_to(**pos_init, speed=0)

    @property
    def pos(self) -> dict:
        """Return absolute positions for all stored 1D galvos in μm."""
        _pos = {}
        for ax in self.axis:
            _pos[ax] = self._galvos[ax].pos
        return _pos

    @property
    def rel_pos(self) -> dict:
        """Return relative positions for all stored 1D galvos in μm."""
        _rel_pos = {}
        for ax in self.axis:
            _rel_pos[ax] = self._galvos[ax].rel_pos
        return _rel_pos

    @property
    def pos_history(self) -> dict:
        """Return absolute position history for all stored 1D galvos."""
        _pos_history = {}
        for ax in self.axis:
            _pos_history[ax] = self._galvos[ax].pos_history
        return _pos_history

    def reset_pos(self):
        """Reset the relative positions of all stored 1D galvos to 0 μm."""
        rst_pos = {}
        for ax in self.axis:
            rst_pos[ax] = 0

        self.go_to(speed=0, **rst_pos)

    @property
    def origin(self) -> dict:
        """Return origin for all stored 1D galvos in μm."""
        _origin = {}
        for ax in self.axis:
            _origin[ax] = (self._galvos[ax].origin)
        return _origin

    def set_origin(self, **orig):
        """
        Set the origin of all stored 1D Galvos in μm.

        Named arguments have the form ``{axis_name: origin}``.

        Parameters
        ----------
        orig : optional, {axis_name: origin}
            Origin in μm for each galvo axis.
        """
        for ax in self.axis:
            if not orig:
                self._galvos[ax].set_origin()
            else:
                try:
                    self._galvos[ax].set_origin(orig[ax])
                except KeyError:
                    print("Axis '{0}' not found in input choices, it remains unchanged")

    def reset_origin(self):
        """Set the origin of all stored 1D galvos to 0 μm."""
        for ax in self.axis:
            self._galvos[ax].set_origin(0)

    def go_to(self, speed: float=0, **new_pos) -> tuple:
        """
        Go to input relative positions in μm input speed in μm/s for all axes.

        Input speed is the same for each axis. For example with 2 axes, if one
        axis is moving a larger distance, then the other axis will finish
        before the longer distance is finished.

        If speed > 0 μm/s then labjack streams.

        Parameters
        ----------
        speed : float, optional
            Speed in μm/s, by default 0 μm/s.
        new_pos : optional, {axis_name: new_pos}
            New position from origin in μm, by default no movement for given
            axis.

        Returns
        -------
        tuple
            1 - a dict, with the actual position of all 1D galvos,
            2 - the actual time of movement in s given by the DAQ.

        Raises
        ------
        KeyboardInterrupt
            Moving stopped by user.
        """
        # use stored 1D galvos to calculate the new absolute position for each axis
        original_pos = self.pos
        new_abs_pos = {}
        for ax in self.axis:
            new_abs_pos[ax] = self._galvos[ax].go_to(new_pos[ax], speed)[0]

        move = MoveMultiDim(self.axis, original_pos, new_abs_pos, speed)

        if self.open_labjack:
            with self.open_labjack:
                if speed == 0 or move.t == 0:
                    # Updater wants a tuple of values matching the number of write registers
                    move_bits = tuple([mb[-1] for mb in tuple(move.bits.values())])
                    actual_t = 0
                    actual_V = self.open_labjack.updater.update(move_bits)
                else:
                    # movement bits for each axis
                    move_bits = tuple(move.bits.values())
                    self.open_labjack.streamer.stream_setup()
                    self.open_labjack.streamer.load_data(move_bits, "int")
                    actual_t = self.open_labjack.streamer.start_stream(move.t)
                    actual_V = self.open_labjack.updater.read()

            try:
                actual_V
            except NameError:
                # stored galvos already have their positions set to the new position
                actual_V = self.open_labjack.updater.read()
                stopped_pos = []
                for ax in self.axis:
                    self._galvos[ax].voltage = actual_V[self._galvos[ax].dac_name]
                    stopped_pos.append(str(self._galvos[ax].pos))
            finally:
                actual_pos = {}
                for ax in self.axis:
                    actual_pos[ax] = Point(ax, voltage=actual_V[self._galvos[ax].dac_name]).pos

            try:
                actual_t
            except NameError:
                actual_t = move.t

            # TODO: Might need to raise KeyboardInterrupt here?
        else:
            # no connected DAQs
            actual_t = 0
            actual_pos = {}
            for ax in self.axis:
                actual_pos[ax] = Point(ax, new_pos[ax]).pos

        return actual_pos, actual_t

        # if self.open_labjack:
        #     try:
        #         # this part is the same as a single galvo axis except it assumes that
        #         # the Labjack updater and streamer have the same number of registers
        #         # as the number of move bits
        #         if speed == 0 or move.t == 0:
        #             # Updater wants a tuple of values matching the number of write registers
        #             move_bits = tuple([mb[-1] for mb in tuple(move.bits.values())])
        #             actual_t = 0
        #             actual_V = self.open_labjack.updater.update(move_bits)
        #         else:
        #             # movement bits for each axis
        #             move_bits = tuple(move.bits.values())
        #             self.open_labjack.streamer.stream_setup()
        #             self.open_labjack.streamer.load_data(move_bits, "int")
        #             actual_t = self.open_labjack.streamer.start_stream(move.t)
        #             actual_V = self.open_labjack.updater.read()
        #     except KeyboardInterrupt:
        #         # self.open_labjack.streamer.stop_stream() KeyboardInterrupt in Streamer handles this
        #         try:
        #             actual_V
        #         except NameError:
        #             actual_V = self.open_labjack.updater.read()

        #         try:
        #             actual_t
        #         except NameError:
        #             actual_t = move.t

        #         # setting the stored 1D galvos to the stopped positions
        #         stopped_pos = []
        #         for ax in self.axis:
        #             self._galvos[ax].voltage = actual_V[self._galvos[ax].dac_name]
        #             stopped_pos.append(str(self._galvos[ax].pos))
        #         print("Stopping at ({0}) = ({1})um".format(", ".join(self.axis), ", ".join(stopped_pos)))
        #         # need to raise KeyboardInterrupt so that calling program above the stack can
        #         # also stop other processes
        #         raise KeyboardInterrupt("Moving stopped by user!")
        #     finally:
        #         actual_pos = {}
        #         for ax in self.axis:
        #             actual_pos[ax] = Point(ax, voltage=actual_V[self._galvos[ax].dac_name]).pos

        # else:
        #     # no connected DAQs
        #     actual_t = 0
        #     actual_pos = {}
        #     for ax in self.axis:
        #         actual_pos[ax] = Point(ax, new_pos[ax]).pos

        # return actual_pos, actual_t


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
    def __init__(self, axis: str, pos : float=None, voltage: float=None):
        """Inits a Point object."""
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
                    coarsened = Point._replace_any_bit(val, k, 0)
                else:
                    # replace coarsen amount pos by 1
                    coarsened = Point._replace_any_bit(val, k, 1)
        return coarsened

if __name__ == '__main__':
    driver = GalvoDriver('x', "DAC0", pos_init=0, open_labjack=False)

    for pos in [-1, 6, 2000, 12300, 1500, 900]:
        driver.go_to(pos, 0)
        print(driver.pos)
        print(driver.pos_history)

    driver.set_origin(900)
    print(driver.rel_pos)

    driver.go_to(100, 10)
    print(driver.pos)

    print("multi-drivers")

    drivers = GalvoDrivers(
        axis=("x", "z"),
        dac_name={"x": "DAC0", "z": "DAC1"},
        pos_init={"x": 0, "z": 0},
        open_labjack=False
    )

    drivers.go_to(x=100, z=300, speed=0)
    print(drivers.pos)
    print(drivers.pos_history)
    print(drivers.rel_pos)
    print(drivers.origin)

    drivers.set_origin(x=300, z=1000)
    print(drivers.pos)
    print(drivers.origin)

    drivers.go_to(x=1000, z=3000, speed=0)
    print(drivers.pos)
    print(drivers.origin)

    drivers.reset_pos()
    print(drivers.pos)
    print(drivers.origin)
