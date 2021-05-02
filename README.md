# Thorlabs Galvo Systems

Wrapper to control Thorlabs [Galvo Systems](https://www.thorlabs.de/newgrouppage9.cfm?objectgroup_id=6057) with a DAC. Currently, only LabJack [T-series DAQs](https://labjack.com/products/t7) are supported but feel free to add others.

## Requirements

- Python >= 3.8.5
- numpy >= 1.19.5
- [OPTIONAL] If using `Thorlabs-Galvo` with a LabJack, then the `LabJack-DAQ` module is required. Please visit the [repository](https://github.com/TobyBi/LabJack-DAQ) for further installation guidelines.

Only written and tested with LabJack DAQ control and Thorlabs GVS112/M Galvo Systems.

## Installation and Usage

To install simply clone the git directory using the following commands:

```bash
git clone https://github.com/TobyBi/Thorlabs-Galvo
```

Import it to use.
