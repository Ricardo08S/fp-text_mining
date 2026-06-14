# PubMed Topic XAI App

Aplikasi sederhana untuk mengeksplorasi hasil akhir skenario 3. Versi awal ini bersifat read-only: aplikasi membaca CSV XAI final, menampilkan daftar 25 topik, pencarian, filter cohesion, ringkasan metrik, dan detail per topik.

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
artifacts/s3_xai_detailed_comparison_hdbscan_25.csv
```

File tersebut adalah hasil akhir skenario 3 dan menjadi sumber data dashboard.

Untuk tahap berikutnya, folder ini bisa berisi:

- `s3_xai_detailed_comparison_hdbscan_25.csv` - wajib untuk dashboard Opsi A.
- `scenario2_winner_for_scenario3.csv` - metadata winner skenario 2, opsional untuk ditampilkan.
- `scenario2_best_model.pkl` - model BERTopic final, nanti dibutuhkan jika aplikasi mulai menerima input teks baru.
- `cache/` - cache hasil parsing, API, atau regenerate XAI jika fitur LLM ditambahkan.

Jika ingin memakai CSV dari lokasi lain tanpa menyalin ke `artifacts/`:

```bash
set XAI_CSV_PATH=D:\path\to\s3_xai_detailed_comparison_hdbscan_25.csv
uvicorn app.main:app --reload
```

## Endpoint

- `GET /` - dashboard.
- `GET /health` - status data source.
- `GET /api/summary` - ringkasan metrik.
- `GET /api/topics` - daftar topik, mendukung query `q`, `min_cohesion`, dan `model`.
- `GET /api/topics/{topic_id}` - detail satu topik.

## Catatan

Versi ini belum melakukan inference dokumen baru dan belum membaca PDF. Itu sengaja ditunda agar aplikasi pertama sederhana, stabil, dan langsung bisa mendemokan hasil skenario 3.
