# Allowlisting do Phishjv no Microsoft 365

Para que os e-mails de **simulação** cheguem à caixa de entrada sem serem bloqueados,
filtrados como spam ou terem os links "clicados" por scanners, configure o Microsoft 365
para tratar o Phishjv como uma ferramenta de simulação de phishing de terceiros.

> Faça isso **apenas** no tenant que você está autorizado a testar (RoE assinado).

## 1. Advanced Delivery Policy (caminho recomendado)

No **Microsoft Defender** (security.microsoft.com):

1. **Email & collaboration → Policies & rules → Threat policies → Advanced delivery**.
2. Aba **Phishing simulation → Add** (ou editar).
3. Informe:
   - **Sending domains**: o domínio que você usa no `SMTP_FROM` do Phishjv.
   - **Sending IPs**: o IP público do servidor que envia as campanhas.
   - **Simulation URLs to allow**: as URLs de clique/landing do Phishjv
     (ex.: `https://seu-phishjv/t/c/*`, `https://seu-phishjv/l/*`).

Isso evita que Defender/EOP marquem as mensagens como ameaça **e** que o Safe Links
"detone" os links automaticamente (o que inflaria o PPP com cliques de robô).

## 2. Por que NÃO usar regras de transporte genéricas

Criar uma *mail flow rule* que simplesmente pula a filtragem (SCL -1) por IP é frágil e
inseguro: abre brecha para abuso e não resolve o Safe Links. A Advanced Delivery Policy é
o mecanismo oficial e mais restrito para simulação.

## 3. Safe Links / Safe Attachments

Mesmo com a policy acima, confirme que as URLs do Phishjv constam em **Simulation URLs to
allow**. Sem isso, o Safe Links abre o link no lado do servidor e gera um evento de clique
falso — o Phishjv já marca esses como `is_bot` pelo *user agent*, mas o ideal é evitá-los
na origem.

## 4. Validação

- Envie uma campanha de teste para uma caixa controlada.
- Confirme que o e-mail chega à **Caixa de entrada** (não Lixo Eletrônico/Quarentena).
- No painel do Phishjv, verifique se aparecem aberturas/cliques **humanos** e se os
  eventos de scanner estão corretamente marcados como `is_bot` (não contam no PPP).

## 5. Provisionamento de usuários (opcional)

Sincronize os alvos a partir do Entra ID/Active Directory (exportação CSV ou, no futuro,
SCIM) para manter nome, e-mail e cargo (que alimenta o `role_weight` do Risk Score).
