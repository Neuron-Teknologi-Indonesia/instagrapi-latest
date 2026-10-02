"""Stored device profiles without a Bloks hash must hydrate a supported pair."""

from instagrapi_latest import Client, config

LEGACY_DEVICE = {
    "cpu": "mt6768",
    "dpi": "480dpi",
    "model": "V2333",
    "device": "V2333",
    "resolution": "1080x2196",
    "app_version": "415.0.0.36.76",
    "manufacturer": "vivo",
    "version_code": "793020341",
    "android_release": "15.0.0",
    "android_version": 35,
}

SUPPORTED_PAIR = config.APP_SETTINGS[config.DEFAULT_APP_VERSION]


def test_legacy_profile_without_bloks_hydrates_the_default_pair():
    client = Client()
    client.set_device(dict(LEGACY_DEVICE))

    assert client.app_profile_hydrated is True
    assert client.device_settings["app_version"] == config.DEFAULT_APP_VERSION
    assert client.device_settings["version_code"] == SUPPORTED_PAIR["version_code"]
    assert client.bloks_versioning_id == SUPPORTED_PAIR["bloks_versioning_id"]
    assert client.device_settings["model"] == "V2333"
    assert config.DEFAULT_APP_VERSION in client.user_agent


def test_supported_pair_is_kept_untouched():
    device = dict(LEGACY_DEVICE)
    device.update(SUPPORTED_PAIR)

    client = Client()
    client.set_device(device)

    assert client.app_profile_hydrated is False
    assert client.device_settings["app_version"] == config.DEFAULT_APP_VERSION
    assert client.bloks_versioning_id == SUPPORTED_PAIR["bloks_versioning_id"]


def test_explicit_app_selection_clears_the_hydration_flag():
    client = Client()
    client.set_device(dict(LEGACY_DEVICE))
    assert client.app_profile_hydrated is True

    client.set_app("449.0.0.48.84")

    assert client.app_profile_hydrated is False
    assert client.device_settings["app_version"] == "449.0.0.48.84"
