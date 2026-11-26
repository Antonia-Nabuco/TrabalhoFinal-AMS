"""Camada de Domínio: entidades e enumerações do diagrama de classes."""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Perfil(str, Enum):
    COLABORADOR = "COLABORADOR"
    ADMINISTRADOR = "ADMINISTRADOR"


class StatusSubmissao(str, Enum):
    PENDENTE = "PENDENTE"
    PUBLICADO = "PUBLICADO"
    REJEITADO = "REJEITADO"


@dataclass
class Usuario:
    id: int
    nome: str
    email: str
    perfil: Perfil
    instituicao: Optional[str] = None
    menor_de_idade: bool = False
