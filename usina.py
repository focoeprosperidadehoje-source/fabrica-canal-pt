import os, sys, json, time, re, datetime
from google.genai import Client
from google.oauth2.service_account import Credentials
import gspread

CHAVE_API = os.environ.get("GEMINI_API_KEY")
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
    {"horario": "06:00", "personagem": "Jesus", "idioma": "PT", "foco": "Manhã: Consagração, sabedoria divina e direção para o dia.", "periodo": "nesta manhã"},
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
hoje = datetime.date.today()
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
data_alvo = None
grade_para_processar = []

data_check = limite_passado
while data_check <= meta_estoque:
    horarios_presentes = dias_existentes.get(data_check, [])
    if len(horarios_presentes) < 2:
        data_alvo = data_check
        grade_para_processar = [v for v in GRADE_DIARIA if v["horario"] not in horarios_presentes]
        break
    data_check += datetime.timedelta(days=1)

if not data_alvo:
    print(f"✅ ESTOQUE ATINGIDO até {meta_estoque}. Dormindo.")
    sys.exit(0)

pilar_do_dia = PILARES[data_alvo.weekday()]
contexto_sazonal = calcular_contexto_sazonal(data_alvo)
print(f"\n📅 DATA ALVO: {data_alvo} | Pilar: {pilar_do_dia}")

esperas_exponenciais = [10, 20, 40, 80, 120]

