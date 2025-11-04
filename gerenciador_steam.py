# gerenciador_steam_tk_full.py
import os
import shutil
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
from tkinter import ttk
from datetime import datetime
import getpass
import threading
import io

# Dependências opcionais
try:
    import requests
except Exception:
    requests = None

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

# fpdf2
try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except Exception:
    FPDF_AVAILABLE = False

# ---------- Configuração de paths (Documentos) ----------
def get_documents_path():
    home = os.path.expanduser("~")
    return os.path.join(home, "Documents" if os.name == "nt" else "Documentos")

BASE_DIR = os.path.join(get_documents_path(), "steam_files")
EMPRESA_DIR = os.path.join(BASE_DIR, "Empresa")
USUARIOS_DIR = os.path.join(BASE_DIR, "Usuarios")
JOGOS_DIR = os.path.join(EMPRESA_DIR, "Jogos")
DOCS_DIR = os.path.join(EMPRESA_DIR, "Documentos")
LOGS_DIR = os.path.join(EMPRESA_DIR, "Logs")
LOG_FILE = os.path.join(LOGS_DIR, "Log_Sistema.txt")
IMAGES_DIR = os.path.join(EMPRESA_DIR, "Imagens_Jogos")  # backup/central images folder

# ---------- Lista de 50 jogos reais e APP IDs (para header images da Steam) ----------
# OBS: os app ids não precisam estar 100% corretos para todos, mas usamos IDs conhecidos para a maioria.
GAMES = [
    ("Counter-Strike 2", 1523900),
    ("Dota 2", 570),
    ("PUBG: Battlegrounds", 578080),
    ("Apex Legends", 1172470),
    ("Rust", 252490),
    ("GTA V", 271590),
    ("Cyberpunk 2077", 1091500),
    ("The Witcher 3", 292030),
    ("Elden Ring", 1245620),
    ("Baldur's Gate 3", 1086940),
    ("Hades", 1145360),
    ("Stardew Valley", 413150),
    ("Terraria", 105600),
    ("ARK: Survival Evolved", 346110),
    ("Palworld", 1623730),
    ("Phasmophobia", 739630),
    ("DayZ", 221100),
    ("Rainbow Six Siege", 359550),
    ("Red Dead Redemption 2", 1174180),
    ("Lethal Company", 1966720),
    ("Sea of Thieves", 1172620),
    ("The Forest", 242760),
    ("The Sims 4", 1222670),
    ("Left 4 Dead 2", 550),
    ("Half-Life 2", 220),
    ("Portal 2", 620),
    ("CS:GO", 730),
    ("Starfield", 1716740),
    ("Valheim", 892970),
    ("Fallout 4", 377160),
    ("No Man's Sky", 275850),
    ("Forza Horizon 5", 1551360),
    ("Dead by Daylight", 381210),
    ("The Binding of Isaac", 250900),
    ("Call of Duty: Warzone", 1962663),
    ("Destiny 2", 1085660),
    ("Overwatch 2", 2357570),
    ("Team Fortress 2", 440),
    ("Euro Truck Simulator 2", 227300),
    ("Among Us", 945360),
    ("Slime Rancher", 433340),
    ("Celeste", 504230),
    ("Dark Souls III", 374320),
    ("Sekiro: Shadows Die Twice", 814380),
    ("Resident Evil 4", 2050650),
    ("Resident Evil Village", 1196590),
    ("Hollow Knight", 367520),
    ("Mass Effect Legendary Edition", 1328670),
    ("Subnautica", 264710),
    ("DOOM Eternal", 782330)
]

STEAM_HEADER_URL = "https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg"

# ---------- Logging pequeno ----------
def registrar_log(msg):
    os.makedirs(LOGS_DIR, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

# ---------- Helpers para nomes de arquivos seguros ----------
def safe_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in " ._-()" else "_" for c in name).strip()

