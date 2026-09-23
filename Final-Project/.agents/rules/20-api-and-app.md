---
trigger: glob
globs: "source_code/api/**, source_code/app/**"
---

# Backend and mobile app conventions

## FastAPI (source_code/api/)
- Pydantic models for every request and response. Response of `/predict` must match:
  `{uvi, uvi_range:[lo,hi], uva_wm2, uvb_wm2, level, skin_type, burn_minutes, cmf, advice:[...], forecast:[{time, uvi}], next_safe_time}`
- Load models once at startup (lifespan event), not per request.
- Endpoints: `GET /health`, `POST /predict`, `GET /forecast`, `POST /sky-image`, `POST /users`, `PUT /users/{id}/settings`.
- Notification scheduler (APScheduler, every 30 min): cooldown 3 h per type per user, hysteresis (alert at ≥ 8, "safe again" at < 6), quiet after sunset. Log every send to `notifications_log`.
- Push through Expo Push Service `https://exp.host/--/api/v2/push/send`.

## Expo app (source_code/app/)
- TypeScript, functional components, hooks. Expo Router for navigation.
- Screens: Onboarding (permissions + 5-question skin-type quiz), Home (UV now, UVA/UVB, burn timer, hourly chart), Camera (sky photo), Settings (notification toggles, threshold, province fallback).
- Colour the UV level with the WHO palette: green #3E9B4F, yellow #D9A400, orange #E36B12, red #D22F3A, violet #8A3FC2.
- If location permission is denied, let the user pick a province; if notifications are denied, the app still works for viewing.
- Light sensor (expo-sensors LightSensor) is Android-only — guard with Platform.OS and hide the feature on iOS.
- Remote push must be tested on a real device (development build on iOS). Do not claim push works from the emulator.
- All user-facing text in Thai.
