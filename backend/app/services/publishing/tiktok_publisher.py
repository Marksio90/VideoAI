"""
Publikacja wideo na TikTok — Content Posting API (v2).
Ulepszenie: dwuetapowy upload + poprawna obsługa limitów.
"""

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class TikTokPublisher:
    BASE_URL = "https://open.tiktokapis.com/v2"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=15))
    async def upload(
        self,
        access_token: str,
        video_path: str,
        title: str,
        description: str,
        **kwargs,
    ) -> dict:
        """
        Uploaduje wideo na TikTok (FILE_UPLOAD).
        Zwraca {publish_id}.
        """
        logger.info("TikTok upload start", title=title)

        import os
        file_size = os.path.getsize(video_path)

        async with httpx.AsyncClient(timeout=300.0) as client:
            # Krok 1: Inicjalizacja uploadu
            init_resp = await client.post(
                f"{self.BASE_URL}/post/publish/inbox/video/init/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "post_info": {
                        "title": title[:150],
                        "description": description[:2200],
                        "disable_comment": False,
                        "privacy_level": "PUBLIC_TO_EVERYONE",
                    },
                    "source_info": {
                        "source": "FILE_UPLOAD",
                        "video_size": file_size,
                        "chunk_size": file_size,
                        "total_chunk_count": 1,
                    },
                },
            )
            init_resp.raise_for_status()
            init_data = init_resp.json()

            publish_id = init_data["data"]["publish_id"]
            upload_url = init_data["data"]["upload_url"]

            # Krok 2: Upload pliku
            with open(video_path, "rb") as f:
                video_data = f.read()

            headers = {
                "Content-Type": "video/mp4",
                "Content-Length": str(file_size),
                "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
            }

            upload_resp = await client.put(
                upload_url,
                headers=headers,
                content=video_data,
            )
            upload_resp.raise_for_status()

            logger.info("TikTok upload zakończony", publish_id=publish_id)
            return {"publish_id": publish_id, "url": None}

    async def check_status(self, access_token: str, publish_id: str) -> dict:
        """Sprawdza status publikacji."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.BASE_URL}/post/publish/status/fetch/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"publish_id": publish_id},
            )
            resp.raise_for_status()
            return resp.json()
