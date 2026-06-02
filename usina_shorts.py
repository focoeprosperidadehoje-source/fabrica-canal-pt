import os, sys, json, time, re, datetime
from google.genai import Client
from google.oauth2.service_account import Credentials
import gspread

CHAVE_API = os.environ.get("GEMINI_API_KEY")
GOOGLE_JSON = os.environ.get("GOOGLE_CREDENTIALS_PT")

print("🔐 Autenticando no Google Sheets (SHORTS)...")
credenciais_dict = json.loads(GOOGLE_JSON)
escopos = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
credenciais = Credentials.from_service_account_info(credenciais_dict, scopes=escopos)
gc = gspread.authorize(credenciais)

client = Client(api_key=CHAVE_API, http_options={'api_version': 'v1'})

def obter_modelo_lite():
    try:
        modelos = client.models.list()
        lite_models = [m.name for m in modelos if 'generateContent' in m.supported_generation_methods and 'flash-lite' in m.name]
        return sorted(lite_models, reverse=True)[0] if lite_models else 'gemini-2.5-flash'
    except:
        return 'gemini-2.5-flash'

modelo_usina = obter_modelo_lite()

ID_PLANILHA = "1KgIjWrLUVlllhlZB1R9fkHGxxZlLsax1aOVGZrYwgnU"
PILARES = {
    0: "Guerra Espiritual e Proteção", 1: "Libertação de Vícios e Amarras",
    2: "Restauração Familiar e Matrimonial", 3: "Providência e Portas Abertas",
    4: "Misericórdia e Cura Física", 5: "O Manto de Maria", 6: "Milagres e Gratidão"
}
GRADE_SHORTS = [
    {"horario": "14:00", "personagem": "Maria", "idioma": "PT", "foco": "Tarde: Intercessão de Aparecida."}
]

MAPA_SINCRONIA = {
    "14:00": "18:00" # O Short das 14h é o Eco do vídeo das 18h
}

aba_shorts = gc.open_by_key(ID_PLANILHA).worksheet("PT_SHORTS")
aba_longos = gc.open_by_key(ID_PLANILHA).worksheet("PT") 

todas_linhas = aba_shorts.get_all_values()
if len(todas_linhas) > 500:
    aba_shorts.delete_rows(2, 100)
    todas_linhas = aba_shorts.get_all_values()

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
    if len(horarios_presentes) < 1:
        data_alvo = data_check
        grade_para_processar = [v for v in GRADE_SHORTS if v["horario"] not in horarios_presentes]
        break
    data_check += datetime.timedelta(days=1)

if not data_alvo:
    print(f"✅ ESTOQUE DE SHORTS ATINGIDO até {meta_estoque}. Dormindo.")
    sys.exit(0)

pilar_do_dia = PILARES[data_alvo.weekday()]
print(f"\n📅 DATA ALVO SHORTS: {data_alvo} | Pilar: {pilar_do_dia}")

dados_longos = aba_longos.get_all_values()

