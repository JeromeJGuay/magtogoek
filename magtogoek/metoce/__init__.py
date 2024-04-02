"""
Sub-Package for metoce data processing.
"""
SENSOR_TYPES = [
    'pco2',  # co2 atm
    'wave',
    'meteo',  # atm_{humidity, temperature, pressure}
    'wind',
    #'debit',  # water current. NOT LOADED as of feb 2023 # FIXME could be removed
    #'vemco'  # Receptor for tags. NOT LOADED as of feb 2023 # FIXME could be removed
]

GENERIC_PARAMETERS = [
    'time',
    'wind_speed',
    'wind_gust',
    'wind_direction',
    #'wind_gust_direction',
    'atm_temperature',
    'atm_humidity',
    'atm_pressure',
    'wave_mean_height',
    'wave_maximal_height',
    'wave_period',
    'wave_direction',
    'temperature',
    'conductivity',
    'salinity',
    'density',
    'dissolved_oxygen',
    'ph',
    'par',
    'scattering',
    'chlorophyll',
    'fdom',
    'pco2_air',
    'pco2_water',
    'u',
    'v',
    'w',
    'e',
    'pg',
    'pg1',
    'pg2',
    'pg3',
    'pg4',
    'corr1',
    'corr2',
    'corr3',
    'corr4',
    'amp1',
    'amp2',
    'amp3',
    'amp4',
    'bt_u',
    'bt_v',
    'bt_w',
    'bt_e',
    'lon',
    'lat',
    'heading',
    'roll',
    'pitch',
    'roll_std',
    'pitch_std',
    'u_ship',
    'v_ship'
]

FIGURES_VARIABLES = {
    'gsp_position': ['lon', 'lat'],
    'gps_motion': ['speed', 'course', 'u_ship', 'v_ship'],
    'compass': ['heading', 'roll', 'pitch', 'roll_std', 'pitch_std'],
    'velocity': ['u', 'v', 'w'],
    'wind': ["wind_speed", "wind_direction", "wind_gust"],
    'meteo': ['atm_temperature', 'atm_humidity', 'atm_pressure'],
    'wave': ['wave_mean_height', 'wave_maximal_height', 'wave_period', 'wave_direction'],
    'ctdo': ['temperature', 'conductivity', 'salinity', 'density', 'dissolved_oxygen'],
    'ph': ['ph'],
    'par': ['par'],
    'eco': ['scattering', 'chlorophyll', 'fdom'],
    'pco2': ['pco2_air', 'pco2_water']
}