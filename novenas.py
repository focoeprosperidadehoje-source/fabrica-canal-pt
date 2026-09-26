# -*- coding: utf-8 -*-
"""
novenas.py — Planejador do slot 06:00 (Novenas) — Canal PT

Regras (aprovadas por Leandro em 2026-09-25):
- Slot 06:00 = vídeo longo de Novena, persona mariana do canal (NUNCA outro santo).
- Novenas tradicionais de preparação de festa têm prioridade (calendário fixo).
- Fora das festas: ciclos de 9 dias de "novena de pedido", tema escolhido pelos
  comentários do canal (aba TEMAS_COMENTARIOS), com anti-repetição e fallback fixo.
- Dias que não cabem num ciclo completo antes de uma festa (e o próprio dia da
  festa) viram "avulsa" = oração da manhã normal.
- O número do dia (1..9) é SEMPRE calculado pela data, nunca pelo Gemini.

Módulo puro (sem rede) exceto escolher_tema_pedido(), que lê/grava na planilha.
"""
import datetime

CANAL = "PT"
TZ = "America/Sao_Paulo"

# Primeiro dia em que o slot 06:00 passa a existir. Antes disso: nada é gerado.
ATIVACAO_06H = datetime.date(2026, 9, 26)
# Início do primeiro ciclo de novena de pedido (dia seguinte à festa de Aparecida).
EPOCA_PEDIDOS = datetime.date(2026, 10, 13)

INVOCACAO_PADRAO = "Nossa Senhora"

# ─────────────────────────── FESTAS (novenas de preparação) ───────────────────────────
# inicio = (mes, dia) do 1º dia da novena. A festa é o dia seguinte ao 9º dia.
FESTAS = [
    {
        "id": "aparecida",
        "inicio": (10, 3),
        "nome": "Novena a Nossa Senhora Aparecida",
        "invocacao": "Nossa Senhora Aparecida",
        "festa": "Solenidade de Nossa Senhora da Conceição Aparecida, Padroeira do Brasil (12 de outubro)",
        # Subtemas oficiais do Santuário Nacional — válidos SOMENTE para 2026.
        "subtemas_oficiais": {
            2026: [
                "Com Maria, a Palavra de Deus nos faz participar da história da salvação",
                "Com Maria, discípula perfeita, cuidamos da vida de cada um e da Casa Comum",
                "Com Maria, construímos a paz e a união pela reconciliação",
                "Com Maria, Mãe discípula, somos redimidos pela Palavra encarnada",
                "Com Maria, levamos o terço e a Bíblia na mão e no coração",
                "Com Maria praticamos a piedade popular, iluminada pela Palavra de Deus",
                "Com Maria, somos igreja de irmãos, reunidos pela Palavra e pelo pão da vida",
                "Com Maria, praticamos a justiça social como compromisso de amor e de paz",
                "Com Maria, em família, a Jornada Bíblica do Santuário nos envia a evangelizar",
            ]
        },
    },
    {
        "id": "imaculada",
        "inicio": (11, 29),
        "nome": "Novena à Imaculada Conceição",
        "invocacao": "Nossa Senhora da Imaculada Conceição",
        "festa": "Solenidade da Imaculada Conceição de Maria (8 de dezembro)",
        "subtemas_oficiais": {},
    },
    {
        "id": "natal",
        "inicio": (12, 16),
        "nome": "Novena de Natal com Nossa Senhora",
        "invocacao": "Nossa Senhora",
        "festa": "Natal do Senhor (25 de dezembro) — Maria, a Mãe que espera o Menino Jesus",
        "subtemas_oficiais": {},
    },
]

# Intenção (dor) de cada dia das novenas de festa — o "chocolate" do título.
INTENCOES_FESTA = [
    "a cura das doenças e a saúde de quem você ama",
    "a restauração e a união da sua família",
    "a reconciliação, o perdão e a paz nos relacionamentos",
    "a libertação dos vícios e de tudo o que aprisiona",
    "a proteção e o futuro dos seus filhos",
    "o emprego, o sustento e as portas abertas",
    "a proteção espiritual da sua casa contra todo mal",
    "as causas impossíveis e desesperadas",
    "a gratidão pelas graças e a consagração da vida a Nossa Senhora",
]

