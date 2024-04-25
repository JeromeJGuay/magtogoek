# Notes on METEOCE processing.

## Variables

#### <u>_Gps_</u> 
###### Variables: `lon`, `lat`, `speed`, `course`, `magnetic_declination`, `u_ship`, `v_ship` 

+ recompute buoy `speed` and `course` from `longitude` and `latitude`.
  + `recompute_speed_course`: True or False (configuration)
+ compute buoy u_ship and v_ship from buoy `speed` and `course`.
  + `compute_uv_ship`: True or False (configuration)

+ `u_ship` and `v_ship` are required to carry out motion corrtion.

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
  + `recompute_density` (configuration):
    + compute pressure from the sampling depth `sampling_depth` (configuration) FIXME 
    + `salinty` and `temperature` corrections are carried out before computing density.
* Dissolved Oxygen Correction:
  + Winkler Rinko correction if`dissolved_oxygen_winkler_correction` (configuration) is True:
    + `dissolved_oxygen_winkler_coeffs`: (d1_w, d2_w)
    + `dissolved_oxygen_rinko_coeffs`: (d0, d1, d2, c0, c1, c2)
  + Salinity correction if `dissolved_oxygen_pressure_correction` (configuration) is True.
  + Pressure correction if `dissolved_oxygen_salinity_correction` (configuration) is True.

#### <u>_Eco_</u> (Environmental Characterization Optics)
###### Variables: `scattering`, `chlorophyll`, `fdom`

#### <u>_pH_</u>
###### Variables: `ph`
The `ph` values correspond to the exterior ph measurement of the Seafet sensor.
+ viking
  + Raw ph values **are not** corrected for salinity.
  + Magtogoek will attempt to correct the data for salinity if: `ph_salinity_correction` (configuration) is True and the `ph_salinity_coeffs` (configuration), psal, k0 and k2 are provided. 
+ metis
  + Both corrected and uncorrected values are present in the raw data, thu the corrected values are loaded and no correction is appied.
  + If the corrections was not carried out by the Metis controller, it cannot be done by Magtogoek since the `ph_temperature` are not in the raw metis dat file.
#### <u>_pco2_</u>
###### Variables: `pco2_air`, `pco2_water`

pco2 values ares computed by multiplying by the molar concentration (xpco2 [ppm]) by the atmospheric pressure. No correction seems to be needed with the Pro-Oceanus.

## Corrections

### Sensors Corrections Sequence
_magtogoek.metoce.correction.apply_sensors_corrections_

* Dissolved Oxygen Correction were not tested.

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

* Note that `salinty` and `temperature` corrections are carried out before computing density.

### Magnetic Declination

###### Variables: `heading`, `wind_direction`, `wave_direction`
If `magnetic_declination` is not provided in the configuration file, the `magnetic_declination` buoy data values.  
* viking
  + Values are not corrected for magnetic declination.
  + Value are rotated by configuration values `magnetic_declination`.
* metis
  + Values are corrected for magnetic declination.
  + Values are rotated by the difference between the configuration values `magnetic_declination` and the `magnetic_declination` buoy data values.
### Drift
###### Variables: `salinity`, `temperature`, `dissolved_oxygen`, `ph`, `scattering`, `chlorophyll`, `fdom`

##### Correction:

* [corrected_values] = [raw_values] - [drift]

* [drift] is computed as a linear correction (in time) equal to 0 for times <= drift_start_time and total drift at the end.
  
    ```
    drift = np.zeros(len(raw_values))
    drift[drift_start_time_index:] = np.linspace(0, total_drift, len(values) - drift_start_time_index)
    corrected_values = raw_values - drift
    ```


##### Configuration:
* `<varialbe>_drift`: Total drift.
* `<variable>_drfit_start_time` (optional): Timestamp of when the drift started. If not provided, it is assumed that the drift started at time zero.


### Calibration with In-Situ Sample

###### Variables: `salinity`, `temperature`, `dissolved_oxygen`, `ph`, `scattering`, `chlorophyll`, `fdom`

##### Correction
* [corrected_values] = A * [raw_values] + B

##### Configuration:
* `<varialbe>_calibration_correction`: A, B
 
## Quality Control
_magtogoek.meteoce.quality_control.meteoce_quality_control_

### Outlier 

###### Variables:
 Fixme can add any variable.

#### Regional
TODO
#### Absolute
TODO

##### Configuration:
* `absolute_outluier`: True or False
* `regional_outlier`: Name of the region. Use the command: TODO to list all reigon.



### Spikes
###### Variables: `salinity`, `temperature`, `dissolved_oxygen`, `ph`, `scattering`, `chlorophyll`, `fdom`

+ TODO

##### Configuration:
* `<varialbe>_spike_threshold`: TODO
* `<varialbe>_spike_window`: TODO

#### Flag Propagation
* Propagation rules:
  * `temperature`, `salinity` -> `density`
  * `temperature`, `salinity` -> `dissolved_oxygen`
  * `temperature`, `salinity` -> `ph`
  * `atmospheric_pressure` -> `pco2 air`
  * `atmospheric_pressure` -> `pco2 water`
* Data with flag values of 0 (no quality control) can only be changed to 3 (probably_bad), 4 (bad).
* Missig value flag (9) won't propagate.

##### Configuration:
* `propagate_flags`: True or False.

