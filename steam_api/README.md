Steam API helper package
------------------------

Arquivos incluídos:
- models.py
- populate_games.py
- download_images.py
- requirements.txt

Sobre o DATABASE_URL já preenchido:
- DEFAULT: mysql+pymysql://root:root@127.0.0.1:3306/steamlib
  (troque essa URL se necessário; você pode setar variável de ambiente DATABASE_URL)

Como usar (resumo):
1) Crie o DB no MySQL Workbench:
    CREATE DATABASE steamlib CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

2) Instale dependências:
    pip install -r requirements.txt

3) Teste populando alguns apps:
    python populate_games.py --limit 50

4) (Opcional) Baixe imagens:
    python download_images.py --limit 50

Observações:
- Os scripts salvam progresso em populate_progress.json e image_progress.json
- Recomendo testar com --limit antes de rodar completo