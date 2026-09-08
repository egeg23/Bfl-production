# Аудит наработок пользователя (egeg23) для цифрового контура продукта БФЛ

Дата: 2026-09-08. Метод: только чтение репозиториев в `/home/user/*` (Read/Grep/Bash cat, `git log`, `diff`, `md5sum`), без интернета и без изменений. Цель — понять, что из существующего кода и практик можно переиспользовать в «управленческом и цифровом контуре» продукта «контрактное юридическое производство БФЛ» (ЛК/портал партнёра, CRM дел, документооборот), оценить зрелость и экономию времени.

---

## 0. Резюме (TL;DR)

1. **Legal AI (4 репозитория) — это один и тот же Flask-прототип в четырёх снимках**, а не четыре продукта. Реально живая ветка — `Legal-v4` (30 коммитов, март 2026, задеплоена на `maximov-tech.ru/legal`). `Leg-ai` и `legal-ai-service` — более ранние копии с mock-LLM, `legal-ai-simple` — статический лендинг + файл промптов.
2. **Что реально работает в Legal-v4:** загрузка PDF/DOC/DOCX/TXT → извлечение текста (pdftotext → pdfimages+tesseract rus+eng для сканов) → генерация 1 из 4 документов через Moonshot/Kimi (`kimi-k2-turbo-preview`) → сборка DOCX (python-docx) → превью 25%/размытие → скачивание. JWT-авторизация, SQLite, тарифы (4 шт.) и «кредиты» в БД. Платежи, e-mail-верификация, уведомления — **моки**; проверка кредитов **выключена** («free mode»); админка — HTML без бэкенда.
3. **Зрелость низкая (прототип/демо, не продакшен):** 0 тестов во всех 4 репо, секреты в git (ключ Moonshot захардкожен в `kimi_api.py`, `.env` закоммичен), **загруженные пользователями документы и сгенерированные DOCX с персональными данными закоммичены в репозиторий** (54 + 28 файлов), CORS `*`, токен в query-string, фоновые `threading.Thread` + SQLite, «прогресс» — искусственные `time.sleep` (~40 с), дрейф маршрутов фронт/бэк.
4. **Для БФЛ из Legal AI переиспользуется не код, а три вещи:** (а) пайплайн «файл → текст (OCR) → LLM → DOCX» как схема, (б) структура промптов «персона + жёсткая структура документа + ссылки на нормы + приложения» (файл `legal_prompts.md`), (в) модель тарифов/кредитов как идея. **Ни одного БФЛ-типа документа нет** (нет заявления о банкротстве, описи имущества, списка кредиторов, ходатайств, ответов ФУ), нет сущности «партнёр/организация», нет стадий дела, SLA и чек-листов.
5. **Настоящие переиспользуемые активы лежат в других репо:** `FlatAi` (FastAPI async + Next.js + OTP-авторизация с каскадом e-mail→Telegram→SMS + Telegram-уведомления + админка + pytest/CI + systemd/nginx-деплой), `seller-ai` (биллинг с серверным прайсингом, Fernet-шифрование ключей, rate-limit, LLM-абстракция Kimi/Claude, OCR-модуль, i18n ×5, HANDOFF-дисциплина, 90 тест-файлов), `Profi_UZ` (Supabase: 36 миграций, 44 RLS-политики, edge-функции, CI-деплой миграций и фронта, «VPS Run» через коммит-файл).
6. **Рекомендация стека MVP портала партнёра/CRM дел:** FastAPI (async SQLAlchemy 2 + Alembic + Postgres + Redis) + Next.js (App Router, shadcn/ui) на VPS в РФ, по скелету `FlatAi`; планировщик SLA — APScheduler (как в FlatAi) с переходом на Celery (как в seller-ai) при росте; LLM-слой — из `seller-ai/api/llm`; OCR — `pdftotext + tesseract` из Legal-v4 / `seller-ai/api/content/ocr.py`. Hosted Supabase (eu-central-1) для данных должников **не подходит** из-за требования локализации ПДн граждан РФ (152-ФЗ, ст. 18 ч. 5 — проверить с юристом), но паттерны RLS/изоляции партнёров из Profi_UZ переносятся на self-hosted Postgres.
7. **Экономия времени (оценка):** каркас портала (auth, роли, партнёр-изоляция, дела, документы, уведомления, админка, деплой, CI) — ~35–45 % трудозатрат MVP уже покрыто существующим кодом; в календарных неделях для одного разработчика с AI-workflow — MVP за ~8–10 недель вместо ~14–18 «с нуля». Ноль экономии на доменной части (стадии БФЛ, формы по 127-ФЗ, регламенты) — её нет нигде.

---

## 1. Контекст и рамка

Продукт (по описанию вакансии) — B2B-сервис: юрфирма продаёт БФЛ должнику → передаёт дело в нашу систему → мы ведём производственную цепочку → партнёр видит статус/сроки/документы/аналитику. Заказчик прямо говорит: сначала конфигурация продукта, потом IT; цифровая оболочка «скорее всего нужна» (ЛК/портал/CRM). Значит, вопрос к наработкам — не «что запустить завтра», а **что станет основой портала партнёра и CRM дел, когда конфигурация будет зафиксирована**, и что можно показать на собеседовании как доказательство скорости.

Ограничения аудита: только локальные копии репозиториев (снимок 2026-09-05), без запуска кода и без доступа к продовым серверам. Оценки времени — экспертные, помечены как оценки.

---

