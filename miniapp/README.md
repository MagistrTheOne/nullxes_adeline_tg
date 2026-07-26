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

Один терминал — бот + туннель сами:

```powershell
cd D:\NULLXES\NULLXES_HUB_BOT
.\scripts\start.ps1
```

`START_TUNNEL=1` (по умолчанию): `python main.py` сам поднимает localhost.run и пишет `WEBAPP_PUBLIC_URL` в `.env`.  
Подожди в логе `WEBAPP_PUBLIC_URL -> https://….lhr.life`, затем в Telegram: `/start` → Mini App.

Текущий URL:

```env
WEBAPP_PUBLIC_URL=https://e483ed52e0b71f.lhr.life
```

Для продакшена: `WEBAPP_SKIP_AUTH=0` (и лучше свой домен / VPS, не free-туннель).

Альтернативы: `run_localtunnel.ps1` · `run_ngrok.ps1` (бесплатно — страница «Visit Site») · `run_tunnel.ps1` (Cloudflare + Happ часто ломается).

