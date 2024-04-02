
The header section is auto generated. 
```dosini
[HEADER]
made_by                       = Auto generated.
last_updated                  = Auto generated.
sensor_type                   = Auto generated. Field use by the `process` command. Do not change.
platform_type                 = One of [`buoy`, `mooring`, `ship`] 
                                Only used if no `platform_file` is given. Use for proper BODC variables.
                                   
```
# Input and output path.
In the `input` and `output` sections, empty fields are considered False.
If both `netcdf_output` and `odf_output` are false, `netcdf_output` will automatically be set to true.
```dosini
[INPUT]
input_files                   = REQUIRED. `path/to/filenames`: Multiple files can be put on the same line or 
                                on multiple lines as long as they are intented by a least a single space.
platform_file                 = `path/to/platform` file.
platform_id                   = platform id (key) in the platform file.
sensor_id                     = sensor id (key) in the platform file.

[OUTPUT]
netcdf_output                 = `path/to/filenames` or (True, 1). If True or 1, netcdf_output = input_files.nc.
odf_output                    = `path/to/filenames` or (True, 1). If True or 1, odf_output is made from 
                                the `odf[files_specifications]`.
```

# Metadata
The `NETCDF_CF` section contains the metadata fields required by the CF conventions. Not necessary for ODF outputs.
```dosini
[NETCDF_CF]
Conventions                   = Auto generated.
title                         = -
institution                   = -
summary                       = -
references                    = Auto generated.
comments                      = -
naming_authority              = Auto generated.
source                        = Orginal method that produced the data. Ex: Numerical model (name), 
                                or instrument sampling (type).
```

The `PROJECT`, `CRUISE` and `GLOBAL_ATTRIBUTES` sections contain metadata. 
The netcdf global attributes will contain all the keys present in these sections, even if the field are left empty. 
Removing them will remove them from the netcdf global attributes. 
For ODF output, only the `CRUISE` section is required.
```dosini
[PROJECT]
project                       = 
sea_name                      = 
sea_code                      = 

[CRUISE]
country_institute_code        = 
cruise_number                 = 
cruise_name                   = 
cruise_description            = 
organization                  = 
chief_scientist               = 
start_date                    = Format: `YYYY-MM-DD` or `YYYY-MM-DDThh:mm:ss.ssss`.
                                A timezone can be specified with `+HH` or a timezone code ` TMZ`. Default: UTC.
                                Ex: 2000-01-01T00:00:00.0000 -> 2000-01-01T00:00:00.0000 or 2000-01-01.
end_date                      = Format: `YYYY-MM-DD` or `YYYY-MM-DDThh:mm:ss.ssss`.
                                A timezone can be specified with `+HH` or a timezone code ` TMZ`. Default: UTC.
                                Ex: 2000-01-01T00:00:00.0000 -> 2000-01-01T00:00:00.0000 or 2000-01-01.
event_number                  = 
event_qualifier1              = 
event_comments                = 

[GLOBAL_ATTRIBUTES]
date_created                  = Auto generated.
cdm_data_type                 = 
country_code                  = 
publisher_email               = 
creator_type                  = 
publisher_name                = 
keywords                      = 
keywords_vocabulary           = 
standard_name_vocabulary      = Auto generated.
aknowledgment                 = 
```

