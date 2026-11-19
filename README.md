# gta6-twitch-ccu-forecast

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/GAD2412/gta6-twitch-ccu-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/GAD2412/gta6-twitch-ccu-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

Forecasts Grand Theft Auto VI's launch-day Twitch viewers for hours 2–24 (UTC) from hour 1's count. Analog method:
each past big launch in the case gives a release-day curve `log(hour h / hour 1)`; hour h's five quantiles are the
weighted empirical quantiles of those curves, scaled by this case's hour-1 count. GTA VI unlocks at midnight local
time (New Zealand 11:00 UTC Nov 18 through US Eastern 05:00 UTC Nov 19), so launches that unlocked the same way get 6x
weight; early-access and weak analogs are down-weighted. Python stdlib only, deterministic, well under a second.

Leave-one-out over 37 past launches: pinball loss 0.731 vs the house baseline's 0.930; on the 12 midnight-local
launches 0.327 (`python3 check.py input/p00.in`).

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards</sub>
