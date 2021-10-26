"""CSC110 Fall 2021 Assignment 3: Forest Fire Weather Index System

Copyright and Usage Information
===============================

This file is provided solely for the personal and private use of students
taking CSC110 at the University of Toronto St. George campus. All forms of
distribution of this code, whether as given or with any changes, are
expressly prohibited. For more information on copyright for CSC110 materials,
please consult our Course Syllabus.

This file is Copyright (c) 2021 Mario Badr and Tom Fairgrieve.
"""
import math
from dataclasses import dataclass

# Initial values that can be used for FFMC, DMC, and DC
INITIAL_FFMC = 85.0
INITIAL_DMC = 6.0
INITIAL_DC = 15.0

# Per-month lookup tables
DMC_DAY_LENGTH_EFFECTIVE = {
    1: 6.5, 2: 7.5, 3: 9.0, 4: 12.8, 5: 13.9, 6: 13.9,
    7: 12.4, 8: 10.9, 9: 9.4, 10: 8.0, 11: 7.0, 12: 6.0
}
DC_DAY_LENGTH_FACTORS = {
    1: -1.6, 2: -1.6, 3: -1.6, 4: 0.9, 5: 3.8, 6: 5.8,
    7: 6.4, 8: 5.0, 9: 2.4, 10: 0.4, 11: -1.6, 12: -1.6
}


@dataclass
class WeatherMetrics:
    """A bundle of metrics that are measured by weather stations.

    Instance Attributes:
        - month: The month of the year (e.g., January is 1, December is 12)
        - day: the day of the month
        - temperature: The noon temperature in degrees Celsius
        - humidity: The noon relative humidity, in %
        - wind_speed: The noon wind speed, in km/h
        - precipitation: The rainfall at noon, in mm

    Representation Invariants:
        - self.month in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12}
        - self.humidity >= 0.0
        - self.wind_speed >= 0.0
        - self.precipitation >= 0.0
    """
    month: int
    day: int
    temperature: float
    humidity: float
    wind_speed: float
    precipitation: float


@dataclass
class FfwiOutput:
    """A bundle of the output metrics in the Canadian Forest Fire Weather Index System.

    Instance Attributes:
        - ffmc: the Fine Fuel Moisture Code
        - dmc: the Duff Moisture Code
        - dc: the Drought Code
        - isi: the Initial Spread Index
        - bui: the Buildup Index
        - fwi: the Fire Weather Index

    Representation Invariants:
        - 0.0 <= self.ffmc <= 101.0
        - self.dmc >= 1.0
        - self.bui >= 0.0
    """
    ffmc: float
    dmc: float
    dc: float
    isi: float
    bui: float
    fwi: float


def calculate_mr(precipitation: float, mo: float) -> float:
    """Return the fine fuel moisture content after rain (mr) based on the effective
    rainfall in precipitation and the fine fuel moisture content from the previous day.

    Preconditions:
        - precipitation > 0.5
    """
    # Equation 2
    rf = precipitation - 0.5

    if mo > 150.0:
        # Equation 3b
        mr = (mo + 42.5 * rf * math.exp(-100.0 / (251.0 - mo)) * (1.0 - math.exp(-6.93 / rf))) + (
            0.0015 * (mo - 150.0) ** 2) * math.sqrt(rf)
    else:
        # Equation 3a
        mr = mo + 42.5 * rf * math.exp(-100.0 / (251.0 - mo)) * (1.0 - math.exp(-6.93 / rf))

    return mr


def calculate_m(wm: WeatherMetrics, ed: float, mo: float) -> float:
    """Return the fine fuel moisture content after drying (m) based on the measurements in wm, the
    EMC for drying in ed, and the fine fuel moisture content from the previous day in mo.

    Preconditions:
        - mo <= 250.0
    """
    if mo == ed:
        return mo

    if mo < ed:
        # Equation 5
        ew = 0.618 * (wm.humidity ** .753) + (10.0 * math.exp((wm.humidity - 100.0) / 10.0)) \
             + 0.18 * (21.1 - wm.temperature) * (1.0 - 1.0 / math.exp(0.115 * wm.humidity))

        if mo <= ew:
            # Use log wetting rate
            # Equation 7a
            k1 = 0.424 * (1.0 - ((100.0 - wm.humidity) / 100.0) ** 1.7) + \
                 (.0694 * math.sqrt(wm.wind_speed)) * (1.0 - ((100.0 - wm.humidity) / 100.0) ** 8)
            kw = k1 * (0.581 * math.exp(0.0365 * wm.temperature))  # Equation 7b
            return ew - (ew - mo) / 10.0 ** kw  # Equation 9
        else:
            return mo

    # Use log drying rate
    # Equation 6a
    k0 = 0.424 * (1.0 - (wm.humidity / 100.0) ** 1.7) + (
            (0.0694 * math.sqrt(wm.wind_speed)) * (1.0 - (wm.humidity / 100.0) ** 8))
    kd = k0 * (0.581 * math.exp(0.0365 * wm.temperature))  # Equation 6b
    m = ed + (mo - ed) / 10.0 ** kd  # Equation 8

    return m


