"""
Tag Example:

(Note that all Metis Tag Data are transmitted on a single line)

[INIT]PMZA-RIKI,2024-02-08,23:30:00,48°38.459'N,068°09.406'W,-9.04,0.1,0.4,NAN,NAN,17.6,1113.533
[POWR]12.23,0.00,0.00,0.00,0.00,0.00,0.35,0.53,0.00,0,01010100
[ECO1]0.008505,1.737,5.708
[CTD]22.1686,4e-05,0.0108,-2.2537
[PH]NAN,NAN,1,6.8176,6.8225
[NO3]0,NAN,0,NAN,
[WIND]7,20.77,205.78,220.72,0,0.2,0.49
[ATMS]22.7,28.8,1024,30.415,0,0,0
[WAVE]2024-02-08,23:15:00,0,0,0,0
[ADCP]NA,NA,NAN,NAN,NAN,NAN
[WNCH] Mission Completed
[END]


Tag Structure:

[INIT]Buoy_Name,Date,Time,Latitude,Longitude,Heading,Pitch,Roll,Pitch_Std,Roll_Std,COG,SOG,Magnetic_Variation,Water_Detection_Main
[POWR]VBatt1,ABatt1,VBatt2,ABatt2,VSolar,ASolar,AMain,ATurbine,AWinch,PM_RH,Relay_State
[ECO1]Scattering,Chlorophyll,FDOM
[CTD]Temperature,Conductivity,Salinity,Density
[PH]Ext_pH_Calc,Int_pH_Calc,Error_Flag,Ext_pH,Int_pH
[NO3]SUNA_Nitrate, SUNA_Nitrogen, SUNA_Bromide, SUNA_RMSE
[Wind]Source,Wind_Dir_Min,Wind_Dir_Ave,Wind_Dir_Max,Wind_Spd_Min,Wind_Spd_Ave,Wind_Spd_Max
                Source: 7: wmt700, 5: wxt536
[ATMS]Air_Temp,Air_Humidity,Air_Pressure,PAR,Rain_Total,Rain_Duration,Rain_Intensity
[WAVE]Wave_Date,Wave_Time,Wave_Period,Wave_Hm0,Wave_H13,Wave_Hmax
[ADCP]ADCPDate,ADCPTime,EW,NS,Vert,Err
[PCO2]CO2_PPM_Air,CO2_PPM_Water,Pressure_Air,Pressure_Water,Air_Humidity
[WNCH]messages
    messages:
        Air temperature is too low
        Waves are too high
        Wave period is too short
        Buoy is moving too fast
        Voltage is too low
        Mission Completed
        No Mission in Progress
        Mission in Progress
        Mission Started
        No String received from CTD
        Interval not reach
[END]
"""

import re
from typing import Dict, List, Union, Optional

import numpy as np

from magtogoek.utils import get_files_from_expression


DAT_FILE_DATA_STRUCTURE = {
    'init': ['buoy_name', 'date', 'time', 'latitude', 'longitude', 'heading', 'pitch', 'roll',  'pitch_std', 'roll_std',
             'cog', 'sog', 'magnetic_declination', 'water_detection'],
    'powr': ['volt_batt_1', 'amp_batt_1', 'volt_batt_2', 'amp_batt_2', 'volt_solar', 'amp_solar', 'amp_main', 'amp_turbine', 'amp_winch', 'pm_rh', 'relay_state'],
    'eco1': ['scattering', 'chlorophyll', 'fdom'],
    'ctd': ['temperature', 'conductivity', 'salinity', 'density'],
    'ph': ['ext_ph_calc', 'int_ph_calc', 'error_flag', 'ext_ph', 'int_ph'],
    'no3': ['nitrate', 'nitrogen', 'bromide', 'rmse'],
    'wind': ['source', 'wind_dir_min', 'wind_dir_ave', 'wind_dir_max', 'wind_spd_min', 'wind_spd_ave', 'wind_spd_max'],
    'atms': ['air_temperature', 'air_humidity', 'air_pressure', 'par', 'rain_total', 'rain_duration', 'rain_intensity'],
    'wave': ['date', 'time', 'period', 'hm0', 'h13', 'hmax'],
    'adcp': ['date', 'time', 'u', 'v', 'w', 'e'],
    'pco2': ['co2_ppm_air', 'co2_ppm_water', 'gas_pressure_air_mbar', 'gas_pressure_water_mbar', 'air_humidity'],
    'wnch': ['message']
}

INSTRUMENTS_TAG = [_tag.upper() for _tag in DAT_FILE_DATA_STRUCTURE.keys()]

DATA_TAG_REGEX = re.compile(rf"\[({'|'.join(INSTRUMENTS_TAG)})]((?:(?!\[).)*)", re.DOTALL)


