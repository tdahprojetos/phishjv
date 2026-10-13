"""Envio de e-mails das campanhas (SMTP), com modo dry-run."""
from __future__ import annotations

import smtplib
from email.message import EmailMessage

from .config import settings
from .security import make_token


def render(template_html: str, *, first_name: str, link: str, tracker: str) -> str:
    """Substitui os placeholders suportados no corpo do e-mail."""
    return (
        template_html.replace("{{first_name}}", first_name)
        .replace("{{link}}", link)
        .replace("{{tracker}}", tracker)
    )


def build_links(campaign_id: int, target_id: int) -> tuple[str, str]:
    """Devolve (link_de_clique, tag_img_do_pixel) já assinados, prontos para o template."""
    base = settings.base_url.rstrip("/")
    click = make_token(campaign_id, target_id, "click")
    open_ = make_token(campaign_id, target_id, "open")
    link = f"{base}/t/c/{click}"
    tracker = f'<img src="{base}/t/o/{open_}" width="1" height="1" alt="" style="display:none">'
    return link, tracker


def send_email(to_addr: str, subject: str, html: str) -> bool:
    """Envia um e-mail. Em dry-run (SMTP_HOST vazio) apenas registra e retorna True."""
    if settings.dry_run:
        print(f"[dry-run] -> {to_addr} | {subject!r} ({len(html)} bytes HTML, não enviado)")
        return True

    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content("Seu cliente de e-mail não suporta HTML.")
    msg.add_alternative(html, subtype="html")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)
    return True
