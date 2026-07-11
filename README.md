# NangMan

게임 친구 매칭 서비스 백엔드 (Django REST Framework)

## 프로젝트 개요

- 유저가 방을 생성하고, 다른 유저의 가입 신청을 방장이 수락하여 게임 친구를 매칭하는 서비스
- 방을 생성한 유저가 해당 방의 방장이 됨

## 기술 스택

- Python / Django / Django REST Framework

## MVP 기능

1. 방장 · 일반 유저 구현
2. 방 생성 및 방 참여 시스템
3. 방 목록 조회 → 가입 신청 → 방장 수락으로 매칭
4. 방 내부 채팅
5. 카카오 소셜로그인 (후순위)

## 폴더 구조

```
NangMan/
├── backend/    # Django DRF 백엔드
└── frontend/   # 테스트용 프론트엔드 (깃 추적 제외)
```
