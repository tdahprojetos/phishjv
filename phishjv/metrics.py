"""Cálculo de métricas: Phish-prone Percentage (PPP) e Risk Score."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import FAILURE_EVENTS, Campaign, Event, EventType, Target


@dataclass
class CampaignStats:
    total: int           # alvos com e-mail enviado/entregue
    opened: int
    clicked: int
    submitted: int
    reported: int
    failed: int          # alvos únicos que falharam (clicou ou submeteu)
    ppp: float           # phish-prone percentage

    def as_dict(self) -> dict:
        return self.__dict__


def _unique_targets(events: list[Event], types: set[EventType]) -> set[int]:
    """Alvos únicos que geraram pelo menos um evento humano (não-bot) dos tipos dados."""
    return {e.target_id for e in events if e.type in types and not e.is_bot}


def campaign_stats(session: Session, campaign_id: int) -> CampaignStats:
    events = list(session.scalars(select(Event).where(Event.campaign_id == campaign_id)))

    sent = _unique_targets(events, {EventType.sent, EventType.delivered})
    total = len(sent) or len(_unique_targets(events, set(EventType)))
    opened = _unique_targets(events, {EventType.opened})
    clicked = _unique_targets(events, {EventType.clicked})
    submitted = _unique_targets(events, {EventType.submitted})
    reported = _unique_targets(events, {EventType.reported})
    failed = _unique_targets(events, FAILURE_EVENTS)

    ppp = round(100.0 * len(failed) / total, 1) if total else 0.0
    return CampaignStats(
        total=total,
        opened=len(opened),
        clicked=len(clicked),
        submitted=len(submitted),
        reported=len(reported),
        failed=len(failed),
        ppp=ppp,
    )


def org_ppp(session: Session) -> float:
    """PPP agregado de todas as campanhas (média ponderada pelo nº de alvos)."""
    total = 0
    failed = 0
    for camp in session.scalars(select(Campaign)):
        s = campaign_stats(session, camp.id)
        total += s.total
        failed += s.failed
    return round(100.0 * failed / total, 1) if total else 0.0


def target_risk_score(session: Session, target: Target) -> int:
    """Risk Score 0–100 por alvo.

    Combina:
      - taxa de falha histórica (clicou/submeteu) — maior peso;
      - submissões de credencial (pior que clique);
      - reportes (reduzem o risco — bom comportamento);
      - recência (falhas recentes pesam mais);
      - peso do cargo (role_weight) como multiplicador.
    """
    events = list(session.scalars(select(Event).where(Event.target_id == target.id)))
    human = [e for e in events if not e.is_bot]
    if not human:
        return 0

    campaigns_touched = {e.campaign_id for e in human}
    n = len(campaigns_touched) or 1

    failed_campaigns = {e.campaign_id for e in human if e.type in FAILURE_EVENTS}
    submitted_campaigns = {e.campaign_id for e in human if e.type == EventType.submitted}
    reported_campaigns = {e.campaign_id for e in human if e.type == EventType.reported}

    fail_rate = len(failed_campaigns) / n
    submit_rate = len(submitted_campaigns) / n
    report_rate = len(reported_campaigns) / n

    base = 100.0 * (0.6 * fail_rate + 0.4 * submit_rate)
    base -= 25.0 * report_rate  # bom comportamento abate risco

    # Recência: falha nos últimos 30 dias adiciona um prêmio de risco.
    now = datetime.now(timezone.utc)
    recent_fail = any(
        e.type in FAILURE_EVENTS and (now - _aware(e.created_at)).days <= 30 for e in human
    )
    if recent_fail:
        base += 10.0

    score = base * max(0.5, target.role_weight)
    return max(0, min(100, round(score)))


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
