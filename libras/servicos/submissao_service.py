"""Camada de Aplicação: regras de negócio do fluxo de aprovação (UC01, RF04-RF06).

Concentrar as regras aqui garante, em um único ponto, que toda alteração gere
histórico (RF08/RNF09) e que o consentimento LGPD seja verificado antes de
qualquer vídeo entrar no fluxo.
"""
from libras.dominio.excecoes import (CampoObrigatorio, ConsentimentoPendente, PermissaoNegada,
                                     SubmissaoInvalida)
from libras.dominio.modelos import Perfil, StatusSubmissao
from libras.servicos.consentimento import VERSAO_TERMO

CAMPOS_OBRIGATORIOS = {"palavra": "Palavra", "acepcao": "Acepção", "classe_gramatical": "Classe gramatical"}


class SubmissaoService:
    def __init__(self, banco, usuarios, sinais, submissoes, videos, notificacoes):
        self.banco = banco
        self.usuarios = usuarios
        self.sinais = sinais
        self.submissoes = submissoes
        self.videos = videos
        self.notificacoes = notificacoes

    # ---------- LGPD ----------
    def aceitar_termo(self, usuario):
        with self.banco.transacao():
            self.usuarios.registrar_termo(usuario.id, VERSAO_TERMO)

    def registrar_consentimento_responsavel(self, usuario, documento_url):
        if not documento_url.strip():
            raise CampoObrigatorio("Informe o documento do responsável.")
        with self.banco.transacao():
            self.usuarios.registrar_consentimento_responsavel(usuario.id, documento_url.strip())

    def _exigir_consentimento(self, usuario):
        faltando = []
        if not self.usuarios.tem_termo(usuario.id):
            faltando.append("termo")
        if usuario.menor_de_idade and not self.usuarios.tem_consentimento_responsavel(usuario.id):
            faltando.append("responsavel")
        if faltando:
            raise ConsentimentoPendente(faltando)

    # ---------- RF01 (inserção) + RF02 + RF04 ----------
    def submeter_sinal(self, colaborador, dados, caminho_video):
        """UC01, passos 1-4. Devolve o id da submissão criada (status PENDENTE)."""
        if colaborador.perfil != Perfil.COLABORADOR:
            raise PermissaoNegada("Apenas colaboradores podem submeter sinais.")
        self._exigir_consentimento(colaborador)

        for chave, rotulo in CAMPOS_OBRIGATORIOS.items():
            if not (dados.get(chave) or "").strip():
                raise CampoObrigatorio(f"O campo '{rotulo}' é obrigatório.")
        dados = {k: (v.strip() if isinstance(v, str) else v) for k, v in dados.items()}

        # E1: vídeo inválido => erro, NADA é registrado como pendente.
        dados_video = self.videos.processar(caminho_video)
        try:
            with self.banco.transacao():
                sinal_id = self.sinais.criar(dados, StatusSubmissao.PENDENTE.value)
                self.sinais.adicionar_video(sinal_id, dados_video)
                submissao_id = self.submissoes.criar(sinal_id, colaborador.id, "NOVO_SINAL",
                                                     StatusSubmissao.PENDENTE.value)
                self.sinais.registrar_historico(sinal_id, colaborador.id, "SUBMISSAO")
                self.notificacoes.notificar_administradores(
                    f"Nova submissão pendente: '{dados['palavra']}' (#{submissao_id}).")
        except Exception:
            self.videos.descartar(dados_video)
            raise
        return submissao_id

    # ---------- consultas ----------
    def fila_de_aprovacao(self, admin):
        self._exigir_admin(admin)
        return self.submissoes.listar_por_status(StatusSubmissao.PENDENTE.value)

    def minhas_submissoes(self, colaborador):
        return self.submissoes.listar_por_colaborador(colaborador.id)

    def detalhar(self, admin, submissao_id):
        """UC01, passo 6: campos + vídeos para revisão."""
        self._exigir_admin(admin)
        sub = self._obter_pendente(submissao_id)
        return sub, self.sinais.buscar_por_id(sub["sinal_id"]), self.sinais.listar_videos(sub["sinal_id"])

    # ---------- UC01 passos 7-9 e fluxo A1 ----------
    def aprovar(self, admin, submissao_id):
        self._exigir_admin(admin)
        sub = self._obter_pendente(submissao_id)
        with self.banco.transacao():
            self.submissoes.atualizar_status(submissao_id, StatusSubmissao.PUBLICADO.value)
            self.sinais.atualizar_status(sub["sinal_id"], StatusSubmissao.PUBLICADO.value)
            self.sinais.registrar_historico(sub["sinal_id"], admin.id, "APROVACAO")
            self.notificacoes.notificar(
                sub["colaborador_id"], f"Sua submissão '{sub['palavra']}' foi APROVADA e publicada.")

    def rejeitar(self, admin, submissao_id, justificativa):
        self._exigir_admin(admin)
        if not (justificativa or "").strip():  # RF06
            raise CampoObrigatorio("A justificativa é obrigatória para rejeitar.")
        sub = self._obter_pendente(submissao_id)
        with self.banco.transacao():
            self.submissoes.atualizar_status(submissao_id, StatusSubmissao.REJEITADO.value,
                                             justificativa.strip())
            self.sinais.atualizar_status(sub["sinal_id"], StatusSubmissao.REJEITADO.value)
            self.sinais.registrar_historico(sub["sinal_id"], admin.id, "REJEICAO")
            self.notificacoes.notificar(
                sub["colaborador_id"],
                f"Sua submissão '{sub['palavra']}' foi REJEITADA. Justificativa: {justificativa.strip()}")

    # ---------- auxiliares ----------
    @staticmethod
    def _exigir_admin(usuario):
        if usuario.perfil != Perfil.ADMINISTRADOR:
            raise PermissaoNegada("Apenas administradores podem executar esta ação.")

    def _obter_pendente(self, submissao_id):
        sub = self.submissoes.buscar_por_id(submissao_id)
        if sub is None:
            raise SubmissaoInvalida("Submissão não encontrada.")
        if sub["status"] != StatusSubmissao.PENDENTE.value:
            raise SubmissaoInvalida("Esta submissão não está mais pendente.")
        return sub


class CatalogoService:
    """Busca pública (RF07): só retorna sinais PUBLICADOS."""

    def __init__(self, sinais):
        self.sinais = sinais

    def buscar(self, termo, campo="palavra", ordem="alfabetica"):
        resultados = []
        for s in self.sinais.buscar_publicados(termo, campo, ordem):
            resultados.append((s, self.sinais.listar_videos(s["id"])))
        return resultados