## 2. Legal AI: четыре репозитория, один прототип

### 2.1. Карта репозиториев и дубли

| Репо | Коммиты / даты | Что это | Состояние LLM |
|---|---|---|---|
| `legal-ai-service` | 2 (2026-03-20) | Первый снимок: план ревью CodeRabbit + код | **mock** (`kimi_api.py` с `MOCK_LEGAL_ANALYSIS`) |
| `Leg-ai` | 8 (2026-03-21) | Тот же код + фиксы по ревью (JWT_SECRET из env, XSS, дубли функций) | **mock** (файл идентичен `legal-ai-service` по md5) |
| `Legal-v4` | 30 (2026-03-25) | Рабочая ветка: реальный Moonshot API, OCR, мультидокумент, превью, деплой-скрипты, доки для Сколково | **реальный** API (`kimi-k2-turbo-preview`, temperature=1 для k2) |
| `legal-ai-simple` | 15 (2026-03-21/22) | Статический фронт «в стиле Remove.bg» + `prompts/legal_prompts.md` | без бэкенда |

Дубли подтверждены `md5sum`: `models.py` и `payments.py` в `Leg-ai` и `Legal-v4` побайтно совпадают; `config.py` и `kimi_api.py` совпадают в `Leg-ai` и `legal-ai-service`; `TARIFFS.md` и `CODERABBIT_REVIEW.md` одинаковы во всех трёх. Различия `Legal-v4` vs `Leg-ai`: `app.py` (+454 строк diff — OCR, фоновый прогресс, превью), `kimi_api.py` (полностью переписан под реальный API). Вывод: **источник истины — `Legal-v4`; остальные три можно архивировать**.

### 2.2. Что реализовано в Legal-v4 (факты по коду)

- **Стек:** Flask 3 + Flask-SQLAlchemy + SQLite (`sqlite:///legal_ai.db` по умолчанию и в `deploy/.env.example`), PyJWT (HS256, access 24 ч / refresh 30 дней, пароли — Werkzeug hash), python-docx, requests, subprocess-вызовы `pdftotext`/`pdfimages`/`tesseract`. Один файл `app.py` на ~1450 строк.
- **Маршруты API (21):** register/login/refresh/me, upload (создаёт `Case` и сохраняет файлы в `uploads/user_{id}/case_{id}/`), cases (пагинация), case GET/DELETE, analyze (запуск фонового потока), progress, payment create/confirm (мок), payments/history, tariffs, balance, auth/send-code + verify-code (код пишется в лог, хранится в dict в памяти), download, pricing, preview (HTML 25 % + DOCX-превью).
- **Пайплайн генерации** (`analyze_with_progress`): извлечение текста (лимит 15 000 символов на файл, до 10 страниц OCR) → `analyze_case_documents` (JSON-аудит документов: хронология, сильные/слабые стороны, недостающие документы) → `generate_legal_document` (системный промпт по типу + пользовательский промпт «извлеки реальные ФИО/суммы/даты, без плейсхолдеров») → эвристическая разметка DOCX (заголовки по ключевым словам, Times New Roman 12, подпись) → `case.paid = True` автоматически.
- **Модель данных:** `User` (кредиты, флаги первой покупки, e-mail-верификация), `Case` (тип документа, JSON-список файлов, статус pending/analyzing/completed/failed/paid, прогресс, цена 5000), `DownloadHistory`, `IPRequest` (лимит 200/30 дней — заведён, но нигде не вызывается), `PaymentTransaction`, `Tariff`, `UserTariff`, `ClarityRequest` (правки юриста — таблица есть, эндпоинта нет).
- **Тарифы (из `TARIFFS.md`/`config.py`):** Разовый 5 000 ₽/1 запрос, Адвокат 175 000 ₽/50, Фирма 500 000 ₽/175, Палата 1 500 000 ₽/500 — сидятся в БД при старте; списание кредитов реализовано дважды (`app.py` и `payments.py`, разная логика), но в `upload` отключено (`'credits_remaining': 999`).
- **Фронт:** статический HTML/JS в `public/` (12 страниц, ~178 КБ). `main.js` обращается к `/api/auth/me`, `/api/auth/register`, `/api/subscription/subscribe`, `/api/cases/{id}/download` — **таких маршрутов в бэкенде нет** (есть `/api/me`, `/api/register`, `/api/download/{id}`). `admin.html` (37 КБ) вызывает `/api/admin/stats|users|tariffs` — в `app.py` слово `admin` не встречается ни разу: **админка — только интерфейс**.
- **Деплой:** `deploy/` (systemd unit с gunicorn, nginx с SSL и без, Dockerfile multi-stage, docker-compose, скрипты) — сгенерированный комплект «из okcomputer»; фактический деплой — `deploy.sh` с `sshpass`/root и `nohup python app.py`, nginx-конфиг `maximov-tech.conf` проксирует `/legal/api/` на `127.0.0.1:5000`.
- **Документы для Сколково** (`docs/skolokovo/`): бизнес-план, техописание, чек-лист. Техописание заявляет RAG, few-shot, fine-tuning, «10 000+ образцов», «500 кейсов» — **в коде этого нет** (ни векторной базы, ни примеров, ни датасета). Использовать как черновик риторики, не как факт.

### 2.3. Типы документов и промпты

