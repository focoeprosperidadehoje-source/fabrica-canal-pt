import os, sys, json, time, re, datetime
from google.genai import Client
from google.oauth2.service_account import Credentials
import gspread
from zoneinfo import ZoneInfo
import novenas

CHAVE_API = os.environ.get("GEMINI_API_KEY")
CHAVE_API_2 = os.environ.get("GEMINI_API_KEY_2", "")
CHAVES_GEMINI = [k for k in [CHAVE_API, CHAVE_API_2] if k]
GOOGLE_JSON = os.environ.get("GOOGLE_CREDENTIALS_PT")

print("🔐 Autenticando no Google Sheets via Service Account...")
credenciais_dict = json.loads(GOOGLE_JSON)
escopos = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
credenciais = Credentials.from_service_account_info(credenciais_dict, scopes=escopos)
gc = gspread.authorize(credenciais)

client = Client(api_key=CHAVE_API, http_options={'api_version': 'v1'})

def obter_cascata_de_modelos():
    try:
        modelos_disponiveis = client.models.list()
        # Lite/8b = cota generosa no tier gratuito. Prioridade máxima.
        lite_models = [m.name for m in modelos_disponiveis if 'generateContent' in m.supported_generation_methods and 'flash' in m.name and ('lite' in m.name or '8b' in m.name)]
        # Flash regular = fallback de último recurso (cota restrita ~20 RPD)
        flash_models = [m.name for m in modelos_disponiveis if 'generateContent' in m.supported_generation_methods and 'flash' in m.name and 'lite' not in m.name and '8b' not in m.name]
        melhor_lite = sorted(lite_models, reverse=True)[0] if lite_models else 'gemini-2.5-flash-lite'
        melhor_flash = sorted(flash_models, reverse=True)[0] if flash_models else 'gemini-2.5-flash'
        return [melhor_lite, melhor_lite, melhor_lite, melhor_lite, melhor_flash]
    except:
        return ['gemini-2.5-flash-lite', 'gemini-2.5-flash-lite', 'gemini-2.5-flash-lite', 'gemini-2.5-flash-lite', 'gemini-2.5-flash']

modelos_cascata = obter_cascata_de_modelos()

def _gerar(modelo, prompt):
    for chave in CHAVES_GEMINI:
        try:
            c = Client(api_key=chave, http_options={'api_version': 'v1'})
            return c.models.generate_content(model=modelo, contents=prompt).text
        except Exception as e:
            if "429" in str(e) and chave != CHAVES_GEMINI[-1]:
                print(f"[WARN] 429 na chave ...{chave[-6:]}. Tentando chave 2...")
                continue
            raise
    raise RuntimeError("Todas as chaves Gemini falharam.")

def calcular_contexto_sazonal(data_alvo):
    ano = data_alvo.year
    a = ano % 19; b = ano // 100; c = ano % 100; d = b // 4; e = b % 4; f = (b + 8) // 25; g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30; i = c // 4; k = c % 4; l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451; mes = (h + l - 7 * m + 114) // 31; dia = ((h + l - 7 * m + 114) % 31) + 1
    pascoa = datetime.date(ano, mes, dia)
    
    cinzas = pascoa - datetime.timedelta(days=46)
    sexta_santa = pascoa - datetime.timedelta(days=2)
    corpus_christi = pascoa + datetime.timedelta(days=60)
    pentecostes = pascoa + datetime.timedelta(days=49)
    maio_1 = datetime.date(ano, 5, 1)
    dia_das_maes = maio_1 + datetime.timedelta(days=(6 - maio_1.weekday() + 7) % 7 + 7)
    
    if data_alvo == pascoa: return "HOJE É DOMINGO DE PÁSCOA."
    if data_alvo == cinzas: return "HOJE É QUARTA-FEIRA DE CINZAS."
    if data_alvo == sexta_santa: return "HOJE É SEXTA-FEIRA SANTA."
    if data_alvo == corpus_christi: return "HOJE É CORPUS CHRISTI."
    if data_alvo == pentecostes: return "HOJE É PENTECOSTES."
    if data_alvo == dia_das_maes: return "HOJE É DIA DAS MÃES."
    if data_alvo.month == 10 and data_alvo.day == 12: return "HOJE É DIA DE NOSSA SENHORA APARECIDA."
    if data_alvo.month == 12 and data_alvo.day == 25: return "HOJE É NATAL."
    if data_alvo.month == 12 and data_alvo.day == 31: return "HOJE É VÉSPERA DE ANO NOVO."
    if data_alvo.month == 1 and data_alvo.day == 1: return "HOJE É ANO NOVO."
    return ""

