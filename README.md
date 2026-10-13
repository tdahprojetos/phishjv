# Phishjv

Plataforma própria de **phishing simulado** e **conscientização em segurança** (security awareness),
construída do zero como trabalho original — inspirada na categoria (KnowBe4, Proofpoint, GoPhish),
sem usar código ou conteúdo proprietário de terceiros.

> ⚠️ **Uso autorizado apenas.** O Phishjv é uma ferramenta para simulações de phishing e treinamento
> **dentro de engajamentos autorizados** (contrato/RoE assinado) ou ambientes próprios de laboratório.
> Usar contra pessoas ou organizações sem autorização expressa é ilegal. Você é o único responsável
> pelo uso que fizer da ferramenta.

## O que faz

- **Campanhas de phishing simulado** — templates de e-mail, páginas de destino, agendamento e envio SMTP.
- **Tracking assinado (HMAC)** — abertura (pixel), clique (redirect), submissão de credencial e reporte,
  com tokens que não podem ser forjados.
- **Detecção de falso-clique** — registra IP e *user agent* de cada evento para separar cliques reais
  de scanners de link (Safe Links, gateways de e-mail).
- **Métricas** — *Phish-prone Percentage* (PPP) por campanha/organização e **Risk Score** por alvo.
- **Painel web** — visão de campanhas, alvos e eventos em tempo real.

## Arquitetura

```
phishjv/
  phishjv/
    config.py        # configuração via ambiente (.env)
    db.py            # engine SQLite + sessão SQLAlchemy
    models.py        # Campaign, Target, Template, Event, Group
    security.py      # tokens de tracking assinados (HMAC)
    metrics.py       # PPP e Risk Score
    mailer.py        # envio SMTP
    main.py          # FastAPI: API + tracking + painel
    templates/       # painel (Jinja2)
  seed.py            # dados de demonstração
  run.py             # inicializa o banco e sobe o servidor
  requirements.txt
  .env.example
```

## Como rodar (desenvolvimento)

```bash
cd ~/Desktop/phishjv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # ajuste PHISHJV_SECRET e SMTP_*
python seed.py                # (opcional) carrega dados de demonstração
python run.py                 # sobe em http://127.0.0.1:8000
```

Painel: http://127.0.0.1:8000/  •  API docs: http://127.0.0.1:8000/docs

## Métricas

- **PPP (Phish-prone %)** = alvos únicos que *falharam* ÷ alvos com e-mail entregue × 100.
  Falha = clicou no link, submeteu dados ou abriu anexo. **Reportar o e-mail conta como acerto.**
- **Risk Score (0–100)** por alvo: combina histórico de falhas, reportes, recência e peso do cargo.

## Treinamento (conscientização)

- 5 trilhas originais em pt-BR (phishing, BEC/spear, senhas+MFA, engenharia social, LGPD),
  cada uma com lições e quiz (nota mínima configurável).
- **Inscrição automática de reforço:** quem falha numa campanha é matriculado na trilha
  vinculada à campanha.
- Páginas `/training` (catálogo + inscrições) e `/training/course/{id}` (lições + quiz).

## Triagem de reportes (estilo PhishER)

- E-mails reportados (via Phish Alert Button, `POST /report`) entram em `/triage`.
- Classificação: `unclassified → clean | spam | threat | simulation`.
- Reportes de simulação são creditados ao alvo e marcados automaticamente.

## Phish Alert Button

Add-in de Outlook em `pab/` (Office.js) que reporta o e-mail selecionado para `/report`.
Veja `pab/README.md` para instalação (sideload / implantação no M365).

## Allowlisting no Microsoft 365

Guia em `docs/allowlisting-m365.md` (Advanced Delivery Policy, Safe Links, validação).

## Testes

```bash
.venv/bin/pytest -q
```

## Roadmap

- [x] Trilhas de treinamento (conteúdo próprio)
- [x] Inscrição automática por comportamento (base dos Smart Groups)
- [x] Fila de triagem dos reportes (estilo PhishER) com classificação
- [x] Phish Alert Button (add-in Outlook)
- [x] Guia de allowlisting no Microsoft 365 (Advanced Delivery Policy)
- [ ] Grupos dinâmicos completos (regras salvas e reavaliadas)
- [ ] Certificado de conclusão em PDF
- [ ] Provisionamento via SCIM / Entra ID
