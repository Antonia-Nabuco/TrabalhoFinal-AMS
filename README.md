# Expansão do Dicionário da Língua Brasileira de Sinais (Libras)

Trabalho Final da disciplina **AMS0002 – Análise e Modelagem de Sistemas**
Professora: Carla Diacui Medeiros Berkenbrock

Protótipo de linha de comando do fluxo **"submeter novo sinal com vídeo → aprovação (ou rejeição) pelo administrador"**, baseado no dicionário do INES (<https://www.ines.gov.br/dicionario-de-libras/>).

## Equipe e atividades

> Ajustem esta tabela para refletir exatamente o que cada integrante fez.

| Integrante | Atividades |
|---|---|
| Antônia Eulina N. de Oliveira Kiatkoski | Engenharia de requisitos (tipos de usuário, histórias, RF/RNF com métricas); caso de uso UC01; conformidade WCAG |
| Sofia L. | Conformidade LGPD; diagramas UML (classes, sequência, atividades); projeto de software (arquitetura em camadas) |
| Isabelle S. | Implementação do protótipo (camadas, CLI, testes); repositório e README |

## Escopo implementado

| Requisito | Situação |
|---|---|
| RF01 – inserção de sinal (palavra, acepção, exemplo, classe gramatical, origem, configuração de mão, assunto) | Implementado |
| RF02 – upload de vídeo (validação de formato/tamanho e armazenamento) | Implementado |
| RF04 – toda submissão passa por aprovação do administrador | Implementado |
| RF05 – colaborador acompanha o status das submissões | Implementado |
| RF06 – rejeição com justificativa obrigatória | Implementado |
| RF07 – busca por palavra/exemplo/acepção/assunto com ordenação | Implementado (só sinais publicados) |
| RF08 – histórico de alterações | Implementado (submissão, aprovação, rejeição) |
| RF10 – thumbnail | Gerada com `ffmpeg`, se estiver instalado |
| RF11 – notificações | Implementado (internas, no terminal) |
| LGPD – termo de consentimento e responsável legal para menores | Implementado (bloqueia a submissão) |
| Alteração/exclusão (RF01), variações regionais (RF03), reporte (RF09) | Fora do escopo do protótipo |

## Arquitetura (seção 3 do documento)

Arquitetura em camadas, com Repository na persistência:

```
main.py                         # monta as camadas (injeção de dependências)
libras/
  apresentacao/cli.py           # terminal (sem regras de negócio)
  servicos/                     # regras de negócio: fluxo UC01, auth, vídeo, notificações, consentimento LGPD
  dominio/                      # entidades, enums e exceções de negócio
  repositorio/repositorios.py   # Repository sobre SQLite (acesso a dados)
tests/test_submissao.py         # testes do fluxo de aprovação
```

O processamento de vídeo (`video_service.py`) roda de forma síncrona no protótipo; no projeto completo seria o worker assíncrono descrito na seção 3.

## Como executar

Requisitos: **Python 3.9+**. Não há dependências externas (usa só a biblioteca padrão). `ffmpeg` é opcional.

```bash
git clone <URL-DO-REPOSITORIO>
cd dicionario-libras
python main.py
```

Os dados ficam na pasta `dados/` (ou em `LIBRAS_DATA`). Na primeira execução é criado um administrador de demonstração:

- e-mail: `admin@ines.gov.br`  senha: `admin123`

### Roteiro de demonstração

1. `3) Cadastrar colaborador` e depois `2) Entrar` com esse usuário.
2. `1) Submeter novo sinal`: preencha os campos e informe o caminho de um vídeo `.mp4`, `.webm` ou `.mov` (até 50 MB). Aceite o termo de consentimento. A submissão fica **PENDENTE**.
3. Saia, entre como administrador, abra a **Fila de aprovação**, revise e **aprove** (ou **rejeite** com justificativa).
4. No menu inicial, use `1) Buscar sinal`: o sinal só aparece depois de aprovado.
5. Entre como colaborador e veja o status e as notificações.

Fluxos alternativos: vídeo com formato inválido (E1) não gera submissão; colaborador menor de 18 anos precisa do termo de um responsável.

### Testes

```bash
python -m unittest -v
```

## Limitações do protótipo

- Sem interface gráfica nem API web.
- Vídeo e thumbnail processados de forma síncrona; a duração do vídeo não é extraída.
- Notificações apenas dentro do sistema (sem e-mail).
- A rotina de exclusão de vídeos rejeitados após 30 dias (LGPD) está apenas especificada.
