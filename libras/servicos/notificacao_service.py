"""RF11: notificações internas (uma tabela; sem e-mail no protótipo)."""
from libras.dominio.modelos import Perfil


class NotificacaoService:
    def __init__(self, usuarios, notificacoes):
        self.usuarios = usuarios
        self.notificacoes = notificacoes

    def notificar(self, usuario_id, mensagem):
        self.notificacoes.criar(usuario_id, mensagem)

    def notificar_administradores(self, mensagem):
        for admin in self.usuarios.listar_por_perfil(Perfil.ADMINISTRADOR.value):
            self.notificacoes.criar(admin["id"], mensagem)

    def listar(self, usuario_id):
        return self.notificacoes.listar(usuario_id)

    def marcar_todas_lidas(self, usuario_id):
        self.notificacoes.marcar_todas_lidas(usuario_id)
