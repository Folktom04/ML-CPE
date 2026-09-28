# Skin-type quiz (day 19)

> **This is a short adaptation of the Fitzpatrick skin-type questionnaire. It has NOT been validated academically.** The result is an estimate used only to compute burn time and warnings, for education, not a medical diagnosis. The app shows the same note on the result screen: "แบบสอบถามนี้เป็นแบบย่อดัดแปลงจาก Fitzpatrick ยังไม่ผ่านการตรวจสอบทางวิชาการ …".

Code: `source_code/app/src/lib/skinQuiz.ts` (questions, scoring), `src/app/quiz.tsx` (screen), tests `__tests__/skinQuiz.test.ts`, `__tests__/quiz.test.tsx`.

## Questions
The full Fitzpatrick questionnaire has 10 items scored 0–4 (total 0–40). Eye colour and natural hair colour are dropped, because almost every Thai user gives the same answer (dark brown / black), so they add no information. Five items remain, each scored 0 (burns most easily) to 4:

1. Colour of skin that is rarely in the sun (inner arm)
2. Freckles on unexposed skin
3. Skin after 1 h in strong sun without sunscreen
4. How much the skin tans after several days in the sun
5. How sensitive the face is to the sun

## Score → type
Total 0–20. The cut-offs are the full scale's (6/7, 13/14, 20/21, 27/28, 34/35) halved: 3.5, 7, 10.5, 14, 17.5. **A score exactly on a cut-off (7 or 14) goes to the lighter type**, which burns sooner, so the warnings err on the safe side.

| Score | 0–3 | 4–7 | 8–10 | 11–14 | 15–17 | 18–20 |
|---|---|---|---|---|---|---|
| Type | I | II | III | IV | V | VI |
| MED (J/m²) | 200 | 250 | 350 | 450 | 600 | 1000 |

Tests check every range edge (0, 3, 4, 7, 8, 10, 11, 14, 15, 17, 18, 20). They also check that for every score the type is never darker than the full scale at twice the score, and differs from it only at 7 and 14, by one lighter type.

The user can also pick a type by hand. Until a type is chosen, the app uses type III and shows a prompt to do the quiz.

## Limitations
- Not validated against a dermatologist's assessment or the full questionnaire, and not tested on Thai users.
- Self-reported answers; skin colour words are subjective.
- Halving the full scale's cut-offs assumes the five kept items carry the same weight as the ten.
