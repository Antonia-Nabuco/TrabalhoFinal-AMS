"""Erros de negócio. A camada de apresentação só precisa capturar ErroDeNegocio."""


class ErroDeNegocio(Exception):
    pass


class AutenticacaoFalhou(ErroDeNegocio):
    pass


class PermissaoNegada(ErroDeNegocio):
    pass


class CampoObrigatorio(ErroDeNegocio):
    pass


class VideoInvalido(ErroDeNegocio):
    """Fluxo de exceção E1 do UC01."""


class SubmissaoInvalida(ErroDeNegocio):
    pass


class ConsentimentoPendente(ErroDeNegocio):
    """LGPD: `faltando` pode conter 'termo' e/ou 'responsavel'."""

    def __init__(self, faltando):
        super().__init__("Consentimento LGPD pendente: " + ", ".join(faltando))
        self.faltando = list(faltando)
