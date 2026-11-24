"""Offline coverage tests for every sensor parser, extractor and entity path."""

from datetime import UTC, datetime, timedelta
import math
from types import SimpleNamespace

import pytest
from test_sensor_defaults import sensors

NOW = datetime(2026, 11, 24, 12, 0, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def fixed_utcnow(monkeypatch):
    """Make relative timestamp assertions deterministic."""
    monkeypatch.setattr(sensors, "dt_util", SimpleNamespace(utcnow=lambda: NOW))


def payload(**sections):
    return dict(sections)


def entity(key, data=None, coordinator=None):
    coordinator = coordinator if coordinator is not None else SimpleNamespace(data=data or {})
    return sensors.ZteNgRouterSensor(
        coordinator=coordinator,
        entry_id="entry",
        router_name="Router",
        key=key,
        name="Sensor",
        device_class=None,
        unit=None,
        state_class=None,
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (0, 0),
        (1.5, 1.5),
        (" 42 ", 42.0),
        ("-", None),
        ("", None),
        ("   ", None),
        ("abc", None),
        ([], None),
        (True, True),
        ("nan", "nan"),
        ("inf", "inf"),
    ],
)
def test_as_number(value, expected):
    result = sensors._as_number(value)
    if isinstance(expected, str) and expected in {"nan", "inf"}:
        assert math.isnan(result) if expected == "nan" else math.isinf(result)
    else:
        assert result == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("", None),
        ("-", None),
        (-1, None),
        ("nan", None),
        ("inf", None),
        ("12.5", 100),
        (10, 80),
        (0, 0),
        ("0", 0),
    ],
)
def test_to_bit_per_s(value, expected):
    assert sensors._to_bit_per_s(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (7, 7),
        (-2, None),
        (True, 1),
        (" 9007199254740993 ", 9007199254740993),
        ("12", 12),
        (12.9, 12),
        (-1.2, None),
        ("nan", None),
        ("inf", None),
        ("-1", None),
        ("-", None),
        ([], None),
    ],
)
def test_bytes_counter(value, expected):
    assert sensors._bytes_counter(value) == expected


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ((None, "", "-", 7, 9), 7),
        (("3x", "4.5"), 4.5),
        ((None, "", []), None),
    ],
)
def test_first_number(values, expected):
    assert sensors._first_number(*values) == expected


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ((None, "-", "  normal  ", 7), "normal"),
        (("3", "x"), 3.0),
        ((None, None, ""), None),
        ((None, [], ""), "[]"),
    ],
)
def test_first_number_or_text(values, expected):
    assert sensors._first_number_or_text(*values) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, None), ("  x  ", "x"), ("-", None), ("", None), (5, "5")],
)
def test_as_text(value, expected):
    assert sensors._as_text(value) == expected


@pytest.mark.parametrize(
    ("data", "key", "expected"),
    [
        ({"data_limit": {"enable": "1"}}, "data_limit_enabled", "on"),
        ({"data_limit": {"enable": 0}}, "data_limit_enabled", "off"),
        ({"data_limit": {"overflow": "1"}}, "data_limit_exceeded", "on"),
        ({"traffic_reset": {"enable": 1}}, "traffic_auto_reset", "on"),
        ({"data_limit": {"type": "1"}}, "data_limit_type", "connection_time"),
        ({"data_limit": {"type": 2}}, "data_limit_type", "data_volume"),
        ({"data_limit": {"value": 3600}}, "data_limit_value", 3600),
        ({"data_limit": {"value": "3600"}}, "data_limit_value", 3600),
        ({"data_limit": {"value": 12.0}}, "data_limit_value", 12),
        ({"data_limit": {"value": True}}, "data_limit_value", None),
        ({"data_limit": {"value": 1.5}}, "data_limit_value", None),
        ({"data_limit": {"value": -1}}, "data_limit_value", None),
        ({"data_limit": {"value": "nan"}}, "data_limit_value", None),
        ({"data_limit": {"ratio": 80}}, "data_limit_warning_percent", 80),
        ({"data_limit": {"ratio": 101}}, "data_limit_warning_percent", None),
        ({"traffic_reset": {"clearday": "31"}}, "traffic_reset_day", 31),
        ({"traffic_reset": {"clearday": 1.5}}, "traffic_reset_day", None),
        ({}, "unrelated_key", None),
    ],
)
def test_data_limit_value(data, key, expected):
    assert sensors._data_limit_value(data, key) == expected


