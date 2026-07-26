# localtunnel -> local Mini App on :8080
# No ngrok "Visit Site" interstitial. Keep this window open.
#
#   .\scripts\run_localtunnel.ps1
#
# Copy the https://….loca.lt URL into WEBAPP_PUBLIC_URL and restart the bot.

npx --yes localtunnel --port 8080
