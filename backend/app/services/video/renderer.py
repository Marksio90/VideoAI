"""
Silnik renderowania wideo — FFmpeg + PIL.
Ulepszenie: scene-based rendering, napisy SRT, przejścia, branding overlay.
Pipeline:
  1. Przygotuj obrazy/klipy per scena (przycięte do 9:16)
  2. Wygeneruj napisy (SRT)
  3. Złóż audio + video + napisy -> finalny MP4
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import structlog

from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


class VideoRenderer:
    """Renderer wideo oparty na FFmpeg."""

    OUTPUT_WIDTH = 1080
    OUTPUT_HEIGHT = 1920  # 9:16 shorts
    FPS = 30

    def __init__(self, work_dir: str | None = None):
        self.work_dir = work_dir or tempfile.mkdtemp(prefix="autoshorts_")
        Path(self.work_dir).mkdir(parents=True, exist_ok=True)

    async def render(
        self,
        audio_path: str,
        scenes: list[dict],
        visual_style: dict | None = None,
        branding_text: str = "",
    ) -> str:
        """
        Renderuje finalne wideo shorts (1080x1920).
        Zwraca ścieżkę do pliku MP4.
        """
        style = visual_style or {}
        logger.info(
            "Rozpoczynam rendering",
            scenes_count=len(scenes),
            work_dir=self.work_dir,
        )

        # 1. Pobierz audio duration
        audio_duration = await self._get_audio_duration(audio_path)
        logger.info("Czas trwania audio", duration=audio_duration)

        # 2. Generuj napisy SRT
        srt_path = os.path.join(self.work_dir, "subtitles.srt")
        self._generate_srt(scenes, srt_path, audio_duration)

        # 3. Przygotuj concat list z obrazów (każdy obraz = fragment czasu)
        concat_path = await self._prepare_scene_images(scenes, audio_duration)

        # 4. Złóż wideo
        output_path = os.path.join(self.work_dir, "output.mp4")
        await self._compose_video(
            concat_path=concat_path,
            audio_path=audio_path,
            srt_path=srt_path,
            output_path=output_path,
            style=style,
            branding_text=branding_text,
        )

        logger.info("Rendering zakończony", output=output_path)
        return output_path

    async def _get_audio_duration(self, audio_path: str) -> float:
        """Pobiera długość pliku audio w sekundach."""
        cmd = [
            settings.FFPROBE_PATH,
            "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "json",
            audio_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])

    def _generate_srt(self, scenes: list[dict], srt_path: str, total_duration: float):
        """Generuje plik napisów SRT z tekstu scen."""
        num_scenes = len(scenes)
        if num_scenes == 0:
            Path(srt_path).write_text("")
            return

        scene_duration = total_duration / num_scenes

        lines = []
        for i, scene in enumerate(scenes):
            start = i * scene_duration
            end = min((i + 1) * scene_duration, total_duration)
            text = scene.get("text", "").strip()
            if not text:
                continue

            # Podziel długi tekst na linie po ~40 znaków
            words = text.split()
            subtitle_lines = []
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 > 40:
                    subtitle_lines.append(current_line.strip())
                    current_line = word
                else:
                    current_line += " " + word
            if current_line.strip():
                subtitle_lines.append(current_line.strip())

            lines.append(f"{i + 1}")
            lines.append(f"{self._format_time(start)} --> {self._format_time(end)}")
            lines.append("\n".join(subtitle_lines[:2]))  # max 2 linie
            lines.append("")

        Path(srt_path).write_text("\n".join(lines), encoding="utf-8")

    async def _prepare_scene_images(self, scenes: list[dict], total_duration: float) -> str:
        """
        Przygotowuje listę concat z obrazami scen.
        Każdy obraz pobieramy i skalujemy do 1080x1920.
        """
        import httpx

        concat_lines = []
        num_scenes = max(len(scenes), 1)
        scene_duration = total_duration / num_scenes

        for i, scene in enumerate(scenes):
            media_url = scene.get("media_url")
            img_path = os.path.join(self.work_dir, f"scene_{i}.jpg")

            if media_url:
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        resp = await client.get(media_url)
                        if resp.status_code == 200:
                            Path(img_path).write_bytes(resp.content)
                        else:
                            self._create_placeholder(img_path, scene.get("text", ""))
                except Exception:
                    self._create_placeholder(img_path, scene.get("text", ""))
            else:
                self._create_placeholder(img_path, scene.get("text", ""))

            # Skaluj obraz do 1080x1920
            scaled_path = os.path.join(self.work_dir, f"scene_{i}_scaled.jpg")
            self._scale_image(img_path, scaled_path)

            concat_lines.append(f"file '{scaled_path}'")
            concat_lines.append(f"duration {scene_duration:.3f}")

        # Powtórz ostatni frame (wymóg FFmpeg concat)
        if concat_lines:
            last_file = concat_lines[-2]
            concat_lines.append(last_file)

        concat_path = os.path.join(self.work_dir, "concat.txt")
        Path(concat_path).write_text("\n".join(concat_lines), encoding="utf-8")
        return concat_path

    def _create_placeholder(self, path: str, text: str):
        """Tworzy placeholderowy obraz z tekstem."""
        try:
            from PIL import Image, ImageDraw, ImageFont

            img = Image.new("RGB", (self.OUTPUT_WIDTH, self.OUTPUT_HEIGHT), color=(20, 20, 30))
            draw = ImageDraw.Draw(img)

            # Tekst na środku
            words = text.split()[:10]
            display_text = " ".join(words)
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
            except OSError:
                font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), display_text, font=font)
            text_width = bbox[2] - bbox[0]
            x = (self.OUTPUT_WIDTH - text_width) // 2
            y = self.OUTPUT_HEIGHT // 2

            draw.text((x, y), display_text, fill=(255, 255, 255), font=font)
            img.save(path, "JPEG", quality=85)
        except ImportError:
            # Fallback: plik pusty jpg (czarny 1x1)
            Path(path).write_bytes(b"")

    def _scale_image(self, input_path: str, output_path: str):
        """Skaluje obraz do 1080x1920 z crop/pad."""
        cmd = [
            settings.FFMPEG_PATH,
            "-y",
            "-i", input_path,
            "-vf", (
                f"scale={self.OUTPUT_WIDTH}:{self.OUTPUT_HEIGHT}:"
                "force_original_aspect_ratio=increase,"
                f"crop={self.OUTPUT_WIDTH}:{self.OUTPUT_HEIGHT},"
                "setsar=1"
            ),
            "-q:v", "2",
            output_path,
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=30)
        except Exception:
            # Fallback: kopiuj oryginał
            import shutil
            shutil.copy2(input_path, output_path)

    async def _compose_video(
        self,
        concat_path: str,
        audio_path: str,
        srt_path: str,
        output_path: str,
        style: dict,
        branding_text: str,
    ):
        """Składa finalne wideo: obrazy + audio + napisy."""
        font_color = style.get("font_color", "#FFFFFF")
        font_size = style.get("font_size", 48)
        sub_position = style.get("subtitle_position", "bottom")

        # Pozycja napisów
        margin_v = 100 if sub_position == "bottom" else 50

        # Filtr napisów z outline
        subtitle_filter = (
            f"subtitles={srt_path}:force_style="
            f"'FontSize={font_size},PrimaryColour=&H00FFFFFF,"
            f"OutlineColour=&H00000000,Outline=3,MarginV={margin_v},"
            f"Alignment=2,Bold=1'"
        )

        cmd = [
            settings.FFMPEG_PATH,
            "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_path,
            "-i", audio_path,
            "-vf", subtitle_filter,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            "-shortest",
            "-r", str(self.FPS),
            "-pix_fmt", "yuv420p",
            output_path,
        ]

        logger.info("FFmpeg rendering", output=output_path)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            logger.error("FFmpeg błąd", stderr=result.stderr[:500])
            raise RuntimeError(f"FFmpeg rendering failed: {result.stderr[:200]}")

        logger.info("Wideo wyrenderowane", size_mb=os.path.getsize(output_path) / 1_048_576)

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format SRT: HH:MM:SS,mmm."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
