"""Testes do núcleo do Phishjv: tokens, métricas, treinamento e inscrição automática."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from phishjv.db import Base
from phishjv.metrics import campaign_stats, target_risk_score
from phishjv.models import (
    Campaign,
    Course,
    Event,
    EventType,
    Question,
    Target,
    Template,
)
from phishjv.security import make_token, read_token
from phishjv.training import enroll_on_failure, grade_quiz, record_completion


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    s = Session()
    try:
        yield s
    finally:
        s.close()


# --------------------------------------------------------------------------- #
# Tokens de tracking                                                           #
# --------------------------------------------------------------------------- #
def test_token_roundtrip():
    tok = make_token(7, 42, "click")
    data = read_token(tok)
    assert data == {"campaign_id": 7, "target_id": 42, "kind": "click"}


def test_token_rejects_tampering():
    tok = make_token(1, 1, "click")
    payload, sig = tok.split(".", 1)
    forged = payload + "x." + sig
    assert read_token(forged) is None
    assert read_token("lixo.invalido") is None


# --------------------------------------------------------------------------- #
# Métricas                                                                     #
# --------------------------------------------------------------------------- #
def _setup_campaign(db) -> Campaign:
    tpl = Template(name="t", subject="s", html="<p>{{link}}</p>")
    db.add(tpl)
    db.flush()
    camp = Campaign(name="c", template_id=tpl.id)
    db.add(camp)
    db.flush()
    return camp


def test_ppp_excludes_bot_clicks(db):
    camp = _setup_campaign(db)
    # 3 alvos, todos receberam; alvo 1 clicou (humano), alvo 2 clique de bot, alvo 3 só abriu.
    targets = [Target(email=f"u{i}@x.com") for i in range(3)]
    db.add_all(targets)
    db.flush()
    for t in targets:
        db.add(Event(campaign_id=camp.id, target_id=t.id, type=EventType.sent))
    db.add(Event(campaign_id=camp.id, target_id=targets[0].id, type=EventType.clicked))
    db.add(Event(campaign_id=camp.id, target_id=targets[1].id, type=EventType.clicked, is_bot=True))
    db.add(Event(campaign_id=camp.id, target_id=targets[2].id, type=EventType.opened))
    db.commit()

    stats = campaign_stats(db, camp.id)
    assert stats.total == 3
    assert stats.clicked == 1          # o clique de bot não conta
    assert stats.failed == 1
    assert stats.ppp == pytest.approx(33.3, abs=0.1)


def test_risk_score_reflects_behaviour(db):
    camp = _setup_campaign(db)
    clicker = Target(email="click@x.com", role_weight=1.0)
    reporter = Target(email="report@x.com", role_weight=1.0)
    db.add_all([clicker, reporter])
    db.flush()
    db.add(Event(campaign_id=camp.id, target_id=clicker.id, type=EventType.submitted))
    db.add(Event(campaign_id=camp.id, target_id=reporter.id, type=EventType.reported))
    db.commit()

    assert target_risk_score(db, clicker) > target_risk_score(db, reporter)
    assert target_risk_score(db, reporter) == 0


# --------------------------------------------------------------------------- #
# Treinamento                                                                  #
# --------------------------------------------------------------------------- #
def _course_with_quiz(db) -> Course:
    course = Course(slug="c1", title="Curso", pass_score=70)
    db.add(course)
    db.flush()
    db.add(Question(course_id=course.id, order=0, prompt="q1",
                    options=["a", "b"], answer_index=1))
    db.add(Question(course_id=course.id, order=1, prompt="q2",
                    options=["a", "b"], answer_index=0))
    db.commit()
    db.refresh(course)
    return course


def test_grade_quiz_pass_and_fail(db):
    course = _course_with_quiz(db)
    q_ids = [q.id for q in course.questions]

    perfect = grade_quiz(db, course, {q_ids[0]: 1, q_ids[1]: 0})
    assert perfect.score == 100 and perfect.passed

    half = grade_quiz(db, course, {q_ids[0]: 1, q_ids[1]: 1})
    assert half.score == 50 and not half.passed


def test_enroll_on_failure_and_completion(db):
    course = _course_with_quiz(db)
    tpl = Template(name="t", subject="s", html="x")
    db.add(tpl)
    db.flush()
    camp = Campaign(name="c", template_id=tpl.id, training_course_id=course.id)
    tgt = Target(email="late@x.com")
    db.add_all([camp, tgt])
    db.commit()

    enr = enroll_on_failure(db, camp, tgt)
    assert enr is not None
    # Idempotente: não duplica a inscrição.
    assert enroll_on_failure(db, camp, tgt).id == enr.id

    q_ids = [q.id for q in course.questions]
    result = grade_quiz(db, course, {q_ids[0]: 1, q_ids[1]: 0})
    record_completion(db, course, tgt, result)
    assert enr.passed is True
    assert enr.score == 100
