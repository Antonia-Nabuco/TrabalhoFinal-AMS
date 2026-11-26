"""Serviço de vídeo (ator "Sistema" do UC01).

Valida formato/tamanho (fluxo de exceção E1), armazena o arquivo e tenta gerar
a thumbnail (RF10). No projeto completo esta etapa roda em um worker assíncrono
(fila de mensagens); no protótipo ela é executada de forma síncrona.
"""
import shutil
import subprocess
import uuid
from pathlib import Path

from libras.dominio.excecoes import VideoInvalido

FORMATOS_PERMITIDOS = {".mp4", ".webm", ".mov"}
TAMANHO_MAXIMO = 50 * 1024 * 1024  # 50 MB


class VideoService:
    def __init__(self, pasta_dados):
        self.pasta_videos = Path(pasta_dados) / "videos"
        self.pasta_thumbs = Path(pasta_dados) / "thumbnails"
        self.pasta_videos.mkdir(parents=True, exist_ok=True)
        self.pasta_thumbs.mkdir(parents=True, exist_ok=True)

    def validar(self, caminho):
        p = Path(caminho).expanduser()
        if not p.is_file():
            raise VideoInvalido("Arquivo de vídeo não encontrado.")
        ext = p.suffix.lower()
        if ext not in FORMATOS_PERMITIDOS:
            raise VideoInvalido("Formato não permitido (use: " + ", ".join(sorted(FORMATOS_PERMITIDOS)) + ").")
        tamanho = p.stat().st_size
        if tamanho == 0:
            raise VideoInvalido("O arquivo de vídeo está vazio.")
        if tamanho > TAMANHO_MAXIMO:
            raise VideoInvalido("O vídeo excede o tamanho máximo de 50 MB.")
        return p, ext[1:], tamanho

    def processar(self, caminho):
        """Valida, armazena e gera a thumbnail. Devolve os dados do vídeo."""
        origem, formato, tamanho = self.validar(caminho)
        nome = uuid.uuid4().hex
        destino = self.pasta_videos / f"{nome}.{formato}"
        shutil.copy2(origem, destino)
        return {
            "url_original": str(origem),
            "url_final": str(destino),
            "thumbnail_url": self._gerar_thumbnail(destino, nome),
            "formato": formato,
            "tamanho": tamanho,
        }

    def _gerar_thumbnail(self, video, nome):
        if not shutil.which("ffmpeg"):
            return None  # sem ffmpeg o protótipo segue sem thumbnail
        thumb = self.pasta_thumbs / f"{nome}.jpg"
        try:
            subprocess.run(["ffmpeg", "-y", "-i", str(video), "-frames:v", "1", str(thumb)],
                           capture_output=True, timeout=60, check=True)
            return str(thumb)
        except (subprocess.SubprocessError, OSError):
            return None

    def descartar(self, dados_video):
        for chave in ("url_final", "thumbnail_url"):
            if dados_video.get(chave):
                Path(dados_video[chave]).unlink(missing_ok=True)
