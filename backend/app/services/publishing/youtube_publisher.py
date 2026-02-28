"""
Publikacja wideo na YouTube — resumable upload.
Ulepszenie: obsługa retry + śledzenie statusu.
"""

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class YouTubePublisher:
    BASE_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
    API_URL = "https://www.googleapis.com/youtube/v3"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=15))
    async def upload(
        self,
        access_token: str,
        video_path: str,
        title: str,
        description: str,
        tags: list[str],
        category_id: str = "22",  # People & Blogs
        privacy: str = "public",
    ) -> dict:
        """
        Uploaduje wideo na YouTube (resumable upload).
        Zwraca {video_id, url}.
        """
        logger.info("YouTube upload start", title=title)

        async with httpx.AsyncClient(timeout=300.0) as client:
            # Krok 1: Inicjalizacja upload sesji
            metadata = {
                "snippet": {
                    "title": title[:100],
                    "description": description[:5000],
                    "tags": tags[:30],
                    "categoryId": category_id,
                },
                "status": {
                    "privacyStatus": privacy,
                    "selfDeclaredMadeForKids": False,
                    "madeForKids": False,
                },
            }

            init_resp = await client.post(
                f"{self.BASE_URL}?uploadType=resumable&part=snippet,status",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=metadata,
            )
            init_resp.raise_for_status()
            upload_url = init_resp.headers["Location"]

            # Krok 2: Upload pliku
            with open(video_path, "rb") as f:
                video_data = f.read()

            upload_resp = await client.put(
                upload_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "video/mp4",
                    "Content-Length": str(len(video_data)),
                },
                content=video_data,
            )
            upload_resp.raise_for_status()
            result = upload_resp.json()

            video_id = result["id"]
            url = f"https://www.youtube.com/shorts/{video_id}"

            logger.info("YouTube upload zakończony", video_id=video_id, url=url)
            return {"video_id": video_id, "url": url}

    async def set_thumbnail(self, access_token: str, video_id: str, thumbnail_path: str):
        """Ustawia miniaturę wideo."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(thumbnail_path, "rb") as f:
                await client.post(
                    f"{self.API_URL}/thumbnails/set?videoId={video_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                    files={"media": ("thumbnail.jpg", f, "image/jpeg")},
                )
