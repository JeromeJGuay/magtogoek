"""
Date: February 15 2022
Made by: jeromejguay

This module contains the functions to read the data send by Viking as of February 2022 format version.

The Buoy Data `.dat` files
--------------------------
[NOM]: Buoy information
    'PMZA-RIKI,110000,240521,8.3.1,000018C0D36B,00.3,00.0,48 39.71N,068 34.90W'
[COMP]: Compass data
    '000DA1B4,FFC58202,-4.634,88.61,0.654,27.98,11.14,24.94'
[OCR]: Radiance, Irradiance
    (note used)
[Triplet]:(Seabird ECO-Triplet) Water Surface Fluorescence
                                            L1, Raw1,   Calc1,      L2, Raw2,   Calc2,  L3, Raw3,   Calc3
                                                          m-1                  mg/m^3                 ppb
    'BBFL2W-1688	05/24/21	10:59:03	700	1376	2.786E-03	695	190	1.066E+00	460	85	3.454E+00'
    700 nm: Scattering (m-1 from seabird)
    695 nm: Chlorophyll (ug/L from seabird)
    460 nm: FDOM (ppb from seabird)
    1 ppb = 1 mg / m³
[Par_digi]: par (Photosynthetic Active Radiation): μmol photons•m-2•s-1,
    '110100,240521,SATPRS1093,30.415,510.646,-1.7,5.7,11.0,162'
[SUNA]: Near surface Nitrate concentration
    'SATSLC1363,2021145,12.000192,7.63,0.1068,0.2978,0.2471,0.00,0.000160'
    (0) Model/serial          (1) YearDdays         (2) Hours of day
    (3) Nitatre [uMol],       (4) Nitrogen [mgN/L], (5) absorbance 254.31 nm,
    (6) absorbance 350.16 nm, (7) Bromide [mg/L],   (8) spectrum average,
[GPS]: GPS
    '110132,A,4839.7541,N,06834.8903,W,003.7,004.4,240521,017.5,W,*7B'
    (0) GPRMC:
    (1) time : (utc) hhmmss.ss
    (2) A/V : Position status. A = Data valid, V = Data invalid.
    (3) lat : DDmm.mmmm
    (4) N/S :
    (5) lon : DDmm.mmmm
    (6) E/W :
    (7) speed : Knots, x.x
    (8) true course:  x.x True degree
    (9) date: ddmmyy
    (10) variation, magnetic x.x
    (11) E/W, mode + checksum : ((A)utonomous, (D)ifferential, (E)stimated, (M)anual input, (N) data not valid.
[CTD]: Temperature, Conductivity, Salinity, Density
    '   7.3413,  2.45966,  23.2697, 18.1612'
[CTDO]: Temperature, Conductivity, Dissolved Oxygen, Salinity
    dissolved oxygen is in [umol / L]
[RTI]: Rowetech ADCP. Near surface velocities (6 meter deep ?)
    bin number, position_cm, 4-beam_vel, 4-enu, 4-corr, 4-amp, ... 16 more for bt.
    '1,407,-258,-157,-263,-32,-160,-369,-202,-30,100,100,100,100,84,83,83,84'
    'Bot,-3,-6,-50,56,129,101,-4,-4,100,100,100,100,76,78,78,77'
[RDI]: Teledyne ADCP. Near surface velocities (6 meter deep ?)
    '110000,240521,E3FFBB0022001400'
[WAVE_M]: Waves (Multi-Électronique sensor)
    date, hour, wave period, averaged wave height, averaged wave height (1/3 period, highest waves), max height.
    '2021/05/24,10:45:00,6.61,0.60,0.48,1.29'
[WAVE_S]: Waves (Seaview sensor)
    NMEA str, Heading, average height, dominant period, wave direction, Hmax, Hmax2, Pmax. angR, angP, date time, index*chk
    '$PSVSW,201.63,1.239,8.695,266.983,1.811,1.575,9.668,3.039,11.004,2021-09-21 00:28:51,2048*76'
[WXT520]: Meteo Conditions
    'Dn=163D,Dm=181D,Dx=192D,Sn=18.0K,Sm=22.7K,Sx=28.0K'
    'Rc=0.00M,Rd=0s,Ri=0.0M,Hc=0.0M,Hd=0s,Hi=0.0M'
    'Ta=6.8C,Ua=45.0P,Pa=1025.4H'
    'Th=7.6C,Vh=14.1#,Vs=14.4V,Vr=3.503V'
    Dn = minimal wind direction | unrelated to min wind strength
    Dm = average wind direction
    Dx = maximal wind direction | unrelated to max wind strength
    Sn = minimal wind strength
    Sm = average wind strength
    Sx = maximal wind strength
    Rc = rain accumulation since midnight in mm
    Rd = rain duration since midnight in second
    Ri = rain intensity in mm/h
    Hc = Hail accumulation in hits/cm²
    Hd = Hail duration since midnight in second
    Hi = Hail intensity in hits/cm²/h
    Ta = temperature in celsius
    Ua = ambient humidity
    Pa = atmospheric pressure.
[WMT700]: Wind:
    'Dn=162.41D,Dm=179.40D,Dx=196.13D,Sn=14.74K,Sm=21.53K,Sx=27.46K'
[wPH]: Surface (water) pH.
    'SEAFET02138,2021-05-24T11:01:26,1266,0000,7.9519,7.9825,-0.892024,-0.938712,7.4124,3.4,7.6'
    sample_number, error_flag, PH_ext, PH_int, ph_ext_volt, ph_ext_volt, pH_temperature, relative_humidity, internal_temperature
[CO2_A]: CO2 in Air. (A/D : analogue device ?. units-> counts)
    Measurement type,Year,Month,Day,Hour,Minute,Second,Zero A/D,Current A/D.
    CO2_ppm,IRGA temperature,Humidity_mbar,Humidity sensor temperature,Gas stream pressure_mbar,
    Las could be `Battery voltage` or `IRGA temperature sensor`.
    'W M,2021,05,25,11,51,24,55544,52106,448.94,40.00,10.70,13.40,1000,12.3'
[CO2_W]: Near surface CO2 in Water
    See CO2_A
[Debit]: Near surface current measured by flow meter.
    '00000167'
    20_000 Pulse = 1 nautical miles. Pulse are measured over 60 seconds.
    1 Pulse = 0.0926 m -> 1 Pulse over 60s -> 0.001543 m/s
[p0] ou [p1]: Power
    (not used)
[VEMCO] Acoustic receiver
     Date       Time    ,Protocol, Serial number
    '2018-05-05 04:27:35,A69-1602,46179'

[MO]: Short string. Not Used
    '942+03272+00360##########799290270601014514000902010401417310###73000502F9FF0300,000,[W]A forced start yoyo was sent'
    Used to get information about the winch (ctd-yoyo) that is a [W] tag within the short string.

    [W]Not in time slot
    -Indicate that we’re not inside the time slot designed to do a MiniWinch mission.
    [W]Too soon after a power-up
    -Indicate that the Buoy Controller just restart and there wasn’t a MiniWinch mission since.
    [W]A start yoyo was sent
    -Indicate that a MiniWinch mission command was send.
    [W]A yoyo mission is in progress
    -Indicate that a MiniWinch mission is still running
    [W]94>  2.6149,  2.57904,   95.000,  28.2356
    -Indicate that a MiniWinch mission ended normally and contains the string received by the CTD
     of the profiler, when this one was in his lowest in his mission.
    [W]Interval not elapsed
    -Indicate there wasn’t a MiniWinch mission because the interval programmed between two
     missions is not elapsed.


    Other message found in files: But not in documentation...
    [W]A forced start yoyo was sent
    [W]35>*** Cable or CTD Jam Detected, Trying To Stop And Retract ***
    [W]22>Error ! Motor Stopped But Drum Running
    [W]Waves too high
    [W]I.N.E
    [W]30>Attention ! Stop On Switch Overrun
    [W]Voltage is too low


Generated winch files
---------------------
<buoy name>_WCH_<date>.dat
#1 Date GPS
#2 Hour GPS
#3 The message received of the Mini-Winch controller. It can be text if it begins with [W]94> you got the data
received by the CTD when it was at it lowest; or the temperature (°C), Conductivity (S/m), Pressure (decibars), salinity (PSU).

Notes
-----
[1] .. [January 2023] JeromeJGuay
    - OCR are not current installed on the buoy. A function was made but is not in used. Furthermore, the documentation
    was not clear on how to decode the hexadecimal values. Here is an exAmple of the OCR string.
    [OCR],29,220916
    D,32,7FF61F47,7FF96AAD,80019C5D,7FF8EEBB,7FF0B2E5,7FFB045E,7FFC0AF4,6CEF2E,5058B5,560C72,516F8D,78A870,48660F,9B89F3,7FF61F00,7FF96AC0,80019C40,7FF8EF00,7FF0B300,7FFB03C0,7FFC0A80
    W,12,7FED43A9,7FF5BCC5,8005D91A,8015D956,7FFCD34E,7FF14B6D,7FFC38AC,29BF350,FA9F3A,9ABAD1,1B610D7,3DD6947,CF5AC95,1635C01,7FED4540,7FF5BD00,8005D900,8015D780,7FFCD6C0,7FF13EC0,7FFC3780

    - Everything is loaded as float since nans are not available for int type in numpy

    - Triplets Data Decoding: The code will to be modified for other wave lengths.
          700 nm: Fluorescence Scattering, 695 nm: Chlorophyll, 460 nm: FDOM

[2] .. [March 2023] JeromeJGuay
    Data from the wave_s wave heights are truncated to the first decimal not rounded.

[3] .. [March 2023] JeromeJGuay
    GPS bearing and course data seem to be bad. We believe that the bearing and course data are instant measurements.
    Thus wave induced rapid horizontal oscillation and the rocking of the buoy, the GPS being located about ~2-3 meters
    above the floating line, result in higher oscillation and amplitude in the speed values. Since speed dependent values
    are average over ~ 1 minutes, we need at least ~1 minutes average values from the gps.

[4] .. [June 2023] JeromeJGuay
    Debit only mesure the amplitude of the flow along the heading of the buoy. It is thus utterly useless

[5] .. [July 2023] JeromeJGuay
    WMT missing values seems to be 999.0 for mean wind speed and mean wind direction and 0 for max/min wind speed and max/min
    wind direction. The WMT missing values are replaced with NANs using a mask made from Mean Wind Speed values.

"""

