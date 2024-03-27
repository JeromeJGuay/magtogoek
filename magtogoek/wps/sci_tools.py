"""
Date: January 2023
Made by jeromejguay


This module contains Water Property Sensor (WPS) related mathematical and scientific functions.

Notes:
    This repository has better documentation on functions and additionnal function.
    Could be a good reference for improvements.

    https://github.com/ooici/ion-functions/blob/master/ion_functions/data/do2_functions.py

"""
import numpy as np
import gsw
from typing import Union, List
from magtogoek.sci_tools import celsius_to_kelvin


GAS_CONSTANT = 8.31446261815324  # the constant in seabird docs differs 8.3144621 J/(K mol). Application Note 99
FARADAY_CONSTANT = 96485.365

def compute_in_situ_density(
        temperature: Union[float, np.ndarray],
        salinity: Union[float, np.ndarray],
        pres: Union[float, List, np.ndarray],
        longitude: Union[float, List, np.ndarray] = None,
        latitude: Union[float, List, np.ndarray] = None
):
    """Compute density using seawater package eos80 functions.

    Compute at sea surface if no `pres` is provided.

    Parameters
    ----------
    temperature :
        (ITS-90)
    salinity :
        (pss-78)
    pres :
        dbar
    longitude :

    latitude :

    Returns
    -------
        rho
    """
    if any(salinity < 0): # silence error from gsw.CT_from_t
        salinity = salinity.copy()
        salinity[np.where(salinity < 0)] = np.nan

    absolute_salinity = gsw.SA_from_SP(SP=salinity, p=pres, lon=longitude, lat=latitude)
    conservative_temperature = gsw.CT_from_t(SA=absolute_salinity, t=temperature, p=pres)

    return gsw.rho(SA=absolute_salinity, CT=conservative_temperature, p=pres)


def rinko_raw_data_from_dissolved_oxygen(
        dissolved_oxygen: Union[float, np.ndarray],
        temperature: Union[float, np.ndarray],
        coeffs: List[float],
):
    """Compute raw measurements from dissolved oxygen using the temperature and calibration coefficients.


    ```(Uchida et al., 2010)

    The equation used, differs from the one in Uchida et al. (2010) since we are settings {e0=1, t=0}.

                        1 + d0 * T
              ----------------------------------  - d1
        N =     DO * (c0 + c1 + c2 * T**2) + 1
             -------------------------------------------
                             d2

    DO: dissolved oxygen [umol/L]
    N: raw values
    T: temperatures
    d0, d1, d2, c0, c1, c2: Calibration Coefficients.
    ```

    Parameters
    ----------
    dissolved_oxygen :

    temperature :

    coeffs :
        [d0, d1, d2, c0, c1, c2]

    Returns
    -------
    Raw measurements of dissolved oxygen.

    References
    ----------
    .. [1] Uchida et al. 2010, IOCCP Report Number 14; ICPO Publication Series Number 134,
            CTD Oxygen Sensor Calibration Procedures, DOI: https://doi.org/10.25607/OBP-1344
    """
    d0, d1, d2, c0, c1, c2 = coeffs

    A = 1 + d0 * temperature
    B = dissolved_oxygen * (c0 + c1 + c2 * temperature ** 2) + 1

    return (A / B - d1) / d2