@pytest.mark.parametrize(
    ("meminfo", "expected"),
    [
        (None, None),
        ({}, None),
        ({"total": "100", "avaliable": "20"}, 80),
        ({"total": "100", "available": "80"}, 20),
        ({"total": "nan", "avaliable": "20"}, None),
        ({"total": "0", "avaliable": "0"}, None),
        ({"total": "100", "avaliable": "101"}, None),
        ({"total": "100", "avaliable": "-1"}, None),
        ({"total": "200", "avaliable": "1"}, 99),
    ],
)
def test_ram_usage(meminfo, expected):
    assert sensors._ram_usage(meminfo) == expected


@pytest.mark.parametrize(
    ("data", "key", "expected"),
    [
        ({"gnss": {"LAT": "12.5"}}, "gnss_latitude", 12.5),
        ({"gnss": {"LON": "-170"}}, "gnss_longitude", -170.0),
        ({"gnss": {"LAT": 91}}, "gnss_latitude", None),
        ({"gnss": {"LON": -181}}, "gnss_longitude", None),
        ({"gnss": {"LAT": "nan"}}, "gnss_latitude", None),
        ({}, "gnss_latitude", None),
    ],
)
def test_gnss_coordinate(data, key, expected):
    assert sensors._gnss_coordinate(data, key) == expected


@pytest.mark.parametrize(
    ("cpuinfo", "expected"),
    [
        ([{"name": "all", "usage": "42.345"}, {"name": "core0", "usage": 99}], round(42.345, 2)),
        ([{"name": "cpu0", "usage": 10}, {"name": "all", "idle": 30}], 70),
        ([{"name": "cpu0", "usage": 10}], 10),
        ([{"name": "cpu0", "idle": 20}], 80),
        (["invalid", 3], None),
        ({"usage": 150}, 100),
        ({"cpu_usage": -5}, 0),
        ({"cpuUsage": "12.3"}, 12.3),
        ({"idle": 40}, 60),
        ({}, None),
        (None, None),
    ],
)
def test_cpu_usage_from_cpuinfo(cpuinfo, expected):
    assert sensors._cpu_usage_from_cpuinfo(cpuinfo) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (422000, 1),
        (361000, 3),
        (173800, 5),
        (524000, 7),
        (185000, 8),
        (151600, 28),
        (460000, 40),
        (499200, 41),
        (286400, 75),
        (620000, 78),
        (693334, 79),
        (100, None),
        (999999, None),
        ("x", None),
        (None, None),
    ],
)
def test_nr_band_from_arfcn(value, expected):
    assert sensors._nr_band_from_arfcn(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, 1),
        (1200, 3),
        (1950, 4),
        (2400, 5),
        (2750, 7),
        (3450, 8),
        (6150, 20),
        (9210, 28),
        (9920, 32),
        (37750, 38),
        (38650, 40),
        (41590, 42),
        (43590, 43),
        (60000, None),
        (-1, None),
        ("x", None),
        (None, None),
    ],
)
def test_lte_band_from_earfcn(value, expected):
    assert sensors._lte_band_from_earfcn(value) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        ("", None),
        ("garbage", "garbage"),
        ("26,11,24,12,30,45,4", "2026-11-24T12:30:45+01:00"),
        ("26, 11, 24, 12, 30, 45, -4", "2026-11-24T12:30:45-01:00"),
        ("26,11,24,12,30,45,0", "2026-11-24T12:30:45+00:00"),
        ("26,13,24,12,30,45,0", "26,13,24,12,30,45,0"),
        ("26,11,24,12,30,45,x", "26,11,24,12,30,45,x"),
    ],
)
def test_parse_sms_date(raw, expected):
    assert sensors._parse_sms_date(raw) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (-1, None),
        (0, NOW),
        (10, NOW - timedelta(seconds=10)),
        ("5", NOW - timedelta(seconds=5)),
    ],
)
def test_seconds_ago_to_datetime(value, expected):
    assert sensors._seconds_ago_to_datetime(value) == expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (payload(wan={"mwan_wanlan1_status": "connected", "real_time": 120}), 120),
        (payload(wan={"mwan_wanlan1_status": "PPP_CONNECTED", "real_time": "60"}), 60),
        (
            payload(
                wan={"current_wan_status": "ipv4_connected", "real_time": ""},
                wwandst={"real_time": 30},
            ),
            30,
        ),
        (payload(wan={"mwan_wanlan1_status": "ipv6_connected", "real_time": 45}), 45),
        (payload(wan={"mwan_wanlan1_status": "ipv4_ipv6_connected", "real_time": 50}), 50),
        (payload(wan={"mwan_wanlan1_status": "disconnected", "real_time": 12}), None),
        (payload(wan={"mwan_wanlan1_status": "connected", "real_time": "unavailable"}), None),
        (payload(), None),
    ],
)
def test_connected_session_seconds(data, expected):
    assert sensors._connected_session_seconds(data) == expected


