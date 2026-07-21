"""Registration, login, token refresh, and logout for parent accounts."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ConflictError, UnauthorizedError
from app.models.user import User
from app.repositories import refresh_token_repository, user_repository
from app.schemas.auth import TokenResponse
from app.security.passwords import hash_password, verify_password
from app.security.tokens import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    refresh_token_expiry,
)


@dataclass
class AuthService:
    session: AsyncSession
    settings: Settings

    async def register(self, *, email: str, password: str, display_name: str) -> User:
        existing = await user_repository.get_by_email(self.session, email)
        if existing is not None:
            raise ConflictError("An account with this email already exists.")

        user = await user_repository.create(
            self.session,
            email=email,
            hashed_password=hash_password(password),
            display_name=display_name,
        )
        await self.session.commit()
        return user

    async def login(self, *, email: str, password: str) -> tuple[User, TokenResponse]:
        user = await user_repository.get_by_email(self.session, email)
        if user is None or user.hashed_password is None:
            raise UnauthorizedError("Invalid email or password.")
        if not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password.")
        if not user.is_active:
            raise UnauthorizedError("This account has been deactivated.")

        tokens = await self._issue_tokens(user.id)
        await self.session.commit()
        return user, tokens

    async def refresh(self, *, refresh_token: str) -> TokenResponse:
        token_hash = hash_refresh_token(refresh_token)
        stored = await refresh_token_repository.get_valid_by_hash(self.session, token_hash)
        if stored is None:
            raise UnauthorizedError("Invalid or expired refresh token.")

        user = await user_repository.get_by_id(self.session, stored.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("Invalid or expired refresh token.")

        # Rotate: revoke the presented token and issue a new pair.
        await refresh_token_repository.revoke(self.session, stored)
        tokens = await self._issue_tokens(user.id)
        await self.session.commit()
        return tokens

    async def logout(self, *, refresh_token: str) -> None:
        token_hash = hash_refresh_token(refresh_token)
        stored = await refresh_token_repository.get_valid_by_hash(self.session, token_hash)
        if stored is not None:
            await refresh_token_repository.revoke(self.session, stored)
            await self.session.commit()

    async def delete_account(self, user: User) -> None:
        await refresh_token_repository.revoke_all_for_user(self.session, user.id)
        await user_repository.delete(self.session, user)
        await self.session.commit()

    async def _issue_tokens(self, user_id: str) -> TokenResponse:
        access_token = create_access_token(user_id, self.settings)
        plain_refresh_token = generate_refresh_token()
        await refresh_token_repository.create(
            self.session,
            user_id=user_id,
            token_hash=hash_refresh_token(plain_refresh_token),
            expires_at=refresh_token_expiry(self.settings),
        )
        return TokenResponse(access_token=access_token, refresh_token=plain_refresh_token)