Реализованные типы (enum `DocumentType`): `complaint` — исковое заявление, `appeal` — апелляционная жалоба, `petition` — досудебная претензия, `statement` — стратегия защиты. Промпты в `Legal-v4/kimi_api.py` заточены **под спор о займе** (ст. 807–810, 395 ГК РФ, госпошлина по ст. 333.19 НК РФ), содержат жёстко зашитые «проценты успеха» и ссылки на конкретные определения ВС РФ (номера дел вписаны в промпт руками — риск галлюцинаций и устаревания). Более чистая версия промптов — `legal-ai-simple/prompts/legal_prompts.md`: 4 системных промпта с чёткой структурой (шапка, заголовок, основания, доказательства, просительная часть, приложения, подпись; ГОСТ Р 7.0.97-2016; инструкция по формату вывода для DOCX). Есть 4 текстовых образца-шаблона (`templates/samples/*.txt`, 9–12 КБ каждый) и большой мок-кейс `mock_responses_kanevsky.json` (7 документов по одному реальному делу — см. п. 2.4 о ПДн).

**Чего нет для БФЛ:** ни одного документа по 127-ФЗ. Нет: заявления гражданина о признании банкротом (ст. 213.4), описи имущества и списка кредиторов/должников (формы по приказу Минэкономразвития № 530 от 05.08.2015 — проверить актуальность редакции), ходатайств (об исключении имущества из конкурсной массы, о выделении прожиточного минимума, об отложении, об утверждении ФУ из конкретной СРО), ответов на запросы финансового управляющего, заявления о внесудебном банкротстве через МФЦ, отчётов ФУ, заявления о завершении процедуры. Нет справочников (перечень документов по ст. 213.4, суды по регионам, СРО), нет валидации полноты пакета.

### 2.4. Качество и зрелость: критические находки

**Безопасность и комплаенс (блокеры для любой юр-системы):**
1. **Секрет в коде:** `Legal-v4/kimi_api.py:24` — реальный ключ Moonshot в исходнике (в `Leg-ai` ключ уже вынесен в env, в v4 вернулся). `Legal-v4/.env` закоммичен (KIMI_API_KEY, SECRET_KEY, JWT_SECRET_KEY). Ключи нужно считать скомпрометированными и ротировать.
2. **ПДн в git:** `Legal-v4/uploads/` (54 файла: PDF/DOC реальных пользователей, в т.ч. судебные документы с номерами дел) и `generated/` (28 DOCX) отслеживаются git. `templates/mock/mock_responses_kanevsky.json` содержит ФИО, дату рождения, номер паспорта и адрес физлица. Для БФЛ, где в каждом деле паспорт, СНИЛС, ИНН, кредиторы, — такая гигиена недопустима; перед любым переиспользованием репо надо чистить историю (`git filter-repo`) или не переносить его вовсе.
3. `CORS(origins='*')`, JWT принимается из query-string (`?token=`), коды верификации в памяти процесса, `IPRequest`-лимиты не подключены, нет rate-limit на login/register, `send_from_directory('/opt/legal-ai-service/public')` — абсолютный путь в коде.
4. Fallback-шаблоны при ошибке LLM обращаются к ключам `case_data['court_name']`, `case_data['plaintiff']`, которых в `case_data` нет → `KeyError` внутри `except`, дело падает в `failed` вместо фолбэка.

**Архитектура/надёжность:** фоновая генерация через `threading.Thread` с SQLite (при gunicorn с 4 воркерами и SQLite — гонки и потеря потоков при рестарте); «прогресс» — фиксированные `time.sleep` (в сумме ~40 с) без связи с реальной работой; DOCX-форматирование — эвристика по ключевым словам (`'1.'…'9.'` → заголовок), markdown из LLM не обрабатывается; дублирование `deduct_credit` и `init_tariffs` в двух модулях; `app.py.backup`, `app.py.fixed`, `EOF`, `PYEOF`, логи — мусор в репо.

**Тестируемость:** тестов нет ни в одном из 4 репо (`find -iname '*test*'` → пусто). `CODERABBIT_REVIEW.md` — план ревью с чек-боксами, почти все пункты не закрыты.

**Оценка зрелости:** демо/прототип (уровень «показать инвестору»), не производственная система. Переносить как код — нецелесообразно; переносить как **знание** (пайплайн, промпт-структура, модель тарифов, грабли) — да.

### 2.5. Что из Legal AI применимо к БФЛ

| Элемент | Применимость | Как использовать |
|---|---|---|
| Пайплайн «файл → текст (OCR) → LLM → DOCX» | Высокая | Схема для модуля «автосборка пакета»: кредитные договоры/справки → извлечение реквизитов → черновики описи/списка кредиторов. Реализовать заново на FastAPI + очередь |
| Структура промптов из `legal_prompts.md` | Высокая | Шаблон для БФЛ-промптов: персона «юрист по банкротству», структура документа по ст. 213.4, обязательные приложения, запрет плейсхолдеров |
| JSON-аудит документов («чего не хватает») | Высокая | Превращается в **чек-лист полноты пакета** по делу — самая ценная идея для производственного контура |
| Тарифы/кредиты (`Tariff`, `UserTariff`) | Средняя | Идея «пакеты» для партнёра, но экономика БФЛ — per-case/этапная, не per-document |
| Превью 25 %/размытие | Низкая | B2C-механика; в B2B не нужна |
| OCR-цепочка `pdftotext → pdfimages → tesseract rus+eng` | Средняя | Рабочая и дешёвая (без токенов); нужен лимит страниц и очередь |
| Деплой-комплект (systemd/nginx/Dockerfile) | Низкая | Есть лучше в FlatAi/seller-ai |
| Промпты с «процентами успеха» и вписанными номерами дел ВС | Отрицательная | Не переносить: галлюцинации, репутационный риск перед СРО |