# Specific processing commands
In these section, empty fields are considered False.
## ADCP
```dosini
[ADCP_PROCESSING]
yearbase                      = YYYY, Year during which the sampling started.
adcp_orientation              = Adcp orientation: Either looking `up` or `down`.
sonar                         = REQUIRED: One of [`os`, `wh`, `sv`, `sw`, `sw_pd0`].
coord_transform               = If True, the velocity data will be transformed to earth coordinates if possible.
navigation_file               = `path/to/netcdf_file` with navigation data. See the `compute nav` 
                                command for more info.
motion_correction_mode        = One of [`bt`, `nav`]. `bt` uses bottom velocity and `nav` velocities computed 
                                form gps tracking. See the `compute nav` command for more info.
leading_trim                  = Removes a count of leading data or data before a given date or datetime.
                                Formats: Date (`YYYY-MM-DD` or `YYYY-MM-DDThh:mm:ss.ssss`) or Count (integer).
                                A timezone can be specified with `+HH` or a timezone code ` TMZ`. Default: UTC.
                                Date ex: 2000-01-01T00:00:00.0000 -> 2000-01-01T00:00:00.0000 or 2000-01-01.
trailing_trim                 = Removes a count of trailing data or data after a given date or datetime.
                                Formats: Date (`YYYY-MM-DD` or `YYYY-MM-DDThh:mm:ss.ssss`) or Count (integer).
                                A timezone can be specified with `+HH` or a timezone code ` TMZ`. Default: UTC.
                                Date ex: 2000-01-01T00:00:00.0000 -> 2000-01-01T00:00:00.0000 or 2000-01-01.
sensor_depth                  = Sensor depth in meter. Will overwrite the one found in the adcp file.
depth_range                   = Value in meter. Cut the bin outside this range. Either `min` or `min, max`.
bad_presssure                 = If True, XducerDepth is set to 0 or to `sensor_depth` if provided.
magnetic_declination          = Declination of the magnetic north in degree east. The value given 
                                should be absolute, not relative to the one configured in the adcp.
keep_bt                       = If True, bottom track data are kept and can be used for motion correction.
start_time                    = Format: `YYYY-MM-DD` or `YYYY-MM-DDThh:mm:ss.ssss`.
                                A timezone can be specified with `+HH` or a timezone code ` TMZ`. Default: UTC.
                                If provided, a new time coordinate vector, starting at `start_time`, 
                                is used instead of the one found in the raw adcp file. Use the parameter 
                                `time_step` to use a different time step than the one found in the adcp 
                                raw adcp file. 
                                Ex: 2000-01-01T00:00:00.0000 -> 2000-01-01T00:00:00.0000 or 2000-01-01.
time_step                     = Time step in seconds. Only use if a `start_time` value is provided.
grid_depth                    = Path and name of the file containing depths
                                to which the dataset should be regridded. Setting this value activates the
                                regridding procedure. The grid file should be a one-column text file
                                containing depth values in meters. For example, the output of:
                                `$ seq 0 10 100 > z.grid`.
grid_method                   = Either `interp` or `bin`. Selects whether vertical dimension
                                regridding will be performed by linear interpolation or bin averaging of the
                                quality-controlled data. Bin averaging selects all data strictly within the bin
                                boundaries and averages them with equal weight.

[ADCP_QUALITY_CONTROL]
quality_control               = If True, quality control is carried out.
amplitude_threshold           = Value Between 0-255: Lower limit. Quality test not carried out if False.
percentgood_threshold         = Value Between 0-100: Lower limit. Quality test not carried out if False.
correlation_threshold         = Value Between 0-255: Lower limit. Quality test not carried out if False.
horizontal_velocity_threshold = Upper limit. Quality test not carried out if False.
vertical_velocity_threshold   = Upper limit. Quality test not carried out if False.
error_velocity_threshold      = Upper limit. Quality test not carried out if False.
sidelobes_correction          = If True sidelobe correction is carried. Quality test not carried out if False.
bottom_depth                  = A bottom depth value can be set for sidelobe correction if needed. 
pitch_threshold               = Value Between 0-180: Upper limit.
roll_threshold                = Value Between 0-180: Upper limit.


[ADCP_OUTPUT]
merge_output_files            = If True, merge the input_files into a single output.
bodc_name                     = If True, Netcdf variables will have bodc parameter code name.
force_platform_metadata       = If True, Metadata from the platform file will overwrite those found in the 
                                raw file.
drop_percent_good             = If True, percent good data are drop from the netcdf output.
drop_correlation              = If True, correlation data are drop from the netcdf output.
drop_amplitude                = If True, amplitude data are drop from the netcdf output.
odf_data                      = Optional. One of  ['vel','anc','both']. Use to specifie which ODF file to produce. 
make_figures                  = If True figure are made and saved next the output files. (NOT YET AVAILABLE)
make_log                      = If True, a log book (text file) is made and saved next to the output file.
```
