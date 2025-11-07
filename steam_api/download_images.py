# download_images.py
import os
import time
import json
import requests
from pathlib import Path
from sqlmodel import Session, select, create_engine
from models import Game

# ============ CONFIGURAÇÃO ============
DATABASE_URL = os.getenv("DATABASE_URL") or "mysql+pymysql://root:root@127.0.0.1:3306/steamlib"
SAVE_DIR = Path(__file__).resolve().parent / "images"
PROGRESS_FILE = Path(__file__).resolve().parent / "image_progress.json"
MAX_RETRIES = 4
INITIAL_SLEEP = 0.5
BACKOFF_FACTOR = 1.6

SAVE_DIR.mkdir(exist_ok=True)
engine = create_engine(DATABASE_URL, echo=False, connect_args={"charset": "utf8mb4"})

def load_progress():
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    return {"downloaded": []}

def save_progress(progress):
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2, ensure_ascii=False), encoding="utf-8")

def download_image(url: str, appid: int) -> str:
    """Baixa a imagem do jogo e retorna o caminho local salvo."""
    filename = SAVE_DIR / f"{appid}.jpg"
    if filename.exists():
        return str(filename)

    tries = 0
    while tries < MAX_RETRIES:
        try:
            r = requests.get(url, timeout=20)
            if r.status_code == 200 and r.content:
                with open(filename, "wb") as f:
                    f.write(r.content)
                return str(filename)
            else:
                tries += 1
                wait = INITIAL_SLEEP * (BACKOFF_FACTOR ** tries)
                print(f"[{appid}] Erro HTTP {r.status_code}, retry {tries} em {wait:.1f}s")
                time.sleep(wait)
        except Exception as e:
            tries += 1
            wait = INITIAL_SLEEP * (BACKOFF_FACTOR ** tries)
            print(f"[{appid}] Erro {e}, retry {tries} em {wait:.1f}s")
            time.sleep(wait)
    return ""

def main(limit=None):
    progress = load_progress()
    downloaded = set(progress.get("downloaded", []))

    with Session(engine) as session:
        query = select(Game).where(Game.header_image.is_not(None))
        results = session.exec(query).all()

        total = len(results)
        print(f"Jogos encontrados com header_image: {total}")
        count = 0

        for game in results:
            if limit and count >= limit:
                print("Limite atingido, parando.")
                break

            if game.appid in downloaded:
                continue

            if not game.header_image:
                continue

            print(f"Baixando imagem de {game.title} ({game.appid})...")
            local_path = download_image(game.header_image, game.appid)
            if local_path:
                game.local_image_path = local_path
                session.add(game)
                session.commit()
                downloaded.add(game.appid)
                count += 1
                progress["downloaded"] = list(downloaded)
                save_progress(progress)
                print(f"[OK] {game.appid} salvo em {local_path}")
            else:
                print(f"[FALHA] Não foi possível baixar {game.appid}")

            time.sleep(INITIAL_SLEEP)

    print("Download finalizado. Imagens salvas em:", SAVE_DIR)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Baixa imagens dos jogos da Steam.")
    parser.add_argument("--limit", type=int, default=None, help="Limitar quantidade para teste")
    args = parser.parse_args()
    main(limit=args.limit)