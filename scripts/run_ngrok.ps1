# ngrok tunnel -> local Mini App on :8080
# Usually more reliable than Cloudflare quick tunnels behind Happ VPN.
#
#   .\scripts\run_ngrok.ps1
#
# Then copy the https://....ngrok-free.dev URL into WEBAPP_PUBLIC_URL and restart the bot.
# Local inspector: http://127.0.0.1:4040

ngrok.cmd http 8080