for video in grade_para_processar:
    horario, persona, idioma, foco_teologico = video["horario"], video["personagem"].upper(), video["idioma"], video["foco"]
    print(f"🎬 PRODUZINDO SHORT: {horario} | {persona}")
    
    horario_longo_ref = MAPA_SINCRONIA[horario]
    titulo_referencia = ""
    for linha in dados_longos[1:]:
        if len(linha) > 6 and linha[0].strip() == str(data_alvo) and linha[1].strip() == horario_longo_ref:
            titulo_referencia = linha[6].strip() 
            break
            
    contexto_eco = f"O vídeo longo correspondente tem o título: '{titulo_referencia}'. O Short DEVE ser um eco deste tema." if titulo_referencia else ""
    
    persona_prompt = "Nossa Senhora Aparecida"
    
    # PAUSA DRAMÁTICA NO NOME DE JESUS
    oracao_padrao = "Ave Maria, cheia de graça... o Senhor é convosco... Bendita sois vós entre as mulheres... e bendito é o fruto do vosso ventre Jesus... Santa Maria, Mãe de Deus... rogai por nós, pecadores... agora e na hora da nossa morte... Amém."

    prompt_principal = f"""
    Atue como um guia espiritual. Crie um roteiro para um vídeo SHORT do YouTube (máximo 35 segundos de fala).
    Tema do dia: {pilar_do_dia}. Foco: {foco_teologico}. Dirigido a: {persona_prompt}.
    {contexto_eco}
    
    ESTRUTURA OBRIGATÓRIA DO ROTEIRO (GUION):
    1. GANCHO (Início): A primeira frase do vídeo. OBRIGATÓRIO começar com reticências minúsculas ("..."). Ela é o complemento sintático da frase final — juntas formam uma única frase contínua e completa.
    2. ORAÇÃO: Escreva EXATAMENTE esta oração: "{oracao_padrao}"
    3. FRASE DE LOOP (Final): A última frase do vídeo. OBRIGATÓRIO terminar com reticências ("..."). Ela deve ser SINTATICAMENTE INCOMPLETA — uma oração aberta cujo complemento natural é exatamente a frase inicial. O ouvinte não percebe a quebra porque o cérebro une fim e início como uma única frase contínua.

    EXEMPLO DE LOOP SINTÁTICO PERFEITO:
    Final (incompleto): "...é por isso que hoje você precisa receber..."
    Início (complemento): "...a graça que Maria guardou especialmente para você."
    Lidos em sequência formam: "é por isso que hoje você precisa receber a graça que Maria guardou especialmente para você."
    
    REGRAS DE FLUIDEZ:
    - Escreva frases fluidas e naturais. Use reticências (...) para marcar pausas de respiração e emoção.
    - O título deve começar com "Oração Rápida: " seguido do tema, e terminar com a hashtag #Shorts.
    - SEM marcações de tempo, SEM asteriscos, SEM emojis no roteiro.
    
    FORMATO EXATO:
    TITULO: [Oração Rápida: Tema - #Shorts]
    GUION: [Roteiro completo com o efeito loop]
    DESC: [Descrição curta convidando para visitar o canal e as playlists]
    TAGS: [Tags separadas por vírgulas]
    """
    
    texto_ia = None
    for _ in range(3): 
        try:
            texto_ia = client.models.generate_content(model=modelo_usina, contents=prompt_principal).text
            break 
        except: time.sleep(10)
            
    if not texto_ia: continue

    try:
        t_match = re.search(r'T[IÍ]TULO:\s*(.*?)(?=GUI[OÓ]N:|DESC:|TAGS:|$)', texto_ia, re.IGNORECASE | re.DOTALL)
        g_match = re.search(r'GUI[OÓ]N:\s*(.*?)(?=DESC:|TAGS:|T[IÍ]TULO:|$)', texto_ia, re.IGNORECASE | re.DOTALL)
        d_match = re.search(r'DESC:\s*(.*?)(?=TAGS:|T[IÍ]TULO:|GUI[OÓ]N:|$)', texto_ia, re.IGNORECASE | re.DOTALL)
        tg_match = re.search(r'TAGS:\s*(.*?)(?=T[IÍ]TULO:|GUI[OÓ]N:|DESC:|$)', texto_ia, re.IGNORECASE | re.DOTALL)
        
        titulo_final = re.sub(r'[*"\[\]]', '', t_match.group(1)).strip() if t_match else "Oração Rápida #Shorts"
        roteiro_final = g_match.group(1).strip() if g_match else texto_ia 
        desc_final = d_match.group(1).strip() if d_match else "Assista ao vídeo completo no canal!"
        tags_final = re.sub(r'[*\[\]]', '', tg_match.group(1)).strip() if tg_match else "shorts, oração, fé"
        
        nova_linha = [str(data_alvo), horario, "Pronto p/ Áudio", persona, idioma, pilar_do_dia, titulo_final, roteiro_final, tags_final, desc_final, "N/A", "N/A"]
        aba_shorts.update(values=[nova_linha], range_name=f"A{proxima_linha_vazia}:L{proxima_linha_vazia}")
        print(f"   ✅ SUCESSO! Short da linha {proxima_linha_vazia} preenchido.")
        proxima_linha_vazia += 1 
        time.sleep(3)
    except Exception as e: print(f"   ❌ Falha ao salvar: {e}")
