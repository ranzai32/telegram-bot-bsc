# BSC Pump Telegram Bot

Простой и интуитивный Telegram бот для управления BSC pump ботом.

## Особенности

- 🚀 **Максимально простой UI**: вставь контракт → нажми старт
- 💰 Автоматическое создание кошелька
- ✅ Проверка поддержки токенов
- 💱 Конвертация BNB ↔ USD
- 📊 Мониторинг баланса

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

3. Отредактируйте `.env` и добавьте свой токен бота от @BotFather:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
API_BASE_URL=http://localhost:8080
```

## Запуск

Убедитесь, что Rust backend запущен на порту 8080, затем:

```bash
python main.py
```

## Использование

1. Откройте бота в Telegram
2. Отправьте `/start`
3. Вставьте адрес контракта токена (CA)
4. Укажите сумму для pump в BNB
5. Укажите сумму для swap в BNB
6. Нажмите кнопку **СТАРТ** 🚀

## Доступные команды

- `/start` - Начать работу с ботом
- `/balance` - Проверить баланс кошелька
- `/cancel` - Отменить текущую операцию
- `/help` - Показать справку

## User Flow

```
/start → Создание кошелька
   ↓
Ввод адреса контракта (CA)
   ↓
Проверка поддержки токена
   ↓
Ввод суммы pump (BNB)
   ↓
Ввод суммы swap (BNB)
   ↓
Подтверждение → СТАРТ 🚀
```

## Структура проекта

```
telegram-bot/
├── main.py             # Main entry point
├── config.py           # Configuration
├── api_client.py       # Rust API client
├── handlers/           # Message and command handlers
│   ├── __init__.py
│   ├── common.py       # Common commands (start, help, balance)
│   └── session.py      # Session creation flow
├── keyboards/          # Inline keyboards
│   ├── __init__.py
│   └── inline.py
├── models/             # Data models
│   ├── __init__.py
│   └── session.py      # User session storage
├── states/             # Conversation states
│   ├── __init__.py
│   └── conversation.py
├── utils/              # Utility functions
│   ├── __init__.py
│   └── converters.py   # Currency converters
├── requirements.txt    # Python dependencies
├── .env.example        # Example configuration
└── README.md          # Documentation
```

## API Integration

Бот взаимодействует с Rust backend через следующие эндпоинты:

- `GET /user/{telegram_id}/wallet/` - Получить/создать кошелек
- `POST /user/{telegram_id}/wallet/balance` - Проверить баланс
- `GET /token/{token_ca}/is-supported` - Проверить поддержку токена
- `GET /token/{token_ca}/pools` - Получить пулы ликвидности
- `POST /bot/session/run` - Запустить pump сессию
- `POST /price/bnb-to-usd` - Конвертировать BNB в USD

## Требования

- Python 3.8+
- Запущенный Rust backend (порт 8080)
- Telegram Bot Token от @BotFather
