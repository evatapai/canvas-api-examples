# Canvas API Examples

Runnable Python examples for the Canvas LMS REST API. Clone the repo, add your own Canvas URL and access token, and run each example from the command line or from a small local web page.

Everything runs on your computer. Your token stays in a local `.env` file and is sent only to your own Canvas domain.

## Quick start

You need Python 3.10 or newer (tested on 3.13) and a Canvas account you can get an access token for.

```bash
git clone <this repository's URL>
cd canvas-api-examples
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and set `CANVAS_BASE_URL` to your Canvas domain, for example `https://your-school.instructure.com`. Then add your credentials. [Get your credentials](#get-your-credentials) below explains both ways to get them, step by step. The shortest is an access token in `CANVAS_TOKEN`.

Then run the first example:

```bash
python -m recipes.01_auth
```

It prints your Canvas user ID and name. If it does, your setup works.

## Get your credentials

You need a Canvas URL and one of two kinds of credentials. Pick one.

### Option A: a personal access token (simplest)

1. In Canvas, open your profile, then **Settings**.
2. Under **Approved Integrations**, create a **New Access Token**. Canvas shows it once, so copy it right away.
3. Put it in `.env` as `CANVAS_TOKEN`.

Your school can turn this option off, and you can set an expiry date on the token.

### Option B: a developer key with OAuth2 (works when Option A is off)

A developer key gives you an access token that lasts about one hour, plus a refresh token that gets new access tokens without asking you to sign in again. The examples use the refresh token automatically, so you set this up once.

You need: a Canvas **account admin** for step 1 (ask yours if you are not one), and a terminal with `curl`. The commands below are for macOS and Linux. On Windows, use WSL or Git Bash.

**Step 1: create the developer key (account admin).**

1. Open `https://<your-canvas-domain>/accounts/<account-id>/developer_keys`. Or go to **Admin**, pick the account, then **Developer Keys**. Check the page header shows the account your users sign in to. A key only works for logins in the account that owns it.
2. Click **+ Developer Key**, then **API Key**.
3. Fill in:
   - **Key Name:** for example `canvas-api-examples`.
   - **Owner Email:** your own address.
   - **Redirect URIs:** `https://localhost/callback`
   - Turn on **Enforce Scopes** and tick the scopes in the table below. Tick only the ones for the recipes you will run. Recipes 1, 2 and 5 only read data.
4. Click **Save**, then switch the key's state to **ON**.
5. Copy the **client ID**: the number in the Details column.
6. Click **Show Key** under it to see the **client secret**. Store it in a password manager.

| Recipes | Scopes to tick |
| --- | --- |
| 1, 5, 6 | `url:GET\|/api/v1/users/:id` |
| 2 | `url:GET\|/api/v1/courses` |
| 3 | `url:POST\|/api/v1/courses/:course_id/assignments`<br>`url:DELETE\|/api/v1/courses/:course_id/assignments/:id`<br>`url:PUT\|/api/v1/courses/:course_id/assignments/:assignment_id/submissions/:user_id`<br>`url:GET\|/api/v1/courses/:course_id/student_view_student` |
| 4 | `url:POST\|/api/v1/courses/:course_id/files`<br>`url:GET\|/api/v1/files/:id/create_success`<br>`url:DELETE\|/api/v1/files/:id` |
| 6 | `url:POST\|/api/v1/courses/:course_id/enrollments`<br>`url:DELETE\|/api/v1/courses/:course_id/enrollments/:id`<br>`url:GET\|/api/v1/courses/:course_id/users` |
| 7 | `url:POST\|/api/v1/courses/:course_id/pages`<br>`url:DELETE\|/api/v1/courses/:course_id/pages/:url_or_id`<br>`url:POST\|/api/v1/courses/:course_id/modules`<br>`url:DELETE\|/api/v1/courses/:course_id/modules/:id`<br>`url:POST\|/api/v1/courses/:course_id/modules/:module_id/items`<br>`url:GET\|/api/v1/courses/:course_id/modules/:module_id/items` |
| 8 | `url:POST\|/api/v1/courses/:course_id/discussion_topics`<br>`url:DELETE\|/api/v1/courses/:course_id/discussion_topics/:topic_id`<br>`url:POST\|/api/v1/courses/:course_id/discussion_topics/:topic_id/entries`<br>`url:POST\|/api/v1/courses/:course_id/discussion_topics/:topic_id/entries/:entry_id/replies`<br>`url:GET\|/api/v1/courses/:course_id/discussion_topics/:topic_id/view` |