---

## 3. Другие репозитории: переиспользуемые паттерны

### 3.1. `seller-ai` — FastAPI + Celery + React/Vite, самый зрелый бэкенд
- **Что есть:** FastAPI-монолит (`api/routers`: auth, billing, admin, agents, support, referral, telegram…), 21 модель, 60 alembic-миграций, Celery worker + beat, Redis, docker-compose (api/worker/beat/nginx), 90 файлов тестов (`tests/test_*.py` + `smoke_*.py`), GitHub Action deploy, ops (systemd-таймеры autodeploy/backup, tg-bridge).
- **Переносимые модули:** `api/billing/plans.py` (серверный каталог цен — «клиент никогда не присылает сумму») и `billing/service.py` (create → callback → activate → refund с гарантиями вебхука, `docs/BILLING-WEBHOOK-GUARANTEE.md`); `api/auth_codes.py` (одноразовые коды из безопасного алфавита, TTL, consume) + регистрация только по OTP e-mail/Telegram (антифарминг); `api/ratelimit.py`, `api/url_safety.py` (SSRF), `api/llm/{kimi,claude,usage}.py` (абстракция провайдеров + учёт токенов), `api/content/ocr.py`, `api/rag/retrieve.py` (простой RAG для базы знаний), Fernet-шифрование чужих токенов в БД (по CLAUDE.md).
- **Практики:** `HANDOFF.md` (360 КБ живого журнала состояния), `INTEGRITY_AUDIT.md` (многоагентный аудит «фейк-данные под бейджем Активен» → паттерн «честные состояния»), `memory/` в репо, i18n ×5 языков (`i18n.tsx` 1,4 МБ) с правилом полного паритета, правило «деплой = git bundle».
- **Для БФЛ:** биллинг партнёров (постоплата/пакеты/этапы), учёт LLM-токенов на дело, RAG по базе практики/регламентов, дисциплина HANDOFF/аудитов. Минус: монолит перегружен маркетплейс-доменом — брать модули, не репо.

### 3.2. `Profi_UZ` (USTA) — Supabase-first SPA
- **Что есть:** React 19 + Vite + shadcn + TanStack Query + i18next (ru/uz/en); Supabase: 36 миграций (зеркало прод-истории), 44 RLS-политики, триггеры, pg_cron, pg_net; 3 edge-функции (`auth-bridge` — вход по коду из Telegram-бота через `generateLink` magiclink; `tg-webhook`; `notify`); GitHub Actions: `deploy-vps.yml`, `deploy-supabase.yml` (db push + functions deploy), `vps-run.yml` (выполнение команды на VPS по коммиту файла `ops/vps-command`). 91 коммит, аудит 29 находок закрыт.
- **Для БФЛ:** образец **изоляции данных по участникам** (заказ/чат/телефон видны только матч-паре и админу) — прямой аналог «партнёр видит только свои дела, ФУ — только назначенные, должник — только своё». Модель ролей клиент/мастер/админ → партнёр-менеджер/производственник/ФУ/админ. Realtime-статусы через подписки. CI-мост «VPS Run» полезен при работе с сервера СРО без SSH.
- **Ограничение:** hosted Supabase в `eu-central-1` — данные должников (ПДн граждан РФ) там хранить нельзя без нарушения требования локализации (152-ФЗ, ст. 18 ч. 5; уточнить с юристом заказчика). Вариант — self-hosted Supabase/Postgres на VPS в РФ, тогда паттерны переносятся полностью.

### 3.3. `FlatAi` (LBM Rentals / suleiman) — самый чистый FastAPI + Next.js скелет
- **Что есть:** FastAPI async (SQLAlchemy 2 async, asyncpg, Alembic), Pydantic 2, APScheduler (cron-задачи по минутам/часам), aiogram-бот, Redis; `app/security.py` (bcrypt, JWT в httpOnly-cookie через Next BFF, constant-time login, HMAC-OTP без таблицы), каскад доставки OTP e-mail → Telegram → SMS (`services/notifications.deliver_owner_otp`), Telegram Gateway для кодов на телефон, `services/notifications.py` — единая точка событий (events_log + Telegram владельцу), `crypto.py` (Fernet), `ratelimit.py`, `url_safety.py`, entitlements (гейтинг функций по подписке), админ-панель (`components/admin/*-tab.tsx`, `api/admin*.py`), интеграции за флагами `*_MOCK`, 19 pytest-тестов + smoke-скрипты, **CI на чистом Postgres** (`alembic upgrade head` + pytest + typecheck/build фронта), деплой systemd + nginx + certbot + бэкапы + uptime-cron. 54 коммита, доки `SECURITY-AUDIT`, `GO-LIVE`, `HANDOFF-SAAS`, `ESIGN-PLAN`.
- **Для БФЛ:** это **готовый каркас портала**: владелец→партнёр, объект→дело, бронь→этап, «гость» → должник (форма заселения с паспортными данными и `passport_ocr` → анкета должника с OCR паспорта), events_log → журнал движения дела, уведомления владельцу → уведомления партнёру о смене статуса/дедлайне, APScheduler → SLA-таймеры и напоминания, `ESIGN-PLAN.md` → подписание доверенности/договора.

