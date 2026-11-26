"""Ponto de entrada: monta as camadas (injeção de dependências manual) e inicia o terminal."""
import os
from pathlib import Path

from libras.apresentacao.cli import CLI
from libras.dominio.modelos import Perfil
from libras.repositorio.repositorios import (Banco, NotificacaoRepository, SinalRepository,
                                             SubmissaoRepository, UsuarioRepository)
from libras.servicos.auth_service import AuthService
from libras.servicos.notificacao_service import NotificacaoService
from libras.servicos.submissao_service import CatalogoService, SubmissaoService
from libras.servicos.video_service import VideoService


def montar(pasta_dados):
    Path(pasta_dados).mkdir(parents=True, exist_ok=True)
    banco = Banco(str(Path(pasta_dados) / "libras.db"))
    usuarios, sinais = UsuarioRepository(banco), SinalRepository(banco)
    submissoes, notif_repo = SubmissaoRepository(banco), NotificacaoRepository(banco)
    auth = AuthService(banco, usuarios)
    notificacoes = NotificacaoService(usuarios, notif_repo)
    submissao = SubmissaoService(banco, usuarios, sinais, submissoes,
                                 VideoService(pasta_dados), notificacoes)
    return banco, auth, submissao, CatalogoService(sinais), notificacoes


def garantir_admin_demo(banco, auth, usuarios_repo=None):
    """Cria o administrador de demonstração na primeira execução."""
    if banco.conn.execute("SELECT 1 FROM usuario WHERE perfil='ADMINISTRADOR'").fetchone() is None:
        auth.cadastrar("Administrador INES", "admin@ines.gov.br", "admin123", Perfil.ADMINISTRADOR)


if __name__ == "__main__":
    banco, auth, submissao, catalogo, notificacoes = montar(os.environ.get("LIBRAS_DATA", "dados"))
    garantir_admin_demo(banco, auth)
    try:
        CLI(auth, submissao, catalogo, notificacoes).executar()
    finally:
        banco.fechar()