ID_PLANILHA = "1KgIjWrLUVlllhlZB1R9fkHGxxZlLsax1aOVGZrYwgnU"
PILARES = {
    0: "Guerra Espiritual e Proteção", 1: "Libertação de Vícios e Amarras",
    2: "Restauração Familiar e Matrimonial", 3: "Providência e Portas Abertas",
    4: "Misericórdia e Cura Física", 5: "O Manto de Maria", 6: "Milagres e Gratidão"
}
GRADE_DIARIA = [
    # Slot 06:00 — Novenas (aprovado 2026-09-25). Planejamento em novenas.py.
    # NÃO gera linhas para datas anteriores a novenas.ATIVACAO_06H nem para datas passadas.
    {"horario": "06:00", "personagem": "Maria", "idioma": "PT", "foco": "Manhã: consagração do dia a Nossa Senhora, proteção, direção e força para o dia que começa.", "periodo": "nesta manhã", "ativacao": novenas.ATIVACAO_06H},
    {"horario": "18:00", "personagem": "Maria", "idioma": "PT", "foco": "HÍBRIDO: Tratar a dor do Pilar do Dia e, no final, fazer a transição para a oração da noite, pedindo sono profundo, alívio da ansiedade e proteção noturna.", "periodo": "nesta noite"}
]

aba = gc.open_by_key(ID_PLANILHA).worksheet("PT")

todas_linhas = aba.get_all_values()
if len(todas_linhas) > 500:
    aba.delete_rows(2, 100)
    todas_linhas = aba.get_all_values()

proxima_linha_vazia = len(todas_linhas) + 1
valores_coluna_a = [linha[0].strip() for linha in todas_linhas[1:] if len(linha) > 0]
valores_coluna_b = [linha[1].strip() for linha in todas_linhas[1:] if len(linha) > 1]

dias_existentes = {}
agora_local = datetime.datetime.now(ZoneInfo(novenas.TZ))
hoje = agora_local.date()
limite_passado = hoje - datetime.timedelta(days=2)

for d_str, h_str in zip(valores_coluna_a, valores_coluna_b):
    if d_str and h_str:
        try:
            d_obj = datetime.datetime.strptime(d_str, '%Y-%m-%d').date()
            if d_obj >= limite_passado:
                if d_obj not in dias_existentes: dias_existentes[d_obj] = []
                dias_existentes[d_obj].append(h_str)
        except: pass

meta_estoque = hoje + datetime.timedelta(days=5)

def slot_exigido(v, d):
    """Travas do slot 06:00: sem retroatividade (evita upload público imediato de vídeo atrasado)."""
    if v.get("ativacao") and d < v["ativacao"]:
        return False
    if v["horario"] == "06:00":
        if d < hoje:
            return False
        if d == hoje and agora_local.hour >= 4:
            return False  # prensa das 04h/05h já não teria tempo com segurança
        if novenas.plano_do_dia(d) is None:
            return False
    return True

data_alvo = None
grade_para_processar = []

data_check = limite_passado
while data_check <= meta_estoque:
    horarios_presentes = dias_existentes.get(data_check, [])
    faltando = [v for v in GRADE_DIARIA if slot_exigido(v, data_check) and v["horario"] not in horarios_presentes]
    if faltando:
        data_alvo = data_check
        grade_para_processar = faltando
        break
    data_check += datetime.timedelta(days=1)

if not data_alvo:
    print(f"✅ ESTOQUE ATINGIDO até {meta_estoque}. Dormindo.")
    sys.exit(0)

pilar_do_dia = PILARES[data_alvo.weekday()]
contexto_sazonal = calcular_contexto_sazonal(data_alvo)
print(f"\n📅 DATA ALVO: {data_alvo} | Pilar: {pilar_do_dia}")

esperas_exponenciais = [10, 20, 40, 80, 120]