# ---------- Função para baixar imagem e salvar como PNG (quando possível) ----------
def download_and_prepare_image(game_name: str, appid: int):
    if not requests:
        registrar_log(f"Requests não disponível — não foi possível baixar imagem para {game_name}")
        return None

    url = STEAM_HEADER_URL.format(appid=appid)
    pasta = os.path.join(JOGOS_DIR, safe_name(game_name))
    os.makedirs(pasta, exist_ok=True)
    png_path = os.path.join(pasta, f"{safe_name(game_name)}.png")
    jpg_temp_path = os.path.join(pasta, f"{safe_name(game_name)}.jpg")

    # Se já existe PNG, mantemos
    if os.path.exists(png_path):
        return png_path

    try:
        resp = requests.get(url, timeout=12)
        if resp.status_code == 200 and resp.content:
            # se PIL disponível, converte para PNG (garante compatibilidade com Tkinter)
            if PIL_AVAILABLE:
                try:
                    img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                    img.save(png_path, format="PNG")
                    registrar_log(f"Imagem baixada e convertida (PNG): {game_name}")
                    return png_path
                except Exception as e:
                    # fallback salvar jpg
                    with open(jpg_temp_path, "wb") as f:
                        f.write(resp.content)
                    registrar_log(f"PIL falhou convertendo imagem de {game_name}: {e} — salvo como JPG")
                    return jpg_temp_path
            else:
                # sem PIL, salvamos como JPG e retorno (Tkinter pode ou não abrir)
                with open(jpg_temp_path, "wb") as f:
                    f.write(resp.content)
                registrar_log(f"Imagem baixada (JPG, sem PIL): {game_name}")
                return jpg_temp_path
        else:
            registrar_log(f"Imagem não encontrada na Steam CDN para {game_name} (HTTP {resp.status_code})")
            return None
    except Exception as e:
        registrar_log(f"Erro baixando imagem para {game_name}: {e}")
        return None

# ---------- Criação de relatórios em PDF (fpdf2) ----------
def criar_relatorios_pdf():
    os.makedirs(DOCS_DIR, exist_ok=True)
    if not FPDF_AVAILABLE:
        # fallback: criar txts
        for i in range(1, 11):
            p = os.path.join(DOCS_DIR, f"Relatorio_{i}.txt")
            if not os.path.exists(p):
                with open(p, "w", encoding="utf-8") as f:
                    f.write(f"Relatório {i}\nGerado automaticamente em {datetime.now().isoformat()}\n")
        registrar_log("FPDF não disponível — relatórios salvos como TXT")
        return

    for i in range(1, 11):
        path = os.path.join(DOCS_DIR, f"Relatorio_{i}.pdf")
        if os.path.exists(path):
            continue
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=14)
        pdf.cell(0, 10, txt=f"Relatório {i} - Steam Empresa", ln=True, align="C")
        pdf.ln(6)
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 8, txt=f"Relatório gerado automaticamente em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
                                 f"Jogos cadastrados: {len(GAMES)}\n")
        pdf.output(path)
    registrar_log("Relatórios PDF criados")

# ---------- Inicialização da estrutura (50 jogos + relatórios) ----------
def criar_estrutura_inicial(download_images=True):
    os.makedirs(JOGOS_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)
    os.makedirs(USUARIOS_DIR, exist_ok=True)

    # Criar pastas de jogos e metadata
    for name, appid in GAMES:
        pasta = os.path.join(JOGOS_DIR, safe_name(name))
        os.makedirs(pasta, exist_ok=True)
        txt = os.path.join(pasta, f"{safe_name(name)}.txt")
        if not os.path.exists(txt):
            with open(txt, "w", encoding="utf-8") as f:
                f.write(f"{name}\nDescrição automática.\nGerado em {datetime.now().isoformat()}\n")
    criar_relatorios_pdf()

    # Usuarios padrão
    if not os.path.exists(os.path.join(USUARIOS_DIR, "admin")):
        criar_usuario("admin", "1234", "ADMIN")
    if not os.path.exists(os.path.join(USUARIOS_DIR, "ryan")):
        criar_usuario("ryan", "1234", "USUARIO")

    registrar_log("Estrutura inicial criada (jogos e relatórios).")

    # Baixar imagens em thread para não travar GUI startup
    if download_images and requests:
        def bg_download():
            registrar_log("Iniciando download de imagens dos jogos (background).")
            for name, appid in GAMES:
                download_and_prepare_image(name, appid)
            registrar_log("Download de imagens concluído.")
        t = threading.Thread(target=bg_download, daemon=True)
        t.start()
    elif not requests:
        registrar_log("requests não instalado — imagens não serão baixadas automaticamente.")

# ---------- Usuários ----------
def criar_usuario(nome, senha, permissao="USUARIO"):
    user = os.path.join(USUARIOS_DIR, nome)
    if not os.path.exists(user):
        os.makedirs(os.path.join(user, "Biblioteca"), exist_ok=True)
        perfil = os.path.join(user, "Perfil.txt")
        with open(perfil, "w", encoding="utf-8") as f:
            f.write(f"Usuário:{nome}\nSenha:{senha}\nPermissão:{permissao}\n")
        registrar_log(f"Usuário criado: {nome} ({permissao})")
        return True
    return False

