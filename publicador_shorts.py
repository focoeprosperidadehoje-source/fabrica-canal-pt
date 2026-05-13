import os, random, re, datetime, time, subprocess, pytz, json, gspread
from google.oauth2.service_account import Credentials
from google.oauth2.credentials import Credentials as YTCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from googleapiclient.discovery import build as build_drive

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

GOOGLE_JSON = os.environ.get("GOOGLE_CREDENTIALS_PT")
# PUXANDO A CHAVE EXCLUSIVA DOS SHORTS PARA NÃO GASTAR A COTA PRINCIPAL
YT_TOKEN_JSON = os.environ.get("YOUTUBE_TOKEN_PT_SHORTS")
HORARIO_ALVO = os.environ.get("HORARIO_ALVO")

print(f"🚀 INICIANDO SERVIDOR MATRIX SHORTS PARA: {HORARIO_ALVO}")

credenciais_dict = json.loads(GOOGLE_JSON)
creds_sheets = Credentials.from_service_account_info(credenciais_dict, scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'])
gc = gspread.authorize(creds_sheets)

aba_shorts = gc.open_by_key("1KgIjWrLUVlllhlZB1R9fkHGxxZlLsax1aOVGZrYwgnU").worksheet("PT_SHORTS")

creds_yt = YTCredentials.from_authorized_user_info(json.loads(YT_TOKEN_JSON))
if creds_yt and creds_yt.expired and creds_yt.refresh_token: creds_yt.refresh(Request())
youtube = build('youtube', 'v3', credentials=creds_yt)
drive_service = build_drive('drive', 'v3', credentials=creds_sheets)

PASTA_TEMP = "/tmp/fabrica_shorts"
os.makedirs(PASTA_TEMP, exist_ok=True)

# IDs DAS PASTAS VERTICAIS
ID_PASTA_JESUS_VERT = "1Xzw7URlFGoMqpMyfOycOpZpnUoX2KmGq"
ID_PASTA_MARIA_APARECIDA_VERT = "1isunRtA4zPkei2sDiTi5VZic1tc3e5gD"
ID_PASTA_MUSICAS = "1gxZA1TlQPzuf737XOo_n8blfOThnddgm"

def baixar_arquivo(file_id, destino):
    request = drive_service.files().get_media(fileId=file_id)
    with open(destino, 'wb') as f: f.write(request.execute())
    return destino

def listar_arquivos(folder_id, extensoes=None):
    res =[]
    page_token = None
    while True:
        try:
            response = drive_service.files().list(q=f"'{folder_id}' in parents and trashed=false", spaces='drive', fields='nextPageToken, files(id, name)', pageToken=page_token).execute()
            for f in response.get('files',[]):
                if extensoes:
                    if f['name'].lower().endswith(extensoes): res.append(f)
                else: res.append(f)
            page_token = response.get('nextPageToken', None)
            if not page_token: break
        except: break
    return res

def obter_duracao(arquivo):
    try: return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', arquivo], capture_output=True, text=True).stdout.strip())
    except: return 60 

dados = aba_shorts.get_all_records()
col_status = aba_shorts.row_values(1).index('Status') + 1

for index, linha in enumerate(dados, start=2):
    if str(linha.get('Status', '')).strip() == 'Pronto p/ Áudio' and str(linha.get('Horario', '')).strip() == HORARIO_ALVO:
        data_str, horario_str, titulo, descricao_ia, tags_str, persona, roteiro = str(linha.get('Data', '')), str(linha.get('Horario', '')), str(linha.get('Titulo', '')), str(linha.get('Descricao', '')), str(linha.get('Tags', '')), str(linha.get('Personagem', '')).upper(), str(linha.get('Roteiro', ''))
        
        print(f"🎬 INICIANDO SHORT: Linha {index} - {persona} às {horario_str}")
        
        # LÓGICA DE APARECIDA O ANO TODO PARA SHORTS
        id_pasta_img = ID_PASTA_JESUS_VERT if persona == 'JESUS' else ID_PASTA_MARIA_APARECIDA_VERT
        voz_escolhida = "pt-BR-AntonioNeural" if persona == 'JESUS' else "pt-BR-FranciscaNeural"
        
        print("   📥 Baixando imagens verticais...")
        arquivos_img = listar_arquivos(id_pasta_img, ('.jpg', '.jpeg', '.png'))
        if not arquivos_img: continue
        
        random.shuffle(arquivos_img)
        imgs_locais = [baixar_arquivo(arquivos_img[i]['id'], f"{PASTA_TEMP}/img_{i}.jpg") for i in range(min(6, len(arquivos_img)))]
        
        arquivos_musica = listar_arquivos(ID_PASTA_MUSICAS, ('.mp3', '.wav'))
        musica_local = baixar_arquivo(random.choice(arquivos_musica)['id'], f"{PASTA_TEMP}/musica.mp3")

        caminho_mp3, caminho_txt = f"{PASTA_TEMP}/audio.mp3", f"{PASTA_TEMP}/roteiro.txt"
        with open(caminho_txt, "w", encoding="utf-8") as f: f.write(roteiro.replace('*', '').replace('_', '').replace('"', ''))
            
        print(f"   🎙️ Gerando Voz Neural ({voz_escolhida})...")
        subprocess.run(["edge-tts", "--voice", voz_escolhida, "--rate=-10%", "--file", caminho_txt, "--write-media", caminho_mp3], capture_output=True)
        duracao_audio = obter_duracao(caminho_mp3)

        print("   🎞️ Fabricando blocos visuais verticais (1080x1920)...")
        tempo_acumulado = 0
        lista_ts =[]
        contador_chunk = 0
        
        while tempo_acumulado < duracao_audio:
            arquivo_ts = f"{PASTA_TEMP}/chunk_{contador_chunk}.ts"
            duracao_padrao = random.randint(6, 9)
            ativo = random.choice(imgs_locais)
            
            efeito_zoom = random.choice(['in', 'out'])
            zoom_cmd = "zoompan=z='1.0+0.0008*on':d=400:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920:fps=24" if efeito_zoom == 'in' else "zoompan=z='1.15-0.0008*on':d=400:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920:fps=24"
            
            subprocess.run(f'ffmpeg -y -loop 1 -framerate 24 -i "{ativo}" -t {duracao_padrao} -vf "scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,{zoom_cmd}" -c:v libx264 -preset ultrafast -pix_fmt yuv420p -an "{arquivo_ts}"', shell=True, capture_output=True)
            
            tempo_acumulado += duracao_padrao
            lista_ts.append(arquivo_ts)
            contador_chunk += 1

        print("   🔥 Mixando Áudio e finalizando o Short...")
        arquivo_concat = f"{PASTA_TEMP}/concat.txt"
        with open(arquivo_concat, "w") as f:
            for ts in lista_ts: f.write(f"file '{ts}'\n")
        video_mudo = f"{PASTA_TEMP}/mudo.mp4"
        subprocess.run(f'ffmpeg -y -f concat -safe 0 -i "{arquivo_concat}" -c copy "{video_mudo}"', shell=True, capture_output=True)

        video_final = f"{PASTA_TEMP}/final_short.mp4"
        subprocess.run(f'ffmpeg -y -i "{video_mudo}" -i "{caminho_mp3}" -stream_loop -1 -i "{musica_local}" -filter_complex "[1:a]apad[v_pad];[2:a]volume=0.15[bgm];[v_pad][bgm]amix=inputs=2:duration=longest[aout]" -map 0:v -map "[aout]" -c:v copy -c:a aac -b:a 192k -t {duracao_audio} "{video_final}"', shell=True, capture_output=True)

        tags_limpas = re.sub(r'[^a-zA-Z0-9áéíóúÁÉÍÓÚçÇ ,]', '', tags_str)
        tags_lista = [t.strip()[:30] for t in tags_limpas.split(',') if t.strip()][:15]
        
        texto_convite = "\n\n🙏 Assista à oração completa e profunda no nosso canal! Clique no link do vídeo relacionado na tela.\n\nNossas Playlists:\nOrações da Manhã: https://www.youtube.com/playlist?list=PLELsEoZ8x93SsNmSh6Wgbjn4daTH6SXjx\nOrações para Dormir: https://www.youtube.com/playlist?list=PLELsEoZ8x93SAjUNUtpBV08zQn4xExhD9"
        
        try: 
            agora_br = datetime.datetime.now(pytz.timezone('America/Sao_Paulo'))
            data_hora_alvo = pytz.timezone('America/Sao_Paulo').localize(datetime.datetime.strptime(f"{data_str} {horario_str}", "%Y-%m-%d %H:%M"))
            publish_at = data_hora_alvo.isoformat() if data_hora_alvo > agora_br else None
        except: publish_at = None
        
        body = {"snippet": {"title": titulo[:100], "description": f"{descricao_ia}{texto_convite}", "tags": tags_lista, "categoryId": "22", "defaultLanguage": "pt-BR", "defaultAudioLanguage": "pt-BR"}, "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False}}
        if publish_at: body["status"]["publishAt"] = publish_at
        
        for tentativa in range(3):
            try:
                video_id = youtube.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(video_final, chunksize=-1, resumable=True, mimetype="video/mp4")).execute().get("id")
                print(f"   🎉 SUCESSO! Short {video_id} publicado.")
                
                try:
                    pid = "PLELsEoZ8x93QGBWUutLm405W5FccVsSGa" if persona == 'JESUS' else "PLELsEoZ8x93Tc4W1A3tGZdU2JF_x1LCeL"
                    youtube.playlistItems().insert(part="snippet", body={"snippet": {"playlistId": pid, "resourceId": {"kind": "youtube#video", "videoId": video_id}}}).execute()
                except Exception as e: print(f"   ⚠️ Aviso: Não foi possível adicionar à playlist: {e}")
                
                aba_shorts.update_cell(index, col_status, 'Publicado')
                break
            except Exception as e: 
                print(f"   ❌ Erro no YouTube (Tentativa {tentativa+1}/3): {e}")
                time.sleep(15)
        break 

print("\n🚀 SERVIDOR MATRIX SHORTS DESLIGANDO.")
