"""Cliente oficial do Google Identity Services (OAuth 2.0 / OIDC) via httpx (Camada 4)."""

import urllib.parse

import httpx

from src.application.dto.auth_dto import GoogleUserInfoDTO
from src.application.ports.auth import IGoogleAuthClient


class GoogleOAuthClient(IGoogleAuthClient):
    """Implementa comunicação direta com os endpoints do Google Identity."""

    AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105
    USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
    TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"

    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
        return f"{self.AUTH_URL}?{urllib.parse.urlencode(params)}"

    def exchange_code_for_user_info(self, code: str, redirect_uri: str) -> GoogleUserInfoDTO:
        data = {
            "code": code,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        with httpx.Client(timeout=10.0) as client:
            token_resp = client.post(self.TOKEN_URL, data=data)
            if token_resp.status_code != 200:
                raise ValueError(f"Erro ao trocar código com Google: {token_resp.text}")

            token_data = token_resp.json()
            access_token = token_data.get("access_token")

            userinfo_resp = client.get(
                self.USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if userinfo_resp.status_code != 200:
                raise ValueError(f"Erro ao obter userinfo do Google: {userinfo_resp.text}")

            userinfo = userinfo_resp.json()
            return GoogleUserInfoDTO(
                sub=userinfo["sub"],
                email=userinfo["email"],
                name=userinfo.get("name", userinfo["email"]),
                avatar_url=userinfo.get("picture"),
            )

    def verify_id_token(self, id_token: str) -> GoogleUserInfoDTO:
        params = {"id_token": id_token}
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(self.TOKENINFO_URL, params=params)
            if resp.status_code != 200:
                raise ValueError(f"ID Token do Google inválido: {resp.text}")

            payload = resp.json()
            return GoogleUserInfoDTO(
                sub=payload["sub"],
                email=payload["email"],
                name=payload.get("name", payload["email"]),
                avatar_url=payload.get("picture"),
            )