import sys
import re
import struct
from datetime import datetime, timedelta
from math import atan2, sqrt, pi, sin, cos
from typing import List, Dict, Union, Optional

import numpy as np

from magtogoek.utils import get_files_from_expression



NAN_FILL_VALUE = np.nan

#TRIPLET_FILL_VALUE = 1e20
WMT_FILL_VALUE = 999.0

# Tag for Unpacked data
DATA_TAG = ['comp', 'triplet', 'par_digi', 'suna', 'gps', 'ctd', 'ctdo', 'rti', 'rdi',
               'wave_m', 'wave_s', 'wxt520', 'wmt700', 'wph', 'co2_w', 'co2_a', 'debit', 'vemco', 'mo']

# Tag found in raw files
INSTRUMENTS_TAG = ["NOM", "COMP", "Triplet", "Par_digi", "SUNA", "GPS", "CTD", "CTDO",  "RTI", "RDI",
                   "WAVE_M", "WAVE_S", "WXT520", "WMT700", "WpH", "CO2_W", "CO2_A", "Debit", "VEMCO", "MO"]  # "OCR", "MO", "FIN"]

DATA_BLOCK_REGEX = re.compile(r"(\[NOM].+?)\[FIN]", re.DOTALL)
DATA_TAG_REGEX = re.compile(rf"\[({'|'.join(INSTRUMENTS_TAG)})],?((?:(?!\[).)*)", re.DOTALL)