METIS_VARIABLES = {
    'init': ['buoy_name', 'time', 'latitude', 'longitude', 'heading', 'pitch', 'roll', 'pitch_std', 'roll_std',
             'cog', 'sog', 'magnetic_declination', 'water_detection'],
    'powr': ['volt_batt_1', 'amp_batt_1', 'volt_batt_2', 'amp_batt_2', 'volt_solar', 'amp_solar', 'amp_main', 'amp_turbine', 'amp_winch', 'pm_rh', 'relay_state'],
    'eco1': ['scattering', 'chlorophyll', 'fdom'],
    'ctd': ['temperature', 'conductivity', 'salinity', 'density'],
    'ph': ['ext_ph_calc', 'int_ph_calc', 'error_flag', 'ext_ph', 'int_ph'],
    'no3': ['nitrate', 'nitrogen', 'bromide', 'rmse'],
    'wind': ['source', 'wind_dir_min', 'wind_dir_ave', 'wind_dir_max', 'wind_spd_min', 'wind_spd_ave', 'wind_spd_max'],
    'atms': ['air_temperature', 'air_humidity', 'air_pressure', 'par', 'rain_total', 'rain_duration', 'rain_intensity'],
    'wave': ['time', 'period', 'hm0', 'h13', 'hmax'],
    'adcp': ['time', 'u', 'v', 'w', 'e'],
    'pco2': ['co2_ppm_air', 'co2_ppm_water', 'gas_pressure_air_mbar', 'gas_pressure_water_mbar', 'air_humidity'],
    'wnch': ['message']
}

METIS_FLOAT_VARIABLES = {
    'init': ['latitude', 'longitude', 'heading', 'pitch', 'roll', 'pitch_std', 'roll_std',
             'cog', 'sog', 'magnetic_declination', 'water_detection'],
    'powr': ['volt_batt_1', 'amp_batt_1', 'volt_batt_2', 'amp_batt_2', 'volt_solar', 'amp_solar', 'amp_main', 'amp_turbine', 'amp_winch'],
    'eco1': ['scattering', 'chlorophyll', 'fdom'],
    'ctd': ['temperature', 'conductivity', 'salinity', 'density'],
    'ph': ['ext_ph_calc', 'int_ph_calc', 'error_flag', 'ext_ph', 'int_ph'],
    'no3': ['nitrate', 'nitrogen', 'bromide', 'rmse'],
    'wind': ['wind_dir_min', 'wind_dir_ave', 'wind_dir_max', 'wind_spd_min', 'wind_spd_ave', 'wind_spd_max'],
    'atms': ['air_temperature', 'air_humidity', 'air_pressure', 'par', 'rain_total', 'rain_duration', 'rain_intensity'],
    'wave': ['period', 'hm0', 'h13', 'hmax'],
    'adcp': ['u', 'v', 'w', 'e'],
    'pco2': ['co2_ppm_air', 'co2_ppm_water', 'gas_pressure_air_mbar', 'gas_pressure_water_mbar', 'air_humidity'],
    'wnch': []
}

NAT_FILL_VALUE = "NaT"
NAN_FILL_VALUE = np.nan

class MetisData:
    """Object to store Metis data.
    Data are store under the tag attribute e.g. self.init, selft. power ... etc.
    """

    def __init__(self, buoy_name: str):
        self.buoy_name: str = buoy_name # required (same as for viking_dat_reader.VikingData)

        self.tags = tuple(t for t in METIS_VARIABLES)

        # coords
        self.time: Union[list, np.ndarray] = [] # required (same as for viking_dat_reader.VikingData)

        self.init = {key: [] for key in METIS_VARIABLES['init']}
        self.powr = {key: [] for key in METIS_VARIABLES['powr']}
        self.eco1 = {key: [] for key in METIS_VARIABLES['eco1']}
        self.ctd = {key: [] for key in METIS_VARIABLES['ctd']}
        self.ph = {key: [] for key in METIS_VARIABLES['ph']}
        self.no3 = {key: [] for key in METIS_VARIABLES['no3']}
        self.wind = {key: [] for key in METIS_VARIABLES['wind']}
        self.atms = {key: [] for key in METIS_VARIABLES['atms']}
        self.wave = {key: [] for key in METIS_VARIABLES['wave']}
        self.adcp = {key: [] for key in METIS_VARIABLES['adcp']}
        self.pco2 = {key: [] for key in METIS_VARIABLES['pco2']}
        self.wnch = {key: [] for key in METIS_VARIABLES['wnch']}

    def __repr__(self):
        repr = (
            f"{self.__class__}\n"
            f"buoy_name: {self.buoy_name}\n"
            f"data: (length: {len(self)})\n"
        )

        for tag in self.tags:
            if self.__dict__[tag] is not None:
                repr += f"  {tag}: (" + ", ".join(list(self.__dict__[tag].keys())) + ")\n"
            else:
                repr += f"  {tag}: (empty)\n"

        return repr

    def __len__(self):
        return len(self.time)

    def drop_empty_tag(self):
        for tag in self.tags:
            if _tag_is_empty(self.__dict__[tag]):
                self.__dict__[tag] = None

    def to_numpy_array(self):
        self.time = np.array(self.time, dtype='datetime64[s]')

        for tag in self.tags:
            if self.__dict__[tag] is not None:
                for variable in self.__dict__[tag]:
                    if variable == 'time':
                        _dtype = 'datetime64[s]'
                    elif variable in METIS_FLOAT_VARIABLES[tag]:
                        _dtype = 'float'
                    else:
                        _dtype = 'str'
                    self.__dict__[tag][variable] = np.array(self.__dict__[tag][variable], dtype=_dtype)


