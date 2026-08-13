# BGAD News Flash site

Static host for the daily News Flash HTML editions. Zero dependencies, Node 18+.

## Routes

| Path | What it serves |
| --- | --- |
| `/` and `/latest` | 302 redirect to the newest issue |
| `/issues/YYYY-MM-DD.html` | a specific issue (this is the URL to flip) |
| `/archive` | simple list of every published issue |
| `/archive.json` | the same list as JSON |
| `/health` | health check used by Railway |

Issues are just files in `public/issues/`, named `YYYY-MM-DD.html` so they sort correctly.

## Deploying to Railway

Option A, from your machine, no repo needed:

```
npm i -g @railway/cli
railway login
railway init        # creates the project, pick a name like bgad-newsflash
railway up          # deploys this folder
railway domain      # generates a public https://<name>.up.railway.app URL
```

Option B, GitHub connected. This folder is already a git repo with one commit,
branch `main`, and the remote set to
`https://github.com/gerdschenkel/bgad-newsflash.git`. Create that repo on
GitHub (empty, no README), then:

```
git push -u origin main
```

In Railway choose New Project, Deploy from GitHub repo, pick `bgad-newsflash`.
Railway detects Node from `package.json` and runs `npm start`. Click Settings,
Networking, Generate Domain. From then on every push redeploys the site.

A custom domain like `newsflash.bgadconsulting.com` can be added under
Settings, Networking, Custom Domain, then a CNAME at your DNS provider.

## Publishing a new issue

Drop the day's HTML into `public/issues/` named by date, then redeploy:

```
cp "BGAD News Flash 14 August 2026.html" public/issues/2026-08-14.html
railway up
```

Or, with the GitHub option, commit and push. Railway redeploys on push, so the
daily routine only has to commit one file.

## Flipboard

Flip `https://<your-domain>/issues/2026-08-13.html`, not `/latest`. A dated URL
is a stable permalink, so the card keeps showing the right issue. The page
carries Open Graph title and description tags, which is what Flipboard reads
when it builds the card.

Cost note: this fits inside Railway's hobby usage. It is a single small Node
process serving static files, idle most of the day.
