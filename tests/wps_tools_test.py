import numpy as np
from magtogoek.wps.sci_tools import pHEXT_from_voltEXT, phINT_from_voltINT


def test_pHINT_from_voltINT():
    """
    Test value from Seabird documentations
    Notes
    -----
    Sea-Bird Scientific, Technical Note on Calculating pH, Application Note 99
    """
    ph_int = np.array([7.8310])
    temp = np.array([15.8735])
    volt = np.array([-1.010404])
    k0 = -1.438788
    k2 = -1.304895E-3

    assert ph_int[0] == np.round(phINT_from_voltINT(temperature=temp, volt=volt, k0=k0, k2=k2), 4)


def test_pHEXT_from_voltEXT():
    """
    Test value from Seabird documentations
    Notes
    -----
    Sea-Bird Scientific, Technical Note on Calculating pH, Application Note 99
    """
    ph_ext = np.array([7.8454])
    temp = np.array([15.8735])
    psal = np.array([36.817])
    volt = np.array([-0.965858])
    k0 = -1.429278
    k2 = -1.142026E-3

    assert ph_ext[0] == np.round(pHEXT_from_voltEXT(temperature=temp, psal=psal, volt=volt, k0=k0, k2=k2)[0], 4)
