# weather_processor.py
import numpy as np
import pandas as pd
from services.coefficient import coefficient_config as config


def sigmoid(x, slope=1.0, shift=0.0):
    return 1.0 / (1.0 + np.exp(-slope * (x - shift)))


def tanh_scaled(x, scale=1.0, shift=0.0):
    return np.tanh((x - shift) / scale)


def detect_extreme_weather(row, hour):
    offset = 0.0
    if not config.EXTREME_WEATHER_ENABLED:
        return offset

    wind = row.get("wind_speed_80m (km/h)", 0)
    temp = row.get("apparent_temperature (°C)", 25)

    if wind > config.EXTREME_WIND_THRESHOLD:
        offset += config.EXTREME_WIND_OFFSET
        print(
            f"极端大风预警：风速 {wind:.1f} km/h，施加偏移 {config.EXTREME_WIND_OFFSET:.2f}"
        )

    if temp > config.EXTREME_TEMP_THRESHOLD:
        offset += config.EXTREME_TEMP_OFFSET
        print(
            f"极端高温预警：体感温度 {temp:.1f}℃，施加偏移 {config.EXTREME_TEMP_OFFSET:.2f}"
        )

    return offset


def calculate_effective_temp(apparent_temp, humidity):
    if humidity > config.HUMIDITY_THRESHOLD:
        delta_humidity = humidity - config.HUMIDITY_THRESHOLD
        temp_offset = min(
            config.HUMIDITY_AMP * delta_humidity, config.HEAT_INDEX_MAX_OFFSET
        )
        return apparent_temp + temp_offset
    return apparent_temp


def get_radiation_value(row):
    if (
        config.USE_DIRECT_RADIATION
        and "direct_radiation (W/m²)" in row
        and not pd.isna(row["direct_radiation (W/m²)"])
    ):
        return row["direct_radiation (W/m²)"]
    elif (
        config.USE_DIFFUSE_RADIATION
        and "diffuse_radiation (W/m²)" in row
        and not pd.isna(row["diffuse_radiation (W/m²)"])
    ):
        return row["diffuse_radiation (W/m²)"]
    elif (
        config.USE_DNI
        and "direct_normal_irradiance (W/m²)" in row
        and not pd.isna(row["direct_normal_irradiance (W/m²)"])
    ):
        return row["direct_normal_irradiance (W/m²)"]
    else:
        if "shortwave_radiation (W/m²)" in row:
            return row.get("shortwave_radiation (W/m²)", 0)
        return row.get("shortwave_radiation", 0)


def get_composite_radiation_factor(row):
    direct = row.get("direct_radiation (W/m²)", 0)
    diffuse = row.get("diffuse_radiation (W/m²)", 0)

    if pd.isna(direct) or pd.isna(diffuse):
        rad = row.get("shortwave_radiation (W/m²)", 0)
        return min(1.0, rad / config.RADIATION_MAX_CLEAR_SKY)

    direct_norm = min(1.0, direct / config.RADIATION_MAX_CLEAR_SKY)
    diffuse_norm = min(1.0, diffuse / config.RADIATION_MAX_CLEAR_SKY)
    factor = config.DIRECT_WEIGHT * direct_norm - config.DIFFUSE_WEIGHT * diffuse_norm
    return np.clip(factor, 0.0, 1.0)


def calculate_solar_factor(row, hour):
    if not (6 <= hour <= 18):
        return 0.0

    if config.RADIATION_STRATEGY == "composite":
        base_solar = get_composite_radiation_factor(row)
    else:
        rad = get_radiation_value(row)
        rad_norm = min(1.0, rad / config.RADIATION_MAX_CLEAR_SKY)
        if config.USE_CLOUD_COVER and "cloud_cover_low (%)" in row:
            cloud_cover = row.get("cloud_cover_low (%)", 50)
            cloud_norm = 1 - (cloud_cover / 100.0)
            base_solar = (
                config.RADIATION_WEIGHT * rad_norm
                + (1 - config.RADIATION_WEIGHT) * cloud_norm
            )
        else:
            base_solar = rad_norm

    if config.USE_SUNSHINE_DURATION and "sunshine_duration (s)" in row:
        sunshine_duration = row.get("sunshine_duration (s)", 0)
        sunshine_norm = min(1.0, sunshine_duration / config.SUNSHINE_DURATION_MAX)
        if sunshine_norm == 0 and base_solar > 0.1:
            base_solar = base_solar * 0.3
        else:
            base_solar = base_solar * max(0.1, sunshine_norm)

    if config.WEATHER_CORRECTION_MODE == "nonlinear":
        solar_factor = sigmoid(
            base_solar, slope=config.PV_SIGMOID_SLOPE, shift=config.PV_SIGMOID_SHIFT
        )
    else:
        solar_factor = base_solar

    return np.clip(solar_factor, 0.0, 1.0)