### Tag keys ###
TAG_VARS = dict(
    COMP_KEYS=['heading', 'pitch', 'roll', 'tilt', 'pitch_std', 'roll_std', 'tilt_std'],
    TRIPLET_KEYS=['time', 'model_number', 'serial_number',
                  'wavelength_1', 'raw_value_1', 'calculated_value_1',
                  'wavelength_2', 'raw_value_2', 'calculated_value_2',
                  'wavelength_3', 'raw_value_3', 'calculated_value_3'],
    PAR_DIGI_KEYS=['time', 'model_number', 'serial_number', 'timer_s', 'par', 'pitch', 'roll', 'intern_temperature'],
    SUNA_KEYS=["time", "model_number", "serial_number", 'nitrate', 'nitrogen',
               'absorbance_254_31', 'absorbance_350_16', 'bromide', 'spectrum_average'],
    GPS_KEYS=['time', 'latitude_N', 'longitude_E', 'speed', 'course', 'variation_E', 'validity'],
    CTD_KEYS=['temperature', 'conductivity', 'salinity', 'density'],
    CTDO_KEYS=['temperature', 'conductivity', 'oxygen', 'salinity'],
    RTI_KEYS=['bin', 'position_cm', 'beam1', 'beam2', 'beam3', 'beam4', 'u', 'v', 'w', 'e',
              'corr1', 'corr2', 'corr3', 'corr4', 'amp1', 'amp2', 'amp3', 'amp4',
              'bt_beam1', 'bt_beam2', 'bt_beam3', 'bt_beam4',
              'bt_u', 'bt_v', 'bt_w', 'bt_e', 'bt_corr1', 'bt_corr2', 'bt_corr3', 'bt_corr4',
              'bt_amp1', 'bt_amp2', 'bt_amp3', 'bt_amp4'],
    RDI_KEYS=['time', 'u', 'v', 'w', 'e'],
    WAVE_M_KEYS=['time', "period", "average_height", "significant_height", "maximal_height"],
    WAVE_S_KEYS=['time', 'heading', 'average_height', 'dominant_period', 'wave_direction',
                 'Hmax', 'Hmax2', 'pmax', 'roll', 'pitch'],
    WXT520_KEYS=['Dn', 'Dm', 'Dx', 'Sn', 'Sm', 'Sx',
                 'Rc', 'Rd', 'Ri', 'Hc', 'Hd', 'Hi',
                 'Ta', 'Ua', 'Pa', 'Th', 'Vh', 'Vs', 'Vr'],
    WMT700_KEYS=['Dn', 'Dm', 'Dx', 'Sn', 'Sm', 'Sx'],
    WPH_KEYS=['time', 'model', 'serial_number', 'sample_number', 'error_flag',
              'ext_ph', 'int_ph', 'int_volt', 'ext_volt', 'ph_temperature', 'rel_humidity', 'int_temperature'],
    CO2_W_KEYS=["time", "auto_zero", "current", "co2_ppm", "irga_temperature", "humidity_mbar",
                "humidity_sensor_temperature", "cell_gas_pressure_mbar"],
    CO2_A_KEYS=['time', 'auto_zero', 'current', "co2_ppm", 'irga_temperature', 'humidity_mbar',
                'humidity_sensor_temperature', "cell_gas_pressure_mbar"],
    DEBIT_KEYS=['flow'],
    VEMCO_KEYS=['time', 'protocol', 'serial_number'],
    MO_KEYS=['adcp_model', 'wind_speed', 'wind_direction', 'air_temperature', 'air_humidity',
            'atm_pressure','temperature', 'salinity', 'triplet_700', 'triplet_695', 'triplet_460',
            'par', 'co2_ppm_water', 'co2_ppm_air', 'ph', 'wave_period', 'wave_average_height', 'wave_maximal_height',
            'power_voltage', 'solar_charging', 'wind_charging', 'power_consumption', 'pitch', 'roll',
            'water_flow', 'heading', 'speed', 'course', 'rain', 'u', 'v', 'w', 'e']
)


class VikingData:
    """Object to store Viking data. """

    def __init__(self, buoy_name: str, firmware: str, controller_sn: str):
        self.buoy_name: str = buoy_name
        self.firmware: Union[List[str], str] = firmware
        self.controller_sn: Union[List[str], str] = controller_sn

        self.time: Union[list, np.ma.MaskedArray] = []
        self.latitude: Union[list, np.ma.MaskedArray] = []
        self.longitude: Union[list, np.ma.MaskedArray] = []

        self.tags = tuple(t for t in DATA_TAG)

        self.comp: dict = {key: [] for key in TAG_VARS['COMP_KEYS']}
        self.triplet: dict = {key: [] for key in TAG_VARS['TRIPLET_KEYS']}
        self.par_digi: dict = {key: [] for key in TAG_VARS['PAR_DIGI_KEYS']}
        self.suna: dict = {key: [] for key in TAG_VARS['SUNA_KEYS']}
        self.gps: dict = {key: [] for key in TAG_VARS['GPS_KEYS']}
        self.ctd: dict = {key: [] for key in TAG_VARS['CTD_KEYS']}
        self.ctdo: dict = {key: [] for key in TAG_VARS['CTDO_KEYS']}
        self.rti: dict = {key: [] for key in TAG_VARS['RTI_KEYS']}
        self.rdi: dict = {key: [] for key in TAG_VARS['RDI_KEYS']}
        self.wave_m: dict = {key: [] for key in TAG_VARS['WAVE_M_KEYS']}
        self.wave_s: dict = {key: [] for key in TAG_VARS['WAVE_S_KEYS']}
        self.wxt520: dict = {key: [] for key in TAG_VARS['WXT520_KEYS']}
        self.wmt700: dict = {key: [] for key in TAG_VARS['WMT700_KEYS']}
        self.wph: dict = {key: [] for key in TAG_VARS['WPH_KEYS']}
        self.co2_w: dict = {key: [] for key in TAG_VARS['CO2_W_KEYS']}
        self.co2_a: dict = {key: [] for key in TAG_VARS['CO2_A_KEYS']}
        self.debit: dict = {key: [] for key in TAG_VARS['DEBIT_KEYS']}
        self.vemco: dict = {key: [] for key in TAG_VARS['VEMCO_KEYS']}
        self.mo: dict = {key: [] for key in TAG_VARS['MO_KEYS']}

    def __repr__(self):
        repr = (
            f"{self.__class__}"
            f"buoy_name: {self.buoy_name}"
            f"firmware: {self.firmware}"
            f"controller_sn: {self.controller_sn}"
            f"data: (length: {len(self)})"
        )
        for tag in self.tags:
            if self.__dict__[tag] is not None:
                repr += f"  {tag}: (" + ", ".join(list(self.__dict__[tag].keys())) + ")\n"
            else:
                repr += f"  {tag}: (empty)\n"
        return repr

    def __len__(self):
        return len(self.time)

    def reformat(self):
        self._squeeze_empty_tag()
        self._to_numpy_array()

        # Notes:
        if self.triplet is not None:  # This Could be done directly during the decoding
            _convert_triplet_wavelength(self.triplet)  # This Could be done directly during the decoding

        if self.wmt700 is not None:
           _set_wmt_fill_value_to_nan(self.wmt700)

    def _to_numpy_array(self):
        self.time = np.array(self.time, dtype='datetime64[s]')
        self.latitude = np.array(self.latitude)
        self.longitude = np.array(self.longitude)

        for tag in self.tags:
            if self.__dict__[tag] is not None:
                for key, value in self.__dict__[tag].items():
                    self.__dict__[tag][key] = np.array(value)

    def _squeeze_empty_tag(self):
        """Set tag where all data are missing to None"""
        for tag in self.tags:
            if _is_empty_tags(data=self.__dict__[tag]) is True:
                self.__dict__[tag] = None


