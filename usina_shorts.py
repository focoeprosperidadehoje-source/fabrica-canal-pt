import os
import sys
import json
import time
import re
import datetime
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
GRADE_SHORTS =[
    {"horario": "08:00", "personagem": "Jesus", "idioma": "PT", "foco": "Manhã: Direção para o dia."},
    {"horario": "13:00", "personagem": "Maria", "idioma": "PT", "foco": "Meio-dia: Causas impossíveis."},
    {"horario": "19:00", "personagem": "Maria", "idioma": "PT", "foco": "Entardecer: Paz no lar."},
    {"horario": "22:00", "personagem": "Jesus", "idioma": "PT", "foco": "Noite: Dormir em paz."}
]

aba = gc.open_by_key(ID_PLANILHA).worksheet("PT_SHORTS")

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
                if d_obj not in dias_existentes: dias_existentes[d_obj] =[]
                dias_existentes[d_obj].append(h_str)
        except: pass

meta_estoque = hoje + datetime.timedelta(days=5) 
data_alvo = None
grade_para_processar =[]

data_check = limite_passado
while data_check <= meta_estoque:
    horarios_presentes = dias_existentes.get(data_check,[])
    if len(horarios_presentes) < 4:
        data_alvo = data_check
        grade_para_processar = [v for v in GRADE_SHORTS if v["horario"] not in horarios_presentes]
        break
    data_check += datetime.timedelta(days=1)

if not data_alvo:
    print(f"✅ ESTOQUE DE SHORTS ATINGIDO até {meta_estoque}. Dormindo.")
    sys.exit(0)

pilar_do_dia = PILARES[data_alvo.weekday()]
print(f"\n📅 DATA ALVO SHORTS: {data_alvo} | Pilar: {pilar_do_dia}")

for video in grade_para_processar:
    horario, persona, idioma, foco_teologico = video["horario"], video["personagem"].upper(), video["idioma"], video["foco"]
    print(f"🎬 PRODUZINDO SHORT: {horario} | {persona}")
    
    persona_prompt = "Jesus Cristo" if persona == 'JESUS' else "Nossa Senhora Aparecida"
    oracao_padrao = "Pai Nosso que estais nos céus, santificado seja o vosso nome. Venha a nós o vosso reino, seja feita a vossa vontade, assim na terra como no céu. O pão nosso de cada dia nos dai hoje. Perdoai-nos as nossas ofensas, assim como nós perdoamos a quem nos tem ofendido. E não nos deixeis cair em tentação, mas livrai-nos do mal. Amém." if persona == 'JESUS' else "Ave Maria, cheia de graça, o Senhor é convosco. Bendita sois vós entre as mulheres, e bendito é o fruto do vosso ventre, Jesus. Santa Maria, Mãe de Deus, rogai por nós, pecadores, agora e na hora da nossa morte. Amém."

    prompt_principal = f"""
    Atue como um guia espiritual. Crie um roteiro para um vídeo SHORT do YouTube (máximo 45 segundos de fala).
    Tema do dia: {pilar_do_dia}. Foco: {foco_teologico}. Dirigido a: {persona_prompt}.
    
    ESTRUTURA OBRIGATÓRIA DO ROTEIRO (GUION):
    1. GANCHO (Início): A primeira frase do vídeo. DEVE ser a continuação lógica da frase final do vídeo.
    2. ORAÇÃO: Escreva EXATAMENTE esta oração: "{oracao_padrao}"
    3. FRASE DE LOOP (Final): A última frase do vídeo. DEVE deixar um gancho gramatical que se conecte perfeitamente com a primeira frase do vídeo.
    
    EXEMPLO DE EFEITO LOOP PERFEITO:
    Final do vídeo (Frase de Loop): "Por isso, feche os olhos e receba..."
    Início do vídeo (Gancho): "...a paz que só Deus pode te dar nesta hora."
    (Quando o vídeo repete automaticamente, o espectador ouve a frase contínua: "Por isso, feche os olhos e receba a paz que só Deus pode te dar nesta hora.")
    
    REGRAS:
    - O título deve ser chamativo e ter a hashtag #Shorts no final.
    - SEM marcações de tempo, SEM asteriscos, SEM emojis no roteiro.
    
    FORMATO EXATO:
    TITULO: [Título magnético - #Shorts]
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
        
        titulo_final = re.sub(r'[*"\[\]]', '', t_match.group(1)).strip() if t_match else "Oração Poderosa #Shorts"
        roteiro_final = g_match.group(1).strip() if g_match else texto_ia 
        desc_final = d_match.group(1).strip() if d_match else "Visite nosso canal para orações completas!"
        tags_final = re.sub(r'[*\[\]]', '', tg_match.group(1)).strip() if tg_match else "shorts, oração, fé"
        
        nova_linha = [str(data_alvo), horario, "Pronto p/ Áudio", persona, idioma, pilar_do_dia, titulo_final, roteiro_final, tags_final, desc_final, "N/A", "N/A"]
        aba.update(values=[nova_linha], range_name=f"A{proxima_linha_vazia}:L{proxima_linha_vazia}")
        print(f"   ✅ SUCESSO! Short da linha {proxima_linha_vazia} preenchido.")
        proxima_linha_vazia += 1 
        time.sleep(3)
    except Exception as e: print(f"   ❌ Falha ao salvar: {e}")