def dissolved_oxygen_from_rinko_raw_measurement(
        raw: Union[float, np.ndarray],
        temperature: Union[float, np.ndarray],
        coeffs: List[float]
):
    """Compute dissolved oxygen from raw measurements using the temperature and calibration coefficients.

    ```(Uchida et al., 2010)

    The equation used, differs from the one in Uchida et al. (2010) since we are settings {e0=1, t=0}.

    Equation used:

                   1 + d0 * T
                -----------------  - 1
        D0 =      d1 + d2 * raw
             ----------------------------
                 c0 + c1 + c2 * T**2

    DO: dissolved oxygen [umol/L]
    N: raw values
    T: temperatures
    d0, d1, d2, c0, c1, c2: Calibration Coefficients.
    ```

    Parameters
    ----------
    raw :

    temperature :

    coeffs :
        [d0, d1, d2, c0, c1, c2]

    Returns
    -------
    Dissolved oxygen [umol/L]

    References
    ----------
    .. [1] Uchida et al. 2010, IOCCP Report Number 14; ICPO Publication Series Number 134,
            CTD Oxygen Sensor Calibration Procedures, DOI: https://doi.org/10.25607/OBP-1344

    """

    d0, d1, d2, c0, c1, c2 = coeffs

    A = 1 + d0 * temperature
    B = d1 + d2 * raw
    C = (c0 + c1 + c2 * temperature ** 2)

    return (A / B - 1) / C


def dissolved_oxygen_correction_winkler(
        dissolved_oxygen: np.ndarray,
        temperature: np.ndarray,
        rinko_coeffs: List[float],
        winkler_coeffs: List[float],
):
    """
    Sensor raw values are retro computed using the calibration coefficients [d0, d1, d2, c0, c1, c2],
    and then the dissolved oxygen is re-computed using the Winkler coefficients [d1_w, d2_w] for [d1, d2].

    Parameters
    ----------
    dissolved_oxygen :

    temperature :

    rinko_coeffs :
        [d0, d1, d2, c0, c1, c2]
    winkler_coeffs :
        Winkler coefficients [d1_w, d2_w]

    Returns
    -------
        Winkler corrected dissolved oxygen.

    Notes
    -----
    Needs to be done on uncorrected data (in pressure or salinity).
    """
    raw = rinko_raw_data_from_dissolved_oxygen(dissolved_oxygen=dissolved_oxygen, temperature=temperature, coeffs=rinko_coeffs)

    rinko_coeffs[1:3] = winkler_coeffs

    return dissolved_oxygen_from_rinko_raw_measurement(raw=raw, temperature=temperature, coeffs=rinko_coeffs)


def dissolved_oxygen_ml_per_L_to_umol_per_L(dissolved_oxygen: Union[float, np.ndarray], inverse=False) -> Union[float, np.ndarray]:
    """
    ```(García and Gordon, 1992)

    O2 [umol/L] = 44.6596 * O2 [ml/L]

    ```

    Parameters
    ----------
    dissolved_oxygen : [ml/L] or [umol/L] if inverse is True

    inverse :
        Do the reverse conversion.

    Returns
    -------
    dissolved_oxygen: [umol/L] or [ml/L] if inverse is True,

    References
    ----------
    .. [1] García and Gordon 1992, Limnology and Oceanography, Oxygen solubility in seawater: Better fitting equations.
    """
    coeff = 44.6596
    if inverse:
        return dissolved_oxygen / coeff
    return coeff * dissolved_oxygen