def _is_empty_tags(data: dict):
    for values in data.values():
        unique_values = np.unique(values)
        if len(unique_values) > 1:
            return False
        elif len(unique_values) == 1 and np.isfinite(unique_values[0]):
            return False
    return True

def _convert_triplet_wavelength(triplet_data: dict):
    """
    700 nm: light scattering (m-1)
    695 nm: Chlorophyll  (ug/l)
    460 nm: FDOM (ppb)

    Returns
    -------

    Notes
    -----
    For other wave lengths: The code will to be modified
    """
    _shape = triplet_data['time'].shape

    scatter_raw, scatter_calc = np.ma.masked_all(_shape), np.ma.masked_all(_shape)
    chloro_raw, chloro_calc = np.ma.masked_all(_shape), np.ma.masked_all(_shape)
    fdom_raw, fdom_calc = np.ma.masked_all(_shape), np.ma.masked_all(_shape)

    for i in ("1", "2", "3"):
        index700 = triplet_data['wavelength_' + i] == 700
        scatter_raw[index700] = triplet_data['raw_value_' + i][index700]
        scatter_calc[index700] = triplet_data['calculated_value_' + i][index700]

        index695 = triplet_data['wavelength_' + i] == 695
        chloro_raw[index695] = triplet_data['raw_value_' + i][index695]
        chloro_calc[index695] = triplet_data['calculated_value_' + i][index695]

        index460 = triplet_data['wavelength_' + i] == 460
        fdom_raw[index460] = triplet_data['raw_value_' + i][index460]
        fdom_calc[index460] = triplet_data['calculated_value_' + i][index460]

    scatter_raw.set_fill_value(NAN_FILL_VALUE)
    scatter_calc.set_fill_value(NAN_FILL_VALUE)
    chloro_raw.set_fill_value(NAN_FILL_VALUE)
    chloro_calc.set_fill_value(NAN_FILL_VALUE)
    fdom_raw.set_fill_value(NAN_FILL_VALUE)
    fdom_calc.set_fill_value(NAN_FILL_VALUE)

    triplet_data.update({
        'scatter_raw': scatter_raw,
        'scatter_calculated': scatter_calc,
        'chloro_raw': chloro_raw,
        'chloro_calculated': chloro_calc,
        'fdom_raw': fdom_raw,
        'fdom_calculated': fdom_calc
    })


def _set_wmt_fill_value_to_nan(wmt_data: dict):
    """Set wmt fill value to NAN.
    A mask is made where `Sm` (mean wind speed) values are equal to 999.0 and applied to all wmt values.
    """
    mask = wmt_data['Sm'] == WMT_FILL_VALUE
    for key, values in wmt_data.items():
        values[mask] = NAN_FILL_VALUE