### 3.4. `tezketkaz` — Flutter + Node/Prisma
- Node (Express/Prisma/BullMQ/socket.io) + Flutter (3 роли), 14 Prisma-миграций, Caddy auto-TLS, Sentry, audit-log, интеграции iiko/Poster, Telegram-вход, `LAUNCH_CHECKLIST.md`. Стек не совпадает с основным (Python/TS) — **не брать как основу**; полезны `LAUNCH_CHECKLIST.md`, `lib/audit.js` (аудит-лог) и модель «партнёрский API-ключ + HMAC-вебхук» (для будущего API «партнёр передаёт дело из своей CRM»).

### 3.5. `FlyMart` — зеркало чужого маркетплейса (35 сервисов, Java/Spring/Camunda)
- Не код пользователя, приватное зеркало заказчика с секретами. Ценность — `_ANALYSIS/FLYMART-AUDIT-AND-PLAN.md`: пример **аудита с оценкой по измерениям и планом на месяц для команды 8 человек** — формат прямо подходит для первого месяца в СРО (аудит текущих IT-инструментов и регламентов). Camunda BPM как референс идеи «оркестрация этапов процесса» — для БФЛ достаточно state-machine в Postgres, Camunda избыточна.

### 3.6. `DevUZ-perfect-` и `Global-Export` — Next.js 16 + Supabase, корпоративные сайты
- Next.js 16 App Router, React 19, Tailwind v4, свой i18n (`[locale]/`, middleware/proxy), Supabase Auth + Server Actions для админки (`Global-Export/app/admin/(panel)/*` — CRUD новостей/товаров/медиа с drag-and-drop и медиатекой), лид-формы → Telegram/Bitrix24, AI-квалификация лидов (Anthropic SDK, ICP+BANT, `lib/qualify/*`), деплой-скрипты nginx. 
- **Для БФЛ:** админка на Server Actions — образец быстрой внутренней CRUD-панели (справочники: суды, СРО, регламенты, шаблоны); `lib/qualify` — идея «AI-квалификация входящего дела» (первичный скоринг: сумма долга, наличие имущества, сделки за 3 года → маршрут судебный/внесудебный).

---

## 4. Сводная таблица «актив → что даёт для БФЛ → зрелость → что дорабатывать»

Зрелость: 1 — прототип/демо, 2 — работает у пользователя, есть дыры, 3 — есть тесты/CI/аудит, 4 — прод с клиентами.

| Актив (файл/модуль) | Что даёт для БФЛ | Зрелость | Что дорабатывать |
|---|---|---|---|
| `Legal-v4/app.py` — пайплайн upload→OCR→LLM→DOCX | Схема модуля автосборки документов и чек-листа полноты | 1 | Переписать на FastAPI + очередь; убрать sleep-прогресс; DOCX по шаблонам (docxtpl), а не эвристикой |
| `Legal-v4/app.py::extract_text_from_file` (pdftotext/pdfimages/tesseract) | Дешёвый OCR сканов без токенов | 2 | Вынести в воркер, лимиты страниц/времени, очередь, хранение в S3-совместимом хранилище в РФ |
| `legal-ai-simple/prompts/legal_prompts.md` | Шаблон структуры промптов для юрдокументов | 2 (как текст) | Написать БФЛ-набор: заявление ст. 213.4, опись, список кредиторов, ходатайства, ответ ФУ; убрать «проценты успеха» |
| `Legal-v4/kimi_api.py::analyze_case_documents` (JSON-аудит, `missing_documents`) | Чек-лист «чего не хватает в пакете» | 1 | Схема JSON под перечень ст. 213.4 + валидация pydantic; человеческая проверка юристом |
| `Legal-v4/models.py` (Tariff/UserTariff/Case) | Идея пакетов и статусов | 1 | Не переносить как есть; новая модель: Partner, Case, Stage, Task, Document, SLA, Event |
| `Legal-v4/docs/skolokovo/*` | Заготовки бизнес-плана/техописания | 1 | Только как черновик формулировок |
| `FlatAi/backend` (FastAPI async, security, OTP-каскад, Telegram, APScheduler, admin, CI) | **Каркас портала партнёра и внутренней CRM** | 3 | Заменить домен (объекты→дела), добавить роли/тенант-изоляцию, RLS или scoped-запросы, журнал аудита |
| `FlatAi/frontend` (Next.js 14, shadcn, BFF-cookie auth, admin tabs, onboarding-wizard) | Готовый UI-скелет ЛК + админки | 3 | Перерисовать под «дело/стадии/документы/дедлайны», добавить kanban/таймлайн |
| `FlatAi/.github/workflows/ci.yml` | CI на чистом Postgres: миграции + pytest + build | 3 | Взять как есть |
| `FlatAi/deploy/*` (systemd, nginx, certbot, backup, uptime) | Прод-эксплуатация на VPS в РФ | 3 | Взять как есть, добавить off-site бэкап с шифрованием |
| `seller-ai/api/billing/*` + `docs/BILLING-WEBHOOK-GUARANTEE.md` | Биллинг партнёров: серверный прайсинг, вебхуки, возвраты | 3 | Адаптировать под этапную/пакетную оплату B2B, счета/акты |
| `seller-ai/api/auth_codes.py`, `ratelimit.py`, `url_safety.py` | Безопасные одноразовые коды, лимиты, SSRF-защита | 3 | Взять как есть |
| `seller-ai/api/llm/{kimi,claude,usage}.py` | Абстракция LLM-провайдера + учёт токенов на дело | 3 | Добавить провайдеров в РФ-контуре (YandexGPT/GigaChat) при требовании заказчика к обработке ПДн |
| `seller-ai/api/rag/retrieve.py` + `scripts/ingest_*` | RAG по регламентам СРО/практике | 2 | Корпус: 127-ФЗ, постановления Пленума ВС, внутренние регламенты |
| `seller-ai` HANDOFF/INTEGRITY_AUDIT/memory | Дисциплина ведения проекта и «честных состояний» | 3 | Перенести правила в CLAUDE.md нового репо |
| `seller-ai/frontend/src/lib/i18n.tsx` | Мультиязычность | 3 | Для БФЛ не нужна (только ru) — не тянуть |
| `Profi_UZ/supabase/migrations/*` (RLS ×44, триггеры, pg_cron) | Образец изоляции данных по участникам, rate-limit в БД | 3 | Перенести идеи на self-hosted Postgres; hosted Supabase — нет (локализация ПДн) |
| `Profi_UZ/.github/workflows/vps-run.yml` | Выполнение команд на сервере через коммит | 3 | Полезно, если у СРО нет SSH для подрядчика |
| `Profi_UZ` edge `auth-bridge` (вход по коду из Telegram-бота) | Вход должника/партнёра без паролей | 3 | Для B2B-партнёров лучше e-mail-OTP/пароль + Telegram как второй канал |
| `Global-Export/app/admin/(panel)` (Server Actions CRUD, медиатека) | Быстрая внутренняя панель справочников | 2 | Использовать, если фронт — Next.js 16 |
| `DevUZ-perfect-/lib/qualify/*` (ICP/BANT-скоринг лида) | Идея AI-скоринга входящего дела | 2 | Правила скоринга под БФЛ (долг, имущество, сделки, доход) |
| `tezketkaz` (`lib/audit.js`, API-ключи + HMAC-вебхуки, LAUNCH_CHECKLIST) | Аудит-лог, партнёрский API | 2 | Переписать на Python; чек-лист запуска — адаптировать |
| `FlyMart/_ANALYSIS/*` | Формат аудита и плана на месяц для команды | 3 (как документ) | Шаблон для «первые 30 дней: аудит процессов СРО» |

