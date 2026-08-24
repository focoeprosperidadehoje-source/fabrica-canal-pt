import os, json, time, datetime, gspread
from google.oauth2.service_account import Credentials
from google.oauth2.credentials import Credentials as YTCredentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.genai import Client

GOOGLE_JSON = os.environ.get("GOOGLE_CREDENTIALS_PT")
YT_TOKEN_JSON = os.environ.get("YOUTUBE_TOKEN_PT")
CHAVE_API_GEMINI = os.environ.get("GEMINI_API_KEY", "")
CHAVE_API_GEMINI_2 = os.environ.get("GEMINI_API_KEY_2", "")
CHAVES_GEMINI = [k for k in [CHAVE_API_GEMINI, CHAVE_API_GEMINI_2] if k]

MAX_RESPOSTAS = 30  # cap de segurança: 30 × 4 execuções × 4 canais = 480 chamadas Gemini/dia

creds_sheets = Credentials.from_service_account_info(json.loads(GOOGLE_JSON), scopes=['https://www.googleapis.com/auth/spreadsheets'])
gc = gspread.authorize(creds_sheets)
configs = gc.open_by_key("1KgIjWrLUVlllhlZB1R9fkHGxxZlLsax1aOVGZrYwgnU").worksheet("Configuracoes").get_all_records()

creds_yt = YTCredentials.from_authorized_user_info(json.loads(YT_TOKEN_JSON))
if creds_yt and creds_yt.expired and creds_yt.refresh_token: creds_yt.refresh(Request())
youtube = build('youtube', 'v3', credentials=creds_yt)
gemini_client = Client(api_key=CHAVES_GEMINI[0], http_options={'api_version': 'v1'})

def _gerar_comunidade(prompt):
    for chave in CHAVES_GEMINI:
        try:
            c = Client(api_key=chave, http_options={'api_version': 'v1'})
            return c.models.generate_content(model=modelo_comunidade, contents=prompt).text.strip()
        except Exception as e:
            if "429" in str(e) and chave != CHAVES_GEMINI[-1]:
                print(f"[WARN] 429 na chave ...{chave[-6:]}. Tentando chave 2...")
                continue
            raise
    raise RuntimeError("Todas as chaves Gemini falharam.")

def obter_modelo_lite():
    # gemini-2.5-flash-lite: free tier, 15 RPM, ~1000 RPD por projeto
    try:
        modelos = gemini_client.models.list()
        nomes = [m.name for m in modelos if 'generateContent' in m.supported_generation_methods]
        for preferido in ['gemini-2.5-flash-lite', 'gemini-3.5-flash-lite', 'gemini-3.1-flash-lite']:
            if any(preferido in n for n in nomes):
                return preferido
        return 'gemini-2.5-flash-lite'
    except:
        return 'gemini-2.5-flash-lite'

modelo_comunidade = obter_modelo_lite()
print(f"🤖 Modelo de IA selecionado para a Comunidade: {modelo_comunidade}")

canal_response = youtube.channels().list(part='id,contentDetails', mine=True).execute()
MEU_CANAL_ID = canal_response['items'][0]['id']
UPLOADS_PLAYLIST_ID = canal_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

LINK_LIVE = f"https://www.youtube.com/channel/{MEU_CANAL_ID}/live"