@pytest.mark.parametrize(
    ("data", "expected"),
    [(payload(device={"device_uptime": "100"}), 100), (payload(), None)],
)
def test_device_uptime_seconds(data, expected):
    assert sensors._device_uptime_seconds(data) == expected


LTE_METRICS = {
    "lte_pci": "lte_pci",
    "lte_earfcn": "lte_action_channel",
    "lte_rsrp": "lte_rsrp",
    "lte_rsrq": "lte_rsrq",
    "lte_sinr": "lte_snr",
    "lte_rssi": "lte_rssi",
}
NR_METRICS = {
    "nr_pci": "nr5g_pci",
    "nr_arfcn": "nr5g_action_channel",
    "nr_rsrp": "nr5g_rsrp",
    "nr_rsrq": "nr5g_rsrq",
    "nr_sinr": "nr5g_snr",
    "nr_rssi": "nr5g_rssi",
}
TRAFFIC_FIELDS = {
    "daily_download": "day_rx_bytes",
    "daily_upload": "day_tx_bytes",
    "rx_packet_errors": "total_rx_error_packets",
    "tx_packet_errors": "total_tx_error_packets",
    "rx_packet_drops": "total_rx_drop_packets",
    "tx_packet_drops": "total_tx_drop_packets",
}


EXTRACT_CASES = [
    (payload(netinfo={"network_provider_fullname": "Operator"}), "network_provider", "Operator"),
    (payload(netinfo={"network_type": "SA"}), "connection_type", "5G SA"),
    (payload(netinfo={"network_type": "ENDC"}), "connection_type", "5G NSA"),
    (payload(netinfo={"network_type": "LTE"}), "connection_type", "LTE"),
    (payload(wifi_module={"wifi_onoff": 1}), "wifi_onoff", True),
    (payload(wlan={"wifi_onoff": "0"}), "wifi_onoff", False),
    (payload(), "wifi_onoff", None),
    (payload(wlan={"main2g_ssid": "Home2G"}), "main2g_ssid", "Home2G"),
    (payload(wlan={"main5g_ssid": "Home5G"}), "main5g_ssid", "Home5G"),
    (payload(netinfo={"signalbar": "3"}), "signalbar", 3),
    (payload(netinfo={"signalbar": 9}), "signalbar", 5),
    (payload(netinfo={"signalbar": -2}), "signalbar", 0),
    (payload(netinfo={"signalbar": "-"}), "signalbar", None),
    (payload(netinfo={"rmcc": "001"}), "rmcc", "001"),
    (payload(netinfo={"rmnc": "01"}), "rmnc", "01"),
    (payload(netinfo={"rmcc": "-"}), "rmcc", None),
    (payload(netinfo={"rmnc": ""}), "rmnc", None),
    (payload(netinfo={"nr5g_action_band": "n78"}), "nr_active_band", "n78"),
    (payload(netinfo={"nr5g_action_band": "78"}), "nr_active_band", "n78"),
    (payload(netinfo={"wan_active_band": "n41"}), "nr_active_band", "n41"),
    (payload(netinfo={"nr5g_action_channel": 620000}), "nr_active_band", "n78"),
    (payload(), "nr_active_band", None),
    (payload(netinfo={"lte_primary_band": "B3"}), "lte_primary_band", "B3"),
    (payload(netinfo={"lte_action_band": 3}), "lte_primary_band", "B3"),
    (payload(netinfo={"lte_pcell_band": "b7"}), "lte_primary_band", "b7"),
    (payload(netinfo={"network_lte_ca_pcell_band": "20"}), "lte_primary_band", "B20"),
    (payload(netinfo={"wan_active_band": "3"}), "lte_primary_band", "B3"),
    (payload(netinfo={"lte_action_channel": 1850}), "lte_primary_band", "B3"),
    (payload(netinfo={"wan_active_band": "n78"}), "lte_primary_band", None),
    (payload(netinfo={"nr5g_cell_id": "123"}), "nr5g_cell_id", "123"),
    (payload(netinfo={"nr5g_cell_id": "-"}), "nr5g_cell_id", None),
    (payload(netinfo={"lac_code": "456"}), "lac_code", "456"),
    (payload(netinfo={"lac_code": ""}), "lac_code", None),
    (payload(netinfo={"lte_band_lock": "1"}), "lte_band_lock", "1"),
    (payload(netinfo={"gw_band_lock": "0"}), "gw_band_lock", "0"),
    (payload(bands_summary="n78+n1"), "bands_summary", "n78+n1"),
    (payload(bands_summary="-"), "bands_summary", None),
    (payload(bands_summary=""), "bands_summary", None),
    (payload(total_bw_mhz="100.9"), "total_bandwidth", 100),
    (payload(total_bw_mhz=0), "total_bandwidth", None),
    (payload(), "total_bandwidth", None),
    (payload(netinfo={"lte_rsrp": "-100"}), "primary_rsrp", -100.0),
    (payload(netinfo={"nr5g_rsrp": "-95"}), "primary_rsrp", -95.0),
    (payload(), "primary_rsrp", None),
    *[(payload(netinfo={field: "-72.5"}), key, -72.5) for key, field in LTE_METRICS.items()],
    *[(payload(netinfo={field: "-95"}), key, -95.0) for key, field in NR_METRICS.items()],
    (payload(wan={"mwan_wanlan1_wan_ipaddr": "10.0.0.1"}), "wan_ipv4", "10.0.0.1"),
    (payload(wan={"mwan_wanlan1_wan_ipaddr": "0.0.0.0"}), "wan_ipv4", None),
    (payload(wan={"mwan_wanlan1_wan_ipaddr": "-"}), "wan_ipv4", None),
    (payload(wan={"mwan_wanlan1_ipv6_wan_ipaddr": "2001::1"}), "wan_ipv6", "2001::1"),
    (payload(wan={"mwan_wanlan1_ipv6_wan_ipaddr": "0::0"}), "wan_ipv6", None),
    (payload(wan={"mwan_wanlan1_ipv6_wan_ipaddr": "0:0:0:0:0:0:0:0"}), "wan_ipv6", None),
    (payload(wan={"mwan_wanlan1_status": "connected"}), "wan_status", "connected"),
    (payload(wan={"current_wan_status": "ppp_connected"}), "wan_status", "ppp_connected"),
    (payload(), "wan_status", None),
    (payload(wan={"mwan_wanlan1_link_state": "up"}), "wan_link_state", "up"),
    (payload(sim_info={"modem_main_state": "ready"}), "modem_main_state", "ready"),
    (payload(netinfo={"modem_main_state": "ready"}), "modem_main_state", "ready"),
    (payload(), "modem_main_state", None),
    (payload(wlan={"RadioOff": "1"}), "radio_off", True),
    (payload(wlan={"RadioOff": "0"}), "radio_off", False),
    (payload(wifi_module={"wifi_onoff": "0"}), "radio_off", True),
    (payload(wlan={"wifi_onoff": "0"}), "radio_off", True),
    (payload(wlan={"radio2_disabled": "1", "radio5_disabled": "1"}), "radio_off", True),
    (payload(wlan={"radio2_disabled": "1", "radio5_disabled": "0"}), "radio_off", False),
    (payload(wifi_module={"wifi_onoff": "1"}), "radio_off", False),
    (payload(wifi_module={"wifi_onoff": "2"}), "radio_off", None),
    (payload(), "radio_off", None),
    (
        payload(device={"hightemp_datalimit_status": "normal"}),
        "hightemp_datalimit_status",
        "normal",
    ),
    (payload(thermal={"5g_modem_temperature": "31"}), "5g_modem_temperature", 31.0),
    (payload(thermal={"modem_temperature": "28.5"}), "modem_temperature", 28.5),
    (payload(thermal={"pa_temp_level": "normal"}), "pa_temp_level", "normal"),
    (payload(sim_info={"tj_temp_level": "2"}), "tj_temp_level", 2.0),
    (payload(user_list_num={"lan_num": "3"}), "connected_lan_devices", 3),
    (payload(user_list_num={"lan_num": "-"}), "connected_lan_devices", None),
    (payload(user_list_num={"wireless_num": 5}), "connected_wifi_devices", 5),
    (payload(user_list_num={"wireless_num": "-"}), "connected_wifi_devices", None),
    (payload(wwandst={"real_rx_speed": "12.5"}), "download_rate", 100),
    (payload(wwandst={"real_rx_speed": "-"}, wan={"real_rx_speed": 2}), "download_rate", 16),
    (payload(), "download_rate", None),
    (payload(wwandst={"real_tx_speed": "1"}), "upload_rate", 8),
    (payload(wwandst={"real_tx_speed": ""}, wan={"real_tx_speed": "10.5"}), "upload_rate", 84),
    (
        payload(wwandst_monthly={"month_rx_bytes": "9007199254740993"}),
        "monthly_download_mb",
        9007199254740993,
    ),
    (payload(wan={"month_rx_bytes": "2048"}), "monthly_download_mb", 2048),
    (payload(wwandst_monthly={"month_tx_bytes": "1024"}), "monthly_upload_mb", 1024),
    (payload(wan={"month_tx_bytes": "512"}), "monthly_upload_mb", 512),
    *[
        (payload(wwandst={field: "9007199254740993"}), key, 9007199254740993)
        for key, field in TRAFFIC_FIELDS.items()
    ],
    (payload(data_limit={"enable": "1"}), "data_limit_enabled", "on"),
    (payload(device={"meminfo": {"total": "200", "avaliable": "50"}}), "ram_usage", 75),
    (
        payload(
            firmware={
                "current_upgrade_state": "fota_idle",
                "new_version_state": "version_has_new_optional_software",
            }
        ),
        "firmware_update_status",
        "version_has_new_optional_software",
    ),
    (
        payload(firmware={"current_upgrade_state": "downloading"}),
        "firmware_update_status",
        "downloading",
    ),
    (payload(firmware={"dm_new_version": "V2"}), "firmware_latest_version", "V2"),
    (
        payload(firmware={"dm_new_version": "version_number_abnormal"}),
        "firmware_latest_version",
        None,
    ),
    (
        payload(firmware={"dm_pkg_total_size": "400", "dm_download_pkg_size": "100"}),
        "firmware_download_progress",
        25,
    ),
    (
        payload(firmware={"dm_pkg_total_size": 100, "dm_download_pkg_size": 500}),
        "firmware_download_progress",
        100,
    ),
    (
        payload(firmware={"dm_pkg_total_size": 0, "dm_download_pkg_size": 10}),
        "firmware_download_progress",
        None,
    ),
    (
        payload(firmware={"dm_pkg_total_size": 100, "dm_download_pkg_size": -1}),
        "firmware_download_progress",
        None,
    ),
    (
        payload(firmware={"dm_pkg_total_size": "nan", "dm_download_pkg_size": 10}),
        "firmware_download_progress",
        None,
    ),
    (payload(gnss={"LAT": "-12.345", "LON": "8", "FIX": "1"}), "gnss_latitude", -12.345),
    (payload(gnss={"LAT": "-12.345", "LON": "8", "FIX": "1"}), "gnss_longitude", 8.0),
    (payload(gnss={"FIX": "1"}), "gnss_fix", "1"),
    (payload(sms={"messages": [1, 2]}), "sms_count", 2),
    (payload(sms={"messages": "not a list"}), "sms_count", 0),
    (payload(sms={"capacity": {"sms_dev_unread_num": "3"}}), "sms_unread_total", 3),
    (payload(sms={"capacity": {"sms_nv_total": "100"}}), "sms_nv_total", 100),
    (payload(sms={"capacity": {"sms_sim_total": "50"}}), "sms_sim_total", 50),
    (payload(sms={"capacity": {"sms_nvused_total": "12"}}), "sms_nv_used_total", 12),
    (
        payload(sms={"latest": {"date": "26,11,24,12,30,45,0"}}),
        "sms_latest",
        "2026-11-24T12:30:45+00:00",
    ),
    (payload(sms={"latest": {"date": "raw-date"}}), "sms_latest", "raw-date"),
    (payload(sms={"latest": "not a dict"}), "sms_latest", None),
    (payload(wan={"real_time": "10"}), "connected_time", NOW - timedelta(seconds=10)),
    (payload(wwandst={"real_time": "20"}), "connected_time", NOW - timedelta(seconds=20)),
    (payload(wan={"real_time": "-"}), "connected_time", None),
    (payload(common_config={"hardware_version": "HW1"}), "hardware_version", "HW1"),
    (payload(common_config={"wa_inner_version": "V1"}), "wa_inner_version", "V1"),
    (payload(device={"cpuinfo": [{"name": "all", "usage": "42"}]}), "cpu_usage", 42),
    (payload(device={"cpu_usage": "55"}), "cpu_usage", 55.0),
    (payload(device={"cpuUsage": 60}), "cpu_usage", 60),
    (payload(device={"cpu_load": "61"}), "cpu_usage", 61.0),
    (payload(device={"cpuload": "62"}), "cpu_usage", 62.0),
    (payload(), "cpu_usage", None),
    (payload(thermal={"cpuss_temp": "45.5"}), "cpu_temp", 45.5),
    (payload(device={"device_uptime": "100"}), "uptime", NOW - timedelta(seconds=100)),
    (payload(), "unknown_key", None),
]


