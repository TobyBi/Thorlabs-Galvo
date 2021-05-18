from galvo import *

def saturation_test_point():
    p = Point("x", 0)
    print(p.pos)
    print(p.pos_comp)
    print(p.voltage)
    print(p.bit)
    print("")

    p = Point("x", 100000)
    print(p.pos)
    print(p.pos_comp)
    print(p.voltage)
    print(p.bit)
    print("")

    p = Point("x", voltage=5)
    print(p.pos)
    print(p.pos_comp)
    print(p.voltage)
    print(p.bit)
    print("")

    p = Point("x", voltage=0)
    print(p.pos)
    print(p.pos_comp)
    print(p.voltage)
    print(p.bit)
    print("")

def sat_test_galvo():
    driver = GalvoDriver('x', "DAC0", pos_init=0, daq=False)


def general_test():
    driver = GalvoDriver('x', "DAC0", pos_init=0, daq=False)

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
        daq=False
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

if __name__ == '__main__':
    driver = GalvoDriver('x', "DAC0", pos_init=0, daq=False)