def validar_login(nome, senha):
    perfil = os.path.join(USUARIOS_DIR, nome, "Perfil.txt")
    if not os.path.exists(perfil):
        return None
    with open(perfil, "r", encoding="utf-8") as f:
        dados = f.read()
        try:
            s = [l for l in dados.splitlines() if l.startswith("Senha:")][0].split(":",1)[1].strip()
            p = [l for l in dados.splitlines() if l.startswith("Permissão:")][0].split(":",1)[1].strip()
        except Exception:
            return None
    if s == senha:
        registrar_log(f"Login sucesso: {nome}")
        return p
    else:
        registrar_log(f"Login falhou: {nome}")
        return None

# ---------- Operações de arquivos ----------
def listar_jogos_empresa():
    if not os.path.exists(JOGOS_DIR):
        return []
    return sorted(os.listdir(JOGOS_DIR))

def caminho_jogo(nome):
    return os.path.join(JOGOS_DIR, nome)

def obter_imagem_jogo(nome):
    pasta = caminho_jogo(nome)
    # procurar png/jpg/jpeg/gif
    for ext in (".png", ".jpg", ".jpeg", ".gif", ".ppm"):
        caminho = os.path.join(pasta, f"{nome}{ext}")
        if os.path.exists(caminho):
            return caminho
    return None

def adicionar_jogo_a_usuario(usuario, jogo):
    src_txt = os.path.join(caminho_jogo(jogo), f"{jogo}.txt")
    src_img = obter_imagem_jogo(jogo)
    dest_pasta = os.path.join(USUARIOS_DIR, usuario, "Biblioteca")
    os.makedirs(dest_pasta, exist_ok=True)
    if os.path.exists(src_txt):
        shutil.copy(src_txt, os.path.join(dest_pasta, f"{jogo}.txt"))
    if src_img:
        shutil.copy(src_img, os.path.join(dest_pasta, os.path.basename(src_img)))
    registrar_log(f"{usuario} adicionou {jogo} à biblioteca")

def remover_jogo_do_usuario(usuario, jogo):
    dest_pasta = os.path.join(USUARIOS_DIR, usuario, "Biblioteca")
    txt = os.path.join(dest_pasta, f"{jogo}.txt")
    if os.path.exists(txt):
        os.remove(txt)
    for ext in (".png", ".jpg", ".jpeg", ".gif", ".ppm"):
        p = os.path.join(dest_pasta, f"{jogo}{ext}")
        if os.path.exists(p):
            os.remove(p)
    registrar_log(f"{usuario} removeu {jogo} da biblioteca")

def listar_biblioteca(usuario):
    pasta = os.path.join(USUARIOS_DIR, usuario, "Biblioteca")
    if not os.path.exists(pasta):
        return []
    files = os.listdir(pasta)
    jogos = []
    for f in files:
        if f.endswith(".txt"):
            nome = f[:-4]
            if nome not in jogos:
                jogos.append(nome)
    return sorted(jogos)

