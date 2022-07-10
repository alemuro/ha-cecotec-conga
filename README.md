# Cecotec Conga integration

This integration aims to manage new versions of Cecotec Conga vacuum cleaner. The ones that cannot be managed with [FreeConga](https://freecon.ga/).

The author of this project categorically rejects any and all responsibility related to vacuums managed by this integration.

## Installation

### HACS (Recommended)

This integration can be added to HACS as a custom repository.

Assuming you have already installed and configured HACS:
1. Go to `HACS > Integrations`
2. Click on the three dots at the upper-right corner and select `custom repositories`.
3. Set `https://github.com/alemuro/ha-cecotec-conga.git` as the repository, and `Integration` as the category.
4. Close this popup and install the `Cecotec Conga` integration.

You're ready! Now continue with the configuration.

### Configuration Through the interface
1. Navigate to `Settings > Devices & Services` and then click `Add Integration`
2. Search for `Cecotec Conga`
3. Enter your credentials

## Supported devices

This integration has been tested with the following vacuum cleaners:
* Conga 5290

[Have you tested a different one and it works? Please tell us!](https://github.com/alemuro/ha-cecotec-conga/issues/new?assignees=&labels=&template=device-tested.md&title=%5BDEVICE-TESTED%5D)

## Supported functionalities

So far the following features have been implemented:
* `TURN_ON`
* `RETURN_HOME` (`TURN_OFF` does the same)

A lot of ideas are in the backlog :) Do you have some idea? [Raise an issue!](https://github.com/alemuro/ha-cecotec-conga/issues/new?assignees=&labels=&template=feature_request.md&title=)

## Legal notice
This is a personal project and isn't in any way affiliated with, sponsored or endorsed by [CECOTEC](https://www.cecotec.es/).

All product names, trademarks and registered trademarks in (the images in) this repository, are property of their respective owners. All images in this repository are used by the project for identification purposes only.
