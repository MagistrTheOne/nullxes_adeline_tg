# Adeline Mini App

Стек: Vite + React + shadcn/ui + lucide + `@tma.js/sdk-react` + `@anam-ai/js-sdk`.

Экраны: **Home** (превью) · **Chat** (общая история с Telegram) · **Live** (Anam WebRTC, Start/Stop).

## Build

```powershell
cd D:\NULLXES\NULLXES_HUB_BOT\miniapp
npm install
npm run build
```

## Запуск (рекомендуется localhost.run)

Без ngrok interstitial / Cloudflare 1033.

Терминал 1 — бот:

```powershell
cd D:\NULLXES\NULLXES_HUB_BOT
.\venv\Scripts\Activate.ps1
python main.py
```

Терминал 2 — туннель:

```powershell
cd D:\NULLXES\NULLXES_HUB_BOT
.\scripts\run_localhost_run.ps1
```

Скопируй `https://….lhr.life` в `.env` → `WEBAPP_PUBLIC_URL`, перезапусти бота, в Telegram: `/start` → Mini App.

Текущий URL:

```env
WEBAPP_PUBLIC_URL=https://e483ed52e0b71f.lhr.life
```

Для продакшена: `WEBAPP_SKIP_AUTH=0` (и лучше свой домен / VPS, не free-туннель).

Альтернативы: `run_localtunnel.ps1` · `run_ngrok.ps1` (бесплатно — страница «Visit Site») · `run_tunnel.ps1` (Cloudflare + Happ часто ломается).

