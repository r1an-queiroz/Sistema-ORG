#!/usr/bin/env python3
"""
populate_games.py

Popula o banco MySQL com *todos* os apps listados pela Steam (ISteamApps/GetAppList)
e consulta detalhes via Storefront API (/api/appdetails).
"""

import os
import time
import json
import argparse
import requests
from typing import Dict, Any, Optional, List
from pathlib import Path

from sqlmodel import Session, select, create_engine
from models import Game  # assumindo que models.py define SQLModel Game com campos descritos abaixo

# ------------- CONFIGURAÇÃO -------------
# Use suas credenciais MySQL: (preenchido com root:root conforme solicitado)
DATABASE_URL = os.getenv("DATABASE_URL") or "mysql+pymysql://root:root@127.0.0.1:3306/steamlib"
# pasta para salvar arquivos temporários / progresso
BASE_DIR = Path(__file__).resolve().parent
PROGRESS_FILE = BASE_DIR / "populate_progress.json"
# endpoints Steam
GET_APPLIST_URL = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
APPDETAILS_URL = "https://store.steampowered.com/api/appdetails?appids={appid}&l=english&cc=us"
# parâmetros de runtime
INITIAL_SLEEP = 0.3   # pausa entre requests para appdetails (ajuste se necessário)
MAX_RETRIES = 5
BACKOFF_FACTOR = 1.8

# ------------ UTILITÁRIOS DB --------------
engine = create_engine(DATABASE_URL, echo=False, connect_args={"charset": "utf8mb4"})

def ensure_db():
    # cria tabelas (se ainda não existirem)
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(engine)

def load_progress() -> Dict[str, Any]:
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    return {"next_index": 0, "processed_appids": []}

def save_progress(progress: Dict[str, Any]):
    PROGRESS_FILE.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")

# ------------ STEAM API HELPERS ------------
def fetch_app_list() -> List[Dict[str, Any]]:
    """
    Retorna lista de apps do endpoint GetAppList.
    Response format:
    { "applist": { "apps": [ {"appid": 10, "name":"Counter-Strike"}, ... ] } }
    """
    print("Fetching app list from Steam...")
    r = requests.get(GET_APPLIST_URL, timeout=30)
    r.raise_for_status()
    j = r.json()
    apps = j.get("applist", {}).get("apps", [])
    print(f"Total apps reported by Steam: {len(apps)}")
    return apps

def fetch_app_details(appid: int) -> Optional[Dict[str, Any]]:
    """
    Consulta store api appdetails. Retorna dict com os dados (j['data']) ou None se não disponível.
    """
    url = APPDETAILS_URL.format(appid=appid)
    tries = 0
    while tries < MAX_RETRIES:
        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code != 200:
                # esperar e retry
                tries += 1
                sleep_time = INITIAL_SLEEP * (BACKOFF_FACTOR ** tries)
                print(f"[{appid}] HTTP {resp.status_code} — retry {tries} after {sleep_time:.1f}s")
                time.sleep(sleep_time)
                continue
            j = resp.json()
            # retorno tem formato { "APPID": { "success": true/false, "data": {...} } }
            if str(appid) not in j:
                return None
            info = j[str(appid)]
            if not info.get("success", False):
                return None
            return info.get("data", {})
        except Exception as e:
            tries += 1
            sleep_time = INITIAL_SLEEP * (BACKOFF_FACTOR ** tries)
            print(f"[{appid}] Exception {e} — retry {tries} after {sleep_time:.1f}s")
            time.sleep(sleep_time)
    print(f"[{appid}] Failed after retries")
    return None

# ------------ MAPEAMENTO DOS CAMPOS ------------
def extract_game_fields(appid: int, data: Dict[str, Any]) -> Dict[str, Any]:
    title = data.get("name")
    description = data.get("short_description") or data.get("about_the_game") or data.get("detailed_description") or ""
    header_image = data.get("header_image")  # URL
    is_free = data.get("is_free", False)
    release = data.get("release_date", {})
    release_date = release.get("date") if isinstance(release, dict) else str(release)
    developers = data.get("developers", [])  # list
    publishers = data.get("publishers", [])  # list
    genres = [g.get("description") for g in data.get("genres", [])] if data.get("genres") else []
    price = data.get("price_overview")  # may be None

    return {
        "appid": int(appid),
        "title": title,
        "description": description,
        "header_image": header_image,
        "is_free": bool(is_free),
        "release_date": release_date,
        "developers": json.dumps(developers, ensure_ascii=False),
        "publishers": json.dumps(publishers, ensure_ascii=False),
        "genres": json.dumps(genres, ensure_ascii=False),
        "price_overview": json.dumps(price, ensure_ascii=False) if price else None,
        "raw_json": json.dumps(data, ensure_ascii=False)
    }

# ------------ PRINCIPAL ------------
def main(limit: Optional[int] = None, resume: bool = True):
    ensure_db()
    apps = fetch_app_list()
    progress = load_progress() if resume else {"next_index": 0, "processed_appids": []}
    start_idx = progress.get("next_index", 0)
    total = len(apps)
    print(f"Starting at index {start_idx} / {total}")

    with Session(engine) as session:
        for idx in range(start_idx, total):
            if limit and idx - start_idx >= limit:
                print(f"Limit {limit} reached — stopping early.")
                break

            app = apps[idx]
            appid = int(app.get("appid"))
            name = app.get("name")

            # pular se já processado (resume)
            if appid in progress.get("processed_appids", []):
                print(f"[{idx}/{total}] Skipping {appid} ({name}) — already processed")
                progress["next_index"] = idx + 1
                save_progress(progress)
                continue

            # verificar se já existe no DB
            exists = session.exec(select(Game).where(Game.appid == appid)).first()
            if exists:
                print(f"[{idx}/{total}] Skipping {appid} ({name}) — exists in DB")
                progress.setdefault("processed_appids", []).append(appid)
                progress["next_index"] = idx + 1
                save_progress(progress)
                continue

            print(f"[{idx}/{total}] Fetching details for {appid} ({name})")
            data = fetch_app_details(appid)
            if not data:
                print(f"[{appid}] No details available — saving minimal record")
                g = Game(appid=appid, title=name or f"App {appid}", description="", raw_json="{}")
                session.add(g)
                session.commit()
                progress.setdefault("processed_appids", []).append(appid)
                progress["next_index"] = idx + 1
                save_progress(progress)
                time.sleep(INITIAL_SLEEP)
                continue

            fields = extract_game_fields(appid, data)
            g = Game(
                appid=fields["appid"],
                title=fields["title"],
                description=fields["description"],
                header_image=fields["header_image"],
                is_free=fields["is_free"],
                release_date=fields["release_date"],
                developers=fields["developers"],
                publishers=fields["publishers"],
                genres=fields["genres"],
                price_overview=fields["price_overview"],
                raw_json=fields["raw_json"]
            )
            try:
                session.add(g)
                session.commit()
                print(f"[{appid}] Saved: {fields['title']}")
            except Exception as e:
                session.rollback()
                print(f"[{appid}] DB error: {e} — skipping")
            progress.setdefault("processed_appids", []).append(appid)
            progress["next_index"] = idx + 1
            save_progress(progress)
            time.sleep(INITIAL_SLEEP)

    print("Finished / stopped. Current progress saved to", PROGRESS_FILE)

# ------------ CLI ------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Populate MySQL DB with Steam app data")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of apps to process (for tests)")
    parser.add_argument("--no-resume", dest="resume", action="store_false", help="Don't resume from previous progress")
    args = parser.parse_args()
    main(limit=args.limit, resume=args.resume)