"""Camada de Persistência (padrão Repository) sobre SQLite.

Os repositórios NÃO fazem commit: quem controla a transação é a camada de
serviço (Banco.transacao), garantindo que o fluxo de aprovação seja atômico.
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime


def agora():
    return datetime.now().isoformat(timespec="seconds")


SCHEMA = """
CREATE TABLE IF NOT EXISTS usuario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL,
    perfil TEXT NOT NULL CHECK (perfil IN ('COLABORADOR','ADMINISTRADOR')),
    instituicao TEXT,
    menor_de_idade INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS termo_consentimento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuario(id),
    versao_termo TEXT NOT NULL,
    data_hora_aceite TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS consentimento_responsavel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuario(id),
    documento_url TEXT NOT NULL,
    data_hora TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sinal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    palavra TEXT NOT NULL,
    acepcao TEXT NOT NULL,
    exemplo TEXT,
    classe_gramatical TEXT,
    origem TEXT,
    configuracao_mao TEXT,
    assunto TEXT,
    status TEXT NOT NULL CHECK (status IN ('PENDENTE','PUBLICADO','REJEITADO'))
);
CREATE TABLE IF NOT EXISTS video (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sinal_id INTEGER NOT NULL REFERENCES sinal(id),
    url_original TEXT NOT NULL,
    url_final TEXT NOT NULL,
    thumbnail_url TEXT,
    formato TEXT NOT NULL,
    tamanho INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS submissao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sinal_id INTEGER NOT NULL REFERENCES sinal(id),
    colaborador_id INTEGER NOT NULL REFERENCES usuario(id),
    tipo TEXT NOT NULL,
    data_envio TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PENDENTE','PUBLICADO','REJEITADO')),
    justificativa TEXT
);
CREATE TABLE IF NOT EXISTS historico_alteracao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sinal_id INTEGER NOT NULL REFERENCES sinal(id),
    usuario_id INTEGER NOT NULL REFERENCES usuario(id),
    tipo_alteracao TEXT NOT NULL,
    data_hora TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notificacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuario(id),
    mensagem TEXT NOT NULL,
    data_hora TEXT NOT NULL,
    lida INTEGER NOT NULL DEFAULT 0
);
"""


class Banco:
    def __init__(self, caminho):
        self.conn = sqlite3.connect(caminho)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)

    @contextmanager
    def transacao(self):
        try:
            yield self.conn
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def fechar(self):
        self.conn.close()


class UsuarioRepository:
    def __init__(self, banco):
        self.db = banco

    def criar(self, nome, email, senha_hash, perfil, instituicao, menor):
        cur = self.db.conn.execute(
            "INSERT INTO usuario (nome, email, senha_hash, perfil, instituicao, menor_de_idade)"
            " VALUES (?,?,?,?,?,?)",
            (nome, email, senha_hash, perfil, instituicao, int(menor)),
        )
        return cur.lastrowid

    def buscar_por_id(self, usuario_id):
        return self.db.conn.execute("SELECT * FROM usuario WHERE id=?", (usuario_id,)).fetchone()

    def buscar_por_email(self, email):
        return self.db.conn.execute("SELECT * FROM usuario WHERE email=?", (email,)).fetchone()

    def listar_por_perfil(self, perfil):
        return self.db.conn.execute("SELECT * FROM usuario WHERE perfil=?", (perfil,)).fetchall()

    def registrar_termo(self, usuario_id, versao):
        self.db.conn.execute(
            "INSERT INTO termo_consentimento (usuario_id, versao_termo, data_hora_aceite) VALUES (?,?,?)",
            (usuario_id, versao, agora()),
        )

    def tem_termo(self, usuario_id):
        return self.db.conn.execute(
            "SELECT 1 FROM termo_consentimento WHERE usuario_id=?", (usuario_id,)
        ).fetchone() is not None

    def registrar_consentimento_responsavel(self, usuario_id, documento_url):
        self.db.conn.execute(
            "INSERT INTO consentimento_responsavel (usuario_id, documento_url, data_hora) VALUES (?,?,?)",
            (usuario_id, documento_url, agora()),
        )

    def tem_consentimento_responsavel(self, usuario_id):
        return self.db.conn.execute(
            "SELECT 1 FROM consentimento_responsavel WHERE usuario_id=?", (usuario_id,)
        ).fetchone() is not None


class SinalRepository:
    # Listas brancas: evitam SQL injection ao montar a consulta de busca (RF07).
    CAMPOS_BUSCA = {"palavra": "palavra", "exemplo": "exemplo", "acepcao": "acepcao", "assunto": "assunto"}
    ORDENS = {"alfabetica": "palavra", "assunto": "assunto, palavra", "mao": "configuracao_mao, palavra"}

    def __init__(self, banco):
        self.db = banco

    def criar(self, dados, status):
        cur = self.db.conn.execute(
            "INSERT INTO sinal (palavra, acepcao, exemplo, classe_gramatical, origem,"
            " configuracao_mao, assunto, status) VALUES (?,?,?,?,?,?,?,?)",
            (dados["palavra"], dados["acepcao"], dados.get("exemplo"), dados.get("classe_gramatical"),
             dados.get("origem"), dados.get("configuracao_mao"), dados.get("assunto"), status),
        )
        return cur.lastrowid

    def atualizar_status(self, sinal_id, status):
        self.db.conn.execute("UPDATE sinal SET status=? WHERE id=?", (status, sinal_id))

    def buscar_por_id(self, sinal_id):
        return self.db.conn.execute("SELECT * FROM sinal WHERE id=?", (sinal_id,)).fetchone()

    def buscar_publicados(self, termo, campo="palavra", ordem="alfabetica"):
        coluna = self.CAMPOS_BUSCA[campo]
        ordenacao = self.ORDENS[ordem]
        return self.db.conn.execute(
            f"SELECT * FROM sinal WHERE status='PUBLICADO' AND {coluna} LIKE ? ORDER BY {ordenacao}",
            (f"%{termo}%",),
        ).fetchall()

    def adicionar_video(self, sinal_id, v):
        self.db.conn.execute(
            "INSERT INTO video (sinal_id, url_original, url_final, thumbnail_url, formato, tamanho)"
            " VALUES (?,?,?,?,?,?)",
            (sinal_id, v["url_original"], v["url_final"], v["thumbnail_url"], v["formato"], v["tamanho"]),
        )

    def listar_videos(self, sinal_id):
        return self.db.conn.execute("SELECT * FROM video WHERE sinal_id=?", (sinal_id,)).fetchall()

    def registrar_historico(self, sinal_id, usuario_id, tipo):
        self.db.conn.execute(
            "INSERT INTO historico_alteracao (sinal_id, usuario_id, tipo_alteracao, data_hora) VALUES (?,?,?,?)",
            (sinal_id, usuario_id, tipo, agora()),
        )

    def listar_historico(self, sinal_id):
        return self.db.conn.execute(
            "SELECT * FROM historico_alteracao WHERE sinal_id=? ORDER BY id", (sinal_id,)
        ).fetchall()


class SubmissaoRepository:
    _JOIN = (
        "SELECT s.*, si.palavra, u.nome AS colaborador_nome FROM submissao s"
        " JOIN sinal si ON si.id = s.sinal_id JOIN usuario u ON u.id = s.colaborador_id"
    )

    def __init__(self, banco):
        self.db = banco

    def criar(self, sinal_id, colaborador_id, tipo, status):
        cur = self.db.conn.execute(
            "INSERT INTO submissao (sinal_id, colaborador_id, tipo, data_envio, status) VALUES (?,?,?,?,?)",
            (sinal_id, colaborador_id, tipo, agora(), status),
        )
        return cur.lastrowid

    def buscar_por_id(self, submissao_id):
        return self.db.conn.execute(self._JOIN + " WHERE s.id=?", (submissao_id,)).fetchone()

    def listar_por_status(self, status):
        return self.db.conn.execute(self._JOIN + " WHERE s.status=? ORDER BY s.data_envio", (status,)).fetchall()

    def listar_por_colaborador(self, colaborador_id):
        return self.db.conn.execute(
            self._JOIN + " WHERE s.colaborador_id=? ORDER BY s.data_envio DESC", (colaborador_id,)
        ).fetchall()

    def atualizar_status(self, submissao_id, status, justificativa=None):
        self.db.conn.execute(
            "UPDATE submissao SET status=?, justificativa=? WHERE id=?", (status, justificativa, submissao_id)
        )


class NotificacaoRepository:
    def __init__(self, banco):
        self.db = banco

    def criar(self, usuario_id, mensagem):
        self.db.conn.execute(
            "INSERT INTO notificacao (usuario_id, mensagem, data_hora) VALUES (?,?,?)",
            (usuario_id, mensagem, agora()),
        )

    def listar(self, usuario_id):
        return self.db.conn.execute(
            "SELECT * FROM notificacao WHERE usuario_id=? ORDER BY id DESC", (usuario_id,)
        ).fetchall()

    def marcar_todas_lidas(self, usuario_id):
        self.db.conn.execute("UPDATE notificacao SET lida=1 WHERE usuario_id=?", (usuario_id,))
