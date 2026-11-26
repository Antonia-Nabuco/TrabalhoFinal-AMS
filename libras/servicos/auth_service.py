"""Cadastro e autenticação. Senhas guardadas com hash PBKDF2 + salt (RNF05)."""
import hashlib
import hmac
import os
import sqlite3

from libras.dominio.excecoes import AutenticacaoFalhou, CampoObrigatorio, ErroDeNegocio
from libras.dominio.modelos import Perfil, Usuario


def _hash(senha, salt=None):
    salt = salt or os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, 200_000)
    return salt.hex() + "$" + h.hex()


def _confere(senha, armazenado):
    salt_hex, _ = armazenado.split("$")
    return hmac.compare_digest(_hash(senha, bytes.fromhex(salt_hex)), armazenado)


def _para_usuario(row):
    return Usuario(row["id"], row["nome"], row["email"], Perfil(row["perfil"]),
                   row["instituicao"], bool(row["menor_de_idade"]))


class AuthService:
    def __init__(self, banco, usuarios):
        self.banco = banco
        self.usuarios = usuarios

    def cadastrar(self, nome, email, senha, perfil=Perfil.COLABORADOR, instituicao=None, menor=False):
        if not nome.strip() or "@" not in email:
            raise CampoObrigatorio("Informe nome e um e-mail válido.")
        if len(senha) < 6:
            raise CampoObrigatorio("A senha deve ter ao menos 6 caracteres.")
        try:
            with self.banco.transacao():
                uid = self.usuarios.criar(nome.strip(), email.strip().lower(), _hash(senha),
                                          perfil.value, instituicao, menor)
        except sqlite3.IntegrityError:
            raise ErroDeNegocio("E-mail já cadastrado.")
        return _para_usuario(self.usuarios.buscar_por_id(uid))

    def autenticar(self, email, senha):
        row = self.usuarios.buscar_por_email(email.strip().lower())
        if row is None or not _confere(senha, row["senha_hash"]):
            raise AutenticacaoFalhou("E-mail ou senha inválidos.")
        return _para_usuario(row)
