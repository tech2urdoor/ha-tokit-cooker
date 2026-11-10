"""The whole integration set up in a real Home Assistant, talking to the pretend cooker.

    pip install pytest-homeassistant-custom-component
    pytest tests/test_homeassistant.py
"""
from __future__ import annotations

from unittest import mock

import pytest
from fake_cooker import MAC, TOKEN, FakeCooker
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tokit_cooker import config_flow, miio
from custom_components.tokit_cooker.const import DOMAIN

UNIQUE = MAC.lower()
ENTRY_DATA = {"host": "127.0.0.1", "token": TOKEN}
NO_NAMES = [{"piid": 20, "value": ""}, {"piid": 19, "value": ""}]


async def _add(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, unique_id=UNIQUE, title="TOKIT Induction Cooker")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    return entry


async def _remove(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


def _entity_id(hass: HomeAssistant, platform: str, key: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{UNIQUE}_{key}")
    assert entity_id, f"no {platform} entity for {key}"
    return entity_id


def _device(hass: HomeAssistant, entry: MockConfigEntry) -> dr.DeviceEntry:
    (device,) = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    return device


def _state(hass: HomeAssistant, platform: str, key: str) -> str:
    return hass.states.get(_entity_id(hass, platform, key)).state


async def _refresh(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


async def test_reads_a_cooker_that_is_off(hass: HomeAssistant, cooker: FakeCooker) -> None:
    entry = await _add(hass)
    assert _state(hass, "sensor", "status") == "off"
    assert _state(hass, "sensor", "temperature") == "22"
    assert _state(hass, "sensor", "power_level") == "0"
    assert _state(hass, "sensor", "fault") == "none"
    assert _state(hass, "binary_sensor", "heating") == "off"
    assert _state(hass, "binary_sensor", "problem") == "off"
    await _remove(hass, entry)


async def test_the_controls_are_there_without_being_enabled_by_hand(hass: HomeAssistant, cooker: FakeCooker) -> None:
    entry = await _add(hass)
    for platform, key in (
        ("number", "power_level"),
        ("number", "target_temperature"),
        ("button", "stop"),
        ("button", "pause"),
        ("button", "resume"),
    ):
        assert hass.states.get(_entity_id(hass, platform, key)) is not None, key
    await _remove(hass, entry)


async def test_the_device_is_named_after_what_the_cooker_reports(hass: HomeAssistant, cooker: FakeCooker) -> None:
    entry = await _add(hass)
    device = _device(hass, entry)
    assert device.model_id == "chunmi.ihcooker.cbhw"
    assert device.sw_version == "2.2.0_0002"
    await _remove(hass, entry)


async def test_select_mode_loads_the_mode_and_does_not_heat(hass: HomeAssistant, cooker: FakeCooker) -> None:
    entry = await _add(hass)
    await hass.services.async_call(DOMAIN, "select_mode", {"mode": "soup"}, blocking=True)
    await hass.async_block_till_done()
    assert cooker.actions == [(2, 1, [{"piid": 8, "value": 5}])]
    assert _state(hass, "sensor", "status") == "idle"
    assert _state(hass, "sensor", "target_temperature") == "155"
    assert _state(hass, "sensor", "power_level") == "0"
    assert _state(hass, "binary_sensor", "heating") == "off"
    await _remove(hass, entry)


@pytest.mark.parametrize(
    ("mode", "number"), [("hotpot", 1), ("steam_boil", 2), ("stir_fry", 3), ("fry", 4), ("soup", 5)]
)
async def test_each_mode_name_sends_its_own_number(
    hass: HomeAssistant, cooker: FakeCooker, mode: str, number: int
) -> None:
    entry = await _add(hass)
    await hass.services.async_call(DOMAIN, "select_mode", {"mode": mode}, blocking=True)
    assert cooker.actions == [(2, 1, [{"piid": 8, "value": number}])]
    await _remove(hass, entry)


async def test_select_mode_refuses_a_mode_it_does_not_know(hass: HomeAssistant, cooker: FakeCooker) -> None:
    entry = await _add(hass)
    with pytest.raises(Exception):  # noqa: B017, PT011 - voluptuous refuses it before anything is sent
        await hass.services.async_call(DOMAIN, "select_mode", {"mode": "simmer"}, blocking=True)
    assert cooker.actions == []
    await _remove(hass, entry)


async def test_select_mode_takes_a_device(hass: HomeAssistant, cooker: FakeCooker) -> None:
    entry = await _add(hass)
    device = _device(hass, entry)
    await hass.services.async_call(DOMAIN, "select_mode", {"mode": "fry", "device_id": device.id}, blocking=True)
    assert cooker.actions == [(2, 1, [{"piid": 8, "value": 4}])]
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(DOMAIN, "select_mode", {"mode": "fry", "device_id": "nope"}, blocking=True)
    assert len(cooker.actions) == 1
    await _remove(hass, entry)


async def test_power_and_temperature_are_refused_while_it_is_not_cooking(
    hass: HomeAssistant, cooker: FakeCooker
) -> None:
    entry = await _add(hass)
    for key, value in (("power_level", 40), ("target_temperature", 90)):
        with pytest.raises(HomeAssistantError):
            await hass.services.async_call(
                "number", "set_value", {"entity_id": _entity_id(hass, "number", key), "value": value}, blocking=True
            )
    assert cooker.actions == [], "a number must never be the thing that sends the first command"
    await _remove(hass, entry)


async def test_the_controls_once_someone_has_pressed_start(hass: HomeAssistant, cooker: FakeCooker) -> None:
    cooker.press_start()
    entry = await _add(hass)
    assert _state(hass, "sensor", "status") == "cooking"
    assert _state(hass, "binary_sensor", "heating") == "on"

    async def number(key: str, value: int) -> None:
        await hass.services.async_call(
            "number", "set_value", {"entity_id": _entity_id(hass, "number", key), "value": value}, blocking=True
        )

    async def press(key: str) -> None:
        await hass.services.async_call(
            "button", "press", {"entity_id": _entity_id(hass, "button", key)}, blocking=True
        )

    await number("power_level", 30)
    assert cooker.actions[-1] == (3, 13, [{"piid": 9, "value": 30}, *NO_NAMES])
    assert cooker.props[(3, 9)] == 30

    await number("target_temperature", 80)
    assert cooker.actions[-1] == (3, 14, [{"piid": 8, "value": 80}, *NO_NAMES])
    assert cooker.props[(3, 8)] == 80

    await press("pause")
    assert cooker.actions[-1] == (2, 3, [])
    assert cooker.status == 4
    await _refresh(hass, entry)
    assert _state(hass, "sensor", "status") == "paused"
    assert _state(hass, "binary_sensor", "heating") == "off"

    await press("resume")
    assert cooker.actions[-1] == (3, 3, NO_NAMES)
    assert cooker.status == 1

    await press("stop")
    assert cooker.actions[-1] == (2, 2, [])
    assert cooker.status == 0
    await _refresh(hass, entry)
    assert _state(hass, "sensor", "status") == "idle"
    assert _state(hass, "sensor", "power_level") == "0"
    assert len(cooker.actions) == 5
    await _remove(hass, entry)


async def test_an_action_the_cooker_turns_down_is_an_error(hass: HomeAssistant, cooker: FakeCooker) -> None:
    entry = await _add(hass)
    with pytest.raises(HomeAssistantError):  # nothing to resume: it's off
        await hass.services.async_call(
            "button", "press", {"entity_id": _entity_id(hass, "button", "resume")}, blocking=True
        )
    await _remove(hass, entry)


async def test_the_target_temperature_stops_at_200(hass: HomeAssistant, cooker: FakeCooker) -> None:
    cooker.press_start()
    entry = await _add(hass)
    with pytest.raises(Exception):  # noqa: B017, PT011 - Home Assistant refuses a value outside the range
        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": _entity_id(hass, "number", "target_temperature"), "value": 230},
            blocking=True,
        )
    assert cooker.actions == []
    await _remove(hass, entry)


async def test_setup_adds_the_cooker(hass: HomeAssistant, cooker: FakeCooker) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": " 127.0.0.1 ", "token": TOKEN.upper()}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == ENTRY_DATA
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.unique_id == UNIQUE
    assert entry.state is ConfigEntryState.LOADED
    await _remove(hass, entry)


async def test_setup_refuses_a_hob_it_has_not_been_tested_on(
    hass: HomeAssistant, socket_enabled: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    with FakeCooker(model="chunmi.ihcooker.v2") as other:
        monkeypatch.setattr(miio, "PORT", other.port)
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], ENTRY_DATA)
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "unsupported_model"
        assert other.actions == []
    assert hass.config_entries.async_entries(DOMAIN) == []


async def test_setup_refuses_a_token_that_is_not_a_token(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "127.0.0.1", "token": "not-a-token"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"token": "invalid_token"}


async def test_setup_says_so_when_nothing_answers(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    with mock.patch.object(config_flow.MiioDevice, "info", side_effect=miio.MiioError("no reply")):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], ENTRY_DATA)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_the_same_cooker_is_not_added_twice(hass: HomeAssistant, cooker: FakeCooker) -> None:
    entry = await _add(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], ENTRY_DATA)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    await hass.async_block_till_done()
    await _remove(hass, entry)
