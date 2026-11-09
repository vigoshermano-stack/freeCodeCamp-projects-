"""Thermocouple reading via the MAX31855 with fault handling.

On hardware this uses the adafruit_max31855 driver over SPI. The read
function raises on any open/short fault so the control loop can trigger
an emergency shutdown instead of running blind.
"""


class ThermocoupleFault(Exception):
    """Raised when the thermocouple reports an open or short circuit."""


class MAX31855Sensor:
    def __init__(self, driver):
        """driver is an object exposing a .temperature property in Celsius."""
        self._driver = driver

    def read_celsius(self):
        try:
            return self._driver.temperature
        except RuntimeError as exc:  # open/short detected by the driver
            raise ThermocoupleFault(str(exc)) from exc


def build_hardware_sensor(cs_pin):
    """Factory for the real Raspberry Pi sensor (imported lazily)."""
    import board
    import digitalio
    import adafruit_max31855

    spi = board.SPI()
    cs = digitalio.DigitalInOut(cs_pin)
    driver = adafruit_max31855.MAX31855(spi, cs)
    return MAX31855Sensor(driver)