@pytest.mark.parametrize(("data", "key", "expected"), EXTRACT_CASES)
def test_extract_value(data, key, expected):
    assert sensors._extract_value(data, key) == expected


@pytest.mark.parametrize(
    ("key", "name", "device_class", "unit", "state_class"),
    sensors.SENSOR_DEFS,
)
def test_entity_metadata(key, name, device_class, unit, state_class):
    data = {"common_config": {"model_name": "G5TC"}}
    sensor = sensors.ZteNgRouterSensor(
        SimpleNamespace(data=data),
        "entry",
        "Router",
        key,
        name,
        device_class,
        unit,
        state_class,
    )
    assert sensor._attr_unique_id == f"entry_{key}"
    assert sensor._attr_translation_key == key
    assert sensor._attr_name == name
    assert sensor._attr_has_entity_name is True
    assert sensor._attr_should_poll is False
    assert getattr(sensor, "_attr_device_class", None) == device_class
    assert getattr(sensor, "_attr_native_unit_of_measurement", None) == unit
    assert getattr(sensor, "_attr_state_class", None) == state_class
    expected_category = "diagnostic" if key in sensors.DIAGNOSTIC_SENSOR_KEYS else None
    assert getattr(sensor, "_attr_entity_category", None) == expected_category
    expected_enabled = key not in sensors.G5TC_OPTIONAL_SENSOR_KEYS
    assert sensor._attr_entity_registry_enabled_default is expected_enabled