# ─────────────────────────── NOVENAS DE PEDIDO ───────────────────────────
# chave -> (rótulo de busca para o título, descrição para o roteirista)
CATEGORIAS = {
    "saude":     ("Novena pela Cura e Saúde", "cura de doenças, saúde física, tratamentos e cirurgias"),
    "familia":   ("Novena pela Restauração da Família", "brigas, afastamento e restauração da família e do casamento"),
    "emprego":   ("Novena para Conseguir Emprego", "desemprego, trabalho, sustento e portas abertas"),
    "dividas":   ("Novena para Sair das Dívidas", "dívidas, aperto financeiro e providência divina"),
    "filhos":    ("Novena pelos Filhos", "proteção, caminho e conversão dos filhos"),
    "vicios":    ("Novena pela Libertação dos Vícios", "vícios, dependência e amarras de quem amamos"),
    "ansiedade": ("Novena para Vencer a Ansiedade", "ansiedade, angústia, tristeza profunda e paz interior"),
    "protecao":  ("Novena de Proteção Espiritual", "proteção contra o mal, inveja e ataques espirituais"),
    "causas":    ("Novena das Causas Impossíveis", "causas impossíveis, urgentes e desesperadas"),
    "luto":      ("Novena de Consolo no Luto", "luto, saudade e consolo pela perda de alguém querido"),
}
# Ordem de fallback quando não há dados de comentários suficientes.
ROTACAO_FALLBACK = ["saude", "familia", "emprego", "ansiedade", "filhos",
                    "protecao", "vicios", "dividas", "causas", "luto"]
JANELA_ANTI_REPETICAO = 3   # não repetir tema dos últimos N ciclos
MIN_COMENTARIOS_RANKING = 5  # abaixo disso, a coleta é considerada insuficiente

# Progressão espiritual dos 9 dias (pedido)
PROGRESSAO_PEDIDO = {
    1: "Dia de ENTREGA: apresentar a dor com honestidade e abrir o coração.",
    2: "Dia de ENTREGA: reconhecer o que não conseguimos carregar sozinhos.",
    3: "Dia de ENTREGA: perdoar e soltar o que pesa, para receber a graça.",
    4: "Dia de PERSEVERANÇA: manter a fé mesmo quando nada parece mudar.",
    5: "Dia de PERSEVERANÇA: a força de Maria aos pés da cruz.",
    6: "Dia de PERSEVERANÇA: combater o desânimo e a voz do medo.",
    7: "Dia de CONFIANÇA: sinais de que a graça já está a caminho.",
    8: "Dia de CONFIANÇA: agradecer antecipadamente pelo que Deus fará.",
    9: "Dia de GRATIDÃO e CONSAGRAÇÃO: entregar a vida e a causa a Nossa Senhora.",
}

# ─────────────────────────── TEXTOS FIXOS DO RITO (TTS) ───────────────────────────
# Reticências = pausas da voz. Ave Maria: pausa DEPOIS de "Jesus" (regra do projeto).
SINAL_DA_CRUZ = "Em nome do Pai... e do Filho... e do Espírito Santo... Amém..."

ATO_DE_CONTRICAO = (
    "Rezemos juntos o ato de contrição... "
    "Meu Deus... porque sois infinitamente bom e Vos amo de todo o meu coração... "
    "pesa-me de Vos ter ofendido... e, com o auxílio da Vossa divina graça... "
    "proponho firmemente emendar-me... e nunca mais Vos tornar a ofender... "
    "Peço e espero o perdão das minhas culpas... pela Vossa infinita misericórdia... Amém..."
)

