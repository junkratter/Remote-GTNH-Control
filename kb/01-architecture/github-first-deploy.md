# Первый выклад репозитория на GitHub (с нуля, без установленного Git)

> **Last updated:** 2026-05-18  
> **Audience:** уже есть пустой репозиторий на github.com, код лежит локально (например клон/копия `gtnh-cyber`).

## 1. Откуда взять файлы

| Ситуация | Что делать |
|----------|------------|
| Уже есть папка с проектом на диске | Это и есть «исходные файлы». Дальше — только `git` + remote на GitHub. |
| Код только на другой машине | Скопировать папку целиком (rsync/scp/USB) на машину, где будете пушить. |
| Хотите начать с официального форка | `git clone <url-форка>` — тогда файлы уже из git; remote часто уже настроен как `origin`. |

Секреты в git **не кладём**: `.env`, `server/.env`, `oc-client/env.lua`, `data/*.sqlite` — см. `README.md` / `.gitignore`.

## 2. Установить Git (macOS)

**Вариант A — Xcode Command Line Tools** (часто уже есть):

```bash
xcode-select --install
git --version
```

**Вариант B — Homebrew:**

```bash
brew install git
git --version
```

Имя и email для коммитов (один раз на машину):

```bash
git config --global user.name "Ваше Имя"
git config --global user.email "you@example.com"
```

## 3. Подключить локальную папку к пустому репозиторию на GitHub

В терминале зайдите в **корень проекта** (где лежат `README.md`, `.git` может ещё не быть).

### Если `.git` ещё нет

```bash
cd /path/to/gtnh-cyber
git init
git branch -M main
git remote add origin https://github.com/<USER>/<REPO>.git
# или SSH:
# git remote add origin git@github.com:<USER>/<REPO>.git
```

### Если `.git` уже есть (например клонировали раньше)

Проверьте remote:

```bash
git remote -v
```

Если `origin` указывает не на ваш новый репозиторий:

```bash
git remote set-url origin https://github.com/<USER>/<REPO>.git
```

## 4. Первый коммит и push

```bash
git status
git add -A
git status   # убедитесь, что нет .env / секретов
git commit -m "Initial import: gtnh-cyber"
git push -u origin main
```

Если GitHub пишет, что на сервере уже есть коммиты (например README при создании репозитория):

```bash
git pull origin main --rebase
# разрешите конфликты, если есть
git push -u origin main
```

## 5. Аутентификация GitHub

### HTTPS + Personal Access Token (PAT)

1. GitHub → **Settings → Developer settings → Personal access tokens** → создать token с правом `repo`.  
2. При `git push` вместо пароля вставьте **token**.

### SSH (удобнее на долгую)

```bash
ssh-keygen -t ed25519 -C "you@example.com" -f ~/.ssh/id_ed25519_github
# публичный ключ ~/.ssh/id_ed25519_github.pub добавить в GitHub → Settings → SSH keys
```

В `~/.ssh/config`:

```text
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_github
```

Remote: `git@github.com:<USER>/<REPO>.git`.

## 6. Опционально: GitHub CLI (`gh`)

Не обязателен для `git push`.

```bash
brew install gh
gh auth login
```

Полезно для PR/issue: `gh pr create`, `gh repo view`.

## 7. Submodules (если используете `kb/05-vendored/`)

После клонирования у других разработчиков:

```bash
git submodule update --init --recursive
```

Первый push с субмодулями: убедитесь, что в GitHub добавлены те же submodule URL, что в `.gitmodules`.

## 8. Что проверить перед публичным push

- [ ] Нет `SERVER_TOKEN` / паролей в истории и в индексе  
- [ ] `README.md` / `README.ru.md` с актуальной документацией  
- [ ] `LICENSE` на месте  
- [ ] CI (если добавите) — отдельным коммитом  

Подробнее: раздел **Publishing to GitHub** в `README.md`.