# ── HABILITAR COMENTÁRIOS (vídeos das últimas 72h) ───────────────────────────
print("🔓 HABILITANDO COMENTÁRIOS nos vídeos recentes...")
try:
    limite_72h = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=72)
    video_ids_72h = []
    page_token_72 = None
    for _ in range(2):
        resp = youtube.playlistItems().list(
            part='snippet', playlistId=UPLOADS_PLAYLIST_ID,
            maxResults=50, pageToken=page_token_72
        ).execute()
        for item in resp.get('items', []):
            pub = item['snippet'].get('publishedAt', '')
            try:
                pt = datetime.datetime.strptime(pub, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
                if pt >= limite_72h:
                    video_ids_72h.append(item['snippet']['resourceId']['videoId'])
            except: pass
        page_token_72 = resp.get('nextPageToken')
        if not page_token_72: break
    for vid in video_ids_72h:
        try:
            youtube.videos().update(
                part="status",
                body={"id": vid, "status": {"selfDeclaredMadeForKids": False, "selfDeclaredMadeWithAlteredContent": True}}
            ).execute()
            print(f"   🔓 Status atualizado: {vid}")
            time.sleep(1)
        except Exception as e:
            print(f"   ⚠️ Não foi possível atualizar {vid}: {e}")
except Exception as e:
    print(f"⚠️ Habilitar comentários: {e}")

# ── VENDEDOR ─────────────────────────────────────────────────────────────────
print("\n💰 INICIANDO O VENDEDOR (COMENTÁRIOS FIXADOS)")
texto_fixo = next((str(c.get('Texto Fixo', c.get('Texto_Fixo', ''))) for c in configs if str(c.get('Idioma', '')).upper() == 'PT'), "")

if texto_fixo:
    limite_24h = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)
    video_ids = []
    page_token_up = None
    for _ in range(4):
        resp_up = youtube.playlistItems().list(
            part='snippet', playlistId=UPLOADS_PLAYLIST_ID,
            maxResults=50, pageToken=page_token_up
        ).execute()
        video_ids += [item['snippet']['resourceId']['videoId'] for item in resp_up.get('items', [])]
        page_token_up = resp_up.get('nextPageToken')
        if not page_token_up: break

    if video_ids:
        videos_req = youtube.videos().list(part='snippet', id=','.join(video_ids[:50])).execute()
        for video in videos_req.get('items', []):
            v_id, v_titulo = video['id'], video['snippet']['title']
            pub_time = datetime.datetime.strptime(video['snippet']['publishedAt'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
            if pub_time >= limite_24h:
                try:
                    comentarios = youtube.commentThreads().list(part='snippet', videoId=v_id, maxResults=100).execute()
                    if not any(t['snippet']['topLevelComment']['snippet'].get('authorChannelId', {}).get('value') == MEU_CANAL_ID for t in comentarios.get('items', [])):
                        if "#shorts" in v_titulo.lower():
                            comentario_final = f"{texto_fixo}\n\n🙏 Que esta oração rápida abençoe seu dia! Convidamos você a visitar nosso canal para fazer as orações completas.\n\nNossas Playlists:\n🌅 Orações da Manhã: https://www.youtube.com/playlist?list=PLELsEoZ8x93SsNmSh6Wgbjn4daTH6SXjx\n🌌 Orações para Dormir: https://www.youtube.com/playlist?list=PLELsEoZ8x93SAjUNUtpBV08zQn4xExhD9"
                        else:
                            link_playlist = "https://www.youtube.com/playlist?list=PLELsEoZ8x93TNhv-zv2LQq3ghOl42D3Ln"
                            if "manhã" in v_titulo.lower(): link_playlist = "https://www.youtube.com/playlist?list=PLELsEoZ8x93SsNmSh6Wgbjn4daTH6SXjx"
                            elif "noite" in v_titulo.lower() or "dormir" in v_titulo.lower(): link_playlist = "https://www.youtube.com/playlist?list=PLELsEoZ8x93SAjUNUtpBV08zQn4xExhD9"
                            comentario_final = f"{texto_fixo}\n\nContinue orando conosco aqui: {link_playlist}\n\n🔴 AO VIVO AGORA — 24h: seus pedidos e os nomes de seus entes queridos são mencionados em oração contínua. Junte-se: {LINK_LIVE}"
                        youtube.commentThreads().insert(part="snippet", body={"snippet": {"videoId": v_id, "topLevelComment": {"snippet": {"textOriginal": comentario_final}}}}).execute()
                        print(f"   ✅ Comentário postado no vídeo: {v_titulo[:30]}")
                        time.sleep(2)
                except Exception as e:
                    print(f"   ⚠️ Erro ao comentar em {v_id}: {e}")

# ── PASTOR DIGITAL ────────────────────────────────────────────────────────────
print("\n🕊️ INICIANDO O PASTOR DIGITAL (RESPOSTAS PERSONALIZADAS)")
try:
    respondidos = 0
    page_token_t = None
    for _pagina in range(10):  # até 1000 threads por execução
        if respondidos >= MAX_RESPOSTAS:
            print(f"   ℹ️ Cap de {MAX_RESPOSTAS} respostas atingido — próxima execução continua.")
            break
        threads_resp = youtube.commentThreads().list(
            part="snippet,replies",
            allThreadsRelatedToChannelId=MEU_CANAL_ID,
            maxResults=100,
            pageToken=page_token_t
        ).execute()
        for thread in threads_resp.get('items', []):
            if respondidos >= MAX_RESPOSTAS:
                break
            top = thread['snippet']['topLevelComment']['snippet']
            autor_id = top.get('authorChannelId', {}).get('value')
            if autor_id == MEU_CANAL_ID:
                continue
            ja_respondi = any(
                r['snippet'].get('authorChannelId', {}).get('value') == MEU_CANAL_ID
                for r in thread.get('replies', {}).get('comments', [])
            )
            if not ja_respondi:
                nome  = top.get('authorDisplayName', 'Irmão(ã)')
                texto = top.get('textOriginal', '')
                prompt = (
                    f"Atue como pastor digital católico empático. Um usuário chamado '{nome}' comentou: '{texto}'. "
                    f"REGRA 1 (HATERS): Se for comentário de ódio ou crítica ao uso de IA/imagens, responda com extrema polidez, respeitando diferenças e focando no amor de Deus. "
                    f"REGRA 2 (FIÉIS): Se for pedido de oração, desabafo ou agradecimento, responda de forma ALTAMENTE PERSONALIZADA. Cite a dor/situação da pessoa e ofereça palavra de conforto ou oração específica. "
                    f"Se mencionar doença, sofrimento ou intercessão, convide organicamente para nossa transmissão 24/7: {LINK_LIVE} "
                    f"Máximo 3-4 linhas. Tom acolhedor e humano. SEM aspas."
                )
                try:
                    resposta = _gerar_comunidade(prompt)
                    youtube.comments().insert(
                        part="snippet",
                        body={"snippet": {"parentId": thread['id'], "textOriginal": resposta}}
                    ).execute()
                    print(f"   ✅ Respondido a {nome}")
                    respondidos += 1
                    time.sleep(3)
                except Exception as e:
                    print(f"   ⚠️ Erro ao responder {nome}: {e}")
        page_token_t = threads_resp.get('nextPageToken')
        if not page_token_t:
            break
    print(f"   Total respondido nesta execução: {respondidos}")
except Exception as e:
    print(f"⚠️ PASTOR DIGITAL erro geral: {e}")
print("🚀 ESTÁGIO 6 CONCLUÍDO!")