PAI_NOSSO = (
    "Pai nosso, que estais nos céus... santificado seja o vosso nome... "
    "venha a nós o vosso reino... seja feita a vossa vontade... assim na terra como no céu... "
    "O pão nosso de cada dia nos dai hoje... perdoai-nos as nossas ofensas... "
    "assim como nós perdoamos a quem nos tem ofendido... e não nos deixeis cair em tentação... "
    "mas livrai-nos do mal... Amém..."
)

AVE_MARIA = (
    "Ave Maria, cheia de graça... o Senhor é convosco... bendita sois vós entre as mulheres... "
    "e bendito é o fruto do vosso ventre Jesus... "
    "Santa Maria, Mãe de Deus... rogai por nós, pecadores... agora e na hora de nossa morte... Amém..."
)

GLORIA = (
    "Glória ao Pai... ao Filho... e ao Espírito Santo... "
    "Como era no princípio... agora e sempre... Amém..."
)

ORACOES_NOVENA = {
    "aparecida": (
        "Rezemos agora a oração desta novena... "
        "Ó Nossa Senhora da Conceição Aparecida... Mãe querida do povo brasileiro... "
        "assim como fostes encontrada nas águas do rio pelas mãos simples dos pescadores... "
        "vinde hoje ao encontro da minha vida... "
        "Olhai para as minhas dores... para as necessidades da minha família... "
        "e para tudo aquilo que eu não consigo carregar sozinho... "
        "Neste dia da vossa novena... eu vos entrego a minha intenção... "
        "e confio que, pela vossa intercessão... o vosso Filho Jesus fará o que for melhor para mim... "
        "Cobri-me com o vosso manto... protegei a minha casa... curai o que está ferido... "
        "e conduzi-me sempre para mais perto de Jesus... Amém..."
    ),
    "imaculada": (
        "Rezemos agora a oração desta novena... "
        "Ó Virgem Imaculada... concebida sem a mancha do pecado... "
        "Mãe pura e cheia de graça... olhai para o meu coração cansado... "
        "Vós que dissestes sim ao plano de Deus... ensinai-me a confiar como vós confiastes... "
        "Neste dia da vossa novena... eu vos entrego a minha intenção... "
        "Purificai a minha vida... afastai de mim todo o mal... "
        "e apresentai o meu pedido ao vosso Filho Jesus... Amém..."
    ),
    "natal": (
        "Rezemos agora a oração desta novena... "
        "Ó Maria... Mãe da espera e da esperança... "
        "vós que guardastes no coração o Menino que ia nascer... "
        "preparai também o meu coração para receber Jesus neste Natal... "
        "Neste dia da novena... eu vos entrego a minha intenção... "
        "e a minha família... para que a luz de Belém entre na nossa casa... "
        "e traga paz... cura... e união... Amém..."
    ),
    "pedido": (
        "Rezemos agora a oração desta novena... "
        "Ó Nossa Senhora... Mãe de Deus e nossa Mãe... "
        "nesta novena eu venho aos vossos pés com um pedido que pesa no meu coração... "
        "Vós conheceis a minha dor... antes mesmo que eu a diga... "
        "Neste dia da novena... eu vos entrego a minha intenção... "
        "e peço que a leveis ao vosso Filho Jesus... como levastes o pedido dos noivos em Caná... "
        "Que seja feita a vontade de Deus... e que eu tenha força para esperar com fé... Amém..."
    ),
}

JACULATORIA = {
    "aparecida": "Nossa Senhora Aparecida... rogai por nós...",
    "imaculada": "Ó Maria concebida sem pecado... rogai por nós que recorremos a vós...",
    "natal": "Nossa Senhora... Mãe do Menino Jesus... rogai por nós...",
    "pedido": "Nossa Senhora... rogai por nós...",
}


def _festas_do_ano(ano):
    out = []
    for f in FESTAS:
        ini = datetime.date(ano, f["inicio"][0], f["inicio"][1])
        out.append((ini, ini + datetime.timedelta(days=8), ini + datetime.timedelta(days=9), f))
    return sorted(out, key=lambda x: x[0])


