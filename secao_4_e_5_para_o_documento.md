## 4. Repositório e Documentação

**Repositório:** <COLE AQUI O LINK DO GITHUB/GITLAB>

O repositório contém o `README.md` estruturado (escopo implementado, arquitetura, instruções de execução, roteiro de demonstração, testes e limitações).

**Atividades por integrante**

- **Antônia Eulina N. de Oliveira Kiatkoski:** engenharia de requisitos (tipos de usuário, histórias, requisitos funcionais e não funcionais com métricas), caso de uso UC01 e conformidade com a WCAG.
- **Sofia L.:** conformidade com a LGPD, diagramas UML (classes, sequência e atividades) e projeto de software (arquitetura em camadas).
- **Isabelle S.:** implementação do protótipo, testes automatizados, repositório e README.

*(Ajustar conforme a divisão real do trabalho.)*

## 5. Código em Funcionamento

O protótipo, em Python (biblioteca padrão e SQLite), roda por terminal e implementa o fluxo do UC01: o colaborador **insere um novo sinal com vídeo** (RF01/RF02), a submissão fica **pendente** (RF04) e o administrador **aprova ou rejeita com justificativa** (RF06). Também estão implementados o histórico de alterações (RF08), as notificações (RF11), a busca pública de sinais publicados (RF07) e o consentimento LGPD, com termo de responsável legal para menores de 18 anos.

A estrutura segue a arquitetura da seção 3 (apresentação, serviços, domínio e repositório). Para executar: `python main.py`; para os testes: `python -m unittest -v` (8 testes cobrindo aprovação, rejeição, vídeo inválido, permissões e LGPD).

*(Se quiserem, anexem prints do terminal mostrando a submissão, a aprovação e a busca.)*