class RawVikingDatReader:
    """Use to read RAW dat files from viking buoy.
    The data are puts in VikingData object and are accessible as attributes."

    Methods
    -------
    read:
        1) Parse through the files looking for data between the tags [NOM] and [FIN]
           - For each data block found over all the files, data are put into dictionaries
             and append to list.
        2) The data is then sorted according to their buoy name and put into VikingData
           objets.
           Data transformed from:
               List( {tags: { var1: value, ..., varN: value} } )
           to
               VikingData(var1: MaskedArray, ..., varN: MaskedArray)
        3) If more then one buoy name was found, returns a Dict of VikingData.
           If not only a VikingData.
    """

    def __init__(self):
        self._buoys_data: Optional[Dict[str, VikingData]] = None
        self.buoys: Optional[list] = None

    def __repr__(self):
        _repr = f"""{self.__class__} 
buoys:\n"""
        for buoy_name, viking_data in self._buoys_data.items():
            _repr += f"  {buoy_name}: (length = {len(viking_data)})\n"
        return _repr

    def read(self, filenames, century:int = 21) -> Union[VikingData, Dict[str, VikingData]]:
        filenames = get_files_from_expression(filenames)
        decoded_data = []
        _count = 0
        _num_of_files = len(filenames)
        for _filename in filenames:
            print(f'File read: {_count}/{_num_of_files}', end='\r')
            with open(_filename) as f:
                data_received = f.read()
                decoded_data += _unpack_data_from_tag_strings(filename=_filename, data_received=data_received, century=century)
            _count += 1
        print(f'File read: {_count}/{_num_of_files}')

        self._load_viking_data(decoded_data)

        if len(self._buoys_data) == 1:
            return list(self._buoys_data.values())[0]
        else:
            return self._buoys_data

    def _load_viking_data(self, decoded_data: list):
        """Put the data in  VikingData object"""
        self._buoys_data = {}

        self.buoys = self._get_buoys_info(decoded_data)

        for key, value in self.buoys.items():
            self._buoys_data[key] = VikingData(buoy_name=key, firmware=value['firmware'],
                                               controller_sn=value['controller_sn'])
            self.__setattr__(key, self._buoys_data[key])

        _count = 0
        _num_of_bloc = len(decoded_data)
        for data_block in decoded_data:
            buoy_data = self._buoys_data[data_block['buoy_name']]

            buoy_data.time.append(data_block['time'])
            buoy_data.latitude.append(data_block['latitude_N'])
            buoy_data.longitude.append(data_block['longitude_E'])

            for tag in DATA_TAG:
                tag_data = buoy_data.__dict__[tag]
                if data_block[tag] is None:
                    for key in tag_data.keys():
                        tag_data[key].append(NAN_FILL_VALUE)
                else:
                    for key in tag_data.keys():
                        tag_data[key].append(data_block[tag][key])
            _count += 1
            print(f'Data Ensemble loaded: {_count}/{_num_of_bloc}', end='\r')
        print(f'Data Ensemble loaded: {_count}/{_num_of_bloc}')

        for viking_data in self._buoys_data.values():
            viking_data.reformat()


    @staticmethod
    def _get_buoys_info(decoded_data: list) -> dict:
        buoy_info = {}
        buoys = set([(block['buoy_name'], block['firmware'], block['controller_sn']) for block in decoded_data])
        for buoy_name in set(buoy[0] for buoy in buoys):
            firmware = []
            controller_sn = []
            for buoy in buoys:
                if buoy[0] == buoy_name:
                    firmware.append(buoy[1])
                    controller_sn.append(buoy[2])
            buoy_info[buoy_name] = {'firmware': firmware, 'controller_sn': controller_sn}

        return buoy_info


def _unpack_data_from_tag_strings(filename:str, data_received: str, century: int = 21) -> list:
    """ Decode the data received.

    Parse through the data and iter over each block between the tags [NOM] and [FIN].
    - Select the appropriate decoder for each tag.
    -- Each decoder return the data in a dictionary.
    - Put each data dictionary into a dictionary except for the data in the NOM tag which
       are place in the root dict (time, lon, lat, ...).
    - Data from each block are append to a list

    Returns
    -------
    List[
        {
        time: []
        tag: {var1: [], ... var2:[]},
        },
    ]
    """
    decoded_data = []

    for data_block in DATA_BLOCK_REGEX.finditer(data_received):
        wxt520 = dict().fromkeys(TAG_VARS['WXT520_KEYS'], float(NAN_FILL_VALUE))
        decoded_block = dict().fromkeys(DATA_TAG)
        for data_sequence in DATA_TAG_REGEX.finditer(data_block.group(1)):
            tag = data_sequence.group(1)
            data = data_sequence.group(2)
            try:
                if tag == "NOM":
                    decoded_block.update(_decode_NOM(data, century=century))
                elif tag == "COMP":
                    decoded_block["comp"] = _decode_COMP(data)
                elif tag == "Triplet":
                    decoded_block["triplet"] = _decode_Triplet(data, century=century)
                elif tag == "Par_digi":
                    decoded_block["par_digi"] = _decode_Par_digi(data, century=century)
                elif tag == "SUNA":
                    decoded_block['suna'] = _decode_SUNA(data)
                elif tag == "GPS":
                    decoded_block["gps"] = _decode_GPS(data, century=century)
                elif tag == "CTD":
                    decoded_block["ctd"] = _decode_CTD(data)
                elif tag == "CTDO":
                    decoded_block["ctdo"] = _decode_CTDO(data)
                elif tag == "RTI":
                    decoded_block["rti"] = _decode_RTI(data)
                elif tag == "RDI":
                    decoded_block["rdi"] = _decode_RDI(data, century=century)
                elif tag == "WAVE_M":
                    decoded_block["wave_m"] = _decode_WAVE_M(data)
                elif tag == "WAVE_S":
                    decoded_block["wave_s"] = _decode_WAVE_S(data)
                elif tag == "WXT520":
                    wxt520.update(_decode_WXT520(data))
                elif tag == "WMT700":
                    decoded_block["wmt700"] = _decode_WMT700(data)
                elif tag == "WpH":
                    decoded_block["wph"] = _decode_WpH(data)
                elif tag == "CO2_W":
                    decoded_block["co2_w"] = _decode_CO2_W(data)
                elif tag == "CO2_A":
                    decoded_block["co2_a"] = _decode_CO2_A(data)
                elif tag == "Debit":
                    decoded_block["debit"] = _decode_Debit(data)
                elif tag == 'MO':
                    decoded_block["mo"] = _decode_MO(data)

            except (TypeError, ValueError, KeyError, AttributeError) as err:
                print(f'\n\n>>>> Error decoding data in file: {filename}')
                print(f'\n>>>> Error:\n {err}')
                print('\n>>>> Block:')
                print(f'{data_block.group(1)}')
                print(f'\n>>>> Tag:\n {tag}')
                print(f'\n>>>> Data:\n {data}')
                sys.exit()

        if bool(wxt520.keys()) is True:
            decoded_block["wxt520"] = wxt520
        decoded_data.append(decoded_block)

    return decoded_data


