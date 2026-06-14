# PubMed Topic XAI App

Aplikasi sederhana untuk mengeksplorasi hasil akhir skenario 3. Versi awal ini bersifat read-only: aplikasi membaca CSV XAI final, menampilkan daftar 25 topik, pencarian, filter skor LLM-as-judge, ringkasan metrik, dan detail per topik.

## Stack

- FastAPI untuk HTTP API dan serving halaman.
- Uvicorn sebagai ASGI server.
- Python standard library untuk membaca CSV agar dependensi tetap ringan.
- Frontend HTML/CSS/JavaScript statis.

## Menjalankan Lokal

Dengan `uv`:

```bash
uv venv
uv pip install -r requirements.txt
uv run uvicorn app.main:app --reload
```

Atau jika dependencies sudah tersedia di environment aktif:

```bash
uvicorn app.main:app --reload
```

Buka:

```text
http://127.0.0.1:8000
```

Jika port 8000 sudah terpakai, gunakan port lain:

```bash
uv run uvicorn app.main:app --reload --port 8002
```

## Logging Lokal

Folder `logs/` dipakai untuk log runtime lokal dan sudah masuk `.gitignore`.

Contoh menjalankan server sambil menyimpan log:

```powershell
New-Item -ItemType Directory -Force logs
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 *> logs/uvicorn.log
```

## Menyiapkan Artifacts

Folder `artifacts/` sengaja masuk `.gitignore` karena berisi output eksperimen, cache, atau model yang ukurannya bisa besar dan tidak selalu cocok masuk git.

Untuk versi aplikasi saat ini, siapkan file berikut:

```text
artifacts/s3_xai_detailed_comparison_hdbscan_25_llm_as_judge.csv
artifacts/s3_xai_judged_results_hdbscan_25.csv
```

File tersebut adalah hasil akhir skenario 3 terbaru: detailed output dari tiga model kandidat dan hasil LLM-as-judge.

Tambahan opsional untuk menampilkan ringkasan eksperimen pemenang skenario 2:

```text
artifacts/scenario2_winner_for_scenario3.csv
```

Jika file opsional ini tidak ada, aplikasi tetap jalan. Dashboard hanya tidak menampilkan metadata seperti arm pemenang, jumlah topik, outlier rate, `c_v`, Hungarian F1, dan harmonic mean.

Untuk tahap berikutnya, folder ini bisa berisi:

- `s3_xai_detailed_comparison_hdbscan_25_llm_as_judge.csv` - wajib untuk dashboard Opsi A terbaru.
- `s3_xai_judged_results_hdbscan_25.csv` - wajib untuk winner model dan skor LLM-as-judge.
- `scenario2_winner_for_scenario3.csv` - metadata winner skenario 2, opsional untuk ditampilkan di dashboard.
- `scenario2_best_model.pkl` - belum dipakai pada versi static; nanti dibutuhkan jika aplikasi mulai menerima input abstract baru.
- `cache/` - cache hasil parsing, API, atau regenerate XAI jika fitur LLM ditambahkan.

Catatan penting: versi saat ini sengaja tidak memakai `.pkl`, tidak load BERTopic, dan tidak menjalankan runtime ML. Input abstract/PDF akan dibuat pada iterasi berikutnya agar aplikasi static ini tetap ringan dan mudah deploy.

Jika ingin memakai CSV dari lokasi lain tanpa menyalin ke `artifacts/`, gunakan:

```bash
set XAI_DETAILED_CSV_PATH=D:\path\to\s3_xai_detailed_comparison_hdbscan_25_llm_as_judge.csv
set XAI_JUDGED_CSV_PATH=D:\path\to\s3_xai_judged_results_hdbscan_25.csv
set SCENARIO2_WINNER_CSV_PATH=D:\path\to\scenario2_winner_for_scenario3.csv
uv run uvicorn app.main:app --reload
```

## Environment Variables

Untuk fitur saat ini, API key belum dipakai karena aplikasi masih read-only dari artifacts. Untuk upgrade input/regenerate XAI nanti, copy `.env.example` menjadi `.env` lalu isi key provider yang memang dipakai pipeline:

```text
OPENROUTER_API_KEY=
GROQ_API_KEY=
```

Model seperti Llama, Qwen, Gemma, atau Gemini dipilih dari provider tersebut lewat konfigurasi backend. Key tetap level provider, bukan per model.

Key hanya boleh dibaca backend. Jangan expose key ke frontend.

## Endpoint

- `GET /` - dashboard.
- `GET /health` - status data source.
- `GET /api/summary` - ringkasan metrik.
- `GET /api/topics` - daftar topik, mendukung query `q`, `min_score`, dan `model`.
- `GET /api/topics/{topic_id}` - detail satu topik.

## Catatan

Versi ini belum melakukan inference dokumen baru dan belum membaca PDF. Itu sengaja ditunda agar aplikasi pertama sederhana, stabil, dan langsung bisa mendemokan hasil skenario 3.
