# 🐄 Cow Monitor

Система видеоаналитики для мониторинга КРС. Детектирует активность (кормление/водопой), сон и оценивает упитанность (БКС) по видеопотоку с камер.

---

## Быстрый старт

```bash
git clone <repo_url>
cd cow_monitor

python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt

python main.py
```

---

## Переменные окружения

Создай файл `.env` в корне проекта:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=cow_monitor
DB_USER=postgres
DB_PASSWORD=yourpassword
```

---

## Структура проекта

```
cow_monitor/
│
├── main.py                        # Точка входа
│
├── database/                      # БД: модели, подключение, инициализация
│   ├── database.py                # engine, SessionLocal, Base
│   ├── models.py                  # Все SQLAlchemy-модели
│   ├── initdb.py                  # Создание таблиц
│   └── reportsdb.py               # Запросы для отчётов
│
├── external_activity/             # Модуль активности (ест/пьёт)
│   ├── activity_analysis.py       # Основная логика анализа
│   ├── sleep_analysis.py          # Анализ сна (лежит/стоит)
│   ├── db_config.py               # Подключение к БД для модуля
│   └── models/
│       ├── bestdown.pt            # YOLOv8: поза коровы (лежит/стоит)
│       └── coweat.pt              # YOLOv8: ест/пьёт
│
├── external_bcs/                  # Модуль оценки упитанности (БКС) с распознаванием ID
│   ├── bcs_analysis.py            # Детекция, ID по бирке, BCS, видео, запись в БД
│   ├── requirements.txt
│   └── models/
│       ├── best_number_classifier.pt  # YOLO: распознавание номера бирки (1–4)
│       ├── bcs_regressor.pth      # Регрессор БКС
│       └── scaler.pkl             # Нормализатор признаков
│   # Детектор коровы: external_activity/models/cow_eat.pt
│
├── ui/                            # Интерфейс PyQt6
│   ├── main_window.py             # Главное окно
│   ├── styles.py                  # Стили QSS
│   ├── notifications.py           # Уведомления
│   ├── reports_dialog.py          # Диалог отчётов
│   ├── bcs_window.py              # Окно БКС
│   └── pages/
│       ├── page_cameras.py        # Страница камер
│       ├── page_monitoring.py     # Мониторинг
│       ├── page_database.py       # База данных
│       ├── page_notifications.py  # Уведомления
│       └── page_enterprise.py     # Предприятие
│
├── vision/                        # Воркеры видеообработки
│   ├── worker.py                  # Основной воркер (активность)
│   └── sleep_worker.py            # Воркер для анализа сна
│
├── reports/                       # Генерация отчётов
│   ├── excel_report.py
│   └── pdf_report.py
│
├── snapshots/                     # Снимки с камер (авто)
├── feedframes/                    # Кадры из видео (авто)
│
├── requirements.txt
└── .env                           # Не коммитить!
```

---

## Модули

### 🍽️ Активность (`external_activity`)
Анализирует видео и определяет, ест или пьёт корова. Результаты пишутся в таблицы `sessions` и `frames`.

### 📊 БКС (`external_bcs`)
Оценивает упитанность коровы по шкале 1–5 с **распознаванием ID по бирке** (YOLO-классификатор номера).
Поддерживает фото и видео. Результаты — в `bcs_sessions` и `bcs_measurements` (поля `recognized_tag`, `frame_number`, `video_path`).

---

## База данных

PostgreSQL. Таблицы создаются автоматически при первом запуске через `database/initdb.py`.

| Таблица | Описание |
|---|---|
| `cows` | Коровы |
| `cameras` | Камеры |
| `sessions` | Сессии активности (ест/пьёт) |
| `frames` | Кадры активности |
| `sleep_sessions` | Сессии сна |
| `sleep_frames` | Кадры сна |
| `bcs_sessions` | Сессии оценки БКС |
| `bcs_measurements` | Измерения БКС |
| `notifications` | Уведомления |
| `ai_activities` | Лог всех ИИ-событий |

---

## Стек

- **Python 3.11+**
- **PyQt6** — интерфейс
- **SQLAlchemy + psycopg2** — БД
- **Ultralytics YOLOv8** — детекция
- **OpenCV** — обработка видео
- **ReportLab / openpyxl** — отчёты