def gerar_novena(data_alvo, plano, contexto_sazonal):
    """Gera a linha da planilha para um dia de novena (festa ou pedido). Retorna lista de 12 colunas ou None."""
    n = plano["dia"]
    categoria = None
    if plano["tipo"] == "festa":
        f = plano["festa"]
        invocacao = f["invocacao"]
        intencao = novenas.INTENCOES_FESTA[n - 1]
        sub = f.get("subtemas_oficiais", {}).get(data_alvo.year)
        linha_sub = (f"Cite UMA única vez, com naturalidade, dentro da REFLEXAO, o tema oficial do Santuário Nacional para este dia: \"{sub[n-1]}\". Depois centre tudo na intenção do dia." if sub else "")
        contexto = (f"Esta é a {f['nome']}, preparação para a {f['festa']}. Hoje é o {n}º dia de 9. "
                    f"INTENÇÃO DO DIA (a dor do fiel): {intencao}. {linha_sub}")
    else:
        categoria = novenas.escolher_tema_pedido(gc.open_by_key(ID_PLANILHA), plano["ciclo_inicio"])
        rotulo, descr = novenas.CATEGORIAS[categoria]
        invocacao = "Nossa Senhora"
        contexto = (f"Esta é a '{rotulo}', uma novena de pedido de 9 dias dirigida a Nossa Senhora. "
                    f"Tema único da novena: {descr}. Hoje é o {n}º dia de 9. {novenas.PROGRESSAO_PEDIDO[n]}")
    if data_alvo.weekday() == 4:
        contexto += " HOJE É SEXTA-FEIRA: toque com delicadeza na Misericórdia e no Perdão."
    if contexto_sazonal:
        contexto += f" Sazonalidade: {contexto_sazonal}."

    cta_final = ("Convide o fiel a rezar a novena completa na playlist do canal e a continuar rezando conosco ao vivo 24 horas."
                 if n == 9 else
                 "Convide o fiel a voltar amanhã cedo para o próximo dia da novena, sem citar horário exato.")

    prompt = f"""
    Atue como um guia espiritual católico empático, fiel à doutrina da Igreja. Você vai escrever as partes VARIÁVEIS de um vídeo de NOVENA dirigido a {invocacao}.
    O rito fixo (sinal da cruz, ato de contrição, oração da novena, Pai Nosso, Ave Maria, Glória) JÁ ESTÁ PRONTO e será inserido pelo sistema — NÃO escreva essas orações.
    CONTEXTO: {contexto}
    Período do dia: "nesta manhã".

    REGRAS:
    1. GANCHO (120 a 180 palavras) — HOOK 3A: (a) AFIRMAÇÃO EMPÁTICA sobre a dor da intenção do dia, PROIBIDO perguntas; (b) ambientação sensorial da manhã que começa; (c) anuncie que hoje é o {n}º dia da novena e que {invocacao} tem uma graça para quem ficar até o final.
    2. REFLEXAO (450 a 600 palavras): uma passagem bíblica curta (cite livro e capítulo) ligada à intenção do dia, e uma meditação calorosa. Insira 1 gancho invisível de retenção (antecipação ou revelação parcial) sem quebrar o clima devocional.
    3. SUPLICA (350 a 500 palavras): súplica pessoal pela intenção do dia, em primeira pessoa ("eu vos peço..."), OBRIGATÓRIO incluir um bloco de intercessão pela saúde (doentes da família, cura física e emocional). Arco: vulnerabilidade → intercessão → confiança.
    4. ENCERRAMENTO (120 a 180 palavras): termine em FORÇA e confiança, nunca em súplica. {cta_final} Convide também a escrever nos comentários a intenção ou o nome de quem ele entrega a {invocacao} nesta novena, porque essas intenções são levadas à nossa oração ao vivo 24 horas. PROIBIDO "digite Amém" ou qualquer engajamento forçado.
    5. PROMESSA (máx 40 caracteres) — complemento do título, que já começa com o nome da novena e o dia. NÃO repita o nome da novena. {'Foque a intenção do dia. Ex: "Pela Cura da Sua Família", "Liberte Seu Filho do Vício".' if plano['tipo']=='festa' else 'OBRIGATÓRIO começar com "Nossa Senhora". Ex: "Nossa Senhora Restaura Sua Saúde", "Nossa Senhora Abre as Portas do Emprego".'} Sem aspas, sem emoji, sem data.
    6. PROIBIDO mencionar horários exatos. Use abundantes reticências (...) para pausas da voz. TEXTO PLANO: sem JSON, sem asteriscos, sem colchetes, sem títulos de seção dentro dos textos.
    7. PROIBIDO citar qualquer santo ou devoção que não seja Nossa Senhora, Jesus e Deus Pai.

    FORMATO EXATO (use estes rótulos, nesta ordem):
    PROMESSA: ...
    GANCHO: ...
    REFLEXAO: ...
    SUPLICA: ...
    ENCERRAMENTO: ...
    DESC: [3 parágrafos com forte SEO. 1º: "{'Novena' if plano['tipo']=='festa' else 'Novena de pedido'} — {n}º dia de 9" + convite à live 24 horas. 2º: descrição emocional da intenção do dia. 3º: palavras-chave e hashtags (#novena).]
    TAGS: [tags separadas por vírgulas, incluindo "novena"]
    """
    rotulos = ["PROMESSA", "GANCHO", "REFLEXAO", "SUPLICA", "ENCERRAMENTO", "DESC", "TAGS"]
    def _lab(r): return r"(?:^|\n)[ \t>*_#]*" + r + r"[ \t*_]*:"
    padrao_fim = "|".join(_lab(r) for r in rotulos)
    for i in range(5):
        try:
            texto = _gerar(modelos_cascata[i], prompt)
        except Exception as e:
            print(f"   ⚠️ Gemini falhou ({e}); nova tentativa...")
            time.sleep(esperas_exponenciais[i]); continue
        t = texto.replace("REFLEXÃO", "REFLEXAO").replace("SÚPLICA", "SUPLICA")
        partes = {}
        for r in rotulos:
            m = re.search(_lab(r) + r"\s*(.*?)(?=(?:" + padrao_fim + r")|\Z)", t, re.IGNORECASE | re.DOTALL)
            partes[r] = re.sub(r'[*#\[\]{}]', '', m.group(1)).strip() if m else ""
        palavras = sum(len(partes[k].split()) for k in ["GANCHO", "REFLEXAO", "SUPLICA", "ENCERRAMENTO"])
        if all(partes[k] for k in ["GANCHO", "REFLEXAO", "SUPLICA", "ENCERRAMENTO"]) and palavras >= 700:
            break
        print(f"   ⚠️ Resposta incompleta da IA ({palavras} palavras). Nova tentativa...")
        time.sleep(esperas_exponenciais[i])
    else:
        print("   ❌ Novena não gerada nesta execução — o scanner tentará de novo na próxima.")
        return None

    promessa = partes["PROMESSA"].replace('"', '').strip()[:45]
    titulo = novenas.montar_titulo(plano, promessa, categoria)
    roteiro = novenas.montar_roteiro(plano, partes["GANCHO"], partes["REFLEXAO"], partes["SUPLICA"], partes["ENCERRAMENTO"])
    tags = partes["TAGS"] or "novena, nossa senhora, oração da manhã"
    desc = partes["DESC"] or f"Novena — {n}º dia de 9."
    tema = novenas.tema_codificado(plano, categoria)
    return [str(data_alvo), "06:00", "Pronto p/ Áudio", "MARIA", "PT", tema, titulo, roteiro, tags, desc, "Pendente", novenas.texto_thumb(plano)]