def calculate_ffmc(wm: WeatherMetrics, f0: float) -> float:
    """Return the Fine Fuel Moisture Code (FFMC) based on the measurements in wm and the previous
    day's FFMC in f0.
    """
    # Calculate the fine fuel moisture content from the previous day
    mo = (147.2 * (101.0 - f0)) / (59.5 + f0)  # Equation 1
    if wm.precipitation > 0.5:
        mo = calculate_mr(wm.precipitation, mo)

    if mo > 250.0:
        mo = 250.0

    # Equation 4 - Fine Fuel equilibrium moisture content (EMC) for drying
    ed = 0.942 * (wm.humidity ** .679) + (11.0 * math.exp((wm.humidity - 100.0) / 10.0)) + (
            0.18 * (21.1 - wm.temperature) * (1.0 - 1.0 / math.exp(0.1150 * wm.humidity)))

    m = calculate_m(wm, ed, mo)

    # Equation 10
    f = (59.5 * (250.0 - m)) / (147.2 + m)

    if f > 101.0:
        f = 101.0
    elif f <= 0.0:
        f = 0.0

    return f


def calculate_dmr(precipitation: float, dm0: float) -> float:
    """Calculate the Duff moisture content after rain based on the current precipitation and the
    previous day's DMC in dm0.

    Preconditions:
        - precipitation > 1.5
    """
    rw = 0.92 * precipitation - 1.27  # Equation 11
    wmi = 20.0 + 280.0 / math.exp(0.023 * dm0)  # Equation 12

    if dm0 <= 33.0:
        b = 100.0 / (0.5 + 0.3 * dm0)  # Equation 13a
    else:
        if dm0 <= 65.0:
            b = 14.0 - 1.3 * math.log(dm0)  # Equation 13b
        else:
            b = 6.2 * math.log(dm0) - 17.2  # Equation 13c

    return wmi + (1000 * rw) / (48.77 + b * rw)  # Equation 14


def calculate_dmc_k(temperature: float, humidity: float, month: int) -> float:
    """Return the log drying rate in DMC based on the temperature, humidity, and month."""
    if temperature < -1.1:
        # Cannot use temperatures less than -1.1 in Equation 16
        temperature = -1.1

    # Equations 16 and 17
    return 1.894 * (temperature + 1.1) * (100.0 - humidity) * (
            DMC_DAY_LENGTH_EFFECTIVE[month] * 0.0001)


def calculate_dmc(wm: WeatherMetrics, dm0: float) -> float:
    """Return the Duff Moisture Code (DMC) based on the measurements in wm and the previous day's
    DMC in dm0.
    """
    if wm.precipitation <= 1.5:
        pr = dm0
    else:
        dmr = calculate_dmr(wm.precipitation, dm0)
        pr = 43.43 * (5.6348 - math.log(dmr - 20.0))  # Equation 15

    # The DMC after rain cannot, theoretically, be less than 0; ensure it is at least 0
    pr = max(0.0, pr)

    rk = calculate_dmc_k(wm.temperature, wm.humidity, wm.month)
    d = pr + rk

    if d <= 1.0:
        d = 1.0
    return d


def calculate_qr(precipitation: float, dc0: float) -> float:
    """Return the moisture equivalent after rain based on the current precipitation and the
    previous day's DC in dc0.

    Preconditions:
        - precipitation > 2.8
    """
    rd = 0.83 * precipitation - 1.27  # Equation 18
    qo = 800.0 * math.exp(-dc0 / 400.0)  # Equation 19
    qr = qo + 3.937 * rd  # Equation 20

    return qr


def calculate_dc(wm: WeatherMetrics, dc0: float) -> float:
    """Return the Drought Code (DC) based on the measurements in wm and the previous day's DC in
    dc0.
    """
    temperature = wm.temperature
    if wm.temperature < -2.8:
        temperature = -2.8

    v = 0.36 * (temperature + 2.8) + DC_DAY_LENGTH_FACTORS[wm.month]  # Equation 22
    # The potential evapotranspiration cannot, theoretically, be less than 0; ensure it's at least 0
    v = max(0.0, v)

    if wm.precipitation > 2.8:
        qr = calculate_qr(wm.precipitation, dc0)
        dr = 400 * math.log(800 / qr)  # Equation 21
        return dr + 0.5 * v  # Equation 23
    else:
        return dc0 + 0.5 * v  # Equation 23


def calculate_isi(wm: WeatherMetrics, ffmc: float) -> float:
    """Return the Initial Spread Index (ISI) based on the measurements in wm and the current ffmc.
    """
    mo = 147.2 * (101.0 - ffmc) / (59.5 + ffmc)
    ff = 19.115 * math.exp(mo * -0.1386) * (1.0 + (mo ** 5.31) / 49300000.0)

    return ff * math.exp(0.05039 * wm.wind_speed)


def calculate_bui(dmc: float, dc: float) -> float:
    """Return the Buildup Index (BUI) based on the current dmc and the current dc.
    """
    if dmc <= 0.4 * dc:
        b = (0.8 * dc * dmc) / (dmc + 0.4 * dc)
    else:
        b = dmc - (1.0 - 0.8 * dc / (dmc + 0.4 * dc)) * (0.92 + (0.0114 * dmc) ** 1.7)

    if b < 0.0:
        b = 0.0

    return b


def calculate_fwi(isi: float, bui: float) -> float:
    """Return the Fire Weather Index (FWI) based on the current isi and the current bui.
    """
    if bui <= 80.0:
        f_d = 0.626 * bui ** 0.809 + 2.0  # Equation 28a
    else:
        f_d = 1000.0 / (25. + 108.64 * math.exp(-0.023 * bui))  # Equation 28b

    bb = 0.1 * isi * f_d  # Equation 29
    if bb <= 1.0:
        return bb  # Equation 30b
    else:
        return math.exp(2.72 * (0.434 * math.log(bb)) ** 0.647)  # Equation 30a