def _decode_NOM(data: str, century: int) -> Optional[dict]:
    data = data.strip('\n').split(',')
    if len(data) != 9:
        return None
    latitude, longitude = NAN_FILL_VALUE, NAN_FILL_VALUE
    if "#" not in data[7]:
        _lat = data[7].split(' ')
        latitude = {'S': -1, 'N': 1}[_lat[1][-1]] * (int(_lat[0]) + round(float(_lat[1][:-1]) / 60, 4))
        _lon = data[8].split(' ')
        longitude = {'W': -1, 'E': 1}[_lon[1][-1]] * (int(_lon[0]) + round(float(_lon[1][:-1]) / 60, 4))
    return {'buoy_name': data[0],#.lower().replace(' ', '_').replace('-', '_'), # I dont remember why I did that.
            'time': _make_timestamp(str(century - 1) + data[2][4:6], data[2][2:4], data[2][0:2],
                                    data[1][0:2], data[1][2:4], data[1][4:6]),
            'firmware': data[3],
            'controller_sn': data[4],
            # 'pc_data_flash': data[5],
            # 'pc_winch_flash': data[6],
            'latitude_N': latitude,
            'longitude_E': longitude}


def _decode_COMP(data: str) -> Optional[dict]:
    """
    [COMP],FFCFBEF1,FFE17319,-2.565,17.36,-0.033,5.205,4.869,8.062
    0: total of the sinus of the heading.
    1: total of the cosine of the heading.
    """
    data = data.strip('\n').split(',')
    if len(data) != 8:
        return None
    sum_sinus = struct.unpack('>i', bytes.fromhex(data[0]))[0]
    sum_cosinus = struct.unpack('>i', bytes.fromhex(data[1]))[0]
    pitch = _safe_float(data[2])
    roll = _safe_float(data[4])
    #sum_sinus, sum_cosinus = _compass_tilt_correction(sum_sinus, sum_cosinus, pitch, roll)
    heading = round(atan2(sum_sinus, sum_cosinus) / pi * 180, 2)
    return {'heading': heading,
            'pitch': pitch,
            'roll': roll,
            'tilt': _safe_float(data[6]),
            'pitch_std': round(sqrt(_safe_float(data[3])), 2),
            'roll_std': round(sqrt(_safe_float(data[5])), 2),
            'tilt_std': round(sqrt(_safe_float(data[7])), 2)}


def _decode_Triplet(data: str, century: int) -> Optional[dict]:
    data = data.strip('\n').split('\t')
    if len(data) != 12:
        return None
    date = data[1].split('/')
    hours = data[2].split(":")
    ids = data[0].split('-')
    wave_length = tuple(map(_safe_float, [data[3], data[6], data[9]]))
    raw_value = tuple(map(_safe_float, [data[4], data[7], data[10]]))
    calculated_value = tuple(map(_safe_float, [data[5], data[8], data[11]]))
    return {'time': _make_timestamp(str(century - 1) + date[2], date[0], date[1], hours[0], hours[1], hours[2]),
            'model_number': ids[0],
            'serial_number': ids[1],
            'wavelength_1': wave_length[0], 'raw_value_1': raw_value[0], 'calculated_value_1': calculated_value[0],
            'wavelength_2': wave_length[1], 'raw_value_2': raw_value[1], 'calculated_value_2': calculated_value[1],
            'wavelength_3': wave_length[2], 'raw_value_3': raw_value[2], 'calculated_value_3': calculated_value[2]
            }


def _decode_Par_digi(data: str, century: int) -> Optional[dict]:
    data = data.strip('\n').split(',')
    if len(data) != 9:
        return None
    model_number, serial_number = re.match(r".*?([A-z]+)([0-9]+)", data[2]).groups()
    return {'time': _make_timestamp(str(century - 1) + data[1][4:6], data[1][2:4], data[1][0:2],
                                    data[0][0:2], data[0][2:4], data[0][4:6]),
            'model_number': model_number,
            'serial_number': serial_number,
            'timer_s': _safe_float(data[4]),
            'par': _safe_float(data[4]),
            'pitch': _safe_float(data[5]),
            'roll': _safe_float(data[6]),
            'intern_temperature': _safe_float(data[7]), }


def _decode_SUNA(data: str) -> Optional[dict]:
    """[SUNA],SATSLC1363,2021144,10.499913,-3.28,-0.0460,0.0809,0.0645,0.00,0.000086"""
    data = data.replace(' ', '').split(',')
    if len(data) != 9:
        return None
    model_number, serial_number = re.match(r".*?([A-z]+)([0-9]+)", data[0]).groups()
    time = NAN_FILL_VALUE
    if '#' not in data[1] + data[2]:
        time = (datetime(int(data[1][0:4]), 1, 1)
                + timedelta(days=int(data[1][4:]), hours=float(data[2]))).strftime('%Y-%m-%dT%H:%M:%S')
    return {"time": time,
            "model_number": model_number,
            "serial_number": serial_number,
            "nitrate": _safe_float(data[3]),
            "nitrogen": _safe_float(data[4]),
            "absorbance_254_31": _safe_float(data[5]),
            "absorbance_350_16": _safe_float(data[6]),
            "bromide": _safe_float(data[7]),
            "spectrum_average": _safe_float(data[8])}


def _decode_GPS(data: str, century: int) -> Optional[dict]:
    """
           0 1         2 3          4 5     6     7      8     9
     '110132,A,4839.7541,N,06834.8903,W,003.7,004.4,240521,017.5,W,*7B'
     """
    data = data.strip('\n').split(',')
    if len(data) != 11:
        return None
    lat_minutes = float(data[2][-7:-2])
    lon_minutes = float(data[4][-7:-2])
    lat = (int(data[2][:-7]) + round(lat_minutes / 60, 4))
    lon = (int(data[4][:-7]) + round(lon_minutes / 60, 4))
    return {'time': _make_timestamp(str(century - 1) + data[8][4:6], data[8][2:4], data[8][0:2],
                                    data[0][0:2], data[0][2:4], data[0][4:6]),
            'latitude_N': {'S': -1, 'N': 1}[data[3]] * lat,
            'longitude_E': {'W': -1, 'E': 1}[data[5]] * lon,
            'speed': _safe_float(data[6]),
            'course': _safe_float(data[7]),
            'variation_E': {'W': -1, 'E': 1}[data[10][0]] * float(data[9]),
            'validity': data[1]}

    # 'checksum': _safe_int(data[8])}