# ---------- Interface Tkinter ----------
class App:
    REFRESH_MS = 2000  # atualiza a cada 2s

    def __init__(self, root):
        self.root = root
        self.root.title("Gerenciador Steam - Login")
        self.usuario = None
        self.permissao = None
        self.image_cache = {}  # cache de imagens (path->tk image)
        self.build_login_ui()

    def build_login_ui(self):
        for w in self.root.winfo_children():
            w.destroy()
        frm = ttk.Frame(self.root, padding=20)
        frm.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frm, text="Steam - Login", font=("TkDefaultFont", 16)).pack(pady=(0,10))
        self.ent_user = ttk.Entry(frm)
        self.ent_user.pack(fill=tk.X, pady=5)
        self.ent_user.insert(0, "ryan")
        self.ent_pass = ttk.Entry(frm, show="*")
        self.ent_pass.pack(fill=tk.X, pady=5)
        btn = ttk.Button(frm, text="Entrar", command=self.tentar_login)
        btn.pack(pady=10)

    def tentar_login(self):
        user = self.ent_user.get().strip().lower()
        pwd = self.ent_pass.get().strip()
        perm = validar_login(user, pwd)
        if perm:
            self.usuario = user
            self.permissao = perm
            registrar_log(f"{user} entrou via GUI")
            self.build_main_ui()
        else:
            messagebox.showerror("Erro", "Usuário ou senha inválidos")

    def build_main_ui(self):
        self.root.title(f"Gerenciador Steam - {self.usuario} ({self.permissao})")
        for w in self.root.winfo_children():
            w.destroy()

        container = ttk.Frame(self.root, padding=6)
        container.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(container)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=6)
        ttk.Label(left, text="Jogos (Empresa)", font=("TkDefaultFont", 12)).pack()
        self.lb_jogos = tk.Listbox(left, width=30, height=25)
        self.lb_jogos.pack(fill=tk.Y, expand=True)
        self.lb_jogos.bind("<<ListboxSelect>>", self.on_jogo_select)

        mid = ttk.Frame(container)
        mid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6)
        ttk.Label(mid, text="Detalhes / Capa", font=("TkDefaultFont", 12)).pack()
        self.canvas = tk.Label(mid, text="Selecione um jogo", anchor="center", width=40, height=20, relief=tk.SUNKEN)
        self.canvas.pack(fill=tk.BOTH, expand=True, pady=6)

        btn_frame = ttk.Frame(mid)
        btn_frame.pack(fill=tk.X)
        self.btn_add = ttk.Button(btn_frame, text="Adicionar à minha biblioteca", command=self.ui_adicionar_jogo)
        self.btn_add.pack(side=tk.LEFT, padx=4, pady=4)
        self.btn_remove = ttk.Button(btn_frame, text="Remover da minha biblioteca", command=self.ui_remover_jogo)
        self.btn_remove.pack(side=tk.LEFT, padx=4, pady=4)

        right = ttk.Frame(container)
        right.pack(side=tk.LEFT, fill=tk.Y, padx=6)
        ttk.Label(right, text="Minha Biblioteca", font=("TkDefaultFont", 12)).pack()
        self.lb_bib = tk.Listbox(right, width=30, height=25)
        self.lb_bib.pack(fill=tk.Y, expand=True)
        self.lb_bib.bind("<<ListboxSelect>>", self.on_bib_select)

        # Menu superior para admin
        menubar = tk.Menu(self.root)
        if self.permissao == "ADMIN":
            admin_menu = tk.Menu(menubar, tearoff=0)
            admin_menu.add_command(label="Criar usuário", command=self.ui_criar_usuario)
            admin_menu.add_command(label="Ver logs", command=self.ui_ver_logs)
            admin_menu.add_command(label="Relatórios", command=self.ui_ver_relatorios)
            menubar.add_cascade(label="Admin", menu=admin_menu)
        menubar.add_command(label="Atualizar", command=self.refresh_all)
        menubar.add_command(label="Logout", command=self.logout)
        self.root.config(menu=menubar)

        self.refresh_all()
        self.root.after(self.REFRESH_MS, self.periodic_refresh)

    def periodic_refresh(self):
        # atualiza lista e tenta carregar nova imagem se houver mudanças
        self.refresh_all()
        self.root.after(self.REFRESH_MS, self.periodic_refresh)

    def refresh_all(self):
        jogos = listar_jogos_empresa()
        self.lb_jogos.delete(0, tk.END)
        for j in jogos:
            self.lb_jogos.insert(tk.END, j)
        bib = listar_biblioteca(self.usuario)
        self.lb_bib.delete(0, tk.END)
        for b in bib:
            self.lb_bib.insert(tk.END, b)

        cur = self.get_selected_listbox_item(self.lb_jogos)
        if cur:
            self.show_jogo_image(cur)

    def get_selected_listbox_item(self, lb):
        sel = lb.curselection()
        if not sel:
            return None
        return lb.get(sel[0])

    def on_jogo_select(self, evt):
        jogo = self.get_selected_listbox_item(self.lb_jogos)
        if jogo:
            self.show_jogo_image(jogo)

    def on_bib_select(self, evt):
        jogo = self.get_selected_listbox_item(self.lb_bib)
        if jogo:
            pasta = os.path.join(USUARIOS_DIR, self.usuario, "Biblioteca")
            img = None
            for ext in (".png", ".jpg", ".jpeg", ".gif", ".ppm"):
                p = os.path.join(pasta, f"{jogo}{ext}")
                if os.path.exists(p):
                    img = p
                    break
            if img:
                self.load_and_show_image(img)
            else:
                self.canvas.config(image="", text=f"{jogo}\n(sem imagem)")

    def show_jogo_image(self, jogo):
        img = obter_imagem_jogo(jogo)
        if img:
            self.load_and_show_image(img)
        else:
            # se não existir imagem ainda, tenta disparar download em background
            # recupera appid da lista GAMES
            appid = None
            for name, aid in GAMES:
                if safe_name(name) == jogo:
                    appid = aid
                    break
            if appid and requests:
                # dispara download rápido em thread
                threading.Thread(target=download_and_prepare_image, args=(jogo, appid), daemon=True).start()
            self.canvas.config(image="", text=f"{jogo}\n(sem imagem)")

    def load_and_show_image(self, path):
        try:
            mtime = os.path.getmtime(path)
            key = (path, mtime)
            if key not in self.image_cache:
                if PIL_AVAILABLE:
                    img = Image.open(path)
                    # redimensiona mantendo proporção para caber no label
                    w, h = img.size
                    max_w, max_h = 400, 420
                    ratio = min(max_w / w, max_h / h, 1)
                    new_size = (int(w * ratio), int(h * ratio))
                    img = img.resize(new_size, Image.LANCZOS)
                    tkimg = ImageTk.PhotoImage(img)
                else:
                    # PhotoImage suporta PNG/GIF nativamente; JPEG pode falhar em alguns builds de Tk
                    tkimg = tk.PhotoImage(file=path)
                self.image_cache = { } if len(self.image_cache) > 80 else self.image_cache
                self.image_cache[key] = tkimg
            tkimg = self.image_cache[key]
            self.canvas.config(image=tkimg, text="")
            self.canvas.image = tkimg
        except Exception as e:
            self.canvas.config(image="", text=f"Erro carregando imagem\n{os.path.basename(path)}")
            registrar_log(f"Erro load image {path}: {e}")

    def ui_adicionar_jogo(self):
        jogo = self.get_selected_listbox_item(self.lb_jogos)
        if not jogo:
            messagebox.showinfo("Info", "Selecione um jogo da lista da empresa.")
            return
        adicionar_jogo_a_usuario(self.usuario, jogo)
        self.refresh_all()
        messagebox.showinfo("OK", f"{jogo} adicionado à sua biblioteca.")

    def ui_remover_jogo(self):
        jogo = self.get_selected_listbox_item(self.lb_bib)
        if not jogo:
            messagebox.showinfo("Info", "Selecione um jogo da sua biblioteca para remover.")
            return
        remover_jogo_do_usuario(self.usuario, jogo)
        self.refresh_all()
        messagebox.showinfo("OK", f"{jogo} removido da sua biblioteca.")

    # ---------- Admin UIs ----------
    def ui_criar_usuario(self):
        nome = simpledialog.askstring("Criar usuário", "Nome do usuário:")
        if not nome:
            return
        nome = nome.strip().lower()
        senha = simpledialog.askstring("Criar usuário", "Senha:", show="*")
        if not senha:
            return
        perm = simpledialog.askstring("Permissão", "Permissão (ADMIN/USUARIO):", initialvalue="USUARIO")
        if not perm:
            perm = "USUARIO"
        criado = criar_usuario(nome, senha, perm.upper())
        if criado:
            messagebox.showinfo("OK", "Usuário criado.")
        else:
            messagebox.showwarning("Aviso", "Usuário já existe.")

    def ui_ver_logs(self):
        if not os.path.exists(LOG_FILE):
            messagebox.showinfo("Logs", "Sem logs ainda.")
            return
        top = tk.Toplevel(self.root)
        top.title("Logs do Sistema")
        txt = tk.Text(top, width=100, height=30)
        txt.pack(fill=tk.BOTH, expand=True)
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            txt.insert("1.0", f.read())
        txt.config(state=tk.DISABLED)

    def ui_ver_relatorios(self):
        arquivos = sorted(os.listdir(DOCS_DIR)) if os.path.exists(DOCS_DIR) else []
        if not arquivos:
            messagebox.showinfo("Relatórios", "Nenhum relatório encontrado.")
            return
        top = tk.Toplevel(self.root)
        top.title("Relatórios")
        lb = tk.Listbox(top, width=80, height=20)
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        for a in arquivos:
            lb.insert(tk.END, a)
        def abrir():
            sel = lb.curselection()
            if not sel:
                return
            arq = lb.get(sel[0])
            caminho = os.path.join(DOCS_DIR, arq)
            if os.name == "nt":
                os.startfile(caminho)
            else:
                try:
                    os.system(f'xdg-open "{caminho}"')
                except:
                    messagebox.showinfo("Abrir", f"Caminho: {caminho}")
        btn = ttk.Button(top, text="Abrir", command=abrir)
        btn.pack(side=tk.RIGHT, padx=6, pady=6)

    def logout(self):
        registrar_log(f"{self.usuario} fez logout")
        self.usuario = None
        self.permissao = None
        self.image_cache.clear()
        self.root.title("Gerenciador Steam - Login")
        self.build_login_ui()

# ---------- Execução ----------
if __name__ == "__main__":
    criar_estrutura_inicial(download_images=True)
    root = tk.Tk()
    root.geometry("1000x700")
    app = App(root)
    root.mainloop()
