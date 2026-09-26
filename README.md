## NLP Farma — Symptom-Drug Advisor

Hibridni NLP savetnik za simptome i lekove na srpskom jeziku, offline-first.

Sistem iz slobodnog teksta na srpskom (latinica ili ćirilica) ekstrahuje simptome,
rangira hipoteze stanja (`condition_candidate`), proverava crvene zastavice
(hitna stanja) i daje informativne predloge lekova iz registra (prvenstveno OTC).

> INFORMATIVNI PREDLOG, NIJE DIJAGNOZA. Ne zamenjuje lekara ili farmaceuta.
> Kod hitnih znakova zvati Hitnu pomoć (194).

## Kako radi

`tekst → normalizacija → ekstrakcija simptoma (gazetteer + fuzzy + TF-IDF) → detekcija negacije → red-flag guard → rangiranje hipoteza → ATC mapiranje → predlog lekova`

Posebna pravila:

* crvena zastavica → preskače se predlog terapije, ispisuje se upozorenje (194)
* vodeća hipoteza iz domena mentalnog zdravlja (`D_ANKSIOZNOST`, `D_DEPRESIJA`,
  `D_PANIKA`, `D_STRES`, `D_BURNOUT`) → lekovi se ne predlažu, daje se uput lekaru/psihologu

## Struktura

```
projekat/
  src/sda/          # glavni paket: cli, pipeline, config, text, nlp, inference, drugs, safety, ui
  scripts/          # prepare_data.py, run_eval.py, ablation.py
  data/
    knowledge/      # symptoms_sr.csv, disease_symptoms.csv, disease_atc.csv, red_flags.csv, test_cases.jsonl
    eval/           # eval skup
    raw/            # lekovi_sample.json (uzorak); pun lekovi.json (6809 zapisa) se učitava ako postoji
  tests/            # pytest testovi
  docs/             # index.html (vizuelni demo: algoritmi + tehnologije), snimci ekrana
```

## Uslovi

* Python >= 3.10 (provereno na 3.12)
* Windows / Linux

## Instalacija

Windows (PowerShell):

```powershell
Set-Location projekat
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

Linux/macOS:

```bash
cd projekat
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

Ako ne radiš `pip install -e .`, dodaj `src` na `PYTHONPATH`:

```powershell
$env:PYTHONPATH="src"
```

```bash
export PYTHONPATH=src
```

Na Windows-u za naša slova (č/ć/ž/š) postavi i:

```powershell
$env:PYTHONIOENCODING="utf-8"
```

## Pokretanje

CLI — analiza jednog opisa:

```bash
python -m sda.cli --text "boli me grlo i imam temperaturu 38" --no-embeddings
python -m sda.cli --file opis.txt --no-embeddings
echo "boli me grlo" | python -m sda.cli --no-embeddings
```

Streamlit UI:

```bash
streamlit run src/sda/ui/streamlit_app.py
```

Testovi:

```bash
pytest -q
```

Evaluacija (metrike + CSV + PNG u `reports/`):

```bash
python scripts/run_eval.py --no-embeddings
python scripts/run_eval.py --no-embeddings --limit 20
```


## Vizuelni demo (HTML)

`docs/index.html` je samostalna stranica (radi offline, bez servera) koja prikazuje
tok podataka, algoritme sa živim primerima (normalizacija, fuzzy skor, TF-IDF, kalkulator
skora) i korišćene tehnologije. Otvori je dvoklikom u browseru.

## Podaci

* `data/knowledge/symptoms_sr.csv` — leksikon simptoma
* `data/knowledge/disease_symptoms.csv` — veza bolest–simptom
* `data/knowledge/disease_atc.csv` — veza bolest–ATC
* `data/knowledge/red_flags.csv` — obrasci hitnih stanja
* `data/raw/lekovi_sample.json` — uzorak registra; ako postoji pun `lekovi.json`
  (u `data/raw/`, korenu repoa ili `C:/Users/Damjan/Documents/Deepseek/lekovi.json`),
  koristi se automatski

## Licenca

MIT
