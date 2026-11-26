"""Camada de Apresentação (terminal). Não contém regras de negócio: só lê, chama serviços e imprime."""
from libras.dominio.excecoes import ConsentimentoPendente, ErroDeNegocio
from libras.dominio.modelos import Perfil
from libras.servicos.consentimento import TEXTO_TERMO


def ler(prompt, obrigatorio=False):
    while True:
        valor = input(prompt).strip()
        if valor or not obrigatorio:
            return valor
        print("  Campo obrigatório.")


def titulo(texto):
    print("\n" + "=" * 60 + f"\n {texto}\n" + "=" * 60)


class CLI:
    def __init__(self, auth, submissao, catalogo, notificacoes):
        self.auth = auth
        self.submissao = submissao
        self.catalogo = catalogo
        self.notificacoes = notificacoes

    def executar(self):
        try:
            while True:
                titulo("DICIONÁRIO DE LIBRAS - EXPANSÃO")
                print("1) Buscar sinal   2) Entrar   3) Cadastrar colaborador   0) Sair")
                op = ler("> ")
                try:
                    if op == "1":
                        self.buscar()
                    elif op == "2":
                        usuario = self.auth.autenticar(ler("E-mail: "), ler("Senha: "))
                        if usuario.perfil == Perfil.ADMINISTRADOR:
                            self.menu_admin(usuario)
                        else:
                            self.menu_colaborador(usuario)
                    elif op == "3":
                        self.cadastrar()
                    elif op == "0":
                        return
                    else:
                        print("Opção inválida.")
                except ErroDeNegocio as erro:
                    print(f"\n[!] {erro}")
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrado.")

    # ---------- público ----------
    def buscar(self):
        titulo("BUSCAR SINAL")
        campos = {"1": "palavra", "2": "exemplo", "3": "acepcao", "4": "assunto"}
        ordens = {"1": "alfabetica", "2": "assunto", "3": "mao"}
        campo = campos.get(ler("Buscar por 1) palavra 2) exemplo 3) acepção 4) assunto [1]: "), "palavra")
        ordem = ordens.get(ler("Ordenar por 1) alfabética 2) assunto 3) configuração de mão [1]: "), "alfabetica")
        resultados = self.catalogo.buscar(ler("Termo (vazio = todos): "), campo, ordem)
        if not resultados:
            print("Nenhum sinal publicado encontrado.")
        for sinal, videos in resultados:
            print(f"\n- {sinal['palavra']}  [{sinal['classe_gramatical'] or '-'} | origem: {sinal['origem'] or '-'}]")
            print(f"  Acepção: {sinal['acepcao']}")
            if sinal["exemplo"]:
                print(f"  Exemplo: {sinal['exemplo']}")
            print(f"  Assunto: {sinal['assunto'] or '-'} | Mão: {sinal['configuracao_mao'] or '-'}")
            for v in videos:
                print(f"  Vídeo: {v['url_final']}")

    def cadastrar(self):
        titulo("CADASTRO DE COLABORADOR")
        nome = ler("Nome: ", True)
        email = ler("E-mail: ", True)
        senha = ler("Senha (mín. 6 caracteres): ", True)
        instituicao = ler("Instituição (opcional): ") or None
        menor = ler("Você tem menos de 18 anos? (s/n): ").lower() == "s"
        self.auth.cadastrar(nome, email, senha, Perfil.COLABORADOR, instituicao, menor)
        print("Cadastro realizado. Faça login para submeter sinais.")

    # ---------- colaborador ----------
    def menu_colaborador(self, usuario):
        while True:
            titulo(f"COLABORADOR: {usuario.nome}")
            print("1) Submeter novo sinal  2) Acompanhar submissões  3) Notificações  0) Sair")
            op = ler("> ")
            try:
                if op == "1":
                    self.submeter(usuario)
                elif op == "2":
                    self.acompanhar(usuario)
                elif op == "3":
                    self.ver_notificacoes(usuario)
                elif op == "0":
                    return
            except ErroDeNegocio as erro:
                print(f"\n[!] {erro}")

    def submeter(self, usuario):
        titulo("NOVO SINAL (UC01 - passos 1 e 2)")
        dados = {
            "palavra": ler("Palavra*: ", True),
            "acepcao": ler("Acepção*: ", True),
            "exemplo": ler("Exemplo: "),
            "classe_gramatical": ler("Classe gramatical* (ex.: SUBSTANTIVO): ", True),
            "origem": ler("Origem (nacional/regional): "),
            "configuracao_mao": ler("Configuração de mão: "),
            "assunto": ler("Assunto: "),
        }
        caminho = ler("Caminho do vídeo (.mp4/.webm/.mov)*: ", True)
        while True:
            try:
                sid = self.submissao.submeter_sinal(usuario, dados, caminho)
                print(f"\nSubmissão #{sid} registrada com status PENDENTE. Os administradores foram notificados.")
                return
            except ConsentimentoPendente as pendente:
                if not self._coletar_consentimento(usuario, pendente.faltando):
                    print("Sem consentimento, a submissão não pode avançar (LGPD).")
                    return

    def _coletar_consentimento(self, usuario, faltando):
        if "termo" in faltando:
            print("\n" + TEXTO_TERMO)
            if ler("Você aceita o termo? (s/n): ").lower() != "s":
                return False
            self.submissao.aceitar_termo(usuario)
        if "responsavel" in faltando:
            print("\nComo você é menor de 18 anos, é necessário o termo assinado por um responsável legal.")
            doc = ler("Caminho/URL do termo assinado (vazio para cancelar): ")
            if not doc:
                return False
            self.submissao.registrar_consentimento_responsavel(usuario, doc)
        return True

    def acompanhar(self, usuario):
        titulo("MINHAS SUBMISSÕES")
        itens = self.submissao.minhas_submissoes(usuario)
        if not itens:
            print("Você ainda não enviou submissões.")
        for s in itens:
            linha = f"#{s['id']} {s['palavra']} - {s['status']} (enviada em {s['data_envio']})"
            if s["justificativa"]:
                linha += f"\n    Justificativa: {s['justificativa']}"
            print(linha)

    # ---------- administrador ----------
    def menu_admin(self, admin):
        while True:
            titulo(f"ADMINISTRADOR: {admin.nome}")
            print("1) Fila de aprovação  2) Notificações  0) Sair")
            op = ler("> ")
            try:
                if op == "1":
                    self.fila(admin)
                elif op == "2":
                    self.ver_notificacoes(admin)
                elif op == "0":
                    return
            except ErroDeNegocio as erro:
                print(f"\n[!] {erro}")

    def fila(self, admin):
        titulo("FILA DE APROVAÇÃO (UC01 - passo 5)")
        fila = self.submissao.fila_de_aprovacao(admin)
        if not fila:
            print("Nenhuma submissão pendente.")
            return
        for s in fila:
            print(f"#{s['id']} {s['palavra']} - por {s['colaborador_nome']} em {s['data_envio']}")
        escolha = ler("\nNúmero da submissão para revisar (vazio = voltar): ")
        if not escolha.isdigit():
            return
        sub, sinal, videos = self.submissao.detalhar(admin, int(escolha))
        titulo(f"REVISÃO DA SUBMISSÃO #{sub['id']} (UC01 - passo 6)")
        for rotulo, chave in [("Palavra", "palavra"), ("Acepção", "acepcao"), ("Exemplo", "exemplo"),
                              ("Classe gramatical", "classe_gramatical"), ("Origem", "origem"),
                              ("Configuração de mão", "configuracao_mao"), ("Assunto", "assunto")]:
            print(f"{rotulo}: {sinal[chave] or '-'}")
        for v in videos:
            print(f"Vídeo para reproduzir: {v['url_final']} ({v['formato']}, {v['tamanho']} bytes)")
        decisao = ler("\n[A]provar, [R]ejeitar ou [V]oltar? ").lower()
        if decisao == "a":
            self.submissao.aprovar(admin, sub["id"])
            print("Sinal PUBLICADO. Colaborador notificado.")
        elif decisao == "r":
            self.submissao.rejeitar(admin, sub["id"], ler("Justificativa*: ", True))
            print("Submissão REJEITADA. Colaborador notificado com a justificativa.")

    # ---------- comum ----------
    def ver_notificacoes(self, usuario):
        titulo("NOTIFICAÇÕES")
        itens = self.notificacoes.listar(usuario.id)
        if not itens:
            print("Sem notificações.")
        for n in itens:
            print(f"[{'lida' if n['lida'] else 'NOVA'}] {n['data_hora']} - {n['mensagem']}")
        self.notificacoes.marcar_todas_lidas(usuario.id)
