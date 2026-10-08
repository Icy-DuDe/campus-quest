# Campus Quest — The Last Ward

## Quick start (Windows PowerShell in VS Code)

1. Extract this ZIP. Open the **campus_quest_complete** folder in VS Code.
2. From the top-level folder, run:

   ```powershell
   python -m venv .venv
   .venv\Scripts\python.exe -m pip install -r campus_quest_backend_final\requirements.txt
   .venv\Scripts\python.exe campus_quest_backend_final\app.py
   ```

3. Open **http://127.0.0.1:5000** in Chrome. The Flask backend now serves the frontend, too. **Only one terminal/server is needed.**
4. Click **ENTER THE GROUNDS** and allow location permission.

## Test at home (Chrome desktop)

Your actual GPS is not at DAVV, so use Chrome's location override to simulate a journey:

1. Press F12 → menu (three dots in Developer Tools) → More tools → Sensors.
2. In Sensors > Location, choose **Other** and type the latitude and longitude of checkpoint 3.
3. Start a **new** game. Repeat for checkpoints 2 or 4, then the other, then 1 or 5, then the other.
4. If the GPS does not update after changing the coordinate, refresh the page. Game progress is preserved by the backend.

Coordinates:

| # | Place | Latitude | Longitude |
|---|---|---|---|
| 1 | Ancient ruins of Akshank | 22.681686603215834 | 75.87866723631592 |
| 2 | Seasonal island view | 22.681073904231067 | 75.878925999408 |
| 3 | Cricket ground | 22.68041805437934 | 75.88003275723203 |
| 4 | C-shaped building | 22.681496434563755 | 75.88100346491773 |
| 5 | Vishesh Jupiter Hospital corner | 22.682554447540795 | 75.88115789942242 |

## Campus deployment tomorrow

- The local `127.0.0.1` URL **will not work from another phone**.
- Browser GPS on phones normally requires HTTPS; deploy the combined Flask app to an HTTPS host (e.g. Render web service). Leave the Render **Root Directory blank** (repository root), set build command to `pip install -r campus_quest_backend_final/requirements.txt`, and start command to `gunicorn --chdir campus_quest_backend_final --bind 0.0.0.0:$PORT app:app`. Commit both `frontend` and `campus_quest_backend_final` folders.
- `gunicorn` is already in the bundled requirements. Configure a strong `CAMPUS_QUEST_ADMIN_TOKEN`.
- The application stores player games in a local SQLite file. Free services may reset local storage on restart; a long-lived production deployment needs persistent storage.
- Your planned 25 m geofences need real-phone field testing. Avoid obstructed or inaccessible spots; obey campus rules and do not rush between locations.

## Technical note

The backend decides checkpoint completion and timer expiration. The frontend only displays clues, dialogue, GPS accuracy, countdown and map markers. Browser developer-tools GPS simulation is **test-only**. The player coordinates aren't proof against malicious GPS spoofing.

## Realistic testing scope

Automated Python logic tests check key game transitions and timeout behavior. Browser JavaScript passes Node syntax checking. Actual phone GPS, map rendering, and HTTPS hosting still require hands-on validation on your devices; they are not guaranteed in advance.