**Step 2: sign in as the user who will own the token.**

The examples act as this user, so use the account you want them to run as.

1. Open a private browser window.
2. Sign in to Canvas as that user. If your school sends you to a single sign-on page and you have a Canvas password, `https://<your-canvas-domain>/login/canvas` is the username and password page.
3. In the same window, open `https://<your-canvas-domain>/api/v1/users/self`. The `name` must be the user you want. If it is someone else, sign out and repeat.

Keep this window open for the next step.

**Step 3: authorize the key and copy the code.**

1. In the same window, open this address as one line. Replace `<your-canvas-domain>` and `<client-id>`. It asks for the scopes from step 1. A scope that is not ticked on the key makes Canvas answer `invalid_scope`, so remove the ones you did not tick:

   ```
   https://<your-canvas-domain>/login/oauth2/auth?client_id=<client-id>&response_type=code&redirect_uri=https://localhost/callback&state=abc&scope=url:GET%7C/api/v1/users/:id%20url:GET%7C/api/v1/courses%20url:POST%7C/api/v1/courses/:course_id/assignments%20url:DELETE%7C/api/v1/courses/:course_id/assignments/:id%20url:PUT%7C/api/v1/courses/:course_id/assignments/:assignment_id/submissions/:user_id%20url:GET%7C/api/v1/courses/:course_id/student_view_student%20url:POST%7C/api/v1/courses/:course_id/files%20url:GET%7C/api/v1/files/:id/create_success%20url:DELETE%7C/api/v1/files/:id%20url:POST%7C/api/v1/courses/:course_id/enrollments%20url:DELETE%7C/api/v1/courses/:course_id/enrollments/:id%20url:GET%7C/api/v1/courses/:course_id/users%20url:POST%7C/api/v1/courses/:course_id/pages%20url:DELETE%7C/api/v1/courses/:course_id/pages/:url_or_id%20url:POST%7C/api/v1/courses/:course_id/modules%20url:DELETE%7C/api/v1/courses/:course_id/modules/:id%20url:POST%7C/api/v1/courses/:course_id/modules/:module_id/items%20url:GET%7C/api/v1/courses/:course_id/modules/:module_id/items%20url:POST%7C/api/v1/courses/:course_id/discussion_topics%20url:DELETE%7C/api/v1/courses/:course_id/discussion_topics/:topic_id%20url:POST%7C/api/v1/courses/:course_id/discussion_topics/:topic_id/entries%20url:POST%7C/api/v1/courses/:course_id/discussion_topics/:topic_id/entries/:entry_id/replies%20url:GET%7C/api/v1/courses/:course_id/discussion_topics/:topic_id/view
   ```

2. Canvas shows your key's name and the user's name. Check both, then click **Authorize**.
3. The browser goes to `https://localhost/callback?code=...&state=abc`. The page will not load, and that is expected. Copy the value after `code=` from the address bar.
4. Use the code right away. It works once and expires quickly.

The `redirect_uri` must match the one on the key exactly.

**Step 4: exchange the code for tokens.**

Run this in your terminal. `read -rs` keeps the secret out of your shell history and off the screen:

```bash
read -rs SECRET        # paste the client secret, then press Enter
curl -X POST https://<your-canvas-domain>/login/oauth2/token \
  -d grant_type=authorization_code \
  -d client_id=<client-id> \
  -d client_secret="$SECRET" \
  -d redirect_uri=https://localhost/callback \
  -d code=<code>
```

The response contains `access_token`, `refresh_token`, `expires_in` (about 3600 seconds) and a `user` object. Copy the `refresh_token` into your password manager. Then run `unset SECRET`.

**Step 5: put the values in `.env`.**

```
CANVAS_BASE_URL=https://<your-canvas-domain>
CANVAS_CLIENT_ID=<client-id>
CANVAS_CLIENT_SECRET=<client secret>
CANVAS_REFRESH_TOKEN=<refresh token>
```

