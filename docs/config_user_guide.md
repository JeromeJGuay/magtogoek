## INCOMPLETE



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


[OUTPUT]
netcdf_output                 = `path/to/filenames` or (True, 1). If True or 1, netcdf_output = input_files.nc.
odf_output                    = `path/to/filenames` or (True, 1). If True or 1, odf_output is made from 
                                the `odf[files_specifications]`.
make_figures                  = + (True, 1) Figures are plotted.
                                + `path/to/directory`: figure ared plotted and saved.
make_log                      = If True, a log book (text file) is made and saved next to the output file.                               
force_platform_metadata       = If True, Metadata from the platform file will overwrite those found in the 
                                raw file.
use_bodc_name                     = If True, Netcdf variables will have bodc parameter code name.
merge_output_files            = If True, merge the input_files into a single output.                               
```

# Metadata
The `NETCDF_CF` section contains the metadata fields required by the CF conventions. Not necessary for ODF outputs.
```dosini
[NETCDF_CF]
Conventions                   = Auto generated if not provided.
title                         = -
institution                   = -
summary                       = -
references                    = Auto generated if not provided.
comments                      = -
naming_authority              = Auto generated if not provided.
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