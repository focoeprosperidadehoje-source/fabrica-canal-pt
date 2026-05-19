name: Usina de Shorts

on:
  schedule:
    - cron: '30 4,5,6 * * *' # 01:30, 02:30, 03:30 BRT
  workflow_dispatch: 

jobs:
  produzir_shorts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3'
      - run: pip install --upgrade google-genai gspread
      - env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          GOOGLE_CREDENTIALS_PT: ${{ secrets.GOOGLE_CREDENTIALS_PT }}
        run: python usina_shorts.py
