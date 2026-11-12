# BACAB Sprint 1.5 — security-conscious Windows PowerShell setup

This release contains **no `.bat`, `.cmd`, `.ps1` or executable installers**.

Scan both the ZIP and extracted folder with Microsoft Defender. Keep Smart App Control ON. Run PowerShell as a normal user, not Administrator.

Use a new folder to preserve the previously validated Sprint 1 installation. We deliberately do not replace or convert old saved audit evidence.

**From the extracted `bacab_mvp` directory:**

```powershell
& "$env:LOCALAPPDATA\Python\pythoncore-3.12-64\python.exe" -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Expected test output: **27 passed**. Open http://127.0.0.1:8501. If the old server is already running, use Ctrl+C in its PowerShell window first.

Dependencies are declared in plain-text `requirements.txt` and `requirements-dev.txt`. The `pip install` step downloads packages over the network, as in the previously successful Sprint 1 setup. If a security tool blocks anything, stop and inspect the warning rather than bypassing it.
