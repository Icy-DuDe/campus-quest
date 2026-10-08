# Campus Quest — Final Backend

IET-DAVV Harry Potter-themed geofenced campus game.

## Final coordinates

1. Ancient Ruins of Akshank
   22.681686603215834, 75.87866723631592

2. Seasonal Island View
   22.681073904231067, 75.878925999408

3. Cricket Ground
   22.68041805437934, 75.88003275723203

4. C-Shaped Building
   22.681496434563755, 75.88100346491773

5. Vishesh Jupiter Corner
   22.682554447540795, 75.88115789942242

## Game rules

- Normal checkpoint radius: 25 m.
- Checkpoint 3 starts the game.
- Reaching checkpoint 3 starts a 7-minute countdown.
- Checkpoints 2 and 4 must both be reached within those 7 minutes.
- Reaching either 2 or 4 gives the OTHER checkpoint a +25 m radius for 3 minutes.
- Therefore the boosted checkpoint radius is 50 m.
- Reaching both starts the final 5-minute phase.
- Checkpoints 1 and 5 must both be reached within those 5 minutes.
- Reaching both wins the game.
- Missing either timer causes GAME_OVER.
- The backend, not the frontend, owns the game state and timers.

## Install and run

Windows PowerShell:

```powershell
cd campus_quest_backend_final
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:CAMPUS_QUEST_ADMIN_TOKEN="change-this-token"
python app.py
```

Server:

http://127.0.0.1:5000

## Automated tests

```powershell
pytest -q
```

## API test without frontend

Start the server, then use PowerShell.

Health:

```powershell
Invoke-RestMethod http://127.0.0.1:5000/api/health
```

Start:

```powershell
$game = Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:5000/api/game/start `
  -ContentType "application/json" `
  -Body '{"player_name":"Test Player"}'

$game | ConvertTo-Json -Depth 10
$game.game_id
```

Replace `$game.game_id` below with the returned ID.

Send the exact Checkpoint 3 coordinate:

```powershell
$body = @{
  latitude  = 22.68041805437934
  longitude = 75.88003275723203
  accuracy  = 5
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:5000/api/game/$($game.game_id)/location" `
  -ContentType "application/json" `
  -Body $body | ConvertTo-Json -Depth 10
```

You should now see:

```text
phase = FIND_WAND_AND_BROOM
seconds_remaining ≈ 420
```

Then test checkpoint 2:

```powershell
$body = @{
  latitude  = 22.681073904231067
  longitude = 75.878925999408
  accuracy  = 5
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:5000/api/game/$($game.game_id)/location" `
  -ContentType "application/json" `
  -Body $body | ConvertTo-Json -Depth 10
```

It should say checkpoint 2 was reached and checkpoint 4 received a temporary radius boost.

Then send checkpoint 4:

```powershell
$body = @{
  latitude  = 22.681496434563755
  longitude = 75.88100346491773
  accuracy  = 5
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:5000/api/game/$($game.game_id)/location" `
  -ContentType "application/json" `
  -Body $body | ConvertTo-Json -Depth 10
```

The phase should become:

```text
FIND_SHIELD_AND_ARTIFACTS
seconds_remaining ≈ 300
```

Then send checkpoint 1 and checkpoint 5 in the same way.

After checkpoint 5:

```text
phase = WON
```

## Testing the 25 m radius

For a real negative test, send a coordinate that is clearly more than 25 m away from a checkpoint.

The backend must leave the checkpoint unreached.

Do not use a point only 1–2 m outside the radius for the first test because GPS/map coordinate rounding can make that ambiguous.

## Testing the timer

You do NOT need to wait seven minutes during development.

For a quick timer test, temporarily change:

```python
"death_eater_duration_seconds": 420
```

to:

```python
"death_eater_duration_seconds": 5
```

and:

```python
"voldemort_duration_seconds": 300
```

to:

```python
"voldemort_duration_seconds": 5
```

Restart the server and test.

Restore 420 and 300 before the final build.

## Real phone testing

Browser geolocation normally requires HTTPS when deployed.

For the local laptop/phone test, the simplest approach is to deploy the backend/frontend to a service with HTTPS, or use an appropriate HTTPS development tunnel.

When physically testing at IET-DAVV:

- allow location permission
- use high-accuracy location if the browser offers it
- wait for a good GPS accuracy reading
- stand at the intended checkpoint
- watch the game state change
- verify all five locations

## Important

The coordinates were supplied as planned Google Maps points. They should be physically verified tomorrow.

The 25 m radius is intentionally tight. If phone GPS at a checkpoint regularly shows an accuracy worse than about 20–25 m, increase the radius before the final demonstration.