You do not need the access token in `.env`. The examples use the refresh token to get a fresh one whenever Canvas rejects the old one, and they keep it in memory only. You must set all three of `CANVAS_CLIENT_ID`, `CANVAS_CLIENT_SECRET` and `CANVAS_REFRESH_TOKEN`, or none of them. If Canvas ever issues a new refresh token, the examples print a warning telling you to update `.env`.

**Step 6: check it.**

```bash
python -m recipes.01_auth
```

It prints your user ID and name.

**If something goes wrong:**

| What you see | Likely cause | Fix |
| --- | --- | --- |
| `error=invalid_scope` | The address has no `scope` parameter, or asks for a scope the key does not have | Add `scope=` with space-separated scopes, and tick each one on the key |
| `error=client_not_allowed_for_user` | You are signed in as a user outside the account that owns the key | Create the key in your users' account, sign in as that user, and authorize again |
| `error=access_denied` | You clicked Deny, or the key is OFF | Switch the key to ON and try again |
| `users/self` shows another person | You are signed in as someone else | Sign out and sign in as the right user |
| The token exchange fails | The code was already used or expired, or `redirect_uri` differs from the key | Repeat step 3 and exchange the code immediately |
| A recipe fails with `401` after you add scopes | Tokens issued earlier cannot use new scopes | Repeat steps 3 and 4 and save the new refresh token |
| `Invalid access token.` after about an hour | The access token expired | Set the three refresh values in `.env` |

Treat the client secret and refresh token like passwords. Never commit them, and never paste them into chat, tickets or screenshots.

## The examples

| Recipe | What it shows | Changes data? |
| --- | --- | --- |
| `01_auth` | Authenticate and call `GET /api/v1/users/self` | No |
| `02_list_courses` | List courses and follow every page of results | No |
| `03_assignment_and_grade` | Create an assignment, grade the course's Test Student, delete the assignment | Yes |
| `04_file_upload` | Canvas's three-step file upload, then delete the file | Yes |
| `05_errors_and_limits` | What a `401` looks like, and the rate-limit headers | No |
| `06_enroll_and_roster` | Enroll a demo user as a Student, list the roster with roles, remove the enrollment | Yes |
| `07_module_with_items` | Create a page and a module, add a heading, the page and a link, then delete both | Yes |
| `08_discussion_topic` | Post a discussion topic with an entry and a reply, read the thread, delete the topic | Yes |

Run any of them with `python -m recipes.<name>`, for example `python -m recipes.02_list_courses`.

Each recipe is one short file. The shared code that handles pagination, retries when Canvas throttles you (`429`), and `401` errors is in `canvaslib/client.py`.

### Recipes that change data

Recipes 3, 4 and 6 to 8 create and delete objects. They only run in the course you name in `.env`:

```
CANVAS_COURSE_ID=<numeric id of a demo course>
CANVAS_ENROLL_USER_ID=<numeric id of a demo user>   # recipe 6 only
```

Recipe 6 needs a second, made-up user, because Canvas does not let you remove your own enrollment. The user must have a login in your Canvas account, and your user needs permission to add and remove students.

Use a demo course, never a course with real students. Recipe 3 grades the course's built-in Test Student, and recipe 6 enrolls only the demo user you name in `CANVAS_ENROLL_USER_ID`, without sending email. All of them delete what they create. If a run fails halfway, check the course for leftovers.

## The local web page

```bash
python server.py
```

Open <http://localhost:3000>. Each recipe is a card with a **Run** button, its result, and its code. The server listens on `localhost` only and refuses requests that come from other websites. Recipes that change data ask for confirmation first.

## Tests

```bash
pytest              # mocked tests: no token and no network needed
pytest -m live      # live tests: call your real Canvas using .env
```

The mocked tests check the code against what Canvas is documented to do. The live tests check it against what Canvas does today, so they catch API changes and wrong assumptions in the mocks. The live tests that change data skip themselves unless `CANVAS_COURSE_ID` is set.

## Keep your data safe

- Never commit `.env`. It is in `.gitignore`.
- Recipe output prints real data from your Canvas account. Before you paste output into an issue, a ticket or a document, remove names, emails and IDs that belong to real students or staff.
- Student data is protected by privacy laws such as FERPA and GDPR. Test against a demo course with made-up data.

## Layout

```
canvaslib/    shared client and runner
recipes/      one file per example
server.py     local web page and API
public/       the web page
tests/        mocked and live tests
```

## License

MIT. See `LICENSE`.
