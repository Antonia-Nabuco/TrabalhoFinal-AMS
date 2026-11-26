"""Testes do fluxo UC01 (submeter -> aprovar/rejeitar). Execute: python -m unittest -v"""
import shutil
import tempfile
import unittest
from pathlib import Path

from libras.dominio.excecoes import (CampoObrigatorio, ConsentimentoPendente, PermissaoNegada,
                                     VideoInvalido)
from libras.dominio.modelos import Perfil
from main import montar

DADOS = {"palavra": "MAMÃE", "acepcao": "A mulher que tem filhos.", "exemplo": "A mãe é importante.",
         "classe_gramatical": "SUBSTANTIVO", "origem": "nacional", "assunto": "FAMÍLIA"}


class TesteFluxoAprovacao(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.banco, self.auth, self.sub, self.catalogo, self.notif = montar(self.tmp / "dados")
        self.admin = self.auth.cadastrar("Admin", "admin@x.com", "123456", Perfil.ADMINISTRADOR)
        self.colab = self.auth.cadastrar("Ana", "ana@x.com", "123456")
        self.video = self.tmp / "sinal.mp4"
        self.video.write_bytes(b"video-falso")
        self.sub.aceitar_termo(self.colab)

    def tearDown(self):
        self.banco.fechar()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_submissao_fica_pendente_e_invisivel(self):
        sid = self.sub.submeter_sinal(self.colab, DADOS, str(self.video))
        self.assertEqual(self.sub.minhas_submissoes(self.colab)[0]["status"], "PENDENTE")
        self.assertEqual(self.catalogo.buscar("MAM"), [])
        self.assertEqual(len(self.notif.listar(self.admin.id)), 1)
        self.assertEqual(len(self.sub.fila_de_aprovacao(self.admin)), 1)
        self.assertTrue(sid)

    def test_aprovacao_publica_e_notifica(self):
        sid = self.sub.submeter_sinal(self.colab, DADOS, str(self.video))
        self.sub.aprovar(self.admin, sid)
        self.assertEqual(len(self.catalogo.buscar("MAM")), 1)
        self.assertIn("APROVADA", self.notif.listar(self.colab.id)[0]["mensagem"])

    def test_rejeicao_exige_justificativa(self):
        sid = self.sub.submeter_sinal(self.colab, DADOS, str(self.video))
        with self.assertRaises(CampoObrigatorio):
            self.sub.rejeitar(self.admin, sid, "  ")
        self.sub.rejeitar(self.admin, sid, "Vídeo sem boa iluminação.")
        self.assertEqual(self.sub.minhas_submissoes(self.colab)[0]["justificativa"], "Vídeo sem boa iluminação.")
        self.assertEqual(self.catalogo.buscar("MAM"), [])

    def test_video_invalido_nao_registra_submissao_E1(self):
        ruim = self.tmp / "sinal.txt"
        ruim.write_text("nao e video")
        with self.assertRaises(VideoInvalido):
            self.sub.submeter_sinal(self.colab, DADOS, str(ruim))
        self.assertEqual(self.sub.minhas_submissoes(self.colab), [])

    def test_colaborador_nao_aprova(self):
        sid = self.sub.submeter_sinal(self.colab, DADOS, str(self.video))
        with self.assertRaises(PermissaoNegada):
            self.sub.aprovar(self.colab, sid)

    def test_sem_termo_bloqueia(self):
        outra = self.auth.cadastrar("Bia", "bia@x.com", "123456")
        with self.assertRaises(ConsentimentoPendente) as ctx:
            self.sub.submeter_sinal(outra, DADOS, str(self.video))
        self.assertEqual(ctx.exception.faltando, ["termo"])

    def test_menor_exige_responsavel(self):
        menor = self.auth.cadastrar("Caio", "caio@x.com", "123456", menor=True)
        self.sub.aceitar_termo(menor)
        with self.assertRaises(ConsentimentoPendente) as ctx:
            self.sub.submeter_sinal(menor, DADOS, str(self.video))
        self.assertEqual(ctx.exception.faltando, ["responsavel"])
        self.sub.registrar_consentimento_responsavel(menor, "termo_assinado.pdf")
        self.assertTrue(self.sub.submeter_sinal(menor, DADOS, str(self.video)))

    def test_historico_registrado(self):
        sid = self.sub.submeter_sinal(self.colab, DADOS, str(self.video))
        self.sub.aprovar(self.admin, sid)
        sinal_id = self.sub.submissoes.buscar_por_id(sid)["sinal_id"]
        tipos = [h["tipo_alteracao"] for h in self.sub.sinais.listar_historico(sinal_id)]
        self.assertEqual(tipos, ["SUBMISSAO", "APROVACAO"])


if __name__ == "__main__":
    unittest.main()
