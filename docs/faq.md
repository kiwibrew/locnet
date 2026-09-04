# Frequently Asked Questions

## What if my technology doesn't last as long as my system?

Each technology has an expected lifespan, and the model accounts for technology that will need to be replaced before the end of the system's life. It divides the system life by the technology lifespan and rounds up to determine the number of times the technology must be purchased:

`tech_refresh = ceil(system_life / tech_lifespan)`

For example, technology with a five-year lifespan in a ten-year system has a refresh count of two. Technology with a six-year lifespan in the same system also has a refresh count of two, because it must be replaced once during that period.

The model multiplies the original capital cost per sector by this refresh count:

`capex_per_sector = capex_per_sector * tech_refresh`

This adjusted sector cost is included in the access-network CapEx. The access-network CapEx then contributes to the model's construction spend, which is used to calculate depreciation over the life of the system.

## How does the model calculate and automatically add backhaul?

The model dimensions backhaul for the busiest hour in the final year of the network's life. It starts with the Year 1 monthly traffic per user, applies the annual traffic-growth rate through the final year, assumes that 8.5% of monthly traffic occurs in the busy hour, and converts that traffic to a peak rate in Mbps per user. The **Backhaul Required** result is this final-year peak rate multiplied by the community-network users supported by the access network, plus the number of Public Access Facility (PAF) seats. PAF seats are used here instead of all people who may share them.

For every backhaul link selected by the user, the model divides the link's rated speed by the final-year peak Mbps per user and rounds the result to estimate how many users that link can support. It then adds the capacities of all selected links. If their combined capacity is lower than the number of users supported by the solution, the model treats the backhaul as underprovisioned.

To close the shortfall, the model finds the selected backhaul link with the lowest average variable bandwidth charge per user over the system life. This is the "cheapest" option for this calculation; it is not necessarily the link with the lowest equipment cost or fixed monthly charge. The model calculates how many additional copies of that link are needed, rounding up so that the shortfall is fully covered, and adds them automatically. The added links appear in the bill of materials and increase the reported available backhaul, backhaul CapEx, and fixed and variable backhaul OpEx. The model only duplicates a backhaul type that the user has already selected; it does not choose a new technology.

## How does the Power Model Work?

The Power Model estimates the power-system costs for each location in a network design. It produces separate capital expenditure (CapEx) and lifetime mains-electricity operating expenditure (OpEx) estimates; together, these are the power component of the solution's total cost of ownership over the selected system life. The model does not automatically choose a power system: select the option that best describes each location, then compare the resulting costs and assumptions.

The model uses the electrical load calculated for the location, the selected system life, and the power, solar, battery, and charger/inverter settings. The mains installation cost, mains electricity price, solar cost, battery cost, charger/inverter base and variable costs, solar efficiency, battery depth of discharge, solar derating, and battery-age derating can all be adjusted in Expert Options. The defaults are intended as practical starting estimates, not quotations for a specific installation.

### Location-specific solar and climate data

Climate inputs are location-specific. The model rounds latitude and longitude to two decimal places. It then reads the matching record from the SQLite `Solar_cache` table. The cache stores the solar and climate statistics plus `sun_jan` through `sun_dec`. These fields contain NASA's monthly `SI_TILTED_AVG_LATITUDE` values in kWh/m²/day.

If the cache cannot supply the required values, the application requests a point climatology from NASA's Prediction Of Worldwide Energy Resources (POWER) service. It stores the result for later use at the same rounded coordinates. POWER supplies long-term climate data, not a short-term weather forecast. Read the [NASA POWER documentation](https://power.larc.nasa.gov/docs/) for data definitions and API guidance.

The application requests tilted-surface solar irradiance, equivalent no-sun days, and temperature at two meters (`T2M`). It uses these values as follows:

- **Monthly solar resource** comes from `SI_TILTED_AVG_LATITUDE`. A value of zero is valid. It means that the location receives no usable solar energy in that month.
- **Minimum solar resource (`min_sun`)** is the lowest valid monthly solar value. The off-grid solar model uses it for panel sizing.
- **Maximum no-sun days (`max_no_sun_days`)** is the highest monthly `EQUIV_NO_SUN_CONSEC_07` value.
- **Annual no-sun days (`annual_no_sun_days`)** is the sum of each monthly no-sun value multiplied by 4.3. The off-grid solar model uses the maximum no-sun value. The hybrid model does not use either no-sun value for its energy cost.
- **Average temperature (`avg_temp`)** comes from the annual `T2M` value. If NASA gives `-999`, the model averages at least ten valid monthly values.
- **Minimum and maximum temperature** come from the valid monthly `T2M` values. The minimum temperature sets the battery cold derating.