def _festa_em(d):
    """Retorna (tipo, festa, dia_n, inicio) se d está numa novena de festa ou é o dia da festa."""
    for ano in (d.year - 1, d.year):
        for ini, fim, dia_festa, f in _festas_do_ano(ano):
            if ini <= d <= fim:
                return ("festa", f, (d - ini).days + 1, ini)
            if d == dia_festa:
                return ("dia_festa", f, None, ini)
    return None


def _proxima_festa_inicio(d):
    for ano in (d.year, d.year + 1):
        for ini, _, _, _ in _festas_do_ano(ano):
            if ini >= d:
                return ini
    return None


def plano_do_dia(d):
    """
    Define o que o slot 06:00 publica na data d.
    Retorna None (slot inexistente) ou dict com:
      tipo: 'festa' | 'pedido' | 'avulsa'
      dia: 1..9 (festa/pedido)
      festa: dict (festa) | ciclo_inicio: date (pedido)
    """
    if d < ATIVACAO_06H:
        return None
    fe = _festa_em(d)
    if fe:
        tipo, f, n, ini = fe
        if tipo == "festa":
            return {"tipo": "festa", "dia": n, "festa": f, "ciclo_inicio": ini}
        return {"tipo": "avulsa", "motivo": f"dia da festa ({f['id']})"}
    if d < EPOCA_PEDIDOS:
        return {"tipo": "avulsa", "motivo": "antes da época de pedidos"}

    # Caminha ciclo a ciclo desde a época até alcançar d.
    cursor = EPOCA_PEDIDOS
    guard = 0
    while cursor <= d and guard < 2000:
        guard += 1
        fe_c = _festa_em(cursor)
        if fe_c:
            _, f, _, ini = fe_c
            cursor = ini + datetime.timedelta(days=10)  # pula novena (9) + dia da festa
            continue
        prox = _proxima_festa_inicio(cursor)
        fim_ciclo = cursor + datetime.timedelta(days=8)
        if prox is None or fim_ciclo < prox:
            if cursor <= d <= fim_ciclo:
                return {"tipo": "pedido", "dia": (d - cursor).days + 1, "ciclo_inicio": cursor}
            cursor = fim_ciclo + datetime.timedelta(days=1)
        else:
            # Não cabe um ciclo completo antes da festa → avulsas até a festa.
            if cursor <= d < prox:
                return {"tipo": "avulsa", "motivo": "intervalo antes de novena de festa"}
            cursor = prox
    return {"tipo": "avulsa", "motivo": "fallback"}


def nome_mes(d):
    meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
             "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    return f"{meses[d.month - 1]} {d.year}"


def nome_playlist(plano, categoria=None):
    if plano["tipo"] == "festa":
        return f"{plano['festa']['nome']} {plano['ciclo_inicio'].year} (Completa)"
    if plano["tipo"] == "pedido":
        return f"{CATEGORIAS[categoria][0]} com Nossa Senhora — {nome_mes(plano['ciclo_inicio'])}"
    return None


def montar_titulo(plano, promessa, categoria=None):
    """Fórmula aprovada: [Palavra-chave de busca] + [Nº Dia] + 🙏 + [Dor/Promessa]."""
    promessa = (promessa or "").strip().strip(".").strip()
    n = plano["dia"]
    if plano["tipo"] == "festa":
        base = f"{plano['festa']['nome']} {n}º Dia 🙏"
    else:
        # Palavra-chave + dia nos primeiros ~40 caracteres (corte do celular); Nossa Senhora vem na promessa.
        base = f"{CATEGORIAS[categoria][0]} – {n}º Dia 🙏"
    titulo = f"{base} {promessa}".strip()
    if len(titulo) > 100:
        titulo = base
    return titulo


def texto_thumb(plano):
    # Sem "º": a fonte Anton da thumbnail pode não ter o glifo.
    return f"DIA {plano['dia']} DA NOVENA"