@pytest.mark.parametrize(
    ("key", "data", "expected"),
    [
        (
            "network_provider",
            payload(netinfo={"network_provider_fullname": "Operator"}),
            "Operator",
        ),
        (
            "connected_time",
            payload(wan={"mwan_wanlan1_status": "connected", "real_time": 10}),
            NOW - timedelta(seconds=10),
        ),
        ("uptime", payload(device={"device_uptime": 20}), NOW - timedelta(seconds=20)),
    ],
)
def test_native_value(key, data, expected):
    assert entity(key, data).native_value == expected


def test_stable_connected_time_survives_small_drift_and_resets_on_session_change():
    data = payload(wan={"mwan_wanlan1_status": "connected", "real_time": 100})
    sensor = entity("connected_time", data)
    first = sensor.native_value
    assert first == NOW - timedelta(seconds=100)
    data["wan"]["real_time"] = 98
    assert sensor.native_value == first
    assert sensor._last_relative_seconds == 98
    data["wan"]["real_time"] = 80
    second = sensor.native_value
    assert second == NOW - timedelta(seconds=80)
    assert second > first
    data["wan"]["real_time"] = 100
    assert sensor.native_value == second
    data["wan"]["mwan_wanlan1_status"] = "disconnected"
    assert sensor.native_value is None
    assert sensor._stable_timestamp is None
    assert sensor._last_relative_seconds is None


