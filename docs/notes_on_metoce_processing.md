# Notes METEOCE on the processing workflow.

## Variables

#### <u>_Gps_</u> 
###### Variables: `lon`, `lat`, `speed`, `course`, `magnetic_declination`, `u_ship`, `v_ship` 

TODO Speed & course recomputation
TODO u_ship, v_ship computation

#### <u>_Compass_</u>
###### Variables: `heading`, `pitch`, `roll`, `pitch_std`, `roll_std`


#### <u>_Atmospheric_</u>
###### Variables: `atm_temperature`, `atm_humidity`, `atm_pressure`


#### <u>_Par_</u>
###### Variable: `par`


#### <u>_Wind_</u>
###### Variables: `wind_speed`, `wind_direction`, `wind_gust`
Metis buoy can return measurement of wind from the _wxt536_ sensor if the _wmt700_ failed.
If wind values come from the _wxt536_ and _wmt700_, a warning will be raised in the logging.
+ motion correction is carried if `u_ship` and `v_ship` are computed and `adcp_motion_correction` is True in the configuration file.


#### <u>_Wave_</u>
###### Variables: `wave_mean_height`, `wave_maximal_height`, `wave_period`


#### <u>_Adcp_</u>
###### Variables: `u`, `v`, `w`, `e`.
+ motion correction is carried if `u_ship` and `v_ship` are computed and `adcp_motion_correction` is True in the configuration file.

The magnetic correction applied to adcp data is given by:
`magnetic_declination` - `adcp_magnetic_declination_preset`,
where `adcp_magnetic_declination_preset` is the value set in the adcp configuration.  

#### <u>_Ctd_</u>
###### Variables: `salinity`, `temperature`, `density`, `dissolved_oxygen`
 
* Density computation:
  + `recompute_density`:
    + compute pressure from the sampling depth `sampling_depth` FIXME 
* Dissolved Oxygen Correction:
  + Winkler Rinko correction if`dissolved_oxygen_winkler_correction` is True in the configuration file requires:
    + `dissolved_oxygen_winkler_coeffs`: (d1_w, d2_w)
    + `dissolved_oxygen_rinko_coeffs`: (d0, d1, d2, c0, c1, c2)
  + Salinity correction if `dissolved_oxygen_pressure_correction` is True in the configuration file.
  + Pressure correction if `dissolved_oxygen_salinity_correction` is True in the configuration file.

#### <u>_Eco_</u> (Environmental Characterization Optics)
###### Variables: `scattering`, `chlorophyll`, `fdom`

#### <u>_pH_</u>
###### Variables: `ph`
* The `ph` values correspond to the ph exterior ph measurement of the Seafet sensor.
+ viking
  + Raw ph values **are not** corrected for salinity.
  + Magtogoek will attempt to correct the data for salinity if: `ph_salinity_correction` is True and the `ph_salinity_coeffs` (psal, k0, k2) are provided in the configuration file. 
+ metis
  + Raw ph values **are** corrected for salinity.
  + Magtogoek will not correct the data for salinity.

#### <u>_pco2_</u>
###### Variables: `pco2_air`, `pco2_water`

pco2 values ares computed by multiplying by the molar concentration (xpco2 \[ppm\]) by the atmospheric pressure. No correction seems to be needed with the Pro-Oceanus.

#### Sensors Corrections Sequence
`salinty` and `temperature` corrections are carried out before computing density.
1. `raw_dissolved_oxygen` from `dissolved_oxygen` (it needs to be done before correcting temperature)
2. `temperature`
   1. drift correction
   2. calibration correction
3. `dissolved_oxygen` from `raw_dissolved_oxygen`
4. `salinity` (it needs to be done before correcting temperature)
   1. drift correction
   2. calibration correction
5. `dissolved_oxygen` 
   1. salinity correction
   2. pressure correction
6. `ph` salinity correction
7. `dissolved_oxygen`, `ph`, `scattering`, `chlorophyll`, `fdom` drift corrections
8. `dissolved_oxygen`, `ph`, `scattering`, `chlorophyll`, `fdom` calibration corrections


#### Magnetic Declination
###### Variables: `heading`, `wind_direction`, `wave_direction`
If `magnetic_declination` is not provided in the configuration file, the `magnetic_declination` buoy data values.  
* viking
  + Values are not corrected for magnetic declination.
  + Value are rotated by configuration values `magnetic_declination`.
* metis
  + Values are corrected for magnetic declination.
  + Values are rotated by the difference between the configuration values `magnetic_declination` and the `magnetic_declination` buoy data values.
#### Drift
###### Variables: `salinity`, `temperature`, `dissolved_oxygen`, `ph`, `scattering`, `chlorophyll`, `fdom`


#### Calibration with In-Situ Sample
###### Variables: `salinity`, `temperature`, `dissolved_oxygen`, `ph`, `scattering`, `chlorophyll`, `fdom`
 
### Quality Control

#### Spikes
###### Variables: `salinity`, `temperature`, `dissolved_oxygen`, `ph`, `scattering`, `chlorophyll`, `fdom`

#### Flag Propagation


