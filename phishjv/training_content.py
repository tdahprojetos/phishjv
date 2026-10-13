"""Conteúdo de treinamento ORIGINAL do Phishjv (pt-BR).

Escrito do zero para o Phishjv — não é derivado de material de terceiros.
Cada trilha tem lições curtas (HTML) e um quiz com explicação por questão.
A função load_courses() insere/atualiza as trilhas no banco de forma idempotente.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Course, Lesson, Question

COURSES: list[dict] = [
    {
        "slug": "phishing-email",
        "title": "Reconhecendo phishing por e-mail",
        "topic": "phishing",
        "summary": "Como identificar e-mails de phishing antes de clicar.",
        "pass_score": 70,
        "lessons": [
            {
                "title": "O que o atacante quer de você",
                "body_html": (
                    "<p>Phishing é uma mensagem que se passa por uma fonte confiável para te levar"
                    " a uma ação: clicar num link, abrir um anexo ou entregar credenciais.</p>"
                    "<p>O golpe explora <b>emoção e pressa</b> — medo de perder a conta, urgência de"
                    " um pagamento, curiosidade sobre um anexo. Quando um e-mail te apressa, desconfie.</p>"
                ),
            },
            {
                "title": "Os 5 sinais clássicos",
                "body_html": (
                    "<ol>"
                    "<li><b>Remetente estranho:</b> o nome exibido não bate com o endereço real"
                    " (passe o mouse sobre o nome).</li>"
                    "<li><b>Urgência/ameaça:</b> \"sua conta será bloqueada em 24h\".</li>"
                    "<li><b>Link disfarçado:</b> o texto diz um site, mas o destino é outro"
                    " (passe o mouse sobre o link sem clicar).</li>"
                    "<li><b>Pedido incomum:</b> trocar senha, pagar boleto, confirmar dados.</li>"
                    "<li><b>Erros e saudação genérica:</b> \"Prezado cliente\", portugues torto.</li>"
                    "</ol>"
                ),
            },
            {
                "title": "O que fazer",
                "body_html": (
                    "<p>Na dúvida, <b>não clique</b>. Acesse o serviço digitando o endereço"
                    " oficial no navegador, nunca pelo link do e-mail.</p>"
                    "<p>Reporte o e-mail suspeito usando o botão de reporte (Phish Alert)."
                    " Reportar é a atitude certa — e, numa simulação, conta como acerto.</p>"
                ),
            },
        ],
        "questions": [
            {
                "prompt": "Qual é a forma mais segura de acessar o site do seu banco após receber"
                " um e-mail pedindo para \"revalidar seus dados\"?",
                "options": [
                    "Clicar no link do e-mail, pois veio do banco",
                    "Digitar o endereço oficial do banco no navegador",
                    "Responder o e-mail pedindo confirmação",
                    "Encaminhar para um colega decidir",
                ],
                "answer_index": 1,
                "explanation": "Sempre acesse digitando o endereço oficial. O link do e-mail pode"
                " levar a um site falso idêntico ao verdadeiro.",
            },
            {
                "prompt": "Um e-mail diz que sua conta será bloqueada em 2 horas se você não agir."
                " Isso é, acima de tudo, um sinal de:",
                "options": [
                    "Bom atendimento",
                    "Pressão/urgência típica de golpe",
                    "Política normal de segurança",
                    "Problema no servidor",
                ],
                "answer_index": 1,
                "explanation": "Urgência artificial é uma das táticas mais comuns de phishing para"
                " te fazer agir sem pensar.",
            },
            {
                "prompt": "Como verificar para onde um link realmente aponta, sem clicar?",
                "options": [
                    "Clicando e voltando rápido",
                    "Passando o mouse sobre o link e lendo o destino",
                    "Não há como saber",
                    "Olhando a cor do link",
                ],
                "answer_index": 1,
                "explanation": "Passar o mouse (hover) mostra a URL real de destino no canto do"
                " cliente de e-mail ou navegador.",
            },
        ],
    },
    {
        "slug": "bec-spear-phishing",
        "title": "Spear phishing e fraude do CEO (BEC)",
        "topic": "bec",
        "summary": "Ataques direcionados que imitam chefes e fornecedores para desviar dinheiro.",
        "pass_score": 70,
        "lessons": [
            {
                "title": "Por que o direcionado é mais perigoso",
                "body_html": (
                    "<p>No <b>spear phishing</b>, o atacante pesquisa você: nome do chefe, projetos,"
                    " fornecedores. A mensagem fica convincente porque usa dados reais.</p>"
                    "<p>O <b>BEC (Business Email Compromise)</b> mira dinheiro: um \"diretor\" pede"
                    " uma transferência urgente, ou um \"fornecedor\" avisa que mudou a conta bancária.</p>"
                ),
            },
            {
                "title": "Regra de ouro: confirme por outro canal",
                "body_html": (
                    "<p>Todo pedido de <b>pagamento, troca de conta bancária ou dados sensíveis</b>"
                    " deve ser confirmado por um segundo canal: ligue para o número que você já"
                    " conhece, fale pessoalmente. Nunca use o contato que veio na própria mensagem.</p>"
                    "<p>Desconfie de \"estou em reunião, não posso falar, só resolve por e-mail\" —"
                    " é a desculpa clássica para impedir a verificação.</p>"
                ),
            },
        ],
        "questions": [
            {
                "prompt": "Um e-mail do \"diretor financeiro\" pede uma transferência urgente e sigilosa."
                " Qual a atitude correta?",
                "options": [
                    "Fazer a transferência para não atrasar",
                    "Confirmar por um canal já conhecido (ligar para o ramal real)",
                    "Responder o e-mail pedindo mais detalhes",
                    "Encaminhar para o estagiário resolver",
                ],
                "answer_index": 1,
                "explanation": "Pedidos de pagamento/urgência/sigilo são a assinatura do BEC."
                " Confirme sempre por um canal independente.",
            },
            {
                "prompt": "Um fornecedor avisa por e-mail que mudou a conta bancária para o próximo"
                " pagamento. O que fazer primeiro?",
                "options": [
                    "Atualizar a conta no sistema e pagar",
                    "Ligar para o contato oficial do fornecedor para validar a mudança",
                    "Confiar, pois o e-mail tem a logo da empresa",
                    "Pagar metade para testar",
                ],
                "answer_index": 1,
                "explanation": "Troca de dados bancários é o alvo nº 1 do BEC. Valide por telefone"
                " num número que você já tinha, não no que veio no e-mail.",
            },
        ],
    },
    {
        "slug": "senhas-mfa",
        "title": "Senhas fortes e MFA",
        "topic": "credenciais",
        "summary": "Como proteger o acesso mesmo quando a senha vaza.",
        "pass_score": 70,
        "lessons": [
            {
                "title": "Senha boa é longa, não complicada",
                "body_html": (
                    "<p>Comprimento vence complexidade. Uma frase-senha como"
                    " <code>cafe-azul-corre-manha</code> é mais forte e mais fácil de lembrar que"
                    " <code>C@f3!</code>.</p>"
                    "<p>Nunca reutilize senhas. Se um site vaza, o atacante testa a mesma senha em"
                    " todos os outros (<i>credential stuffing</i>). Use um gerenciador de senhas.</p>"
                ),
            },
            {
                "title": "MFA: sua rede de segurança",
                "body_html": (
                    "<p>O <b>segundo fator (MFA)</b> faz a senha sozinha não bastar. Prefira app"
                    " autenticador ou chave física a SMS.</p>"
                    "<p>Cuidado com <b>fadiga de MFA</b>: se chegar um monte de pedidos de aprovação"
                    " que você não iniciou, <b>negue</b> — alguém está tentando entrar com sua senha.</p>"
                ),
            },
        ],
        "questions": [
            {
                "prompt": "Qual senha é, na prática, mais segura?",
                "options": [
                    "P@ss1!",
                    "cavalo-bateria-grampo-correto",
                    "123456",
                    "seu nome + ano",
                ],
                "answer_index": 1,
                "explanation": "Frases-senha longas têm muito mais entropia e resistem melhor a"
                " ataques de força bruta e dicionário.",
            },
            {
                "prompt": "Seu celular recebe vários pedidos de aprovação de login que você não fez."
                " O que isso indica e o que fazer?",
                "options": [
                    "É normal; aprove para parar os avisos",
                    "Alguém tem sua senha; negue e troque a senha",
                    "Bug do app; ignore",
                    "Aprove uma vez só",
                ],
                "answer_index": 1,
                "explanation": "É ataque de fadiga de MFA. Negar e trocar a senha imediatamente"
                " impede o acesso indevido.",
            },
        ],
    },
    {
        "slug": "engenharia-social",
        "title": "Engenharia social: vishing e smishing",
        "topic": "engenharia-social",
        "summary": "Golpes por telefone (vishing) e SMS/WhatsApp (smishing).",
        "pass_score": 70,
        "lessons": [
            {
                "title": "O golpe que vem pela voz e pelo SMS",
                "body_html": (
                    "<p><b>Vishing</b> é phishing por telefone: alguém se passa por banco, suporte"
                    " de TI ou órgão público e pede dados ou acesso remoto.</p>"
                    "<p><b>Smishing</b> é por SMS/WhatsApp: \"sua encomenda está retida, pague a taxa\","
                    " com um link curto. O link curto esconde o destino real.</p>"
                ),
            },
            {
                "title": "Ninguém legítimo pede isso",
                "body_html": (
                    "<p>Banco, TI e governo <b>nunca</b> pedem sua senha completa, o código do SMS"
                    " (OTP) ou acesso remoto ao seu computador por ligação não solicitada.</p>"
                    "<p>Desligou? Ligue de volta no número oficial do cartão/site — não no número"
                    " que te ligou.</p>"
                ),
            },
        ],
        "questions": [
            {
                "prompt": "Uma ligação do \"seu banco\" pede o código de 6 dígitos que acabou de"
                " chegar no seu SMS. Você deve:",
                "options": [
                    "Informar, pois é o banco",
                    "Nunca informar o código; o banco não pede isso",
                    "Informar só os 3 primeiros dígitos",
                    "Perguntar o nome do atendente e informar",
                ],
                "answer_index": 1,
                "explanation": "O código OTP é justamente o que o golpista precisa para entrar."
                " Nenhum banco legítimo pede esse código por telefone.",
            },
            {
                "prompt": "Um SMS diz que sua encomenda está retida e pede o pagamento de uma taxa"
                " por um link encurtado. A melhor ação é:",
                "options": [
                    "Pagar a taxa para liberar",
                    "Não clicar; verificar direto no site oficial da transportadora",
                    "Responder o SMS pedindo detalhes",
                    "Clicar só para ver o site",
                ],
                "answer_index": 1,
                "explanation": "É smishing. Links encurtados escondem o destino. Verifique o"
                " rastreamento no site oficial, digitando o endereço você mesmo.",
            },
        ],
    },
    {
        "slug": "protecao-dados-lgpd",
        "title": "Proteção de dados e LGPD no dia a dia",
        "topic": "dados",
        "summary": "Cuidados práticos para não vazar dados pessoais e da empresa.",
        "pass_score": 70,
        "lessons": [
            {
                "title": "Dado pessoal é responsabilidade de todos",
                "body_html": (
                    "<p>A LGPD trata de dados que identificam uma pessoa (nome, CPF, e-mail, saúde)."
                    " Vazar esses dados gera dano às pessoas e multa à empresa.</p>"
                    "<p>Princípio prático: colete e compartilhe só o <b>mínimo necessário</b>, com"
                    " quem tem necessidade real de saber.</p>"
                ),
            },
            {
                "title": "Erros comuns que vazam dados",
                "body_html": (
                    "<ul>"
                    "<li>Enviar planilha com dados pessoais para o e-mail errado (confira o destinatário!).</li>"
                    "<li>Usar <b>Cc</b> em vez de <b>Cco</b> em disparo para muitas pessoas externas.</li>"
                    "<li>Deixar documentos sensíveis na impressora ou na mesa.</li>"
                    "<li>Subir dados em ferramentas pessoais/não aprovadas.</li>"
                    "</ul>"
                    "<p>Suspeita de vazamento? Comunique o time de segurança <b>imediatamente</b> —"
                    " o tempo de resposta reduz o impacto.</p>"
                ),
            },
        ],
        "questions": [
            {
                "prompt": "Você vai enviar um comunicado por e-mail para 200 clientes externos."
                " Para não expor os endereços uns aos outros, use:",
                "options": [
                    "Campo Para (To) com todos",
                    "Campo Cc com todos",
                    "Campo Cco (Bcc)",
                    "Tanto faz",
                ],
                "answer_index": 2,
                "explanation": "Cco (Bcc) oculta os destinatários entre si. Usar Para/Cc expõe"
                " e-mails de todos — um vazamento de dados pessoais.",
            },
            {
                "prompt": "Você percebeu que enviou uma planilha com CPFs para o destinatário errado."
                " O que fazer primeiro?",
                "options": [
                    "Nada, foi sem querer",
                    "Avisar o time de segurança/privacidade imediatamente",
                    "Apagar da sua caixa de enviados e seguir",
                    "Pedir para a pessoa deletar e esquecer",
                ],
                "answer_index": 1,
                "explanation": "É um incidente de dados. Comunicar rápido permite conter o impacto"
                " e cumprir as obrigações da LGPD.",
            },
        ],
    },
]


def load_courses(session: Session) -> int:
    """Insere as trilhas que ainda não existem (idempotente). Retorna quantas criou."""
    created = 0
    for data in COURSES:
        exists = session.scalar(select(Course).where(Course.slug == data["slug"]))
        if exists:
            continue
        course = Course(
            slug=data["slug"],
            title=data["title"],
            topic=data["topic"],
            summary=data["summary"],
            pass_score=data["pass_score"],
        )
        session.add(course)
        session.flush()
        for i, les in enumerate(data["lessons"]):
            session.add(
                Lesson(
                    course_id=course.id,
                    order=i,
                    title=les["title"],
                    body_html=les["body_html"],
                )
            )
        for i, q in enumerate(data["questions"]):
            session.add(
                Question(
                    course_id=course.id,
                    order=i,
                    prompt=q["prompt"],
                    options=q["options"],
                    answer_index=q["answer_index"],
                    explanation=q["explanation"],
                )
            )
        created += 1
    session.commit()
    return created