def _decode_CTD(data: str) -> Optional[dict]:
    """"""
    for s in ('\n', ','):
        data = data.strip(s)
    data = data.replace(' ', '').split(',')

    if len(data) != 4:
        return None
    return {'temperature': _safe_float(data[0]),
            'conductivity': _safe_float(data[1]),
            'salinity': _safe_float(data[2]),
            'density': _safe_float(data[3])}


def _decode_CTDO(data: str) -> Optional[dict]:
    """No test string in files."""
    for s in ('\n', ','):
        data = data.strip(s)
    data = data.replace(' ', '').split(',')

    if len(data) != 4:
        return None
    return {'temperature': _safe_float(data[0]),
            'conductivity': _safe_float(data[1]),
            'dissolved_oxygen': _safe_float(data[2]),
            'salinity': _safe_float(data[3])}


def _decode_RTI(data: str) -> Optional[dict]:
    """
    Data are in meters (SI)
    """
    data = data.replace('\n', ',').split(',')
    position_cm = _safe_float(data[1])
    beam_vel_mms = tuple(map(_safe_float, data[2:6]))
    enu_mms = tuple(map(_safe_float, data[6:10]))
    corr_pc = tuple(map(_safe_float, data[10:14]))
    amp_dB = tuple(map(_safe_float, data[14:18]))
    bt_beam_vel_mms = tuple(map(_safe_float, data[19:23]))
    bt_enu_mms = tuple(map(_safe_float, data[23:27]))
    bt_corr_pc = tuple(map(_safe_float, data[27:31]))
    bt_amp_dB = tuple(map(_safe_float, data[31:35]))
    if len(data) != 36:
        return None
    return {'bin': _safe_float(data[0]),
            'position_cm': position_cm,
            'beam1': beam_vel_mms[0], 'beam2': beam_vel_mms[1],
            'beam3': beam_vel_mms[2], 'beam4': beam_vel_mms[3],
            'u': enu_mms[0], 'v': enu_mms[0], 'w': enu_mms[0], 'e': enu_mms[3],
            'corr1': corr_pc[0], 'corr2': corr_pc[1], 'corr3': corr_pc[2], 'corr4': corr_pc[3],
            'amp1': amp_dB[0], 'amp2': amp_dB[1], 'amp3': amp_dB[2], 'amp4': amp_dB[3],
            'bt_beam1': bt_beam_vel_mms[0], 'bt_beam2': bt_beam_vel_mms[1],
            'bt_beam3': bt_beam_vel_mms[2], 'bt_beam4': bt_beam_vel_mms[3],
            'bt_u': bt_enu_mms[0], 'bt_v': bt_enu_mms[0],
            'bt_w': bt_enu_mms[0], 'bt_e': bt_enu_mms[3],
            'bt_corr1': bt_corr_pc[0], 'bt_corr2': bt_corr_pc[1],
            'bt_corr3': bt_corr_pc[2], 'bt_corr4': bt_corr_pc[3],
            'bt_amp1': bt_amp_dB[0], 'bt_amp2': bt_amp_dB[1],
            'bt_amp3': bt_amp_dB[2], 'bt_amp4': bt_amp_dB[3],
            }


def _decode_RDI(data: str, century: int) -> Optional[dict]:
    data = data.strip('\n').split(',')
    if len(data) != 3:
        return None
    if data[2] == "No Valid Speed":
        return None
    enu_mms = tuple(struct.unpack('hhhh', bytes.fromhex(data[2])))
    return {'time': _make_timestamp(str(century - 1) + data[1][4:6], data[1][2:4],
                                    data[1][0:2], data[0][0:2], data[0][2:4], data[0][4:6]),
            'u': float(enu_mms[0]), 'v': float(enu_mms[1]), 'w': float(enu_mms[2]), 'e': float(enu_mms[3]),
            }


def _decode_WAVE_M(data: str) -> Optional[dict]:
    data = data.strip('\n').split(',')
    if len(data) != 6:
        return None
    if "#" in data[0]:
        return None
    return {'time': data[0].replace('/', '-') + 'T' + data[1],
            "period": _safe_float(data[2]),
            "average_height": _safe_float(data[3]),
            "significant_height": _safe_float(data[4]),
            "maximal_height": _safe_float(data[5])}


def _decode_WAVE_S(data: str) -> Optional[dict]:
    data = data.strip('\n').split(',')
    if len(data) != 11:
        return None
    time = data[10].replace(' ', 'T')
    return {'time': time,
            'heading': _safe_float(data[1]),
            'average_height': _safe_float(data[2]),
            'dominant_period': _safe_float(data[3]),
            'wave_direction': _safe_float(data[4]),
            'Hmax': _safe_float(data[5]),
            'Hmax2': _safe_float(data[6]),
            'pmax': _safe_float(data[7]),
            'roll': _safe_float(data[8]),
            'pitch': _safe_float(data[9])}


def _decode_WXT520(data: str) -> dict:
    keys = ['Dn', 'Dm', 'Dx', 'Sn', 'Sm', 'Sx',
            'Rc', 'Rd', 'Ri', 'Hc', 'Hd', 'Hi',
            'Ta', 'Ua', 'Pa',
            'Th', 'Vh', 'Vs', 'Vr']
    regex = r'([A-z]+)=(\d+(?:\.\d+)?)'
    decoded_data = dict()  #.fromkeys(keys, float(NAN_FILL_VALUE)) not necessary ? July 2023
    for key, value in re.findall(regex, data.strip('\n')):
        decoded_data[key] = _safe_float(value)
    return decoded_data


def _decode_WMT700(data: str) -> dict:
    keys = ['Dn', 'Dm', 'Dx', 'Sn', 'Sm', 'Sx']
    regex = r'([A-z]+)=(\d+(?:\.\d+)?)'
    decoded_data = dict()  #.fromkeys(keys, float(NAN_FILL_VALUE)) not necessary ? July 2023
    for key, value in re.findall(regex, data.strip('\n')):
        decoded_data[key] = _safe_float(value)
    return decoded_data