def _tag_is_empty(data: Dict[str, list]):
    for value in data.values():
        if value:
            return False
    return True



class RawMetisDatReader:
    """Read Raw Dta file from Metis Buoy.
    The data are puts in a MetisData object and are accessible as attributes"
    """

    def __init__(self):
        self._buoys_data: Optional[Dict[str, MetisData]] = None
        self.buoys: Optional[list] = None

    def __repr__(self):
        _repr = (f"{self.__class__}"
                 f"    buoys:\n")
        for buoy_name, viking_data in self._buoys_data.items():
            _repr += f"  {buoy_name}: (length = {len(viking_data)})\n"
        return _repr

    def read(self, filenames) -> Union[MetisData, Dict[str, MetisData]]:
        filenames = get_files_from_expression(filenames)
        _num_of_files = len(filenames)

        unpacked_data = []

        _num_file_read = 0
        for _filename in filenames:
            print(f'File read: {_num_file_read}/{_num_of_files}', end='\r')
            with open(_filename, 'r') as f:
                for line in f:
                    _dd = _unpack_data_from_tag_string(line)
                    unpacked_data.append(_dd)
            _num_file_read += 1
        print(f'File read: {_num_file_read}/{_num_of_files}')

        self._load_metis_data(unpacked_data=unpacked_data)

        if len(self._buoys_data) == 1:
            return list(self._buoys_data.values())[0]
        else:
            return self._buoys_data

    def _load_metis_data(self, unpacked_data: List[Dict[str, Dict[str, str]]]):
        self._buoys_data = {}

        buoy_names = set([_d['init']['buoy_name'] for _d in unpacked_data])

        for key in buoy_names:
            self._buoys_data[key] = MetisData(buoy_name=key)
            self.__setattr__(key, self._buoys_data[key])

        _ensemble_count = 0
        _number_of_ensemble = len(unpacked_data)

        for _data in unpacked_data:
            buoy_data = self._buoys_data[_data['init']['buoy_name']]
            buoy_data.time.append(_data['init']['time'])

            for tag in METIS_VARIABLES:
                if tag in _data:
                    for key in _data[tag]:
                        buoy_data.__dict__[tag][key].append(_data[tag][key])
                else:
                    for key in METIS_VARIABLES[tag]:
                        if key == "time":
                            buoy_data.__dict__[tag][key].append(NAT_FILL_VALUE)
                        else:
                            buoy_data.__dict__[tag][key].append(NAN_FILL_VALUE)

            _ensemble_count += 1
        print(f'Data Ensemble loaded: {_ensemble_count}/{_number_of_ensemble}', end='\r')

        for metis_data in self._buoys_data.values():
            metis_data.drop_empty_tag()
            metis_data.to_numpy_array()

def _unpack_data_from_tag_string(data: str) -> Dict[str, Dict[str, str]]:
    """Unpack Metis Tag Data
    Returns Data as a dictionary of {TAG:DATA}
    """

    unpacked_data = {}
    for data_sequence in DATA_TAG_REGEX.finditer(data):
        tag = data_sequence.group(1).lower()
        data = data_sequence.group(2).split(",")

        unpacked_data[tag] = {key: value for key, value in zip(DAT_FILE_DATA_STRUCTURE[tag], data)}

    for tag in ['init', 'wave', 'adcp']:
        if tag in unpacked_data:
            _time = unpacked_data[tag].pop('time')
            _date = unpacked_data[tag].pop('date')
            unpacked_data[tag]['time'] = _make_timestamp(date=_date, time=_time)

    unpacked_data['init']['latitude'] = _degree_minute_to_degree_decimal(unpacked_data['init']['latitude'])
    unpacked_data['init']['longitude'] = _degree_minute_to_degree_decimal(unpacked_data['init']['longitude'])


    return unpacked_data


def _make_timestamp(date: str, time: str) -> str:
    _time = f'{date}T{time}'
    if "NA" in _time: # Fixme maybe remove after fixing 2023 dat?
        return "NaT"                    # Fixme maybe remove after fixing 2023 dat?
    return _time

def _degree_minute_to_degree_decimal(value: str) -> float:
    """

    Parameters
    ----------
    value: Degree minutes
        Format: "48°38.459'N", "48°38.459'S", "068°09.406'W", "068°09.406'E"

    Returns
    -------
       Value in degree deciaml
    """
    m = re.match("(\d+)°(\d+.\d+)'(\S+)", value)
    if m is not None:
        _dd = float(m.group(1)) + float(m.group(2))/60 * {'N':1, 'E':1, 'S':-1, 'W':-1}[m.group(3)]
        return str(round(_dd, 4))
    else:
         return 'NAN'


# if __name__ == '__main__':
#     import matplotlib.pyplot as plt
#
#     filename = "/home/jeromejguay/ImlSpace/Data/pmza_2023/IML-4/PMZA-RIKI_FileTAGS.dat"
#     md = RawMetisDatReader().read(filenames=filename)