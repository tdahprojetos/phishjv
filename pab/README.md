# Phish Alert Button (PAB) — add-in de Outlook

Botão que permite ao usuário reportar, com um clique, um e-mail suspeito direto para a
**fila de triagem do Phishjv** (endpoint `POST /report`).

## Arquivos

- `manifest.xml` — manifesto do add-in de Outlook (Office Add-in).
- `taskpane.html` — painel que lê o e-mail selecionado e envia para o Phishjv via Office.js.
- `icon-64.png` / `icon-128.png` — ícones do botão (adicione os seus).

## Como instalar (sideload para testes)

1. Hospede os arquivos de `pab/` em uma URL **HTTPS** pública e ajuste as URLs
   `https://phishjv.example.com` no `manifest.xml` e o endpoint no `taskpane.html`.
2. No Outlook: **Obter Suplementos → Meus Suplementos → Adicionar um suplemento personalizado
   → Adicionar do arquivo** e selecione o `manifest.xml`.
3. Abra um e-mail e clique em **Phishjv — Reportar phishing**.

Para implantação em toda a organização, use o **Centro de administração do Microsoft 365
→ Configurações → Suplementos integrados** (ou Exchange: *Get-App / New-App*).

## Observações

- O add-in envia assunto, remetente e um trecho do corpo (até 2000 caracteres) — **não** a
  mensagem inteira — para `POST /report`.
- Em um e-mail de **simulação** do Phishjv, prefira o link de reporte assinado
  (`/t/r/<token>`), que credita o acerto ao alvo na campanha.
