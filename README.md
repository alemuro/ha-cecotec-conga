![GitHub](https://img.shields.io/github/license/alemuro/ha-cecotec-conga?style=flat-square)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/alemuro/ha-cecotec-conga?style=flat-square)
![GitHub Release Date](https://img.shields.io/github/release-date/alemuro/ha-cecotec-conga?style=flat-square)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=alemuro&repository=ha-cecotec-conga&category=integration)

# Cecotec Conga 5290 integration

This integration aims to manage Cecotec Conga 5290 vacuum cleaner which cannot be managed by [FreeConga](https://freecon.ga/) or [BadConga](https://github.com/adrigzr/badconga).

The author of this project categorically rejects any and all responsibility related to vacuums managed by this integration.

![integration screenshot](screenshot.jpg)

## HACS Installation

1. Navigate to `Settings > Devices & Services` and then click `Add Integration`
2. Search for `Cecotec Conga`
3. Enter your credentials

## Supported devices

This integration has been tested with the following vacuum cleaners:

| Model name | Supported?                                                    |
| ---------- | ------------------------------------------------------------- |
| Conga 5290 | ✅ Yes!                                                        |
| Conga 2290 | ❌ [No](https://github.com/alemuro/ha-cecotec-conga/issues/12) |
| Conga 3090 | ❌ [No](https://github.com/alemuro/ha-cecotec-conga/issues/19) |
| Conga 3690 | ❌ [No](https://github.com/alemuro/ha-cecotec-conga/issues/10) |
| Conga 4690 | ❌ [No](https://github.com/alemuro/ha-cecotec-conga/issues/13) |
| Conga 5090 | ❌ [No](https://github.com/alemuro/ha-cecotec-conga/issues/14) |
| Conga 6090 | ❌ [No](https://github.com/alemuro/ha-cecotec-conga/issues/9)  |


[Have you tested a different one and it works? Please tell us!](https://github.com/alemuro/ha-cecotec-conga/issues/new?assignees=&labels=&template=device-tested.md&title=%5BDEVICE-TESTED%5D)

## Supported functionalities

So far the following features have been implemented:
* `TURN_ON` - Enables the button to start the vacuum.
* `RETURN_HOME` (`TURN_OFF` does the same) - Enables the button to return the vacuum to home.
* `BATTERY` - Shows the status of the battery.
* `FAN_SPEED` - Allows changing the speed of the fan when the vacuum is cleaning.
* `SEND_COMMAND` - Allows sending custom commands, like setting water drop or starting a plan (in future releases).

A lot of ideas are in the backlog :) Do you have some idea? [Raise an issue!](https://github.com/alemuro/ha-cecotec-conga/issues/new?assignees=&labels=&template=feature_request.md&title=)

### Set water drop level

This can be set directly using the **Water Level** select entity (`select.<device_name>_water_level`) with options `Off`, `Low`, `Medium`, or `High`.

Alternatively, use the integration service or `vacuum.send_command`:

```yaml
service: cecotec_conga.set_water_level
target:
  entity_id: vacuum.conga
data:
  water_level: Medium
```

### Start plan

You can trigger cleaning plans directly by pressing the generated plan buttons (`button.<device_name>_start_<plan>`), or via the dedicated service:

```yaml
service: cecotec_conga.start_plan
target:
  entity_id: vacuum.conga
data:
  plan: Cuina
```

*(The `vacuum.send_command` service with `command: start_plan` continues to be supported for backwards compatibility).*

## Developers

### Running unit tests

Run unit tests locally using `pytest`:

```bash
uv run --with pytest --with pytest-asyncio pytest tests/ -v
```

### Local testing

If you already have a Conga, you can test communication with your device using `test.py`: 

1. Install dependencies through `pipenv`. Execute `pipenv install`.
2. Open virtualenv: `pipenv shell`.
3. Create a `.env` file with the variables `CONGA_USERNAME`, `CONGA_PASSWORD` and `CONGA_SN` (serial number). The serial number is retrieved by the script.
4. Execute `python test.py`.


There is a Makefile target to start a Docker container with this integration installed as a `custom_component`. Execute `make test-local`. This will create a local folder `.config`. To set debugging mode add this to `.config/configuration.yaml` file:

```
logger:
  default: info
  logs:
    custom_components.cecotec_conga: debug
```

## Legal notice
This is a personal project and isn't in any way affiliated with, sponsored or endorsed by [CECOTEC](https://www.cecotec.es/).

All product names, trademarks and registered trademarks in (the images in) this repository, are property of their respective owners. All images in this repository are used by the project for identification purposes only.
