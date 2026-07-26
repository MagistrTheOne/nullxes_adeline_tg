# localhost.run SSH tunnel -> local Mini App on :8080
# No ngrok "Visit Site" page. Keep this window open.
#
#   .\scripts\run_localhost_run.ps1
#
# Copy the https://….lhr.life URL into WEBAPP_PUBLIC_URL and restart the bot.

ssh -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 -o ExitOnForwardFailure=yes -R 80:127.0.0.1:8080 nokey@localhost.run
