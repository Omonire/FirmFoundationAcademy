# Putting the website online

This guide is written for someone who has not done this before. Follow the
steps in order. It takes about fifteen minutes and costs nothing.

If any step says something you do not understand, that is normal. Send the
step number to whoever is helping you.

---

## What is happening

Right now the website is a folder of files on your computer. Putting it
online means putting that same folder on a company's computers, called
**Vercel**, so that anyone with the internet address can visit it.

There are two parts:

| Part | What it is |
|---|---|
| The website itself | The seven pages you already know |
| A small program | Serves those pages with the menu and footer already built in |

The program is written in Python, in a file called `api/index.py`.

---

## Before you start: two accounts

- **GitHub** — you already have this one.
- **Vercel** — you need to make one. Go to <https://vercel.com/signup> and
  sign up. Choose "Continue with GitHub" and it will link the two together.
  The free plan is fine and does not ask for card details.

---

## Step 1 — Connect the two

1. Go to <https://vercel.com> and log in.
2. Click **Add New...** then **Project**.
3. You will see a list of your GitHub repositories. Find
   `FirmFoundationAcademy` and click **Import**.

   > If it is not on the list, click **Adjust GitHub App Permissions**
   > and give Vercel access, then come back.

4. On the next screen, the defaults are fine. Click **Deploy**.

That is it. Wait a minute or two and your site is live at a free address
like `firm-foundation-academy.vercel.app`.

---

## Step 2 — Add the secret settings

You will do this now even though nothing uses it yet. It means the settings
are ready and no secret ever gets typed into a web page.

1. In Vercel, open your project.
2. Click the **Settings** tab, then **Environment Variables** on the left.
3. Click **Add Environment Variable** three times, adding each of these.
   Leave every other box empty, including the one that asks which branches
   to apply it to.

   | Name | Value |
   |---|---|
   | `FLASK_ENV` | `production` |
   | `GEMINI_API_KEY` | leave empty for now |
   | `SUPABASE_URL` | `https://pmdnmmyoomecrycsjwoa.supabase.co` |

4. Click **Save**.

> **About secrets.** A "secret" is a piece of information that should not be
> public — like a password or an API key. Anything written directly into a
> web page can be read by anyone who visits it, by right-clicking and
> choosing "View Source". So keys go here, in Vercel's settings, where only
> you can see them. The program reads them from the environment. Never paste
> a key into a web page.

---

## Step 3 — Check it worked

Open your live address and click through all seven pages. Check:

- [ ] The menu appears at the top of every page
- [ ] The footer appears at the bottom of every page
- [ ] The page you are on is highlighted in the menu
- [ ] The Gallery opens and photos appear

Now open <yoursite>/health. You should see a short line of text like:

```
{"configured":{...},"env":"production","status":"ok"}
```

It only says whether each setting is present or missing. It never shows the
actual value, so it is safe to share. `status: ok` means the site is running.

---

## Running it on your own computer

You do not need this to put the site online, but it lets you see changes
before the internet does.

1. Open the project folder.
2. In the address bar, type `cmd` and press Enter.
3. Type these one at a time, pressing Enter after each:

   ```
   pip install -r api/requirements.txt
   python -m api.index
   ```

4. Open <http://127.0.0.1:5000> in your browser.
5. To stop it, click the window and press `Ctrl` + `C`.

### When you change a page

1. Edit the file and save it.
2. Refresh the browser. You will see the change straight away.
3. When you are happy, commit and push:

   ```
   git add .
   git commit -m "describe what you changed"
   git push
   ```

4. Vercel notices and updates the live site by itself, usually within a
   minute or two. You can watch it happen on the **Deployments** tab.

---

## When something goes wrong

**The site shows "Deployment failed".** Open the Deployments tab, click the
red one, and read the message at the bottom. Most often it means a file was
spelled slightly differently. The most common cause is `api/index.py` not
being in a folder called `api`.

**The pages load but have no menu or footer.** The `api` folder is missing,
or `vercel.json` is not in the top-level folder. Both need to sit next to
`index.html`.

**A change does not show up on the live site.** You edited the file but did
not run `git push` — steps 3 and 4 above.

**Something is wrong with a specific page.** Run the tests on your computer:

```
python -m api.test
```

If it says `OK`, the program is working and the problem is in the page
content. If it lists a failure, the name of the test tells you which part.

---

## The one rule to remember

Never type a secret into a web page file. If a key is ever needed, it goes
in Step 2 instead. If you are ever unsure whether something is a secret,
assume it is and ask.