def _decode_WpH(data: str) -> Optional[dict]:
    data = data.strip('\n').split(',')
    if len(data) != 11:
        return None
    model, serial_number = re.match(r".*?([A-z]+)([0-9]+)", data[0]).groups()
    return {'model': model,
            'serial_number': serial_number,
            'time': data[1],
            'sample_number': _safe_float(data[2]),
            'error_flag': _safe_float(data[3]),
            'ext_ph': _safe_float(data[4]),
            'int_ph': _safe_float(data[5]),
            'ext_volt': _safe_float(data[6]),
            'int_volt': _safe_float(data[7]),
            'ph_temperature': _safe_float(data[8]),
            'rel_humidity': _safe_float(data[9]),
            'int_temperature': _safe_float(data[10])}


def _decode_CO2_W(data: str) -> Optional[dict]:
    data = data.strip('\n').split(',')
    if len(data) != 15:
        return None
    return {"time": _make_timestamp(*data[1:7]),
            "auto_zero": _safe_float(data[7]),
            "current": _safe_float(data[8]),
            "co2_ppm": _safe_float(data[8]),
            "irga_temperature": _safe_float(data[9]),
            "humidity_mbar": _safe_float(data[10]),
            "humidity_sensor_temperature": _safe_float(data[11]),
            "cell_gas_pressure_mbar": _safe_float(data[12])}


def _decode_CO2_A(data: str) -> Optional[dict]:
    data = data.strip('\n').split(',')
    if len(data) != 15:
        return None
    return {'time': _make_timestamp(*data[1:7]),
            'auto_zero': _safe_float(data[7]),
            'current': _safe_float(data[8]),
            "co2_ppm": _safe_float(data[8]),
            'irga_temperature': _safe_float(data[9]),
            'humidity_mbar': _safe_float(data[10]),
            'humidity_sensor_temperature': _safe_float(data[11]),
            "cell_gas_pressure_mbar": _safe_float(data[12])}


def _decode_Debit(data: str) -> dict:
    if "#" in data:
        return {'flow': NAN_FILL_VALUE}
    else:
        return {'flow': round(int(data.strip('\n'), 16) * 0.001543, 4)}


def _decode_VEMCO(data: str) -> Optional[dict]:
    if "No answer" in data:
        return None
    data = data.replace('\n', '').split(',')
    return {'time': data[0].replace(' ', 'T'),
            'protocol': data[1],
            'serial_number': data[2]}


def _decode_MO(data: str) -> dict:
    adcp_model = {'D': 'RDI', 'T': "RTI"}[data[0]]

    if adcp_model == 'RDI':
        _d = data[97: 113]

        if len(_d) != 118:
            return None

        if '#' in _d:
            enu_mms = [float(np.nan)] * 4
        else:
            enu_mms = list(struct.unpack('hhhh', bytes.fromhex(_d)))
    else:
        _d = data[97: 109]

        if len(_d) != 116:
            return  None

        if '#' in _d:
            enu_mms = [float(np.nan)] * 4
        else:
            enu_mms = list(struct.unpack('<hhh', bytes.fromhex(data[97: 109]))) + [float(np.nan)]

    return {
        'adcp_model': adcp_model,
        'wind_speed': _safe_float(data[1:3]),
        'wind_gust': _safe_float(data[3:6]),
        'wind_direction': _safe_float(data[6:9]),
        'air_temperature': _safe_float(data[9:12])/10,
        'air_humidity': _safe_float(data[12:14]),
        'atm_pressure': _safe_float(data[14:18]) + 1000,
        'temperature': _safe_float(data[18:22])/100,
        'salinity': _safe_float(data[22:26])/100,
        'triplet_700': _safe_float(data[26:30])*10**(_safe_float(data[30:32])-3),#_safe_float()(data[26:30]) * 10 ** (-_safe_float()(data[30:32]) - 3),
        'triplet_695': _safe_float(data[32:36])*10**(_safe_float(data[36:38])-3),#_safe_float()(data[32:36]) * 10 ** (-_safe_float()(data[36:38]) - 3),
        'triplet_460': _safe_float(data[38:42])*10**(_safe_float(data[42:44])-3),#_safe_float()(data[38:42]) * 10 ** (-_safe_float()(data[42:44]) - 3),
        'par': _safe_float(data[44:48]),
        'co2_ppm_water': _safe_float(data[48:53]) / 10,
        'co2_ppm_air': _safe_float(data[53:58]) / 10,
        'ph': _safe_float(data[58:63]) / 10000,
        'wave_period': _safe_float(data[63:66]) / 10,
        'wave_average_height': _safe_float(data[66:68]) / 10,
        'wave_maximal_height': _safe_float(data[68:71]) / 10,
        'power_voltage': _safe_float(data[71:74])/10,
        'solar_charging': _safe_float(data[74:76]) / 10,
        'wind_charging': _safe_float(data[76:78]) / 10,
        'power_consumption': _safe_float(data[78:80]) / 10,
        'pitch' : _safe_float(data[80:82]),
        'roll': _safe_float(data[82:84]),
        'water_flow': _safe_float(data[84:86]) / 10,
        'heading': _safe_float(data[86:89]),
        'speed': _safe_float(data[89:91]),
        'course': _safe_float(data[91:94]),
        'rain': _safe_float(data[94:97]),
        'u': enu_mms[0] / 1000,
        'v': enu_mms[1] / 1000,
        'w': enu_mms[2] / 1000,
        'e': enu_mms[3] / 1000,
    }


def _safe_float(value: str, ) -> Union[float]:
    try:
        return float(NAN_FILL_VALUE) if '#' in value else float(value)
    except ValueError:
        return float(NAN_FILL_VALUE)


def _make_timestamp(Y: str, M: str, D: str, h: str, m: str, s: str) -> str:
    time = Y + "-" + M + "-" + D + "T" + h + ":" + m + ":" + s
    return 'NaT' if "#" in time else time


if __name__ == "__main__":
    import matplotlib.pyplot as plt


    _path = '/home/jeromejguay/ImlSpace/Data/pmza_2022/raw/IML-11/*.dat'

    bd = RawVikingDatReader().read(_path)


