"""카카오 OAuth 토큰 교환 · 사용자 정보 조회."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests
from django.conf import settings


class KakaoAPIError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


@dataclass(frozen=True)
class KakaoProfile:
    id: str
    nickname: str


def _require_kakao_settings() -> tuple[str, str, str]:
    rest_api_key = getattr(settings, 'KAKAO_REST_API_KEY', '') or ''
    client_secret = getattr(settings, 'KAKAO_CLIENT_SECRET', '') or ''
    redirect_uri = getattr(settings, 'KAKAO_REDIRECT_URI', '') or ''
    if not rest_api_key:
        raise KakaoAPIError('KAKAO_REST_API_KEY 가 설정되지 않았습니다.')
    if not client_secret:
        raise KakaoAPIError('KAKAO_CLIENT_SECRET 가 설정되지 않았습니다.')
    if not redirect_uri:
        raise KakaoAPIError('KAKAO_REDIRECT_URI 가 설정되지 않았습니다.')
    return rest_api_key, client_secret, redirect_uri


def build_authorize_url(*, state: str | None = None) -> str:
    """브라우저에서 열 카카오 인가 URL."""
    rest_api_key, _, redirect_uri = _require_kakao_settings()
    from urllib.parse import urlencode

    params = {
        'client_id': rest_api_key,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
    }
    if state:
        params['state'] = state
    return f'https://kauth.kakao.com/oauth/authorize?{urlencode(params)}'


def exchange_code_for_token(code: str) -> dict[str, Any]:
    rest_api_key, client_secret, redirect_uri = _require_kakao_settings()
    try:
        response = requests.post(
            'https://kauth.kakao.com/oauth/token',
            data={
                'grant_type': 'authorization_code',
                'client_id': rest_api_key,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri,
                'code': code,
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8'},
            timeout=10,
        )
    except requests.RequestException as exc:
        raise KakaoAPIError(f'카카오 토큰 요청 실패: {exc}') from exc

    payload = _json_or_text(response)
    if response.status_code >= 400:
        raise KakaoAPIError(
            _kakao_error_message(payload, fallback='카카오 토큰 교환에 실패했습니다.'),
            status_code=response.status_code,
            payload=payload,
        )
    if 'access_token' not in payload:
        raise KakaoAPIError('카카오 응답에 access_token 이 없습니다.', payload=payload)
    return payload


def fetch_kakao_profile(access_token: str) -> KakaoProfile:
    try:
        response = requests.get(
            'https://kapi.kakao.com/v2/user/me',
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8',
            },
            timeout=10,
        )
    except requests.RequestException as exc:
        raise KakaoAPIError(f'카카오 사용자 정보 요청 실패: {exc}') from exc

    payload = _json_or_text(response)
    if response.status_code >= 400:
        raise KakaoAPIError(
            _kakao_error_message(payload, fallback='카카오 사용자 정보 조회에 실패했습니다.'),
            status_code=response.status_code,
            payload=payload,
        )

    kakao_id = payload.get('id')
    if kakao_id is None:
        raise KakaoAPIError('카카오 사용자 id 가 없습니다.', payload=payload)

    properties = payload.get('properties') or {}
    account = payload.get('kakao_account') or {}
    profile = account.get('profile') or {}
    nickname = (
        properties.get('nickname')
        or profile.get('nickname')
        or f'kakao_{kakao_id}'
    )
    return KakaoProfile(id=str(kakao_id), nickname=str(nickname))


def _json_or_text(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text


def _kakao_error_message(payload: Any, *, fallback: str) -> str:
    if isinstance(payload, dict):
        return str(
            payload.get('error_description')
            or payload.get('msg')
            or payload.get('error')
            or fallback
        )
    if isinstance(payload, str) and payload.strip():
        return payload
    return fallback
