# solar-friend

# introduction

This package contains the following modules
* Solar yield forecasting (current day, tomorrow and the day after)
* Solar invertor tracker
* Electricity meter tracker (consumption-injection)
* Interface to home assistant (via REST API sensors)
* Tracking database (influx db) : via docker container (included in this package) or externally provided (e.g. on NAS)
* Visualization of data (grafana) : via docker container (included in this package) or externally provided (e.g. on NAS)

# installation

The description below is installation on a rasberry pi but can be installed in any docker environment.
