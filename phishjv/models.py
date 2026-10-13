"""Modelos de dados do Phishjv."""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CampaignStatus(str, enum.Enum):
    draft = "draft"
    scheduled = "scheduled"
    running = "running"
    completed = "completed"


class ReportClassification(str, enum.Enum):
    unclassified = "unclassified"
    clean = "clean"          # e-mail legítimo reportado por engano
    spam = "spam"            # spam/marketing, sem ameaça
    threat = "threat"        # phishing/malware real
    simulation = "simulation"  # simulação do próprio Phishjv


class EnrollmentStatus(str, enum.Enum):
    assigned = "assigned"        # inscrito (ex.: por falhar numa campanha)
    in_progress = "in_progress"
    completed = "completed"


class EventType(str, enum.Enum):
    """Eventos de um alvo numa campanha, em ordem de gravidade crescente — menos 'reported'."""

    sent = "sent"          # e-mail enviado
    delivered = "delivered"
    opened = "opened"      # abriu o e-mail (pixel)
    clicked = "clicked"    # clicou no link
    submitted = "submitted"  # submeteu dados na landing page
    reported = "reported"  # reportou como phishing (ACERTO do usuário)


# Eventos que caracterizam "falha" do alvo para fins de PPP.
FAILURE_EVENTS = {EventType.clicked, EventType.submitted}


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    targets: Mapped[list["Target"]] = relationship(back_populates="group")


class Target(Base):
    __tablename__ = "targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    first_name: Mapped[str] = mapped_column(String(120), default="")
    last_name: Mapped[str] = mapped_column(String(120), default="")
    position: Mapped[str] = mapped_column(String(160), default="")
    # Peso do cargo no risco (1.0 = padrão; cargos sensíveis > 1.0).
    role_weight: Mapped[float] = mapped_column(default=1.0)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    group: Mapped[Group | None] = relationship(back_populates="targets")
    events: Mapped[list["Event"]] = relationship(back_populates="target")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    subject: Mapped[str] = mapped_column(String(300))
    # Corpo HTML do e-mail. Suporta placeholders {{first_name}}, {{link}}, {{tracker}}.
    html: Mapped[str] = mapped_column(Text)
    # HTML da landing page (opcional). Placeholder {{action}} = endpoint de submissão.
    landing_html: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus), default=CampaignStatus.draft
    )
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id"))
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id"), nullable=True)
    # Trilha de reforço: quem falhar nesta campanha é inscrito automaticamente nela.
    training_course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.id"), nullable=True
    )
    # URL para onde o clique redireciona (landing própria ou externa de treinamento).
    landing_url: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    launched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    template: Mapped[Template] = relationship()
    events: Mapped[list["Event"]] = relationship(back_populates="campaign")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), index=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("targets.id"), index=True)
    type: Mapped[EventType] = mapped_column(Enum(EventType), index=True)
    # Metadados para separar clique real de scanner (false positive).
    ip: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(512), default="")
    # Marcado quando o evento parece vir de um scanner de link, não de um humano.
    is_bot: Mapped[bool] = mapped_column(default=False)
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_now
    )

    campaign: Mapped[Campaign] = relationship(back_populates="events")
    target: Mapped[Target] = relationship(back_populates="events")


# --------------------------------------------------------------------------- #
# Treinamento / conscientização                                                #
# --------------------------------------------------------------------------- #
class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    topic: Mapped[str] = mapped_column(String(80), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    # Nota mínima (%) para aprovar no quiz.
    pass_score: Mapped[int] = mapped_column(Integer, default=70)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    lessons: Mapped[list["Lesson"]] = relationship(
        back_populates="course", order_by="Lesson.order", cascade="all, delete-orphan"
    )
    questions: Mapped[list["Question"]] = relationship(
        back_populates="course", order_by="Question.order", cascade="all, delete-orphan"
    )


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    order: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(200))
    body_html: Mapped[str] = mapped_column(Text)

    course: Mapped[Course] = relationship(back_populates="lessons")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    order: Mapped[int] = mapped_column(Integer, default=0)
    prompt: Mapped[str] = mapped_column(Text)
    # Lista de alternativas (JSON).
    options: Mapped[list] = mapped_column(JSON, default=list)
    # Índice (0-based) da alternativa correta.
    answer_index: Mapped[int] = mapped_column(Integer, default=0)
    explanation: Mapped[str] = mapped_column(Text, default="")

    course: Mapped[Course] = relationship(back_populates="questions")


class Enrollment(Base):
    __tablename__ = "enrollments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("targets.id"), index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    status: Mapped[EnrollmentStatus] = mapped_column(
        Enum(EnrollmentStatus), default=EnrollmentStatus.assigned
    )
    # Motivo da inscrição (ex.: "falha na campanha Q4").
    reason: Mapped[str] = mapped_column(String(300), default="")
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    target: Mapped[Target] = relationship()
    course: Mapped[Course] = relationship()


class Report(Base):
    """E-mail reportado pelo usuário (via Phish Alert Button). Fila de triagem estilo PhishER."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Preenchido quando o reporte veio de uma simulação do Phishjv (via token).
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id"), nullable=True)
    target_id: Mapped[int | None] = mapped_column(ForeignKey("targets.id"), nullable=True)
    reporter_email: Mapped[str] = mapped_column(String(320), default="")
    subject: Mapped[str] = mapped_column(String(500), default="")
    sender: Mapped[str] = mapped_column(String(320), default="")
    snippet: Mapped[str] = mapped_column(Text, default="")
    classification: Mapped[ReportClassification] = mapped_column(
        Enum(ReportClassification), default=ReportClassification.unclassified, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    classified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    target: Mapped[Target | None] = relationship()