def tema_codificado(plano, categoria=None):
    """Formato lido pelo publicador: NOVENA|<playlist>|<dia>|<tipo>|<chave>"""
    chave = plano["festa"]["id"] if plano["tipo"] == "festa" else categoria
    return f"NOVENA|{nome_playlist(plano, categoria)}|{plano['dia']}|{plano['tipo']}|{chave}"


def chave_oracao(plano):
    return plano["festa"]["id"] if plano["tipo"] == "festa" else "pedido"


def montar_roteiro(plano, gancho, reflexao, suplica, encerramento):
    """Esqueleto fixo do rito + blocos variáveis do Gemini."""
    k = chave_oracao(plano)
    partes = [
        gancho.strip(),
        SINAL_DA_CRUZ,
        ATO_DE_CONTRICAO,
        reflexao.strip(),
        ORACOES_NOVENA[k],
        suplica.strip(),
        PAI_NOSSO,
        AVE_MARIA,
        GLORIA,
        JACULATORIA[k],
        encerramento.strip(),
        SINAL_DA_CRUZ,
    ]
    return "\n\n".join(p for p in partes if p)


# ─────────────────────────── ESTADO NA PLANILHA ───────────────────────────
ABA_NOVENAS = "NOVENAS"
ABA_TEMAS = "TEMAS_COMENTARIOS"


def _aba(planilha, nome, cabecalho):
    try:
        return planilha.worksheet(nome)
    except Exception:
        ws = planilha.add_worksheet(title=nome, rows=1000, cols=len(cabecalho))
        ws.update(values=[cabecalho], range_name="A1")
        return ws


def escolher_tema_pedido(planilha, ciclo_inicio):
    """
    Tema do ciclo de pedido. Uma vez escolhido, fica gravado na aba NOVENAS e é
    reutilizado nos 9 dias (idempotente). Retorna chave de CATEGORIAS.
    """
    ws_nov = _aba(planilha, ABA_NOVENAS, ["Canal", "Inicio", "Tipo", "Categoria", "Fonte", "Criado_em"])
    linhas = ws_nov.get_all_values()[1:]
    ciclo_str = str(ciclo_inicio)
    do_canal = [l for l in linhas if len(l) >= 4 and l[0] == CANAL and l[2] == "pedido"]
    for l in do_canal:
        if l[1] == ciclo_str and l[3] in CATEGORIAS:
            return l[3]

    usados = [l[3] for l in sorted(do_canal, key=lambda x: x[1]) if l[1] < ciclo_str][-JANELA_ANTI_REPETICAO:]

    escolha, fonte = None, "fallback"
    try:
        ws_t = _aba(planilha, ABA_TEMAS, ["Canal", "Data", "Categoria", "Contagem"])
        rows = [r for r in ws_t.get_all_values()[1:] if len(r) >= 4 and r[0] == CANAL]
        if rows:
            ultima = max(r[1] for r in rows)
            dt_ult = datetime.datetime.strptime(ultima, "%Y-%m-%d").date()
            if (ciclo_inicio - dt_ult).days <= 30:
                lote = []
                for r in rows:
                    if r[1] == ultima and r[2] in CATEGORIAS:
                        try: lote.append((r[2], int(r[3])))
                        except ValueError: pass
                if sum(c for _, c in lote) >= MIN_COMENTARIOS_RANKING:
                    for cat, cnt in sorted(lote, key=lambda x: -x[1]):
                        if cnt > 0 and cat not in usados:
                            escolha, fonte = cat, f"comentarios {ultima}"
                            break
    except Exception as e:
        print(f"[WARN] Ranking de comentários indisponível: {e}")

    if not escolha:
        idx = len(do_canal)
        for i in range(len(ROTACAO_FALLBACK)):
            cand = ROTACAO_FALLBACK[(idx + i) % len(ROTACAO_FALLBACK)]
            if cand not in usados:
                escolha = cand
                break

    ws_nov.append_row([CANAL, ciclo_str, "pedido", escolha, fonte,
                       datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")])
    print(f"📿 Novo ciclo de pedido {ciclo_str}: '{escolha}' ({fonte})")
    return escolha