for video in grade_para_processar:
    horario, persona, idioma, foco_teologico, periodo_dia = video["horario"], video["personagem"].upper(), video["idioma"], video["foco"], video["periodo"]
    print(f"🎬 PRODUZINDO: {horario} | {persona}")

    if data_alvo.weekday() == 4:
        foco_teologico += " OBRIGATÓRIO: Aprofunde o tema da Misericórdia e do Perdão." if horario == "06:00" else " OBRIGATÓRIO: Conecte o tema com a Paixão de Cristo e o Sacramento da Reconciliação."

    persona_prompt = "Jesus Cristo" if persona == 'JESUS' else "Nossa Senhora (Maria)"

    prompt_tema = f"Atue como Teólogo. Crie um tema curto (máx 8 palavras) para uma oração. Pilar: '{pilar_do_dia}', dirigida a '{persona_prompt}', momento: '{foco_teologico}'. Sazonalidade: '{contexto_sazonal}'. APENAS o tema, sem aspas ou asteriscos."
    tema_gerado = None
    for i in range(5):
        try:
            tema_gerado = client.models.generate_content(model=modelos_cascata[i], contents=prompt_tema).text.replace('*', '').replace('"', '').replace('[', '').replace(']', '').strip()
            break 
        except: time.sleep(esperas_exponenciais[i])
            
    if not tema_gerado: continue 
    time.sleep(5)

    regra_meditacao = "OBRIGATÓRIO: Na descrição (DESC), adicione um aviso destacado dizendo que ao final do vídeo há 5 minutos de música celestial para dormir/meditar." if horario == "18:00" else ""
    regra_persona = "OBRIGATÓRIO: Como você se dirige a Jesus, É PROIBIDO mencionar Maria ou Nossa Senhora." if persona == 'JESUS' else "OBRIGATÓRIO: Como você se dirige a Maria, DEVE usar as invocações 'Nossa Senhora', 'Mãe' ou 'Virgem Maria'."

    prompt_principal = f"""
    Atue como um guia espiritual empático. Escreva uma oração extensa de 1500 a 1800 palavras sobre "{tema_gerado}" dirigida a {persona_prompt}. 
    CONTEXTO: Período do dia: "{periodo_dia}". Enfoque: "{foco_teologico}". Sazonalidade: "{contexto_sazonal}".
    
    REGRAS DE RETENÇÃO E COPYWRITING (MUITO IMPORTANTE):
    1. FÓRMULA DO TÍTULO: O título DEVE OBRIGATORIAMENTE seguir a fórmula: [Dor do Fiel] + [Solução/Milagre]. É ESTRITAMENTE PROIBIDO começar o título com a palavra "Oração".
    2. FÓRMULA DA THUMB: Máximo de 4 palavras. DEVE ser um gatilho de urgência conectado ao tema (Ex: "MILAGRE URGENTE HOJE", "SALVE SUA FAMÍLIA", "FIM DA ANSIEDADE").
    3. REGRA DOS 15 SEGUNDOS (HOOK 3A): O início do roteiro DEVE ter 3 blocos rápidos:
       - Atenção (0-5s): Uma AFIRMAÇÃO EMPÁTICA sobre a dor do fiel. (PROIBIDO usar perguntas diretas).
       - Ambientação Sensorial (5-10s): Conecte a dor com o cenário de {periodo_dia}.
       - Autoridade/Agenda (10-15s): Diga que {persona_prompt} tem uma palavra de libertação e peça para ficar até o final.
    4. CTA IMEDIATO: Peça naturalmente no início: "Se você crê, digite 'Amém, eu recebo' nos comentários agora mesmo".
    5. RESET DE ATENÇÃO (MEIO DO VÍDEO): Exatamente na metade do roteiro, insira uma frase falada para reconectar o espectador.
    6. GANCHOS INVISÍVEIS DE RETENÇÃO: A cada 300 a 400 palavras, incorpore organicamente — sem que o fiel perceba a técnica — um dos seguintes recursos: (a) ANTECIPAÇÃO: anuncie que algo importante será revelado logo adiante, sem revelar ainda; (b) REVELAÇÃO PARCIAL: entregue uma parte da resposta espiritual e sinalize que há mais; (c) VALIDAÇÃO EMOCIONAL: nomeie exatamente o que o fiel está sentindo naquele momento, criando reconhecimento profundo; (d) VIRADA DE BLOCO: faça uma transição inesperada de tom — de súplica para gratidão, de dor para esperança — que renove a atenção. Os ganchos devem ser invisíveis: o fiel não percebe a técnica, apenas sente que não consegue parar de ouvir. Nunca quebre o clima devocional.

    REGRAS GERAIS:
    7. PROIBIDO MENCIONAR HORÁRIOS EXATOS: Nunca diga "06:00" ou "18:00". Use apenas "{periodo_dia}".
    8. PAUSAS: OBRIGATÓRIO usar abundantes pontos suspensivos (...) para forçar pausas na voz da IA.
    9. ANTI-JSON: Escreva em TEXTO PLANO. PROIBIDO JSON, chaves {{ }} ou asteriscos (*).
    {regra_persona}
    {regra_meditacao}
    
    FORMATO EXATO:
    TITULO: [Dor + Solução]
    THUMB: [Gatilho de Urgência conectado ao tema - Máx 4 palavras]
    GUION: [Oração completa de 1500 a 1800 palabras]
    DESC: [Descrição de 3 parágrafos com forte SEO]
    TAGS: [Tags separadas por vírgulas]
    """
    
    texto_ia = None
    for i in range(5): 
        try:
            texto_ia = client.models.generate_content(model=modelos_cascata[i], contents=prompt_principal).text
            break 
        except: time.sleep(esperas_exponenciais[i])
            
    if not texto_ia: continue

    try:
        t_match = re.search(r'T[IÍ]TULO:\s*(.*?)(?=THUMB:|GUI[OÓ]N:|DESC:|TAGS:|$)', texto_ia, re.IGNORECASE | re.DOTALL)
        th_match = re.search(r'THUMB:\s*(.*?)(?=GUI[OÓ]N:|DESC:|TAGS:|T[IÍ]TULO:|$)', texto_ia, re.IGNORECASE | re.DOTALL)
        g_match = re.search(r'GUI[OÓ]N:\s*(.*?)(?=DESC:|TAGS:|T[IÍ]TULO:|THUMB:|$)', texto_ia, re.IGNORECASE | re.DOTALL)
        d_match = re.search(r'DESC:\s*(.*?)(?=TAGS:|T[IÍ]TULO:|THUMB:|GUI[OÓ]N:|$)', texto_ia, re.IGNORECASE | re.DOTALL)
        tg_match = re.search(r'TAGS:\s*(.*?)(?=T[IÍ]TULO:|THUMB:|GUI[OÓ]N:|DESC:|$)', texto_ia, re.IGNORECASE | re.DOTALL)
        
        titulo_final = re.sub(r'[*"\[\]]', '', t_match.group(1)).strip() if t_match else "Oração Poderosa"
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
