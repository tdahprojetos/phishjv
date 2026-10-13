"""Serviços de treinamento: inscrição automática por falha e correção de quiz."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Campaign, Course, Enrollment, EnrollmentStatus, Target


def enroll_on_failure(session: Session, campaign: Campaign, target: Target) -> Enrollment | None:
    """Inscreve o alvo na trilha de reforço da campanha, se ainda não estiver inscrito."""
    if not campaign.training_course_id:
        return None
    existing = session.scalar(
        select(Enrollment).where(
            Enrollment.target_id == target.id,
            Enrollment.course_id == campaign.training_course_id,
        )
    )
    if existing:
        return existing
    enr = Enrollment(
        target_id=target.id,
        course_id=campaign.training_course_id,
        reason=f"Falha na campanha: {campaign.name}",
    )
    session.add(enr)
    session.commit()
    return enr


@dataclass
class QuizResult:
    score: int
    passed: bool
    total: int
    correct: int
    feedback: list[dict]  # [{question_id, chosen, correct_index, ok, explanation}]


def grade_quiz(session: Session, course: Course, answers: dict[int, int]) -> QuizResult:
    """Corrige o quiz. `answers` mapeia question_id -> índice escolhido."""
    questions = course.questions
    total = len(questions)
    correct = 0
    feedback: list[dict] = []
    for q in questions:
        chosen = answers.get(q.id)
        ok = chosen is not None and int(chosen) == q.answer_index
        if ok:
            correct += 1
        feedback.append(
            {
                "question_id": q.id,
                "chosen": chosen,
                "correct_index": q.answer_index,
                "ok": ok,
                "explanation": q.explanation,
            }
        )
    score = round(100 * correct / total) if total else 0
    return QuizResult(
        score=score,
        passed=score >= course.pass_score,
        total=total,
        correct=correct,
        feedback=feedback,
    )


def record_completion(
    session: Session, course: Course, target: Target, result: QuizResult
) -> Enrollment:
    """Registra o resultado do quiz na inscrição (cria uma se não existir)."""
    enr = session.scalar(
        select(Enrollment).where(
            Enrollment.target_id == target.id, Enrollment.course_id == course.id
        )
    )
    if not enr:
        enr = Enrollment(target_id=target.id, course_id=course.id, reason="Acesso direto")
        session.add(enr)

    enr.score = result.score
    enr.passed = result.passed
    if result.passed:
        enr.status = EnrollmentStatus.completed
        enr.completed_at = datetime.now(timezone.utc)
    else:
        enr.status = EnrollmentStatus.in_progress
    session.commit()
    return enr