def dissolved_oxygen_umol_per_L_to_umol_per_kg(dissolved_oxygen: Union[float, np.ndarray], density: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """
    ```

    O2 [umol/kg] =  1000 [L/m3] * O2 [umol/L] / density [kg/m3]

    ```

    Parameters
    ----------
    dissolved_oxygen : [umol/L]
    density : [kg/m3]
        potential density

    Returns
    -------
    dissolved_oxygen [umol/kg]

    """

    return 1000 * dissolved_oxygen / density


def _compute_scaled_temperature(temperature: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """

    ```
    T_s = ln[(298.15 - T) / (273.15 + T)]```

    Parameters
    ----------
    temperature :
        Temperature as measured by in-situ sensor.

    Returns
    -------

    """
    return np.log((298.15 - temperature) / celsius_to_kelvin(temperature))


def phINT_from_voltINT(temperature: Union[float, np.ndarray], volt: Union[float, np.ndarray], k0: float, k2: float) -> Union[float, np.ndarray]:
    """Base on Seabird documentation

    ```(Martz et al. 2010)
    pH_INT = (V_INT - k0_INT - K2_INT * t) / S_nernst

    S_nernst = (R * T * ln(10)) / F

    T : temperature in Kelvin
    t : temperature in Celsius
    V_INT : raw interior voltage
    K0_INT : Interior cell standard potential Offset (From Calibration).
    K2_INT : Interior temperature slope coefficient (From Calibration).
    F : Faraday Constant

    ```

    Parameters
    ----------
    temperature :
        Temperature in Celsius.
    volt :
        Raw interior voltage.
    k0 :
        Interior cell standard potential Offset (From Calibration).
    k2 :
        Interior temperature slope coefficient (From Calibration).

    Returns
    -------
    ph :
        Interior pH

    References
    ----------
    .. [1] T.R. Martz, J. G. Connery, K. S. Johnson. Testing the Honeywell Durafet for seawater pH applications.
           Limnol. Ocean-ogr.: Methods, 8:172-184, 2010.

    .. [2] Sea-Bird Scientific, Technical Note on Calculating pH, Application Note 99

    """

    s_nernst = _compute_s_nernst(temperature)
    return (volt - k0 - k2 * temperature) / s_nernst


def voltEXT_from_pHEXT(ph: Union[float, np.ndarray], temperature: Union[float, np.ndarray], psal: float,
                       k0: float, k2: float) -> Union[float, np.ndarray]:
    """Based on Seabird documentations

    Compute voltExt from the pHext, the temperature measured by the pH probe, the salinity used in the probe configuration
    and the K0 and K2 exterior calibration coefficient.

    ```(Johnson et al. 2016)
    V_EXT = S_nernst*(pH_EXT
                      - log(Cl_T)
                      - 2*log(Y_HCl)_T
                      + log(1 + S_T/K_S)
                      + log((1000 - 1.005 * psal) / 1000))) + k0_EXT + k2_EXT * t

    S_nernst = (R * T * ln(10)) / F

    T : temperature in Kelvin
    t : temperature in Celsius
    psal : salinity in PSU
    V_EXT : raw exterior voltage
    K0_EXT : Exterior cell standard potential Offset (From Calibration).
    K2_Ext : Exterior temperature slope coefficient (From Calibration).
    F : Faraday Constant
    K_S : acid_dissociation_constant_HSO4
    log(Y_HCl)_T : log_of_HCl_activity_as_temperature_function
    ```

    Parameters
    ----------
    ph :
        Exterior pH.
    temperature :
        Temperature in Celsius.
    psal :
        Practical salinity.
    k0 :
        Exterior cell standard potential Offset (From Calibration).
    k2 :
        Exterior temperature slope coefficient (From Calibration).

    Returns
    -------
    volt :
        Exterior Voltage

    References
    ----------
    .. [1] Johnson et al.2016, Analytical Chemistry, DeepSea DuraFET: A pressure tolerant pH sensor designed for global sensor networks.

    .. [2] Sea-Bird Scientific, Technical Note on Calculating pH, Application Note 99
    """
    s_nernst = _compute_s_nernst(temperature)
    cl_t = total_chloride_in_seawater(psal=psal)
    log_y_hcl_t = log_of_HCl_activity_as_temperature_function(temperature=temperature, psal=psal)
    s_t = total_sulfate_in_seawater(psal=psal)
    k_s = acid_dissociation_constant_HSO4(temperature=temperature, psal=psal)

    return k0 + k2 * temperature + s_nernst * (ph
                                               - np.log10(cl_t)
                                               - 2 * log_y_hcl_t
                                               + np.log10(1 + (s_t / k_s))
                                               + np.log10((1000 - 1.005 * psal) / 1000))


def pHEXT_from_voltEXT(volt: Union[float, np.ndarray], temperature: Union[float, np.ndarray],
                       psal: Union[float, np.ndarray], k0: float, k2: float) -> Union[float, np.ndarray]:
    """Taken from Seabird documentations

    Compute pH exterior from the exterior voltage using in-situ temperature and salinity.
    pH exterior can be calculated from the pH value return by the probe with the `voltEXT_from_pHEXT`.

    ```(Johnson et al. 2016)
    pH_EXT = (V_EXT - k0_EXT - k2_EXT * t) / S_nernst
             + log(Cl_T)
             + 2*log(Y_HCl)_T
             - log(1 + S_T/K_S)
             - log((1000 - 1.005 * psal) / 1000))

    S_nernst = (R * T * ln(10)) / F

    T : temperature in Kelvin
    t : temperature in Celsius
    psal : salinity in PSU
    V_EXT : raw exterior voltage
    K0_EXT : Exterior cell standard potential Offset (From Calibration).
    K2_Ext : Exterior temperature slope coefficient (From Calibration).
    F : Faraday Constant
    K_S : acid_dissociation_constant_HSO4
    log(Y_HCl)_T : log_of_HCl_activity_as_temperature_function
    ```

    Parameters
    ----------
    volt :
        Raw exterior voltage.
    temperature :
        Temperature in Celsius.
    psal :
        Practical salinity.
    k0 :
        Exterior cell standard potential Offset (From Calibration).
    k2 :
        Exterior temperature slope coefficient (From Calibration).

    Returns
    -------
    ph :
        Exterior pH

    References
    ----------
    .. [1] Johnson et al.2016, Analytical Chemistry, DeepSea DuraFET: A pressure tolerant pH sensor designed for global sensor networks.

    .. [2] Sea-Bird Scientific, Technical Note on Calculating pH, Application Note 99

    """
    s_nernst = _compute_s_nernst(temperature)
    cl_t = total_chloride_in_seawater(psal=psal)
    log_y_hcl_t = log_of_HCl_activity_as_temperature_function(temperature=temperature, psal=psal)
    s_t = total_sulfate_in_seawater(psal=psal)
    k_s = acid_dissociation_constant_HSO4(temperature=temperature, psal=psal)

    return ((volt - k0 - k2 * temperature) / s_nernst
            + np.log10(cl_t)
            + 2 * log_y_hcl_t
            - np.log10(1 + (s_t / k_s))
            - np.log10((1000 - 1.005 * psal) / 1000))


def _compute_s_nernst(temperature:  Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """
    ```
    s_nernst = R * temperature_Kelvin * ln(10) / F
    ```

    R: Gas Constant -> 8.31446261815324
    F: Faraday Constant -> 96485.365

    """
    return GAS_CONSTANT * celsius_to_kelvin(temperature) * np.log(10) / FARADAY_CONSTANT


def total_chloride_in_seawater(psal: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """Taken from Seabird documentations

    ```(Dickson et al. 2007)
    Cl_T = (0.99889/35.453)*(S/1.80655)*(1000/(1000-1.005*S))

    S : Salinity in PSU
    ```

    Parameters
    ----------
    psal :
        practical salinity

    References
    ----------
    .. [1] Dickson et al. 2007, IOCCP Report No.8, Guide to Best Practices for Ocean CO2 Measurements

    .. [2] Sea-Bird Scientific, Technical Note on Calculating pH, Application Note 99
    """
    return (0.99889 / 35.453) * (psal / 1.80655) * (1000 / (1000 - 1.005 * psal))


def sample_ionic_strength(psal: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """Taken from Seabird documentations

    ```(Dickson et al. 2007)
    I = (19.924*psal)/(1000-1.005*psal)

    psal : Salinity in PSU
    ```

    Parameters
    ----------
    psal :
        practical salinity

    References
    ----------
    .. [1] Dickson et al. 2007, IOCCP Report No.8, Guide to Best Practices for Ocean CO2 Measurements

    .. [2] Sea-Bird Scientific, Technical Note on Calculating pH, Application Note 99
    """
    return (19.924 * psal) / (1000 - 1.005 * psal)


def debye_huckel_HCl_activity_constant(temperature: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """Taken from Seabird documentations

    ```(Khoo et al. 1977)
    A_DH = 0.0000034286 * t**2 + 0.00067524 * t + 0.49172143

    t: temperature in Celsius
    ```

    Parameters
    ----------
    temperature :
        temperature in Celsius

    References
    ----------
    .. [1] Khoo et al. 1977, Analytical Chemistry,
        Determination of hydrogen ion concentrations in seawater from 5C to 40C: standard potentials at salinities 20 to 45%

    .. [2] Sea-Bird Scientific, Technical Note on Calculating pH, Application Note 99
    """
    return 0.0000034286 * temperature ** 2 + 0.00067524 * temperature + 0.49172143


def log_of_HCl_activity_as_temperature_function(temperature: Union[float, np.ndarray], psal: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """Taken from Seabird documentations

    ```(Khoo et al. 1977)
                     -A_DH * sqrt(I)
    log(Y_HCl)_T = --------------------  + (0.08885 - 0.000111 * t) * I
                   1 + 1.394 * sqrt(I)

    t: temperature in Celsius
    I : sample_ionic_strength
    A_DH : HCl_activity_constant
    ```

    Parameters
    ----------
    psal :
        practical salinity
    temperature :
        temperature in Celsius

    References
    ----------
    .. [1] Khoo et al. 1977, Analytical Chemistry,
        Determination of hydrogen ion concentrations in seawater from 5C to 40C: standard potentials at salinities 20 to 45%

    .. [2] Sea-Bird Scientific, Technical Note on Calculating pH, Application Note 99
    """
    a_dh = debye_huckel_HCl_activity_constant(temperature=temperature)
    ionic_s = sample_ionic_strength(psal=psal)

    return -(a_dh * np.sqrt(ionic_s)) / (1 + 1.394 * np.sqrt(ionic_s)) + (0.08885 - 0.000111 * temperature) * ionic_s


def total_sulfate_in_seawater(psal: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """Taken from Seabird Documentations

    ```(Dickson et al. 2007)
    S_T = (0.1400 / 96.062) * (psal / 1.80655)

    psal : Salinity in PSU
    ```

    Parameters
    ----------
    psal :
        practical salinity

    References
    ----------
    .. [1]  Dickson et al. 2007, IOCCP Report No.8, Guide to Best Practices for Ocean CO2 Measurements

    .. [2]  Sea-Bird Scientific, Technical Note on Calculating pH, Application Note 99
    """

    return (0.1400 / 96.062) * (psal / 1.80655)


def acid_dissociation_constant_HSO4(temperature: Union[float, np.ndarray], psal: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """Taken from Seabird documentations

    ```(Dickson et al. 2007)
    K_S = (1 - 0.001005 * S)*exp( a0 + a1 + a2 + a3 + a4)

    a0 = (-4276.1/T) + 141.328 - 23.093 * ln(T)
    a1 = ((-13856/T) + 324.57 - 47.986*ln(T))*sqrt(I)
    a2 = ((35474/T) - 771.54 + 114.723*ln(T))*I
    a3 = -(2698/T)*I**(3/2)
    a4 =  (1776/T)*I**2

    T : temperature in Kelvin
    S : Salinity in PSU
    I : sample_ionic_strength
    ```

    Parameters
    ----------
    psal :
        practical salinity
    temperature :
        temperature in Celsius

    References
    ----------
    .. [1] Dickson et al. 2007, IOCCP Report No.8, Guide to Best Practices for Ocean CO2 Measurements

    .. [2] Sea-Bird Scientific, Technical Note on Calculating pH, Application Note 99
    """
    temp_k = celsius_to_kelvin(temperature)
    ionic_s = sample_ionic_strength(psal=psal)
    a0 = (-4276.1 / temp_k) + 141.328 - 23.093 * np.log(temp_k)
    a1 = ((-13856 / temp_k) + 324.57 - 47.986 * np.log(temp_k)) * np.sqrt(ionic_s)
    a2 = ((35474 / temp_k) - 771.54 + 114.723 * np.log(temp_k)) * ionic_s
    a3 = -(2698 / temp_k) * ionic_s ** (3 / 2)
    a4 = (1776 / temp_k) * ionic_s ** 2

    return (1 - 0.001005 * psal) * np.exp(a0 + a1 + a2 + a3 + a4)


def log_of_HCl_activity_as_temperature_and_pressure_function(psal: Union[float, np.ndarray],
                                                             temperature: Union[float, np.ndarray],
                                                             pres: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """(Khoo et al. 1977)

   log(Y_HCL)_TP = log_t + ((V_HCl * P) / (10 * ln(10) * R * T)) / 2

   log_t : log_of_HCl_activity_as_temperature_function
   V_HCl : partial molal volume of HCl cm**3/mol
   P : pressure in dbar
   R : Gas Constant
   T : temperature in Kelvin

   Parameters
   ----------
   psal :
       practical salinity
   temperature :
       temperature in Celsius
   pres :
       pressure in dbar
   """
    temp_k = celsius_to_kelvin(temperature)
    log_t = log_of_HCl_activity_as_temperature_function(psal=psal, temperature=temperature)
    v_hcl = partial_molal_volume_hcl(temperature=temperature)

    return log_t + ((v_hcl * pres) / (10 * np.log(10) * GAS_CONSTANT * temp_k)) / 2


def partial_molal_volume_hcl(temperature: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """(Millero 1983)

   V_HCl = 17.85 + 0.1044 * t - 0.001316 * t**2

   t: temperature in Celsius

   Parameters
   ----------
   temperature :
       temperature in Celsius

   """
    return 17.85 + 0.1044 * temperature - 0.001316 * temperature ** 2


def dissolved_oxygen_correction_for_salinity_SCOR_WG_142(dissolved_oxygen: np.ndarray, salinity: np.ndarray, temperature: np.ndarray):
    """Compute salinity compensated dissolved oxygen using SCOR WG 142 recommended coefficients.

    ```(Benson and Krause, 1984; García and Gordon, 1992)
    DO_sc = DO*exp[
            a0 + ac
    T_s = ln[(298.15 - T) / (273.15 + T)]

    DO: dissolved oxygen
    T_s : Scaled temperature
    T : temperature as measured by the in-situ sensor
    S : Salinity [PSU]
    a0, a1, a2, a3, a4, a5 = 2.00907, 3.22014, 4.0501, 4.94457, -0.256847, 3.88767
    b0, b1, b2, b3 = -6.24523e-3, -7.37614e-3, -1.03410e-2, -8.17083e-3
    c0 = -4.8868e-7
    ```

    Parameters
    ----------
    dissolved_oxygen :
        Dissolved oxygen as measured by in-situ sensor.
    salinity : [PSU]
        Practical salinity
    temperature :
        temperature as measured by the in-situ sensor

    Returns
    -------
        Salinity compensated dissolved oxygen

    References
    ----------
    .. [1] Benson and Krause 1984, Limnology and Oceanography, The concentration and isotopic fractionation of oxygen
            dissolved in freshwater and seawater in equilibrium with the atmosphere.
    .. [2] García and Gordon 1992, Limnology and Oceanography, Oxygen solubility in seawater: Better fitting equations.
    .. [3] Bittig et al. 2018, SCOR WG 142: Quality Control Procedures for Oxygen and Other Biogeochemical Sensors on
            Floats and Gliders. Recommendations on the conversion between oxygen quantities for Bio-Argo floats and
            other autonomous sensor platforms. https://doi.org/10.13155/45915

    """
    a0, a1, a2, a3, a4, a5 = 2.00907, 3.22014, 4.0501, 4.94457, -0.256847, 3.88767
    b0, b1, b2, b3 = -6.24523e-3, -7.37614e-3, -1.03410e-2, -8.17083e-3
    c0 = -4.8868e-7

    t_s = _compute_scaled_temperature(temperature)

    poly_a = a0 + a1*t_s + a2*t_s**2 + a3*t_s**3 + a4*t_s**4 + a5*t_s**5
    poly_b = b0 + b1*t_s + b2*t_s**2 + b3*t_s**3

    oxy_solubility = np.exp(poly_a + poly_b*salinity + c0*salinity**2)

    return dissolved_oxygen * oxy_solubility


def dissolved_oxygen_correction_for_pressure_JAC(
        dissolved_oxygen: np.ndarray, pressure: np.ndarray
) -> np.ndarray:
    """Dissolved oxygen pressure correction for JAC(ARO-FT) oxygen sensor.

    ```(Thierry et al., 2022; Uchida et al., 2010)

    DO_pc = DO * [1 + cp * Pressure / 1000]

    DO : dissolved oxygen
    Pressure : pressure in dbar

    cp : Pressure coefficient = 0.032

    ```

    Parameters
    ----------
    dissolved_oxygen :
        Dissolved oxygen [umol/kg] (I don't know why the units matters)...
    pressure :
        Pressure in dbar


    Returns
    -------
        Pressure compensated dissolved oxygen.

    References
    ----------
    .. [1] Thierry Virginie, Bittig Henry, Gilbert Denis, Kobayashi Taiyo, Kanako Sato, Schmid Claudia (2022).
            Processing Argo oxygen data at the DAC level. DOI: https://doi.org/10.13155/39795
    .. [2] Uchida et al. 2010, IOCCP Report Number 14; ICPO Publication Series Number 134,
            CTD Oxygen Sensor Calibration Procedures, DOI: https://doi.org/10.25607/OBP-1344

    """
    cp = 0.032

    return dissolved_oxygen * (1 + cp * pressure / 1000)


def pH_correction_for_salinity(
        ph: np.ndarray,
        temperature: np.ndarray,
        salinity: np.ndarray,
        ph_temperature: np.ndarray,
        cal_psal: float,
        k0: float,
        k2: float
) -> np.ndarray:
    """
    Recompute pH using in-situ salinity from a CTD.
    1. Compute the pH probe voltage using:
        -The pH measured by the ph sensor.
        -The temperature measured by the ph sensor (which was used to compute the pH).
        -The constant salinity used.
        -k0 and k1 coefficients.
    2. Compute the pH using:
        -pH probe voltage
        - In-situ temperature and salinity from a CTD
        -k0 and k1 coefficients.


    Parameters
    ----------
    ph :
        ph measured by pH Sensor
    temperature :
        temperature measured by CTD in Celsius
    salinity :
        Practical salinity measured by CTD
    ph_temperature :
        temperature measured by pH sensor.
    cal_psal :
        Constant salinity (From Calibration).
    k0 :
        Exterior cell standard potential Offset (From Calibration).
    k2 :
        Exterior temperature slope coefficient (From Calibration).

    Returns
    -------
        Corrected pH

    """
    volt = voltEXT_from_pHEXT(ph=ph, temperature=ph_temperature, psal=cal_psal, k0=k0, k2=k2)
    ph = pHEXT_from_voltEXT(volt=volt, temperature=temperature, psal=salinity, k0=k0, k2=k2)

    return ph

def air_pco2_from_xco2(xco2: np.ndarray, atmospheric_pressure: np.ndarray) -> np.ndarray:
    """
    ```
    pco2[uatm] = xco2[ppm] * pressure[atm]
    ```

    Parameters
    ----------
    xco2:
        [ppm].
    atmospheric_pressure:
        [atm]
    Returns
    -------
        pco2_air: [air]
    """
    return xco2 * atmospheric_pressure

def water_pco2_from_wet_xco2(xco2: np.array, atmospheric_pressure: np.ndarray) -> np.ndarray:
    """
    ```
    pco2[uatm] = xco2[ppm] * pressure[atm]
    ```

    Parameters
    ----------
    xco2:
        [ppm]
    atmospheric_pressure:
        [atm]

    Returns
    -------
        pco2_water: [uatm]

    See Also
    --------
        water_pco2_from_dry_xco2: for dry xco2 measurements.

    """
    return xco2 * atmospheric_pressure

def water_pco2_from_dry_xco2(
        xco2: np.ndarray, atmospheric_pressure: np.ndarray, salinity: np.ndarray, temperature: np.ndarray
) -> np.ndarray:
    """
    ```
    pco2[uatm] = xco2[ppm] * (pressure[atm] - seawater_vapor_pressure[atm])
    ```

    Parameters
    ----------
    xco2:
        [ppm]
    salinity:
        [PSU]
    temperature:
        temperature [Celsius] at which xCO2 was measured.
    atmospheric_pressure:
        [atm]

    Returns
    -------
        pco2_water

    References
    ----------
    .. [1] Weiss, R., & Price, B. (1980). Nitrous Oxide Solubility in Water and Seawater. Marine Chemistry, 8, 347-359.
            https://doi.org/10.1016/0304-4203(80)90024-9

    See Also
    --------
        water_pco2_from_wet_xco2: for wet xco2 measurements.
    """
    return xco2 * (atmospheric_pressure - compute_seawater_vapor_pressure(salinity=salinity, temperature=temperature))


# Not Used Pro-Oceanus xco2 values are measured wet at 100% humidity saturation
def compute_seawater_vapor_pressure(salinity: np.ndarray, temperature: np.ndarray) -> np.ndarray:
    """
    ```
    ln_kvp = (
        24.4543 - 67.4509 * (100 / t_Kelvin)
        - 4.8489 * np.log(t_Kelvin/ 100)
        - 0.000544 * salinity
    )

    seawater_vapor_pressure = np.exp(ln_kvp)
    ```

    Parameters
    ----------
    salinity:
        [PSU]
    temperature:
        temperature [Celsius]

    Returns
    -------
        seawater vapor pressure [atm]

    References
    ----------
    .. [1] Weiss, R., & Price, B. (1980). Nitrous Oxide Solubility in Water and Seawater. Marine Chemistry, 8, 347-359.
        https://doi.org/10.1016/0304-4203(80)90024-9

    """
    t_Kelvin = celsius_to_kelvin(temperature)
    ln_kvp = (
        24.4543 - 67.4509 * (100 / t_Kelvin)
        - 4.8489 * np.log(t_Kelvin/ 100)
        - 0.000544 * salinity
    )

    return np.exp(ln_kvp)


# Not used. Oceanus-Pro xco2 values seems to be already compensated ?
def water_pco2_temperature_compensation(
        pco2_cell: np.ndarray, temperature_cell: np.ndarray, temperature_in_situ: np.ndarray
) -> np.ndarray:

    """pco2 values are compensated for the temperature difference between the seawater (in-situ) and the
    seawater temperature in the measurement cell.


    ```Taken from the R Package SeaCarb

    pco2 = pco2_cell * exp(0.0423 * (temperature_in_situ - temperature_cell))
    ```

    Parameters
    ----------
    pco2_cell:
        pco2 [ppm] as measured in the cell.
    temperature_cell:
        temperature [Celsius] at which xCO2 was measured.
    temperature_in_situ:
        seawater temperature [Celsius]


    References
    ----------
    .. [1] Pierrot D., Neill C., Sullivan K., Castle R., Wanninkhof R., LÃ¼ger H., Johannessen T., Olsen A.,
            Feely R. A. and Cosca C. E., 2009. Recommendations for autonomous underway pCO2 measuring
            systems and data-reduction routines. Deep-Sea Res. II 56, 512-522.
    .. [2] Takahashi T., Williams R.T., and Ros D.L. (1982) Carbonate chemistry. GEOSECS Pacific Expedition, Volume 3,
            Hydrographic Data 1973-1974, 77-83.
    """

    return pco2_cell * np.exp(0.0423 * (temperature_in_situ - temperature_cell))