---

## 5. Рекомендация базового стека MVP портала партнёра / CRM дел

**Принципы выбора:** (1) привычки пользователя — Python/FastAPI и TypeScript/Next.js, работа через Claude Code с HANDOFF-дисциплиной, деплой на собственный VPS; (2) ПДн должников → сервер в РФ, шифрование чувствительных полей, аудит доступа; (3) MVP — это статусы, документы, сроки и отчётность для партнёра, а не AI-генерация (AI — второй этап).

**Рекомендуемый стек (вариант A, основной):**
- **Backend:** FastAPI + SQLAlchemy 2 async + Alembic + PostgreSQL 16 + Redis — по скелету `FlatAi/backend` (auth, OTP-каскад, Telegram-бот, events_log, admin, entitlements, Fernet). Планировщик SLA/напоминаний — APScheduler (из FlatAi); при росте очередей документов/OCR — Celery worker/beat (из seller-ai).
- **Доменная модель (новая):** `Partner` (юрфирма, реквизиты, менеджеры), `Case` (должник, регион, суд, тип процедуры), `Stage` (справочник стадий: приём → сбор документов → подготовка заявления → подача → принятие/введение процедуры → реструктуризация/реализация → завершение → освобождение), `Task` (с SLA, исполнителем, точкой передачи), `Document` (тип, версия, статус проверки, хранилище), `Event` (журнал, неизменяемый), `Deadline` (судебные и внутренние сроки), `Report` (для партнёра).
- **Изоляция данных:** tenant_id (partner_id) во всех таблицах + scoped-зависимости FastAPI (`my_property_ids` в FlatAi → `my_case_ids`) и/или Postgres RLS по образцу `Profi_UZ` (RLS даёт защиту от ошибок в коде).
- **Frontend:** Next.js (App Router) + shadcn/ui + TanStack Query — из `FlatAi/frontend` (BFF-cookie auth, admin-tabs, onboarding-wizard). Экраны MVP: список дел партнёра с фильтрами по стадии/просрочке, карточка дела (таймлайн стадий, документы, дедлайны, комментарии), передача нового дела (форма + загрузка пакета + чек-лист), отчёт партнёру (SLA, сроки, результат), внутренняя панель производства (kanban задач, назначение ФУ/юриста), справочники (суды, СРО/ФУ, шаблоны).
- **Документы:** хранилище файлов на VPS/MinIO (S3-совместимо, в РФ), генерация DOCX по шаблонам (`docxtpl`/python-docx), OCR — `pdftotext + tesseract` (Legal-v4) в воркере; LLM (черновики, чек-лист полноты, извлечение реквизитов из кредитных договоров) — через абстракцию `seller-ai/api/llm` с флагом `AI_MOCK` (как в FlatAi CI) и обязательной проверкой юристом («честные состояния», без «AI-готово» над черновиком).
- **Уведомления:** Telegram (aiogram, FlatAi) + e-mail (Yandex SMTP/Postbox, FlatAi) — партнёру о смене статуса/дедлайне, производству — о просрочке SLA.
- **Эксплуатация:** systemd + nginx + certbot + бэкапы + uptime (FlatAi `deploy/`), CI на чистом Postgres (FlatAi `ci.yml`), деплой по push (Profi_UZ `deploy-vps.yml`) или bundle (seller-ai), Sentry (tezketkaz `lib/sentry.js` как референс).
- **Проектная дисциплина:** `CLAUDE.md` + `HANDOFF.md` + `memory/` (seller-ai), периодические многоагентные аудиты (INTEGRITY_AUDIT), запрет ПДн/секретов в репо (уже зафиксирован в `bfl-production/CLAUDE.md`).

