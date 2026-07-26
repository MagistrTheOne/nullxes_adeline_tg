# nullxes_adeline_tg

Telegram bot + Mini App for **Adeline Kalen / NULLXES**.

- **Bot:** aiogram, OpenAI brain + tools, Anam voice replies  
- **Mini App:** Vite + React + shadcn/ui + `@anam-ai/js-sdk` (Home / Chat / Live)

## Quick start

1. Copy `.env.example` → `.env` and fill secrets  
2. `python -m venv venv` → activate → `pip install -r requirements.txt`  
3. `cd miniapp && npm install && npm run build`  
4. `python main.py`  
5. Expose `:8080` with HTTPS tunnel (`scripts/run_localhost_run.ps1`) and set `WEBAPP_PUBLIC_URL`

See [miniapp/README.md](miniapp/README.md) for Mini App details.
