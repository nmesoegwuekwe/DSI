# FORECAST AND OPTIMIZATION FOR RENEWABLE ENERGY SCHEDULING

![Set up](https://github.com/gno-lit/DSI/blob/main/Final%20project/Forecast-Code/Screenshot%202022-05-10%20075449.png)

## Background
One of the most important challenges to tackle climate change is the decarbonisation of energy production with the use of renewable energy sources such as wind and solar. A challenge here is that renewable energy cannot be produced on demand but the production depends literally on when the wind blows and when the sun shines, which is usually not when demand for electricity is highest. Storing energy is costly and normally associated with loss of energy. Thus, with having more and more renewable energy in the grid, it becomes increasingly important to forecast accurately both the energy demand and the energy production from renewables, to be able to produce power from on-demand-sources (e.g., gas plants) if needed, to shed loads and schedule demand to certain times where possible, and to optimally schedule energy storage solutions such as batteries. In particular, a nowadays common setup is a rooftop solar installation and a battery, together with certain demand flexibilities. Here, we need to forecast the electricity demand, the renewable energy production, and the wholesale electricity price, to be able to then optimally schedule the charging and discharging of the battery, and to schedule the schedulable parts of the demand (when to put the washing machine, when to use the pool pump, etc.). In this way, we can charge the battery with overproduction of solar energy, and use power from the battery instead of power from the grid when energy prices are highest, as well as schedule demand according to energy availability.

## Data description
The goal is to develop an optimal battery schedule and an optimal lecture schedule, based on predictions of future values of energy demand and production. In particular, in this project, we have the following data available. Energy consumption data recorded every 15 minutes from 6 buildings on the Monash Clayton campus, up to September 2020. Solar production data, again with 15 minutes of granularity, from 6 rooftop solar installations from the Clayton campus, also up to September 2020. Furthermore, weather data is available from the Australian Bureau of Meteorology and electricity price data is available from the Australian Energy Market Operator. The goal is now to optimally schedule a battery and timetabled activities (lectures) for the month of October 2020.

![Forecast Performance (Building demand)](https://github.com/gno-lit/DSI/blob/main/Final%20project/Forecast-Code/Building%201.png)

![Forecast Performance (Solar)](https://github.com/gno-lit/DSI/blob/main/Final%20project/Forecast-Code/Solar%201.png)

*Dependencies*: see requirements.txt

## Documentation

Description of folders:
```
*Forecasting component*

Forecast-Code: scripts related to forecasting and time series data
Forecast-Data: raw and processed data for phase1 and phase2
Forecast-Results: output of forecasting

