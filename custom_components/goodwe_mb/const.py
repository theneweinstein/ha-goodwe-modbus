"""Constants for integration_blueprint."""

from logging import Logger, getLogger

import probatio
from homeassistant.const import CONF_ADDRESS, CONF_PROTOCOL, CONF_SCAN_INTERVAL

LOGGER: Logger = getLogger(__package__)

DOMAIN = "goodwe_mb"
MANUFACTURER = "Goodwe"
ATTRIBUTION = "Data provided by http://jsonplaceholder.typicode.com/"
CONF_UNIT_ID = "unit_id"
SCAN_INTERVAL = 30
PROTOCOLS = ["tcp", "serial"]
STEP_USER_DATA_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_ADDRESS): str,
        probatio.Required(CONF_PROTOCOL): probatio.In(PROTOCOLS),
        probatio.Required(CONF_UNIT_ID): int,
        probatio.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): int,
    }
)
