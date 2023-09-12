"""Enmax"""
import debugpy
debugpy.listen(5678)
debugpy.wait_for_client()

import logging
import aiohttp
from typing import Optional
import xml.etree.ElementTree as ET

from ..const import USER_AGENT
from ..exceptions import InvalidAuth
from .base import UtilityBase


_LOGGER = logging.getLogger(__file__)

class Enmax(UtilityBase):
    @staticmethod
    def name() -> str:
        """Distinct recognizable name of the utility."""
        return "Enmax Energy"

    @staticmethod
    def subdomain() -> str:
        """Return the opower.com subdomain for this utility."""
        return "enmx"

    @staticmethod
    def timezone() -> str:
        """Return the timezone."""
        return "America/Edmonton"

    @staticmethod
    def accepts_mfa() -> bool:
        """Check if Utility implementations supports MFA."""
        return False

    @staticmethod
    async def async_login(
        session: aiohttp.ClientSession,
        username: str,
        password: str,
        optional_mfa_secret: Optional[str],
    ) -> None:

        """Get request digest"""
        async with session.post(
            "https://www.enmax.com/SignInSite/_vti_bin/sites.asmx",
            headers={
                "User-Agent": USER_AGENT,
                "Content-Type": 'text/xml',
                },
            data=b'<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">  <soap:Body>    <GetUpdatedFormDigest xmlns="http://schemas.microsoft.com/sharepoint/soap/" />  </soap:Body></soap:Envelope>',
            raise_for_status=True,
        ) as resp:
            xml = await resp.text()

        xml = ET.fromstring(xml)
        for i in xml.iter():
            if(i.tag == "{http://schemas.microsoft.com/sharepoint/soap/}GetUpdatedFormDigestResult"):
                requestdigest = i.text

        """Login to the utility website."""
        async with session.post(
            "https://www.enmax.com/SignInSite/_vti_bin/Enmax.Internet.Auth/AuthService.svc/AuthenticateUser",
            json={
                "email": username,
                "password": password,
                "autoUnlockIntervalMinutes": 15,
                "queryString": "",
            },
            headers={
                "User-Agent": USER_AGENT,
                "X-RequestDigest": requestdigest,
                "referer": 'https://www.enmax.com/sign-in',
            },
            raise_for_status=True,
        ) as resp:
            result = await resp.json()
            if result['ErrorMessage']:
                raise InvalidAuth(result['ErrorMessage'])

        """Authorization code for opower"""
        async with session.post(
            "https://www.enmax.com/YourAccountSite/_vti_bin/Enmax.Internet.Opower/MyEnergyIQService.svc/IssueAccessToken",
            headers={"User-Agent": USER_AGENT},
            raise_for_status=True,
        ) as resp:
            token = await resp.text()
            _LOGGER.info(token)
            return str(token).replace('"', '')