NASA uses `-999` as a missing-data marker. Reliable and intermittent mains systems need valid temperature data, but do not need solar or no-sun data. They can continue with `-999` in the solar diagnostic fields. Solar systems need usable solar and no-sun data. If that data is unavailable, the model returns an error that says Solar power is not supported at that location. Hybrid systems need twelve valid monthly solar values and at least one positive value. They can continue without no-sun data. If every monthly solar value is zero, the model returns an error that says Hybrid power is not supported at that location.

If NASA cannot supply the data that a selected system needs, the application/API returns a 502 response with the detail: `The NSAS POWER service returned incomplete or invalid data.`

### Power-system options

| Selected system | Battery autonomy used by the model | Mains-power treatment |
| --- | --- | --- |
| **Reliable mains** | The configurable reliable-power outage duration (`power_reliable_hours`) | Assumes mains energy is used throughout the system life. |
| **Intermittent mains** | The configurable intermittent-power outage duration (`power_intermittent_hours`) | Assumes mains energy is used throughout the system life, with battery capacity covering the configured outages. |
| **Hybrid solar and mains** | The configurable hybrid autonomy duration (`power_hybrid_hours`) | Uses monthly solar generation and mains power for the remaining energy demand. |
| **Off-grid solar** | `max_no_sun_days × 24` hours | Uses no mains installation or mains-energy OpEx. |

Reliable and intermittent mains systems include a battery to cover their configured outage period, a charger/inverter, the mains installation cost, and lifetime mains electricity. Hybrid systems combine solar, batteries, a charger/inverter, and a mains connection. They use solar energy where it is available and mains energy for the remaining demand. Off-grid solar systems size battery autonomy for the worst no-sun period and have no mains-energy cost.

### Battery, solar, and charger assumptions

For systems with a battery, the model starts with the location's electrical load, the applicable autonomy period, and the configured depth of discharge. It then increases the requirement for battery-age derating over the full system life and applies a temperature-based cold derating using the location's coldest valid monthly `T2M` value. Lithium-ion batteries lose usable capacity as they age, and cold temperatures reduce the energy they can store, so both adjustments increase the installed battery capacity required to meet the same load.

For solar and hybrid systems, the model sizes panel area from the required daily energy and solar resource. Hybrid sizing uses the lowest positive monthly solar value and final-year panel output. It applies the configured panel efficiency and solar derating over the system life. For every month and system year, the hybrid model calculates the solar energy from the fixed panel area. It limits solar use to the location's daily energy demand and charges mains power for the remaining energy. It gives no credit for excess solar energy.

Panel generation capacity uses a peak irradiance assumption of 1,350 watts per square metre. Panel cost uses the configured local cost per watt. Charger/inverter cost consists of a base cost plus a variable cost. It scales with load for mains systems and with calculated solar-panel capacity for solar and hybrid systems.

The model reports the battery, charger/inverter, and solar cost components with the CapEx and OpEx results. Off-grid and hybrid `power_capex` values include the calculated solar cost.

### Important limitations

This is a planning model, not a detailed electrical-system design. It uses long-term monthly climate data. It does not model local shading, terrain effects on irradiation, daily battery cycling, panel orientation, soiling, solar export, or intraday battery dispatch. These factors can materially change the best design, particularly at high and low latitudes. Use a site survey, local energy data, and a detailed engineering design before procurement or construction.

## My model doesn't cover as many people as I expect it should, why is that?

There are a few reasons this could happen. If the viewshed shows you've covered an area but the Population geographic coverage is too low, it's likely the WorldPop API data is incorrect for your location. You should untick "Allow model to determine households" and enter your own value for each location where the population is incorrect.

If your population geographic coverage is low because your viewshed is very small, try raising up the antenna another five or ten meters. This can help when there are nearby obstructions like buildings or trees.

## Why is it so slow to run a new model?

New models fetch large data tiles from three different APIs, and sometimes this can take a minute or two. Once you've run a model in a particular area, future runs will be fast because the LocNet server will have the data cached.

## What determines the default GPS point when adding a location?

The application tries to place its pin in the centre of the country chosen. This was determined by an algorothm, so if you find the location was wrong, open a ticket in Github and we'll fix it!

## What does the Site Structure option in a location do; it's not clear if anything changes if you choose "Use a Building" or "Tower/mast/utility pole".

This is a legacy option that no longer impacts the model. It's in the directions for use of the application so it's being left in for now. Some day it will disappear.
