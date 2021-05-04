# Thorlabs Galvo Systems

Wrapper to control Thorlabs [Galvo Systems](https://www.thorlabs.de/newgrouppage9.cfm?objectgroup_id=6057) with a DAC. Currently, only LabJack [T-series DAQs](https://labjack.com/products/t7) are supported but feel free to add others.



## Requirements

- Python >= 3.8.5
- numpy >= 1.19.5
- [OPTIONAL] If using `Thorlabs-Galvo` with a LabJack, then the `LabJack-DAQ` module is required. Please visit the [repository](https://github.com/TobyBi/LabJack-DAQ) for further installation guidelines.

Only written and tested with LabJack DAQ control and Thorlabs GVS112/M Galvo Systems.



## Installation

To install simply clone the git directory using the following commands:

```bash
git clone https://github.com/TobyBi/Thorlabs-Galvo
```

Move the `galvo` file into your working directory and import to use!



## Usage

For either single or multiple Galvo Drivers,  the main functions to interact with are

- `reset_origin` to reset the origin back to axis origin,
- `set_origin` to set the origin to a position offset from the axis origin,
- `reset_pos` which resets the position to the origin (not the axis origin), and
- `go_to` to set the position relative to the current origin at a set speed, the speed is the same for both axes.



While moving the mirrors using the galvo, the absolute position, relative position, and origin are obtained using

- `pos`,
- `rel_pos`, and
- `origin`, respectively.



More details are given in the [documentation](https://tobybi.github.io/Thorlabs-Galvo/galvo.html).



## Changing Galvo constants

### DAC Output

Currently, the output range of DAC is from 0 to 5V and is found in the constant variable `DAC_RANGE` in the `galvo.py` file.

```python
# Voltage range of the DAC
DAC_RANGE = [0, 5]
```

If this changes, adjust it accordingly.



### Galvo Calibration

When changing the Thorlabs Galvo system, the voltage and position conversion must be recalibrated.

Firstly, send the minimum and maximum voltage range to the Galvo and measure the distance between the two (or more) shots.

Next, the constant conversion constants must be changed. To change them, search for the variable `CALIBRATION`

```python
# Full length range of DAC in m
CALIBRATION = {
    "x": 12.37e-3,
    "z": 12.5e-3
}
```

and adjust the values.



Currently, the axis +ve and -ve directions are set via the `"slope"` key and the starting origin via the `"intercept"` key in the `POSITION_TO_VOLTAGE` dictionary.

```python
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
```



Another calibration is to centre the rod and laser beam in the z-axis. Either change the height of the spindle translation stage or adjust the `POSITION_CENTRE_CORRECTION`  variable.

```python
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
```



For reference the equation for conversion from position to voltage is

```python
voltage = POSITION_TO_VOLTAGE["x"]["slope"]*(pos + POSITION_CENTRE_CORRECTION) + POSITION_TO_VOLTAGE["x"]["intercept"]
```

