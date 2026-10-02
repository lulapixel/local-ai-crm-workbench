# Usar o ProspectOS Local

Abra **ProspectOS Local** na área de trabalho. A janela inicia o serviço, confere sua disponibilidade e abre **Mesa do gestor**. Nela, confira a recomendação, prepare sua oferta e acompanhe recebimentos declarados. A fila por tempo continua em **Minha sessão**. Não é necessário abrir terminal ou manter uma aba do navegador. Uma segunda abertura foca a janela existente. Fechar o aplicativo encerra o serviço que ele iniciou.

Em **Minha sessão**, escolha 15, 30 ou 60 minutos. A ordem é: conversas respondidas, textos do bot para revisar, retornos vencidos e novos contatos elegíveis. Cada item explica a razão e abre o contato ou a revisão correspondente. O score é uma heurística; minutos são estimativas fixas. O planejamento não usa IA, não dispara capturas e não transmite mensagens. Instagram continua acessível pela navegação, com sua fila própria.

O acompanhamento mostra os estados comerciais registrados, os limites e a agenda do bot e a configuração dos canais. Um executável Codex detectado não comprova login ou modelo. As aprovações de destinatário e texto continuam no bot. Este launcher mantém envios externos desativados; integrar e validar contas/canais é uma etapa separada.

## Onde ficam os dados desta instalação

- Código: este checkout do projeto.
- Dados persistentes: `desktop/local-data`, incluindo SQLite, backups e perfil da janela. A pasta está excluída do Git. Não removê-la para atualizar a interface.
- Runtime da janela: `desktop/local-runtime`, excluído do Git.
- Testes e demonstração: `desktop/local-validation`, isolado dos dados persistentes e excluído do Git.

A preparação cria uma base própria quando não há dados locais e preserva uma base existente. Não copia credenciais, sessão de Instagram nem dados de outras instalações. Não mover este checkout ou apagar o Python configurado: este pacote local depende deles. Isso é um aplicativo local com atalho, não um instalador autossuficiente ou assinado para distribuição pública.

## Preparação e recuperação

`desktop/prepare-local.py` aceita `--runtime` com uma distribuição Electron Windows existente e `--python` com o Python que contém as dependências do backend. Exige frontend compilado e prepara `desktop/local-runtime`. Feche o aplicativo antes de preparar novamente esse runtime. Não baixa executáveis nem reutiliza `app.asar`, backend ou updater antigos. Mantém os avisos de licença do runtime.

A opção `--scraper` permite preparar também uma cópia explicitamente indicada de `google-maps-scraper.exe` em `backend/`, excluída do Git. Disponibilidade do arquivo não comprova aceitação ou funcionamento atual da fonte externa. A validação desta entrega não executou captura externa.

`ProspectOS.exe --smoke` usa uma base de teste isolada, desativa a automação e grava um recibo em `desktop/local-validation/desktop-smoke.json`. A captura da janela é um diagnóstico opcional; uma falha dessa captura fica separada da disponibilidade do serviço e do carregamento da interface.

Depois da validação, `desktop/install-local-shortcut.ps1` cria **ProspectOS Local.lnk** na área de trabalho. Recusa sobrescrever um atalho do mesmo nome que aponte para outro aplicativo. O atalho instalado usa a janela normal, sem flags de teste.

Se o serviço falhar, a tela de inicialização oferece **Tentar novamente**. Confira se o checkout, o build e o Python ainda existem. Não usa porta de arquivo antigo ou anexa outro serviço: valida a identidade da instância anunciada pelo próprio processo. O modo opcional `--software-rendering` desativa aceleração gráfica para diagnóstico de compatibilidade.

O aplicativo local não usa o feed de atualização do projeto anterior. Atualizações desta versão devem ser preparadas e verificadas neste checkout. [Distribuição manual do Electron](https://www.electronjs.org/docs/latest/tutorial/application-distribution) e [guia de segurança](https://www.electronjs.org/docs/latest/tutorial/security) fundamentam o layout, isolamento e guardas de navegação; não representam uma auditoria completa das dependências.