**Вариант B (запасной, если заказчик готов к self-hosted Supabase в РФ):** Supabase self-hosted (Postgres + Auth + Storage + Realtime + Edge) + Next.js/Vite по образцу `Profi_UZ` — быстрее для CRUD и realtime-статусов, RLS «из коробки», но сложнее в эксплуатации (docker-стек Supabase), меньше контроля над фоновыми задачами/OCR, и у пользователя опыт только с hosted-версией.

**Чего не делать:** не развивать Flask-код Legal-v4 (SQLite, threading, отсутствие тестов, дрейф фронта); не переносить репо с ПДн; не начинать с AI-генерации документов — сначала статусы/сроки/документооборот (это то, что партнёр покупает по описанию продукта), AI — как ускоритель производства на этапе 2.

---

## 6. Оценка экономии времени (экспертная оценка, не измерение)

Допущение: 1 разработчик (пользователь) + Claude Code-workflow, MVP = портал партнёра + внутренняя CRM дел + документы + уведомления + админка + деплой/CI, без интеграций с внешними системами (kad.arbitr, Федресурс, Госуслуги — отдельный этап).

| Блок MVP | С нуля (нед.) | С переиспользованием (нед.) | Источник экономии |
|---|---|---|---|
| Каркас backend (auth, роли, OTP, JWT, rate-limit, config, миграции) | 2,0 | 0,5 | FlatAi + seller-ai |
| Доменная модель БФЛ (партнёр/дело/стадии/задачи/SLA/события) | 2,5 | 2,5 | нет (новое) |
| Документы: загрузка, хранилище, версии, OCR, DOCX-шаблоны | 2,0 | 1,25 | Legal-v4 (OCR/DOCX), seller-ai ocr |
| Уведомления Telegram/e-mail, планировщик SLA | 1,0 | 0,25 | FlatAi |
| Frontend ЛК партнёра + внутренняя панель + админка | 4,0 | 2,5 | FlatAi frontend, shadcn, admin-tabs |
| Биллинг партнёров (счета/пакеты, вебхуки) | 1,5 | 0,75 | seller-ai billing |
| CI/деплой/бэкапы/мониторинг | 1,0 | 0,25 | FlatAi ci.yml + deploy/, Profi_UZ workflows |
| Тесты/аудит безопасности/ПДн-гигиена | 1,5 | 1,0 | паттерны есть, писать заново |
| **Итого** | **~15,5** | **~9,0** | **экономия ~40 %** |

Интерпретация: реалистичный горизонт MVP — **8–10 недель** чистой разработки после фиксации конфигурации продукта (стадии, SLA, точки передачи, роли), против 14–18 «с нуля». Ключевой риск сроков — не код, а незафиксированный производственный регламент: пока нет карты стадий и ответственных, доменная модель будет переписываться. Поэтому первые 2–4 недели роли — на конфигурацию (как и просит заказчик), параллельно — подготовка каркаса из FlatAi (это можно показать на собеседовании как «готовый фундамент»).

---

## 7. Обязательные действия перед переиспользованием (безопасность)

1. Ротировать ключ Moonshot и секреты из `Legal-v4/.env` и `kimi_api.py` (считать утёкшими).
2. Не переносить `Legal-v4` целиком; при необходимости сохранить историю — вычистить `uploads/`, `generated/`, `.env`, `templates/mock/mock_responses_kanevsky.json`, логи через `git filter-repo`, затем force-push и уведомить о ротации.
3. В новом репо `bfl-production` — `.gitignore` уже исключает `.env`; добавить исключения `uploads/`, `generated/`, `*.docx`, `*.pdf` и pre-commit-хук поиска секретов (gitleaks) — пункт для первой недели.
4. При переносе FlatAi-скелета проверить, что в него не уезжают демо-учётки (`demo@…`) и break-glass admin из `.env`.
5. Для ПДн должников: шифрование чувствительных полей (Fernet из FlatAi/seller-ai), журнал доступа (кто открыл дело), сроки хранения, размещение сервера в РФ, договор поручения на обработку ПДн с партнёрами — согласовать с юристом СРО.

---

## 8. Источники

Все источники — локальные файлы (снимок репозиториев 2026-09-05), интернет не использовался.