for video in grade_para_processar:
    horario, persona, idioma, foco_teologico, periodo_dia = video["horario"], video["personagem"].upper(), video["idioma"], video["foco"], video["periodo"]
    print(f"🎬 PRODUZINDO: {horario} | {persona}")

    if horario == "06:00":
        plano = novenas.plano_do_dia(data_alvo)
        if plano and plano["tipo"] in ("festa", "pedido"):
            nova_linha = gerar_novena(data_alvo, plano, contexto_sazonal)
            if nova_linha:
                try:
                    aba.update(values=[nova_linha], range_name=f"A{proxima_linha_vazia}:L{proxima_linha_vazia}")
                    print(f"   ✅ NOVENA salva na linha {proxima_linha_vazia}: {nova_linha[6]}")
                    proxima_linha_vazia += 1
                    time.sleep(5)
                except Exception as e: print(f"   ❌ Falha ao salvar novena: {e}")
            continue
        print(f"   ☀️ Slot 06:00 avulso ({plano.get('motivo') if plano else '-'}) — oração da manhã padrão.")

    if data_alvo.weekday() == 4:
        foco_teologico += " OBRIGATÓRIO: Aprofunde o tema da Misericórdia e do Perdão." if horario == "06:00" else " OBRIGATÓRIO: Conecte o tema com a Paixão de Cristo e o Sacramento da Reconciliação."

    persona_prompt = "Jesus Cristo" if persona == 'JESUS' else "Nossa Senhora (Maria)"

    prompt_tema = f"Atue como Teólogo. Crie um tema curto (máx 8 palavras) para uma oração. Pilar: '{pilar_do_dia}', dirigida a '{persona_prompt}', momento: '{foco_teologico}'. Sazonalidade: '{contexto_sazonal}'. APENAS o tema, sem aspas ou asteriscos."
    tema_gerado = None
    for i in range(5):
        try:
            tema_gerado = _gerar(modelos_cascata[i], prompt_tema).replace('*', '').replace('"', '').replace('[', '').replace(']', '').strip()
            break 
        except: time.sleep(esperas_exponenciais[i])
            
    if not tema_gerado: continue 
    time.sleep(5)

    regra_meditacao = "OBRIGATÓRIO: Na descrição (DESC), adicione um aviso destacado dizendo que ao final do vídeo há 5 minutos de música celestial para dormir/meditar." if horario == "18:00" else ""
    regra_persona = "OBRIGATÓRIO: Como você se dirige a Jesus, É PROIBIDO mencionar Maria ou Nossa Senhora." if persona == 'JESUS' else "OBRIGATÓRIO: Como você se dirige a Maria, DEVE usar as invocações 'Nossa Senhora', 'Mãe' ou 'Virgem Maria'."

    instrucao_titulo = (
        "TITULO:[Título magnético. OBRIGATÓRIO começar com 'Nossa Senhora' ou 'Aparecida'. FORMATO: 'Nossa Senhora [Dor do fiel] [promessa urgente]'. Ex: 'Nossa Senhora Cura Sua Família Esta Noite'. SEM DATA. SEM ASTERISCOS OU COLCHETES]"
        if persona == 'MARIA' else
        "TITULO:[Título magnético. OBRIGATÓRIO começar com a dor/situação do fiel, NUNCA com 'Jesus' ou 'Oração'. FORMATO: '[Dor crítica do fiel] — [promessa de alívio urgente]'. Ex: 'Sua Família Sofre — Faça Esta Oração AGORA'. SEM DATA. SEM ASTERISCOS OU COLCHETES]"
    )

    prompt_principal = f"""
    Atue como um guia espiritual empático. Escreva uma oração extensa de 1500 a 1800 palavras sobre "{tema_gerado}" dirigida a {persona_prompt}. 
    CONTEXTO: Período do dia: "{periodo_dia}". Enfoque: "{foco_teologico}". Sazonalidade: "{contexto_sazonal}".
    
    REGRAS DE RETENÇÃO E COPYWRITING (MUITO IMPORTANTE):
    1. FÓRMULA DO TÍTULO: Siga EXATAMENTE a instrução de formato abaixo. Para Nossa Senhora: OBRIGATÓRIO começar com 'Nossa Senhora' ou 'Aparecida'. Para Jesus: começar com a dor do fiel. É ESTRITAMENTE PROIBIDO começar com a palavra "Oração".
    2. FÓRMULA DA THUMB (MODELO CAMPEÃO — dados reais de CTR): 2 ou 3 palavras = RESULTADO CONCRETO + palavra de urgência no final (HOJE / AGORA). Ex: "MILAGRE HOJE", "PORTAS ABERTAS AGORA", "CURA HOJE", "FAMÍLIA RESTAURADA HOJE". PROIBIDO usar só palavras de calma/abstratas sem resultado (ex.: "PAZ PROFUNDA", "NOITE SERENA", "DESCANSO") — no teste real, "MIRACLE TODAY" teve 4,7% de CTR e "DEEP PEACE TONIGHT" 1,6%.
    3. REGRA DOS 15 SEGUNDOS (HOOK 3A): O início do roteiro DEVE ter 3 blocos rápidos:
       - Atenção (0-5s): Uma AFIRMAÇÃO EMPÁTICA sobre a dor do fiel. (PROIBIDO usar perguntas diretas).
       - Ambientação Sensorial (5-10s): Conecte a dor com o cenário de {periodo_dia}.
       - Autoridade/Agenda (10-15s): Diga que {persona_prompt} tem uma palavra de libertação e peça para ficar até o final.
    4. CTA IMEDIATO: Peça naturalmente no início: "Se você crê, digite 'Amém, eu recebo' nos comentários agora mesmo". No ENCERRAMENTO, peça também com naturalidade que o fiel ENVIE esta oração para alguém que está precisando (ex.: "Se você lembrou de alguém enquanto rezava, envie esta oração para essa pessoa agora."). Compartilhar é o pedido principal do final.
    5. RESET DE ATENÇÃO (MEIO DO VÍDEO): Exatamente na metade do roteiro, insira uma frase falada para reconectar o espectador.
    6. GANCHOS INVISÍVEIS DE RETENÇÃO: A cada 300 a 400 palavras, incorpore organicamente — sem que o fiel perceba a técnica — um dos seguintes recursos: (a) ANTECIPAÇÃO: anuncie que algo importante será revelado logo adiante, sem revelar ainda; (b) REVELAÇÃO PARCIAL: entregue uma parte da resposta espiritual e sinalize que há mais; (c) VALIDAÇÃO EMOCIONAL: nomeie exatamente o que o fiel está sentindo naquele momento, criando reconhecimento profundo; (d) VIRADA DE BLOCO: faça uma transição inesperada de tom — de súplica para gratidão, de dor para esperança — que renove a atenção. Os ganchos devem ser invisíveis: o fiel não percebe a técnica, apenas sente que não consegue parar de ouvir. Nunca quebre o clima devocional.

    REGRAS GERAIS:
    7. PROIBIDO MENCIONAR HORÁRIOS EXATOS: Nunca diga "06:00" ou "18:00". Use apenas "{periodo_dia}".
    8. PAUSAS: OBRIGATÓRIO usar abundantes pontos suspensivos (...) para forçar pausas na voz da IA.
    9. ANTI-JSON: Escreva em TEXTO PLANO. PROIBIDO JSON, chaves {{ }} ou asteriscos (*).
    {regra_persona}
    {regra_meditacao}
    
    FORMATO EXATO:
    {instrucao_titulo}
    THUMB: [Gatilho de Urgência conectado ao tema - Máx 4 palavras]
    GUION: [Oração completa de 1500 a 1800 palavras]
    DESC: [Descrição de 3 parágrafos com forte SEO. PRIMEIRO parágrafo: convida para as orações AO VIVO 24h do canal ('Estamos AO VIVO 24 horas rezando pelos seus pedidos — ative o sininho para não perder nenhuma oração'). SEGUNDO parágrafo: descrição emocional desta oração. TERCEIRO parágrafo: keywords e hashtags.]
    TAGS: [Tags separadas por vírgulas]
    """
    
    texto_ia = None
    for i in range(5): 
        try:
            texto_ia = _gerar(modelos_cascata[i], prompt_principal)
            break 
        except: time.sleep(esperas_exponenciais[i])
            
    if not texto_ia: continue

    try:
        t_match = re.search(r'T[IÍ]TULO:\s*(.*?)(?=THUMB:|GUI[OÓ]N:|DESC:|TAGS:|$)', texto_ia, re.IGNORECASE | re.DOTALL)
        th_match = re.search(r'THUMB:\s*(.*?)(?=GUI[OÓ]N:|DESC:|TAGS:|T[IÍ]TULO:|$)', texto_ia, re.IGNORECASE | re.DOTALL)
        g_match = re.search(r'GUI[OÓ]N:\s*(.*?)(?=DESC:|TAGS:|T[IÍ]TULO:|THUMB:|$)', texto_ia, re.IGNORECASE | re.DOTALL)
        d_match = re.search(r'DESC:\s*(.*?)(?=TAGS:|T[IÍ]TULO:|THUMB:|GUI[OÓ]N:|$)', texto_ia, re.IGNORECASE | re.DOTALL)
        tg_match = re.search(r'TAGS:\s*(.*?)(?=T[IÍ]TULO:|THUMB:|GUI[OÓ]N:|DESC:|$)', texto_ia, re.IGNORECASE | re.DOTALL)
        
        titulo_final = re.sub(r'[*"\[\]]', '', t_match.group(1)).strip() if t_match else "Nossa Senhora Cuida de Você Hoje"
        thumb_final = re.sub(r'[*"\[\]]', '', th_match.group(1)).strip() if th_match else "MILAGRE URGENTE HOJE"
        roteiro_final = g_match.group(1).strip() if g_match else texto_ia 
        desc_final = d_match.group(1).strip() if d_match else "Oração diária."
        tags_final = re.sub(r'[*\[\]]', '', tg_match.group(1)).strip() if tg_match else "oração, fé, proteção"
        
        nova_linha = [str(data_alvo), horario, "Pronto p/ Áudio", persona, idioma, tema_gerado, titulo_final, roteiro_final, tags_final, desc_final, "Pendente", thumb_final]
        aba.update(values=[nova_linha], range_name=f"A{proxima_linha_vazia}:L{proxima_linha_vazia}")
        print(f"   ✅ SUCESSO! Linha {proxima_linha_vazia} preenchida.")
        proxima_linha_vazia += 1 
        time.sleep(5)
    except Exception as e: print(f"   ❌ Falha ao salvar: {e}")
