# Canais de envio assistido e automático

O WhatsApp manual permanece funcional: aprovar texto e contato, abrir conversa e confirmar envio. Não há transmissão automática por essa abertura.

Conectores implementados para configuração futura: **Resend** (e-mail em texto) e **WhatsApp Cloud API** (template previamente aprovado, com um parâmetro no corpo). Contas, aprovação do template, autorização dos destinatários e teste real de entrega permanecem pendentes. Nenhum serviço pago foi contratado e nenhuma mensagem real foi enviada durante desenvolvimento.

## Configuração local

Credenciais somente no ambiente do processo, fora do Git e do navegador. A API não recebe tokens nem devolve valores de segredo.

| Canal | Variáveis necessárias |
|---|---|
| Codex | `PROSPECTOS_CODEX_BIN` opcional, caminho absoluto do `codex.exe`; sessão ChatGPT já autenticada |
| Resend | `PROSPECTOS_RESEND_API_KEY`, `PROSPECTOS_EMAIL_FROM` (remetente validado) |
| WhatsApp | `PROSPECTOS_WA_TOKEN`, `PROSPECTOS_WA_PHONE_ID`, `PROSPECTOS_WA_API_VERSION`, `PROSPECTOS_WA_TEMPLATE`, `PROSPECTOS_WA_TEMPLATE_BODY` (corpo exato aprovado, com um `{{1}}`), `PROSPECTOS_WA_LANGUAGE` opcional (padrão `pt_BR`) |
| Liberação de transmissão | `PROSPECTOS_BOT_LIVE_SENDS=1` somente após provisionar e verificar os canais |

E-mail do destinatário é informado e revisado pelo operador; não se inventam endereços. Número WhatsApp deriva do contato atual normalizado. Prévia mostra corpo final, destinatário e fingerprint de remetente/template/payload. Aprovação final compara o fingerprint e exige atestado de autorização de contato. Isso não constitui verificação independente de consentimento pelo software.

## Estados e recuperação

`queued → sending → provider_accepted`; antes da transmissão, alterações ou configuração ausente resultam em `blocked`. Erro após início de tentativa ou reinício resulta em `unknown`. Não há repetição automática de estado incerto. Somente bloqueio anterior à requisição permite nova aprovação/tentativa. O operador verifica o painel do provedor e reconcilia o CRM em caso de resultado incerto.

Aceitação pelo provedor não prova entrega, leitura ou resposta. Ao obter um ID, o bot registra envio e agenda somente o próximo retorno, caso o lead ainda esteja elegível. Se o status mudar durante a requisição, a aceitação fica registrada e a atualização do CRM pede reconciliação. Edição enquanto a requisição está em andamento é bloqueada.

Webhook de entrega/resposta, supressão por unsubscribe e coleta automática de consentimento não estão implementados. Não ativar campanhas sem autorização dos contatos e procedimentos adequados ao canal. O bot não aprova templates nem cria contas.

Referências: [Resend — envio](https://resend.com/docs/api-reference/emails/send-email), [Meta — coleção oficial WhatsApp](https://www.postman.com/meta/whatsapp-business-platform/documentation/wlk6lh4/whatsapp-cloud-api).
