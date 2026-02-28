"""
Publikacja Reels na Instagram — Graph API.
Ulepszenie: dwuetapowy process (create container -> publish) + polling statusu.
"""

import asyncio

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class InstagramPublisher:
    GRAPH_URL = "https://graph.facebook.com/v19.0"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=15))
    async def upload(
        self,
        access_token: str,
        ig_user_id: str,
        video_url: str,  # Publiczny URL do wideo (S3 presigned)
        caption: str,
        share_to_feed: bool = True,
    ) -> dict:
        """
        Publikuje Reel na Instagram.
        Wymaga publicznego URL wideo (presigned S3 lub CDN).
        Zwraca {media_id, url}.
        """
        logger.info("Instagram Reel upload start", ig_user_id=ig_user_id)

        async with httpx.AsyncClient(timeout=120.0) as client:
            # Krok 1: Utwórz media container
            create_resp = await client.post(
                f"{self.GRAPH_URL}/{ig_user_id}/media",
                params={
                    "media_type": "REELS",
                    "video_url": video_url,
                    "caption": caption[:2200],
                    "share_to_feed": str(share_to_feed).lower(),
                    "access_token": access_token,
                },
            )
            create_resp.raise_for_status()
            container_id = create_resp.json()["id"]

            # Krok 2: Poll — czekaj aż wideo będzie gotowe
            await self._wait_for_processing(client, container_id, access_token)

            # Krok 3: Publikuj
            publish_resp = await client.post(
                f"{self.GRAPH_URL}/{ig_user_id}/media_publish",
                params={
                    "creation_id": container_id,
                    "access_token": access_token,
                },
            )
            publish_resp.raise_for_status()
            media_id = publish_resp.json()["id"]

            url = f"https://www.instagram.com/reel/{media_id}/"
            logger.info("Instagram Reel opublikowany", media_id=media_id)
            return {"media_id": media_id, "url": url}

    async def _wait_for_processing(
        self, client: httpx.AsyncClient, container_id: str, access_token: str
    ):
        """Czeka na przetworzenie wideo przez Instagram (max 60s)."""
        for _ in range(12):  # 12 * 5s = 60s
            resp = await client.get(
                f"{self.GRAPH_URL}/{container_id}",
                params={
                    "fields": "status_code",
                    "access_token": access_token,
                },
            )
            data = resp.json()
            status = data.get("status_code")

            if status == "FINISHED":
                return
            elif status == "ERROR":
                raise RuntimeError(f"Instagram media processing failed: {data}")

            await asyncio.sleep(5)

        raise TimeoutError("Instagram media processing timeout (60s)")
