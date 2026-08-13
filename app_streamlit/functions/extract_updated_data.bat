@echo off

:: Change directory to peoject directory
cd /d "%~dp0"

call ..\..\elec_env\Scripts\activate

python extract_updated_data.py
git add ../data/demand_electricty_generation_mlready.csv
git commit -m "auto-update: updated dataset to current date"
git push -u origin master

call ..\..\elec_env\Scripts\deactivate

powershell -Command "(New-Object -ComObject WScript.Shell).Popup('Data - Electricity - successfully extracted and pushed to GitHub!', 5, 'Streamlit Automation', 64)"