def test_stable_uptime_uses_ten_second_tolerance_and_clears_invalid_values():
    data = payload(device={"device_uptime": 100})
    sensor = entity("uptime", data)
    first = sensor.native_value
    assert first == NOW - timedelta(seconds=100)
    data["device"]["device_uptime"] = 95
    assert sensor.native_value == first
    data["device"]["device_uptime"] = 50
    second = sensor.native_value
    assert second == NOW - timedelta(seconds=50)
    assert second > first
    data["device"]["device_uptime"] = "-"
    assert sensor.native_value is None
    assert sensor._stable_timestamp is None
    assert sensor._last_relative_seconds is None


@pytest.mark.parametrize(
    ("key", "data", "expected"),
    [
        ("network_provider", payload(), None),
        (
            "data_limit_value",
            payload(data_limit={"type": 1}),
            {"limit_type": "connection_time", "value_unit": "s"},
        ),
        (
            "data_limit_value",
            payload(data_limit={"type": "2"}),
            {"limit_type": "data_volume", "value_unit": "router_native"},
        ),
        (
            "data_limit_value",
            payload(data_limit={"type": 3}),
            {"limit_type": None, "value_unit": None},
        ),
        (
            "gnss_latitude",
            payload(gnss={"FIX": "1", "SOURCE": "GNSS", "FIX_TIME": " old "}),
            {"fix": "1", "source": "GNSS", "fix_time": "old"},
        ),
        ("gnss_fix", payload(gnss={"FIX": "0"}), {"fix": "0", "source": None, "fix_time": None}),
        (
            "firmware_update_status",
            payload(firmware={"new_version_state": "offer", "current_upgrade_state": "fota_idle"}),
            {"new_version_state": "offer", "current_upgrade_state": "fota_idle"},
        ),
        (
            "sms_latest",
            payload(
                sms={
                    "capacity": {
                        "sms_nv_total": "100",
                        "sms_sim_total": "50",
                        "sms_nvused_total": "12",
                        "sms_nv_rev_total": "1",
                        "sms_nv_send_total": "2",
                        "sms_nv_draftbox_total": "3",
                        "sms_sim_rev_total": "4",
                        "sms_sim_send_total": "5",
                        "sms_sim_draftbox_total": "6",
                        "sms_dev_unread_num": "7",
                        "sms_sim_unread_num": "8",
                    },
                    "messages": [1, 2],
                    "latest": {
                        "id": 9,
                        "tag": "inbox",
                        "date": "26,11,24,12,30,45,4",
                        "number": "secret",
                        "text": "secret",
                    },
                }
            ),
            {
                "total_messages": 2,
                "capacity_sms_nv_total": "100",
                "capacity_sms_sim_total": "50",
                "capacity_sms_nvused_total": "12",
                "capacity_sms_nv_rev_total": "1",
                "capacity_sms_nv_send_total": "2",
                "capacity_sms_nv_draftbox_total": "3",
                "capacity_sms_sim_rev_total": "4",
                "capacity_sms_sim_send_total": "5",
                "capacity_sms_sim_draftbox_total": "6",
                "capacity_sms_dev_unread_num": "7",
                "capacity_sms_sim_unread_num": "8",
                "latest_id": 9,
                "latest_tag": "inbox",
                "latest_date": "2026-11-24T12:30:45+01:00",
            },
        ),
        (
            "sms_latest",
            payload(sms={"messages": "not a list"}),
            {
                "total_messages": 0,
                "capacity_sms_nv_total": None,
                "capacity_sms_sim_total": None,
                "capacity_sms_nvused_total": None,
                "capacity_sms_nv_rev_total": None,
                "capacity_sms_nv_send_total": None,
                "capacity_sms_nv_draftbox_total": None,
                "capacity_sms_sim_rev_total": None,
                "capacity_sms_sim_send_total": None,
                "capacity_sms_sim_draftbox_total": None,
                "capacity_sms_dev_unread_num": None,
                "capacity_sms_sim_unread_num": None,
            },
        ),
    ],
)
def test_extra_state_attributes(key, data, expected):
    assert entity(key, data).extra_state_attributes == expected
