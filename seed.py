"""Carrega dados de demonstração para visualizar o Phishjv rapidamente.

Cria um grupo, alvos, um template, uma campanha e simula eventos (abertura, clique,
submissão, reporte e um evento de 'scanner') para o painel e as métricas ganharem vida.
"""
from __future__ import annotations

from phishjv.db import SessionLocal, init_db
from phishjv.models import (
    Campaign,
    CampaignStatus,
    Course,
    Enrollment,
    Event,
    EventType,
    Group,
    Target,
    Template,
)
from phishjv.training_content import load_courses

EMAIL_HTML = """\
<p>Olá {{first_name}},</p>
<p>Detectamos um acesso incomum à sua conta. Confirme sua identidade em até 24h
para evitar o bloqueio:</p>
<p><a href="{{link}}">Verificar minha conta</a></p>
<p>Equipe de Segurança</p>
{{tracker}}
"""

LANDING_HTML = """\
<!doctype html><meta charset="utf-8"><title>Entrar</title>
<form method="post" action="{{action}}" style="max-width:320px;margin:60px auto;font-family:sans-serif">
  <h3>Entrar na sua conta</h3>
  <input name="user" placeholder="Usuário" style="width:100%;padding:8px;margin:6px 0">
  <input name="pass" type="password" placeholder="Senha" style="width:100%;padding:8px;margin:6px 0">
  <button style="width:100%;padding:9px">Entrar</button>
</form>
"""

TARGETS = [
    ("ana.souza@exemplo-interno.local", "Ana", "Souza", "Analista Financeiro", 1.4),
    ("bruno.lima@exemplo-interno.local", "Bruno", "Lima", "Desenvolvedor", 1.0),
    ("carla.dias@exemplo-interno.local", "Carla", "Dias", "Diretora", 1.8),
    ("diego.alves@exemplo-interno.local", "Diego", "Alves", "Suporte TI", 1.1),
    ("elisa.rocha@exemplo-interno.local", "Elisa", "Rocha", "RH", 1.2),
    ("fabio.melo@exemplo-interno.local", "Fabio", "Melo", "Comercial", 1.0),
]

# (índice do alvo, tipo de evento, é_bot)
EVENTS = [
    (0, EventType.opened, False), (0, EventType.clicked, False), (0, EventType.submitted, False),
    (1, EventType.opened, False), (1, EventType.reported, False),
    (2, EventType.opened, False), (2, EventType.clicked, False),
    (3, EventType.opened, False),
    (4, EventType.opened, False), (4, EventType.clicked, False), (4, EventType.submitted, False),
    (5, EventType.clicked, True),  # scanner de link: NÃO deve contar no PPP
]


def main() -> None:
    init_db()
    s = SessionLocal()
    try:
        # Trilhas de treinamento originais (idempotente).
        n = load_courses(s)
        print(f"Trilhas de treinamento carregadas: +{n}")

        if s.query(Campaign).count():
            print("Banco já tem campanhas. Pulei a criação de demo.")
            return

        group = Group(name="Piloto - Matriz")
        s.add(group)
        s.flush()

        targets = []
        for email, fn, ln, pos, w in TARGETS:
            t = Target(
                email=email, first_name=fn, last_name=ln, position=pos,
                role_weight=w, group_id=group.id,
            )
            s.add(t)
            targets.append(t)
        s.flush()

        tpl = Template(
            name="Alerta de acesso incomum",
            subject="[Ação necessária] Acesso incomum à sua conta",
            html=EMAIL_HTML,
            landing_html=LANDING_HTML,
        )
        s.add(tpl)
        s.flush()

        # Trilha de reforço vinculada à campanha (quem falha é inscrito nela).
        reforco = s.query(Course).filter_by(slug="phishing-email").first()

        camp = Campaign(
            name="Q4 - Conscientização (piloto)",
            status=CampaignStatus.running,
            template_id=tpl.id,
            group_id=group.id,
            training_course_id=reforco.id if reforco else None,
        )
        s.add(camp)
        s.flush()

        # Todos receberam o e-mail.
        for t in targets:
            s.add(Event(campaign_id=camp.id, target_id=t.id, type=EventType.sent))
        # Eventos simulados.
        for idx, etype, is_bot in EVENTS:
            s.add(
                Event(
                    campaign_id=camp.id,
                    target_id=targets[idx].id,
                    type=etype,
                    is_bot=is_bot,
                    user_agent="SafeLinks-Scanner" if is_bot else "Mozilla/5.0",
                )
            )
        # Inscreve automaticamente quem falhou como humano (clicou/submeteu, não-bot).
        if reforco:
            failed_human = sorted(
                {idx for idx, et, is_bot in EVENTS
                 if et in (EventType.clicked, EventType.submitted) and not is_bot}
            )
            for idx in failed_human:
                s.add(
                    Enrollment(
                        target_id=targets[idx].id,
                        course_id=reforco.id,
                        reason=f"Falha na campanha: {camp.name}",
                    )
                )
            print(f"Inscrições de reforço criadas: {len(failed_human)}")

        s.commit()
        print(f"Seed OK: grupo={group.id} alvos={len(targets)} campanha={camp.id}")
        print("Suba o servidor com: python run.py  ->  http://127.0.0.1:8000")
    finally:
        s.close()


if __name__ == "__main__":
    main()