def weather_derived_factor(row, hour):
    cloud = row.get("cloud_cover_low (%)", 50)
    apparent_temp = row.get("apparent_temperature (°C)", 25)
    humidity = row.get("relative_humidity_2m (%)", 65)
    wind = row.get("wind_speed_80m (km/h)", config.WIND_BASE)

    if 9 <= hour <= 16:
        solar_strength = calculate_solar_factor(row, hour)
        pv_offset = config.PV_OFFSET_FACTOR * solar_strength
    else:
        pv_offset = 0.0

    if 12 <= hour <= 21:
        effective_temp = calculate_effective_temp(apparent_temp, humidity)
        if config.WEATHER_CORRECTION_MODE == "nonlinear":
            temp_norm = sigmoid(
                effective_temp,
                slope=config.TEMP_SIGMOID_SLOPE,
                shift=config.TEMP_SIGMOID_THRESHOLD,
            )
            max_offset = config.TEMP_OFFSET_FACTOR * 10
            temp_offset = -max_offset * temp_norm
        else:
            temp_offset = -config.TEMP_OFFSET_FACTOR * (
                effective_temp - config.TEMP_BASE
            )
    else:
        temp_offset = 0.0

    if hour >= 20 or hour <= 6:
        if config.WEATHER_CORRECTION_MODE == "nonlinear":
            wind_dev = wind - config.WIND_TANH_SHIFT
            wind_offset = config.WIND_OFFSET_FACTOR * tanh_scaled(
                wind_dev, scale=config.WIND_TANH_SCALE
            )
        else:
            wind_offset = config.WIND_OFFSET_FACTOR * (wind - config.WIND_BASE)
    else:
        wind_offset = 0.0

    return 1.0 + pv_offset + temp_offset + wind_offset


def calculate_gen_risk_offset(apparent_temp: float):
    if apparent_temp > config.GEN_RISK_TEMP_THRESHOLD:
        excess = apparent_temp - config.GEN_RISK_TEMP_THRESHOLD
        offset = -config.GEN_RISK_PENALTY * excess
        return max(offset, -0.15)
    return 0.0


def calculate_weather_components(row, hour):
    apparent_temp = row.get("apparent_temperature (°C)", 25)
    humidity = row.get("relative_humidity_2m (%)", 65)
    wind = row.get("wind_speed_80m (km/h)", 5)

    if 9 <= hour <= 16:
        solar_strength = calculate_solar_factor(row, hour)
        pv_offset = config.PV_OFFSET_FACTOR * solar_strength
    else:
        pv_offset = 0.0

    effective_temp = calculate_effective_temp(apparent_temp, humidity)
    humidity_contribution = effective_temp - apparent_temp

    if 12 <= hour <= 21:
        temp_from_actual = -config.TEMP_OFFSET_FACTOR * (
            apparent_temp - config.TEMP_BASE
        )
        humidity_offset = -config.TEMP_OFFSET_FACTOR * humidity_contribution
    else:
        temp_from_actual = 0.0
        humidity_offset = 0.0

    if hour >= 20 or hour <= 6:
        wind_offset = config.WIND_OFFSET_FACTOR * (wind - config.WIND_BASE)
    else:
        wind_offset = 0.0

    extreme_offset = detect_extreme_weather(row, hour)

    weather_factor_raw = (
        1.0 + pv_offset + temp_from_actual + humidity_offset + wind_offset
    )

    return {
        "pv_offset": pv_offset,
        "temp_offset": temp_from_actual,
        "humidity_offset": humidity_offset,
        "wind_offset": wind_offset,
        "extreme_offset": extreme_offset,
        "weather_factor_raw": weather_factor_raw,
        "effective_temp": effective_temp,
        "humidity_contribution": humidity_contribution,
    }
