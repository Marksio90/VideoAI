"""
Połączenia z platformami (YouTube, TikTok, Instagram) — tokeny OAuth.
Ulepszenie: szyfrowanie tokenów w bazie + automatyczny refresh.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class PlatformConnection(BaseModel):
    __tablename__ = "platform_connections"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)  # youtube, tiktok, instagram
    platform_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    platform_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    channel_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scopes: Mapped[str] = mapped_column(Text, default="")

    is_active: Mapped[bool] = mapped_column(default=True)

    user = relationship("User", back_populates="platform_connections")
