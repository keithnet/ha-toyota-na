import logging

from homeassistant import config_entries
import voluptuous as vol

from toyota_na import ToyotaOneAuth, ToyotaOneClient
from toyota_na.exceptions import AuthError

# Patch auth code
from .patch_auth import authorize, login
ToyotaOneAuth.authorize = authorize
ToyotaOneAuth.login = login
import json

from .const import DOMAIN
from .brands import BRANDS, BRAND_TOYOTA, BRAND_SUBARU

_LOGGER = logging.getLogger(__name__)


def _configure_auth_for_brand(brand: str):
    """Set ForgeRock auth URLs for the selected brand."""
    brand_config = BRANDS.get(brand, BRANDS[BRAND_TOYOTA])
    auth_host = brand_config["auth_host"]
    ToyotaOneAuth.ACCESS_TOKEN_URL = f"https://{auth_host}/oauth2/realms/root/realms/tmna-native/access_token"
    ToyotaOneAuth.AUTHORIZE_URL = f"https://{auth_host}/oauth2/realms/root/realms/tmna-native/authorize"
    ToyotaOneAuth.AUTHENTICATE_URL = f"https://{auth_host}/json/realms/root/realms/tmna-native/authenticate"


class ToyotaNAConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Toyota / Subaru (North America) connected services."""

    def __init__(self):
        self.brand = BRAND_TOYOTA
        self.client = None
        self.user_info = None
        self.otp_info = None

    async def async_step_user(self, user_input=None):
        """Step 1: Select brand."""
        if user_input is not None:
            self.brand = user_input["brand"]
            return await self.async_step_credentials()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("brand", default=BRAND_TOYOTA): vol.In({
                    BRAND_TOYOTA: "Toyota",
                    BRAND_SUBARU: "Subaru (SubaruConnect)",
                }),
            }),
        )

    async def async_step_credentials(self, user_input=None):
        """Step 2: Enter username and password."""
        errors = {}
        if user_input is not None:
            try:
                _configure_auth_for_brand(self.brand)
                self.client = ToyotaOneClient()
                self.user_info = user_input
                await self.client.auth.authorize(user_input["username"], user_input["password"])
                return await self.async_step_otp()
            except AuthError:
                errors["base"] = "not_logged_in"
                _LOGGER.error("Not logged in with username and password")
            except Exception:
                errors["base"] = "unknown"
                _LOGGER.exception("Unknown error with username and password")
        return self.async_show_form(
            step_id="credentials",
            data_schema=vol.Schema(
                {vol.Required("username"): str, vol.Required("password"): str}
            ),
            errors=errors,
        )

    async def async_step_otp(self, user_input=None):
        """Step 3: Enter OTP verification code."""
        errors = {}
        if user_input is not None:
            try:
                self.otp_info = user_input
                data = await self.async_get_entry_data(self.client, errors)
                if data:
                    return await self.async_create_or_update_entry(data=data)
            except AuthError:
                errors["base"] = "not_logged_in"
                _LOGGER.error("Not logged in with one time password")
            except Exception:
                errors["base"] = "unknown"
                _LOGGER.exception("Unknown error with one time password")
        return self.async_show_form(
            step_id="otp",
            data_schema=vol.Schema(
                {vol.Required("code"): str}
            ),
            errors=errors,
        )

    async def async_get_entry_data(self, client, errors):
        try:
            await client.auth.login(self.user_info["username"], self.user_info["password"], self.otp_info["code"])
            id_info = await client.auth.get_id_info()
            return {
                "tokens": client.auth.get_tokens(),
                "email": id_info["email"],
                "username": self.user_info["username"],
                "password": self.user_info["password"],
                "brand": self.brand,
            }
        except AuthError:
            errors["base"] = "otp_not_logged_in"
            _LOGGER.error("Invalid Verification Code")
        except Exception:
            errors["base"] = "unknown"
            _LOGGER.exception("Unknown error")

    async def async_create_or_update_entry(self, data):
        existing_entry = await self.async_set_unique_id(f"{DOMAIN}:{data['email']}")
        if existing_entry:
            self.hass.config_entries.async_update_entry(existing_entry, data=data)
            await self.hass.config_entries.async_reload(existing_entry.entry_id)
            return self.async_abort(reason="reauth_successful")
        brand_name = BRANDS[self.brand]["name"]
        return self.async_create_entry(title=f"{brand_name}: {data['email']}", data=data)

    async def async_step_reauth(self, data):
        # Preserve brand from existing entry if re-authenticating
        self.brand = data.get("brand", BRAND_TOYOTA)
        return await self.async_step_credentials()
