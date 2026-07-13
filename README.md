# ⏱️ טיימר כנסים

אפליקציית ניהול זמנים לכנסים בסגנון stagetimer: לוח בקרה למנהל הכנס + מסך תצוגה
במסך מלא לדובר, עם ספירה לאחור שהופכת לאדומה ויורדת למינוס כשחורגים מהזמן.

## מה יש בפנים

- **לוח בקרה** — הזנת לו"ז הכנס מראש (שם דובר + דקות), הפעלה בלחיצת ▶️ לכל דובר,
  השהיה, מעבר לדובר הבא/הקודם, הוספת/הפחתת דקה תוך כדי, ושליחת הודעות לדובר.
- **מסך תצוגה** — שעון ענק במסך מלא. ירוק כשיש זמן, כתום כשמתקרבים לסוף,
  ואדום עם מינוס כשחורגים (למשל ‎-2:35‎).
- **סנכרון חי** — לוח הבקרה ומסך התצוגה מתעדכנים זה מזה תוך שנייה,
  גם כשהם פתוחים במחשבים שונים.
- ייבוא לו"ז מלא בהדבקה, וגיבוי/שחזור לקובץ JSON.

## הרצה מקומית (לבדיקה)

```bash
pip install -r requirements.txt
streamlit run app.py
```

## פריסה לאינטרנט (GitHub + Streamlit Community Cloud — בחינם)

1. **יוצרים ריפו בגיטהאב**: נכנסים ל־[github.com/new](https://github.com/new),
   נותנים שם (למשל `conference-timer`), בוחרים **Public**, ולוחצים Create repository.
2. **מעלים את הקבצים**: בעמוד הריפו לוחצים **uploading an existing file**
   וגוררים לשם את `app.py`, `requirements.txt` ואת התיקייה `.streamlit`
   (או דוחפים עם git):

   ```bash
   cd conference-timer
   git init
   git add .
   git commit -m "Conference timer app"
   git branch -M main
   git remote add origin https://github.com/<שם-המשתמש>/conference-timer.git
   git push -u origin main
   ```

3. **מפרסמים ב־Streamlit**: נכנסים ל־[share.streamlit.io](https://share.streamlit.io),
   מתחברים עם חשבון הגיטהאב, לוחצים **Create app** → בוחרים את הריפו,
   branch‏ `main`, ו־Main file path‏ `app.py` → **Deploy**.
4. אחרי כדקה מקבלים כתובת קבועה בסגנון `https://your-app.streamlit.app`.

## שימוש ביום הכנס

| מסך | כתובת |
|---|---|
| לוח בקרה (אצלכם) | `https://your-app.streamlit.app` |
| מסך הדובר (מקרן) | `https://your-app.streamlit.app/?view=display` + לחיצה על F11 |

## שווה לדעת

- בתוכנית החינמית של Streamlit האפליקציה "נרדמת" אחרי חוסר פעילות, והלו"ז
  שבזיכרון נמחק. לכן: להזין את הלו"ז ביום הכנס (או להוריד גיבוי JSON מראש
  ולשחזר ממנו), ולהשאיר את לוח הבקרה פתוח לאורך האירוע.
- כל מי שמחזיק בכתובת הראשית יכול לשלוט בטיימר — לשתף עם הקהל רק את
  כתובת ה־`?view=display`.
