import os, json, time, datetime, gspread
from google.oauth2.service_account import Credentials
from google.oauth2.credentials import Credentials as YTCredentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.genai import Client

GOOGLE_JSON = os.environ.get("GOOGLE_CREDENTIALS_PT")
YT_TOKEN_JSON = os.environ.get("YOUTUBE_TOKEN_PT")
CHAVE_API_GEMINI = os.environ.get("GEMINI_API_KEY")

creds_sheets = Credentials.from_service_account_info(json.loads(GOOGLE_JSON), scopes=['https://www.googleapis.com/auth/spreadsheets'])
gc = gspread.authorize(creds_sheets)
configs = gc.open_by_key("1KgIjWrLUVlllhlZB1R9fkHGxxZlLsax1aOVGZrYwgnU").worksheet("Configuracoes").get_all_records()

creds_yt = YTCredentials.from_authorized_user_info(json.loads(YT_TOKEN_JSON))
if creds_yt and creds_yt.expired and creds_yt.refresh_token: creds_yt.refresh(Request())
youtube = build('youtube', 'v3', credentials=creds_yt)
gemini_client = Client(api_key=CHAVE_API_GEMINI, http_options={'api_version': 'v1'})

# CAÇADOR DE FLASH-LITE (Para economizar cota)
def obter_modelo_lite():
    try:
        modelos = gemini_client.models.list()
        lite_models =[m.name for m in modelos if 'generateContent' in m.supported_generation_methods and 'flash-lite' in m.name]
        return sorted(lite_models, reverse=True)[0] if lite_models else 'gemini-2.5-flash'
    except:
        return 'gemini-2.5-flash-lite'

modelo_comunidade = obter_modelo_lite()
print(f"🤖 Modelo de IA selecionado para a Comunidade: {modelo_comunidade}")

canal_response = youtube.channels().list(part='id,contentDetails', mine=True).execute()
MEU_CANAL_ID = canal_response['items'][0]['id']
UPLOADS_PLAYLIST_ID = canal_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

print("💰 INICIANDO O VENDEDOR (COMENTÁRIOS FIXADOS)")
texto_fixo = next((str(c.get('Texto Fixo', c.get('Texto_Fixo', ''))) for c in configs if str(c.get('Idioma', '')).upper() == 'PT'), "")

if texto_fixo:
    limite_24h = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)
    playlist_req = youtube.playlistItems().list(part='snippet', playlistId=UPLOADS_PLAYLIST_ID, maxResults=15).execute()
    video_ids = [item['snippet']['resourceId']['videoId'] for item in playlist_req.get('items',[])]
    
    if video_ids:
        videos_req = youtube.videos().list(part='snippet', id=','.join(video_ids)).execute()
        for video in videos_req.get('items',[]):
            v_id, v_titulo = video['id'], video['snippet']['title']
            pub_time = datetime.datetime.strptime(video['snippet']['publishedAt'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
            
            if pub_time >= limite_24h:
                try:
                    comentarios = youtube.commentThreads().list(part='snippet', videoId=v_id, maxResults=100).execute()
                    if not any(t['snippet']['topLevelComment']['snippet'].get('authorChannelId', {}).get('value') == MEU_CANAL_ID for t in comentarios.get('items',[])):
                        
                        # RADAR DE SHORTS: Define o texto do comentário fixado
                        if "#shorts" in v_titulo.lower():
                            comentario_final = f"{texto_fixo}\n\n🙏 Que esta oração rápida abençoe seu dia! Convidamos você a visitar nosso canal para fazer as orações completas.\n\nNossas Playlists:\n🌅 Orações da Manhã: https://www.youtube.com/playlist?list=PLELsEoZ8x93SsNmSh6Wgbjn4daTH6SXjx\n🌌 Orações para Dormir: https://www.youtube.com/playlist?list=PLELsEoZ8x93SAjUNUtpBV08zQn4xExhD9"
                        else:
                            link_playlist = "https://www.youtube.com/playlist?list=PLELsEoZ8x93TNhv-zv2LQq3ghOl42D3Ln" 
                            if "manhã" in v_titulo.lower(): link_playlist = "https://www.youtube.com/playlist?list=PLELsEoZ8x93SsNmSh6Wgbjn4daTH6SXjx"
                            elif "noite" in v_titulo.lower() or "dormir" in v_titulo.lower(): link_playlist = "https://www.youtube.com/playlist?list=PLELsEoZ8x93SAjUNUtpBV08zQn4xExhD9"
                            comentario_final = f"{texto_fixo}\n\nContinue orando conosco aqui: {link_playlist}"
                        
                        youtube.commentThreads().insert(part="snippet", body={"snippet": {"videoId": v_id, "topLevelComment": {"snippet": {"textOriginal": comentario_final}}}}).execute()
                        print(f"   ✅ Comentário fixado postado no vídeo: {v_titulo[:30]}")
                        time.sleep(2)
                except: pass

print("\n🕊️ INICIANDO O PASTOR DIGITAL (COM CURTIDAS E RESPOSTAS PERSONALIZADAS)")
try:
    threads = youtube.commentThreads().list(part="snippet,replies", allThreadsRelatedToChannelId=MEU_CANAL_ID, maxResults=20).execute()
    for thread in threads.get('items',[]):
        top = thread['snippet']['topLevelComment']['snippet']
        comentario_id = thread['snippet']['topLevelComment']['id']
        
        if top.get('authorChannelId', {}).get('value') == MEU_CANAL_ID: continue
        
        # CURTIR O COMENTÁRIO (Coraçãozinho)
        try: youtube.comments().rate(id=comentario_id, rating='like').execute()
        except: pass
        
        ja_respondi = any(r['snippet'].get('authorChannelId', {}).get('value') == MEU_CANAL_ID for r in thread.get('replies', {}).get('comments',[]))
        if not ja_respondi:
            nome, texto = top.get('authorDisplayName', 'Irmão(ã)'), top.get('textOriginal', '')
            
            prompt = f"""Atue como um pastor digital católico empático. Um usuário chamado '{nome}' comentou: '{texto}'. 
            REGRA 1 (HATERS): Se for um comentário de ódio, intolerância religiosa ou crítica ao uso de imagens, responda com extrema polidez, dizendo que respeitamos as diferenças, pedindo para focar no amor de Deus e ignorar as pequenas coisas.
            REGRA 2 (FIÉIS): Se for um pedido de oração, desabafo ou agradecimento, responda de forma ALTAMENTE PERSONALIZADA. Cite a dor ou situação que a pessoa mencionou e ofereça uma palavra de conforto ou oração específica para o caso dela.
            Máximo 3 a 4 linhas. Tom acolhedor e humano. SEM aspas."""
            
            try:
                resposta = gemini_client.models.generate_content(model=modelo_comunidade, contents=prompt).text.strip()
                youtube.comments().insert(part="snippet", body={"snippet": {"parentId": thread['id'], "textOriginal": resposta}}).execute()
                print(f"   ✅ Respondido e Curtido: {nome}")
                time.sleep(3)
            except: pass
except: pass
print("🚀 ESTÁGIO 6 CONCLUÍDO!")
