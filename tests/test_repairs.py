"""Repair issue creation and the reauth fix flow."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "zte_5g_router"


def load_repairs():
    package = types.ModuleType("zte_repairs_test")
    package.__path__ = [str(ROOT)]

    class FlowType:
        CONFIG_FLOW = "config_flow"

    class RepairsFlowResult(dict):
        pass

    class RepairsFlow:
        hass = None
        data = None
        issue_id = None

        def async_show_form(self, **kwargs):
            return RepairsFlowResult(type="form", **kwargs)

        def async_abort(self, **kwargs):
            return RepairsFlowResult(type="abort", **kwargs)

    repairs_component = types.ModuleType("homeassistant.components.repairs")
    repairs_component.FlowType = FlowType
    repairs_component.RepairsFlow = RepairsFlow
    repairs_component.RepairsFlowResult = RepairsFlowResult
    components = types.ModuleType("homeassistant.components")
    components.repairs = repairs_component

    entries = types.ModuleType("homeassistant.config_entries")
    entries.SOURCE_REAUTH = "reauth"
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object

    created = []
    deleted = []

    def async_create_issue(*args, **kwargs):
        created.append((args, kwargs))

    def async_delete_issue(*args, **kwargs):
        deleted.append((args, kwargs))

    issue_registry = types.ModuleType("homeassistant.helpers.issue_registry")
    issue_registry.IssueSeverity = types.SimpleNamespace(ERROR="error")
    issue_registry.async_create_issue = async_create_issue
    issue_registry.async_delete_issue = async_delete_issue
    helpers = types.ModuleType("homeassistant.helpers")
    helpers.issue_registry = issue_registry

    spec = importlib.util.spec_from_file_location("zte_repairs_test.repairs", ROOT / "repairs.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {
        "zte_repairs_test": package,
        "homeassistant.components": components,
        "homeassistant.components.repairs": repairs_component,
        "homeassistant.config_entries": entries,
        "homeassistant.core": core,
        "homeassistant.helpers": helpers,
        "homeassistant.helpers.issue_registry": issue_registry,
    }):
        spec.loader.exec_module(module)
    return module, created, deleted, FlowType


repairs, created, deleted, FlowType = load_repairs()


class RepairTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        created.clear()
        deleted.clear()

    def test_auth_issue_is_scoped_to_the_config_entry(self):
        repairs.async_create_auth_issue(Mock(), "entry-1", "Router")
        self.assertEqual(len(created), 1)
        args, kwargs = created[0]
        self.assertEqual(args[1], "zte_5g_router")
        self.assertEqual(args[2], "auth_failed_entry-1")
        self.assertEqual(kwargs["config_entry_id"], "entry-1")
        self.assertEqual(kwargs["data"], {"entry_id": "entry-1"})
        self.assertEqual(kwargs["translation_key"], "auth_failed")
        self.assertEqual(kwargs["translation_placeholders"], {"name": "Router"})
        self.assertTrue(kwargs["is_fixable"])
        self.assertFalse(kwargs["is_persistent"])

    def test_auth_issue_is_deleted_after_success(self):
        repairs.async_delete_auth_issue(Mock(), "entry-1")
        self.assertEqual(deleted[0][0][1:], ("zte_5g_router", "auth_failed_entry-1"))

    async def test_init_step_shows_confirmation(self):
        flow = repairs.ZteAuthRepairFlow()
        flow.hass = Mock()
        flow.data = {"entry_id": "entry-1"}
        form = await flow.async_step_init()
        self.assertEqual(form["step_id"], "confirm")

    async def test_fix_flow_starts_reauth_and_clears_issue(self):
        start_flow = AsyncMock(return_value={"flow_id": "flow-1"})
        hass = types.SimpleNamespace(
            config_entries=types.SimpleNamespace(
                flow=types.SimpleNamespace(async_init=start_flow)
            )
        )
        flow = repairs.ZteAuthRepairFlow()
        flow.hass = hass
        flow.data = {"entry_id": "entry-1"}
        form = await flow.async_step_confirm()
        self.assertEqual(form["step_id"], "confirm")
        start_flow.assert_not_awaited()

        result = await flow.async_step_confirm({})
        self.assertEqual(result["type"], "abort")
        self.assertEqual(result["reason"], "reauth_started")
        self.assertEqual(result["next_flow"], (FlowType.CONFIG_FLOW, "flow-1"))
        start_flow.assert_awaited_once_with(
            "zte_5g_router",
            context={"source": "reauth", "entry_id": "entry-1"},
        )
        self.assertEqual(deleted[0][0][1:], ("zte_5g_router", "auth_failed_entry-1"))

    async def test_create_fix_flow_returns_repair_flow(self):
        flow = await repairs.async_create_fix_flow(Mock(), "auth_failed_entry-1", {})
        self.assertIsInstance(flow, repairs.ZteAuthRepairFlow)


if __name__ == "__main__":
    unittest.main()
