"""Repairs for problems that need user action on the router integration."""

from __future__ import annotations

from homeassistant.components.repairs import FlowType, RepairsFlow, RepairsFlowResult
from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
import voluptuous as vol

from .const import DOMAIN

AUTH_ISSUE = "auth_failed"


def auth_issue_id(entry_id: str) -> str:
    """Return the registry issue ID for a config entry."""
    return f"{AUTH_ISSUE}_{entry_id}"


def async_create_auth_issue(hass: HomeAssistant, entry_id: str, router_name: str) -> None:
    """Raise a repair when the stored router password was rejected."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        auth_issue_id(entry_id),
        config_entry_id=entry_id,
        data={"entry_id": entry_id},
        is_fixable=True,
        is_persistent=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key=AUTH_ISSUE,
        translation_placeholders={"name": router_name},
    )


def async_delete_auth_issue(hass: HomeAssistant, entry_id: str) -> None:
    """Clear the repair after a successful login."""
    ir.async_delete_issue(hass, DOMAIN, auth_issue_id(entry_id))


class ZteAuthRepairFlow(RepairsFlow):  # type: ignore[misc]  # HA base is Any without stubs
    """Offer to start the regular reauthentication flow."""

    async def async_step_init(self, user_input: dict[str, str] | None = None) -> RepairsFlowResult:
        """Start with the confirmation step."""
        return await self.async_step_confirm(user_input)

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> RepairsFlowResult:
        """Start Home Assistant's reauth flow for the affected entry."""
        if user_input is not None:
            entry_id = str((self.data or {}).get("entry_id", ""))
            result = await self.hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_REAUTH, "entry_id": entry_id},
            )
            async_delete_auth_issue(self.hass, entry_id)
            return self.async_abort(
                reason="reauth_started",
                next_flow=(FlowType.CONFIG_FLOW, result["flow_id"]),
            )

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
        )


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create the flow that fixes an auth failure."""
    return ZteAuthRepairFlow()
