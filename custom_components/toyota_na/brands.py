# Brand configuration for Toyota / Subaru multi-brand support.
# This file must NOT import from const.py or any patched modules
# to avoid circular import issues at load time.

BRAND_TOYOTA = "T"
BRAND_SUBARU = "S"

BRANDS = {
    BRAND_TOYOTA: {
        "name": "Toyota",
        "auth_host": "login.toyotadriverslogin.com",
        "user_agent": "ToyotaOneApp/3.10.0 (com.toyota.oneapp; build:3100; Android 14) okhttp/4.12.0",
        "manufacturer": "Toyota Motor North America",
        "requires_account_bootstrap": False,
    },
    BRAND_SUBARU: {
        "name": "Subaru",
        "auth_host": "login.subarudriverslogin.com",
        "user_agent": "SubaruConnect/2.3.1 (com.subaru.oneapp; build:48; Android 14) okhttp/4.12.0",
        "manufacturer": "Subaru of America",
        "requires_account_bootstrap": True,
    },
}