- Контекст задачи: `<scratchpad>/context.md`, `.../scratchpad/vacancy.txt`
- Целевой репо: `/home/user/bfl-production/README.md`, `/home/user/bfl-production/CLAUDE.md`, `/home/user/bfl-production/.gitignore`
- Legal-v4: `/home/user/Legal-v4/app.py` (маршруты, OCR, фоновый поток, fallback-шаблоны), `/home/user/Legal-v4/kimi_api.py` (строка 24 — ключ; промпты; модель), `/home/user/Legal-v4/models.py`, `/home/user/Legal-v4/auth.py`, `/home/user/Legal-v4/payments.py`, `/home/user/Legal-v4/config.py`, `/home/user/Legal-v4/document_generator.py`, `/home/user/Legal-v4/preview_generator.py`, `/home/user/Legal-v4/public/admin.html` (вызовы `/api/admin/*`), `/home/user/Legal-v4/public/static/js/main.js` (дрейф маршрутов), `/home/user/Legal-v4/deploy/*`, `/home/user/Legal-v4/deploy.sh`, `/home/user/Legal-v4/nginx-config/maximov-tech.conf`, `/home/user/Legal-v4/docs/skolokovo/{business_plan,technical_description,checklist}.md`, `/home/user/Legal-v4/RULES.md`, `/home/user/Legal-v4/TARIFFS.md`, `/home/user/Legal-v4/templates/mock/mock_responses_kanevsky.json`, `/home/user/Legal-v4/templates/samples/*.txt`; `git ls-files` (`.env`, `uploads/` — 54 файла, `generated/` — 28 файлов отслеживаются); `git log` (30 коммитов, 2026-03-25)
- Leg-ai / legal-ai-service: `/home/user/Leg-ai/kimi_api.py` (mock), `/home/user/Leg-ai/CODERABBIT_REVIEW.md`, `/home/user/Leg-ai/TARIFFS.md`, `/home/user/Leg-ai/requirements.txt`, `git log` (8 и 2 коммита); `md5sum`/`diff` общих файлов между тремя репо
- legal-ai-simple: `/home/user/legal-ai-simple/README.md`, `/home/user/legal-ai-simple/prompts/legal_prompts.md`, `git log` (15 коммитов, авторы egeg23 / Kimi Claw)
- Поиск тестов: `find … -iname '*test*'` по четырём Legal-репо — пусто; поиск БФЛ-терминов (`банкрот|127-ФЗ|финансовый управляющий|ЕФРСБ`) по всем репо — совпадений в коде пользователя нет (только оферта FlyMart и общие фразы в промптах)
- seller-ai: `/home/user/seller-ai/README.md`, `/home/user/seller-ai/CLAUDE.md`, `/home/user/seller-ai/memory/MEMORY.md`, `/home/user/seller-ai/HANDOFF.md` (шапка), `/home/user/seller-ai/INTEGRITY_AUDIT.md`, `/home/user/seller-ai/api/routers/auth.py`, `/home/user/seller-ai/api/auth_codes.py`, `/home/user/seller-ai/api/billing/plans.py`, `/home/user/seller-ai/api/billing/service.py`, `/home/user/seller-ai/api/llm/`, `/home/user/seller-ai/api/content/ocr.py`, `/home/user/seller-ai/api/rag/`, `/home/user/seller-ai/tests/` (90 файлов), `/home/user/seller-ai/alembic/versions/` (60), `/home/user/seller-ai/ops/`, `/home/user/seller-ai/docs/`, `/home/user/seller-ai/frontend/src/lib/i18n.tsx`
- Profi_UZ: `/home/user/Profi_UZ/README.md`, `/home/user/Profi_UZ/DEPLOY.md`, `/home/user/Profi_UZ/CLAUDE.md`, `/home/user/Profi_UZ/MVP_PLAN.md`, `/home/user/Profi_UZ/supabase/migrations/` (36 файлов; `grep -c 'create policy'` → 44), `/home/user/Profi_UZ/supabase/functions/{auth-bridge,notify,tg-webhook}`, `/home/user/Profi_UZ/.github/workflows/{deploy-vps,deploy-supabase,vps-run}.yml`, `git log` (91 коммит)
- FlatAi: `/home/user/FlatAi/README.md`, `/home/user/FlatAi/backend/app/{security.py,api/auth.py,services/notifications.py,integrations/telegram_gateway.py,scheduler.py,crypto.py,ratelimit.py,url_safety.py,entitlements.py}`, `/home/user/FlatAi/backend/tests/` (19 файлов), `/home/user/FlatAi/backend/pytest.ini`, `/home/user/FlatAi/.github/workflows/ci.yml`, `/home/user/FlatAi/deploy/`, `/home/user/FlatAi/docs/` (SECURITY-AUDIT, GO-LIVE, ESIGN-PLAN, HANDOFF-SAAS), `/home/user/FlatAi/backend/requirements.txt`, `git log` (54 коммита, до 2026-08-18)
- tezketkaz: `/home/user/tezketkaz/README.md`, `/home/user/tezketkaz/pubspec.yaml`, `/home/user/tezketkaz/backend/src/{lib/audit.js,lib/jwt.js,routes/integration.js,middleware/auth.js}`, `/home/user/tezketkaz/backend/prisma/migrations/`, `/home/user/tezketkaz/LAUNCH_CHECKLIST.md`
- FlyMart: `/home/user/FlyMart/README.md`, `/home/user/FlyMart/_ANALYSIS/{FLYMART-ARCHITECTURE,FLYMART-AUDIT-AND-PLAN}.md`
- DevUZ-perfect-: `/home/user/DevUZ-perfect-/README.md`, `/home/user/DevUZ-perfect-/package.json`, `/home/user/DevUZ-perfect-/middleware.ts`, `/home/user/DevUZ-perfect-/lib/qualify/`, `/home/user/DevUZ-perfect-/supabase/migrations/`
- Global-Export: `/home/user/Global-Export/README.md`, `/home/user/Global-Export/package.json`, `/home/user/Global-Export/proxy.ts`, `/home/user/Global-Export/app/admin/(panel)/`
- Нормативные ссылки в тексте (127-ФЗ ст. 213.4; приказ Минэкономразвития № 530 от 05.08.2015; 152-ФЗ ст. 18 ч. 5) приведены по памяти без проверки в интернете — **требуют верификации юристом** перед включением в план.
