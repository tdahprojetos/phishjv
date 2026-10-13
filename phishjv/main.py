"""Phishjv — aplicação FastAPI: API de gestão, endpoints de tracking e painel."""
from __future__ import annotations

import base64
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import __version__
from .config import settings
from .db import get_session, init_db
from .mailer import build_links, render, send_email
from .metrics import campaign_stats, org_ppp, target_risk_score
from .models import (
    FAILURE_EVENTS,
    Campaign,
    CampaignStatus,
    Course,
    Enrollment,
    Event,
    EventType,
    Group,
    Report,
    ReportClassification,
    Target,
    Template,
)
from .security import read_token
from .training import enroll_on_failure, grade_quiz, record_completion
from .training_content import load_courses

app = FastAPI(title="Phishjv", version=__version__)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# GIF transparente de 1x1 para o pixel de abertura.
_PIXEL = base64.b64decode(
    "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)

# Assinaturas comuns de scanners/proxies que abrem links automaticamente (false positive).
_BOT_HINTS = (
    "bot", "spider", "crawl", "preview", "scan", "proofpoint", "barracuda",
    "mimecast", "microsoft", "safelinks", "google", "slackbot", "python-requests",
    "curl", "wget", "headless",
)


def _looks_like_bot(user_agent: str) -> bool:
    ua = (user_agent or "").lower()
    return any(h in ua for h in _BOT_HINTS)


def _now_utc():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    # Garante que as trilhas de treinamento originais existam.
    from .db import SessionLocal

    s = SessionLocal()
    try:
        load_courses(s)
    finally:
        s.close()


# --------------------------------------------------------------------------- #
# Schemas de entrada da API                                                    #
# --------------------------------------------------------------------------- #
class TargetIn(BaseModel):
    email: EmailStr
    first_name: str = ""
    last_name: str = ""
    position: str = ""
    role_weight: float = 1.0
    group_id: int | None = None


class TemplateIn(BaseModel):
    name: str
    subject: str
    html: str
    landing_html: str = ""


class CampaignIn(BaseModel):
    name: str
    template_id: int
    group_id: int | None = None
    landing_url: str = ""


# --------------------------------------------------------------------------- #
# API de gestão                                                                #
# --------------------------------------------------------------------------- #
@app.post("/api/targets")
def create_target(data: TargetIn, s: Session = Depends(get_session)):
    t = Target(**data.model_dump())
    s.add(t)
    s.commit()
    return {"id": t.id}


@app.post("/api/templates")
def create_template(data: TemplateIn, s: Session = Depends(get_session)):
    t = Template(**data.model_dump())
    s.add(t)
    s.commit()
    return {"id": t.id}


@app.post("/api/campaigns")
def create_campaign(data: CampaignIn, s: Session = Depends(get_session)):
    if not s.get(Template, data.template_id):
        raise HTTPException(404, "template não encontrado")
    c = Campaign(**data.model_dump())
    s.add(c)
    s.commit()
    return {"id": c.id}


@app.post("/api/campaigns/{campaign_id}/launch")
def launch_campaign(campaign_id: int, s: Session = Depends(get_session)):
    """Envia a campanha para todos os alvos do grupo (ou todos, se sem grupo)."""
    camp = s.get(Campaign, campaign_id)
    if not camp:
        raise HTTPException(404, "campanha não encontrada")

    q = select(Target)
    if camp.group_id:
        q = q.where(Target.group_id == camp.group_id)
    targets = list(s.scalars(q))
    if not targets:
        raise HTTPException(400, "nenhum alvo para esta campanha")

    sent = 0
    for tgt in targets:
        link, tracker = build_links(camp.id, tgt.id)
        html = render(camp.template.html, first_name=tgt.first_name, link=link, tracker=tracker)
        if send_email(tgt.email, camp.template.subject, html):
            s.add(Event(campaign_id=camp.id, target_id=tgt.id, type=EventType.sent))
            sent += 1

    from datetime import datetime, timezone

    camp.status = CampaignStatus.running
    camp.launched_at = datetime.now(timezone.utc)
    s.commit()
    return {"sent": sent, "dry_run": settings.dry_run}


@app.get("/api/campaigns/{campaign_id}/stats")
def get_stats(campaign_id: int, s: Session = Depends(get_session)):
    if not s.get(Campaign, campaign_id):
        raise HTTPException(404, "campanha não encontrada")
    return campaign_stats(s, campaign_id).as_dict()


# --------------------------------------------------------------------------- #
# Endpoints de tracking (acessados pelos alvos)                                #
# --------------------------------------------------------------------------- #
def _record(s: Session, token: str, etype: EventType, request: Request) -> dict | None:
    data = read_token(token)
    if not data:
        return None
    ua = request.headers.get("user-agent", "")
    ip = request.client.host if request.client else ""
    is_bot = _looks_like_bot(ua)
    s.add(
        Event(
            campaign_id=data["campaign_id"],
            target_id=data["target_id"],
            type=etype,
            ip=ip,
            user_agent=ua[:512],
            is_bot=is_bot,
        )
    )
    s.commit()

    # Inscrição automática na trilha de reforço quando um humano falha.
    if etype in FAILURE_EVENTS and not is_bot:
        camp = s.get(Campaign, data["campaign_id"])
        tgt = s.get(Target, data["target_id"])
        if camp and tgt:
            enroll_on_failure(s, camp, tgt)
    return data


@app.get("/t/o/{token}")
def track_open(token: str, request: Request, s: Session = Depends(get_session)):
    _record(s, token, EventType.opened, request)
    return Response(content=_PIXEL, media_type="image/gif")


@app.get("/t/c/{token}")
def track_click(token: str, request: Request, s: Session = Depends(get_session)):
    data = _record(s, token, EventType.clicked, request)
    if not data:
        raise HTTPException(404, "link inválido")
    camp = s.get(Campaign, data["campaign_id"])
    if camp and camp.landing_url:
        return RedirectResponse(camp.landing_url, status_code=302)
    # Landing própria do template, se houver.
    base = settings.base_url.rstrip("/")
    return RedirectResponse(f"{base}/l/{token}", status_code=302)


@app.get("/l/{token}", response_class=HTMLResponse)
def landing(token: str, s: Session = Depends(get_session)):
    data = read_token(token)
    if not data:
        raise HTTPException(404, "página inválida")
    camp = s.get(Campaign, data["campaign_id"])
    base = settings.base_url.rstrip("/")
    action = f"{base}/l/{token}/submit"
    if camp and camp.template.landing_html:
        return HTMLResponse(camp.template.landing_html.replace("{{action}}", action))
    return HTMLResponse(
        "<h2>Treinamento Phishjv</h2>"
        "<p>Este foi um e-mail de phishing <b>simulado</b> de um exercício autorizado.</p>"
        "<p>Em um ataque real, seus dados estariam comprometidos. Reporte e-mails suspeitos.</p>"
    )


@app.post("/l/{token}/submit", response_class=HTMLResponse)
def landing_submit(token: str, request: Request, s: Session = Depends(get_session)):
    # NÃO armazenamos credenciais submetidas — registramos apenas o evento.
    data = _record(s, token, EventType.submitted, request)
    if not data:
        raise HTTPException(404, "página inválida")
    return HTMLResponse(
        "<h2>Treinamento Phishjv</h2>"
        "<p>Você acabou de submeter dados em uma página de phishing <b>simulada</b>.</p>"
        "<p>Nenhum dado foi armazenado. Da próxima vez, verifique o remetente e a URL.</p>"
    )


@app.get("/t/r/{token}")
def track_report(token: str, request: Request, s: Session = Depends(get_session)):
    """Alvo reportou o e-mail da SIMULAÇÃO como phishing (via Phish Alert Button)."""
    data = _record(s, token, EventType.reported, request)
    if not data:
        raise HTTPException(404, "token inválido")
    tgt = s.get(Target, data["target_id"])
    s.add(
        Report(
            campaign_id=data["campaign_id"],
            target_id=data["target_id"],
            reporter_email=tgt.email if tgt else "",
            subject="(simulação Phishjv)",
            classification=ReportClassification.simulation,
            classified_at=_now_utc(),
        )
    )
    s.commit()
    return {"ok": True, "message": "Reporte registrado. Obrigado!"}


class ReportIn(BaseModel):
    reporter_email: str = ""
    subject: str = ""
    sender: str = ""
    snippet: str = ""


@app.post("/report")
def submit_report(data: ReportIn, s: Session = Depends(get_session)):
    """Reporte de um e-mail REAL suspeito (do Phish Alert Button). Entra na fila de triagem."""
    r = Report(
        reporter_email=data.reporter_email,
        subject=data.subject[:500],
        sender=data.sender[:320],
        snippet=data.snippet[:4000],
        classification=ReportClassification.unclassified,
    )
    s.add(r)
    s.commit()
    return {"ok": True, "report_id": r.id}


# --------------------------------------------------------------------------- #
# Treinamento                                                                  #
# --------------------------------------------------------------------------- #
@app.get("/training", response_class=HTMLResponse)
def training_list(request: Request, s: Session = Depends(get_session)):
    courses = list(s.scalars(select(Course)))
    enrollments = list(s.scalars(select(Enrollment)))
    completed = sum(1 for e in enrollments if e.passed)
    return templates.TemplateResponse(
        "training_list.html",
        {
            "request": request,
            "version": __version__,
            "courses": courses,
            "enrollments": enrollments,
            "total_enr": len(enrollments),
            "completed": completed,
        },
    )


@app.get("/training/course/{course_id}", response_class=HTMLResponse)
def training_course(
    course_id: int, request: Request, target_id: int | None = None,
    s: Session = Depends(get_session),
):
    course = s.get(Course, course_id)
    if not course:
        raise HTTPException(404, "trilha não encontrada")
    return templates.TemplateResponse(
        "course.html",
        {
            "request": request,
            "version": __version__,
            "course": course,
            "target_id": target_id or "",
            "result": None,
        },
    )


@app.post("/training/course/{course_id}/submit", response_class=HTMLResponse)
async def training_submit(
    course_id: int, request: Request, s: Session = Depends(get_session)
):
    course = s.get(Course, course_id)
    if not course:
        raise HTTPException(404, "trilha não encontrada")

    form = await request.form()
    target_id = form.get("target_id")
    answers: dict[int, int] = {}
    for q in course.questions:
        raw = form.get(f"q{q.id}")
        if raw is not None and str(raw).isdigit():
            answers[q.id] = int(raw)

    result = grade_quiz(s, course, answers)
    if target_id and str(target_id).isdigit():
        tgt = s.get(Target, int(target_id))
        if tgt:
            record_completion(s, course, tgt, result)

    return templates.TemplateResponse(
        "course.html",
        {
            "request": request,
            "version": __version__,
            "course": course,
            "target_id": target_id or "",
            "result": result,
        },
    )


# --------------------------------------------------------------------------- #
# Triagem (fila estilo PhishER)                                                #
# --------------------------------------------------------------------------- #
@app.get("/triage", response_class=HTMLResponse)
def triage(request: Request, s: Session = Depends(get_session)):
    reports = list(s.scalars(select(Report).order_by(Report.created_at.desc())))
    pending = sum(1 for r in reports if r.classification == ReportClassification.unclassified)
    threats = sum(1 for r in reports if r.classification == ReportClassification.threat)
    return templates.TemplateResponse(
        "triage.html",
        {
            "request": request,
            "version": __version__,
            "reports": reports,
            "pending": pending,
            "threats": threats,
            "classes": [c.value for c in ReportClassification],
        },
    )


@app.post("/triage/{report_id}/classify")
async def classify_report(
    report_id: int, request: Request, s: Session = Depends(get_session)
):
    r = s.get(Report, report_id)
    if not r:
        raise HTTPException(404, "reporte não encontrado")
    form = await request.form()
    value = str(form.get("classification", ""))
    try:
        r.classification = ReportClassification(value)
    except ValueError:
        raise HTTPException(400, "classificação inválida")
    r.classified_at = _now_utc()
    s.commit()
    return RedirectResponse("/triage", status_code=303)


# --------------------------------------------------------------------------- #
# Painel                                                                       #
# --------------------------------------------------------------------------- #
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, s: Session = Depends(get_session)):
    campaigns = list(s.scalars(select(Campaign)))
    rows = [{"c": c, "stats": campaign_stats(s, c.id)} for c in campaigns]
    targets = list(s.scalars(select(Target)))
    risk = sorted(
        ({"t": t, "score": target_risk_score(s, t)} for t in targets),
        key=lambda r: r["score"],
        reverse=True,
    )[:10]
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "version": __version__,
            "campaigns": rows,
            "org_ppp": org_ppp(s),
            "n_targets": len(targets),
            "risk": risk,
            "dry_run": settings.dry_run,
        },
    )
