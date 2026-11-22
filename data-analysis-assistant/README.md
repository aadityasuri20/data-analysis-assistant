# Natural-Language Data Analysis Assistant

A Streamlit app that reads a CSV and answers plain-English questions. Gemini selects an analysis and explains the result. Pandas calculates it and Matplotlib displays applicable charts.

## Run on Windows

From the project root:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: streamlit pandas matplotlib google-genai
.\.venv\Scripts\python.exe -m streamlit run code/app.py
```

Open the local URL shown in PowerShell. Upload the CSV, enter your Gemini API key in the password field, and enter `gemini-3.5-flash-lite` as the model. Try “Which fuel type has the most records?” The included data gives Diesel, 2,153 records.

## Colab prototype

Open `code/Project_File.ipynb` in Colab. Provide the CSV and configure the `GEMINI_API_KEY` secret for live requests. The notebook also includes saved outputs.

- Shareable prototype link: [add approved URL]
- Team: [add member names and enrollment numbers]

See `docs/SUBMISSION_CHECKLIST.md` for remaining submission items. See `test-data/README.md` for test evidence and guidance on sharing the CSV.
