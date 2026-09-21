"""Streamlit UI: streamlit run src/sda/ui/streamlit_app.py."""
from __future__ import annotations

import sys
from pathlib import Path

# Bootstrap: dodaj src/ na sys.path da `import sda` radi i bez PYTHONPATH
# (streamlit pokreće fajl kao skript, ne kao modul).
_SRC = Path(__file__).resolve().parents[2]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def main() -> None:
    import streamlit as st

    from sda.config import DISCLAIMER_SR
    from sda.inference.explain import format_explanation
    from sda.pipeline import SymptomDrugAdvisor

    st.set_page_config(page_title="Simptom-Drug savetnik", layout="centered")
    st.title("Simptom–Drug savetnik")
    st.caption("Informativni predlog (condition_candidate). Nije dijagnoza.")

    with st.sidebar:
        st.header("Podešavanja")
        no_emb = st.checkbox("Offline TF-IDF (bez embeddings)", value=True)
        top_k_c = st.slider("Broj hipoteza", 1, 5, 3)
        top_k_d = st.slider("Broj lekova", 1, 10, 5)

    default = "boli me grlo i imam temperaturu 38"
    text = st.text_area("Opišite simptome na srpskom (latinica ili ćirilica):", value=default, height=100)
    go = st.button("Analiziraj", type="primary")

    if go:
        if not text or not text.strip():
            st.warning("Unesite opis simptoma.")
            return
        with st.spinner("Analiziram..."):
            try:
                advisor = SymptomDrugAdvisor(
                    use_embeddings=not no_emb, no_embeddings=no_emb
                )
                res = advisor.analyze(text)
            except Exception as exc:
                st.error(f"Greška: {exc}")
                return
        st.subheader("Ekstrahovani simptomi")
        if res.symptoms:
            st.table(
                [
                    {
                        "simptom": m.symptom_id,
                        "kanonično": m.canonical_sr,
                        "metoda": m.method,
                        "skor": round(m.score, 3),
                        "pogodak": m.matched_text,
                    }
                    for m in res.symptoms
                ]
            )
        else:
            st.info("Nema prepoznatih simptoma.")
        if res.negated_symptoms:
            st.caption(
                "Negirano: "
                + ", ".join(m.symptom_id for m in res.negated_symptoms)
            )
        if res.red_flags:
            for h in res.red_flags:
                st.error(f"CRVENA ZASTAVICA [{h.severity}]: {h.action_message_sr}")
        st.subheader("Rangirane hipoteze stanja")
        if res.candidates[:top_k_c]:
            for i, c in enumerate(res.candidates[:top_k_c], 1):
                st.markdown(f"**{i}. {c.disease_sr}** (`{c.disease_id}`, skor {c.score:.3f})")
                items = res.explanations.get(c.disease_id, [])
                st.caption(format_explanation(c, items))
            try:
                import pandas as pd

                df = pd.DataFrame(
                    [
                        {"stanje": c.disease_sr, "skor": c.score}
                        for c in res.candidates[:top_k_c]
                    ]
                ).set_index("stanje")
                st.bar_chart(df)
            except Exception:
                pass
        else:
            st.info("Nema hipoteza.")
        st.subheader("Predloženi lekovi iz registra")
        if res.drugs[:top_k_d]:
            for i, d in enumerate(res.drugs[:top_k_d], 1):
                r = d.record
                badge = "OTC" if r.is_otc() else "Rx"
                st.markdown(
                    f"**{i}. {r.naziv_leka}** ({r.atc}, {badge}) — skor {d.score:.3f}"
                )
                st.caption(
                    f"INN: {r.inn} | {r.oblik_doza} | {r.nosilac} | rešenje {r.broj_resenja}"
                )
                st.caption(d.reason)
        else:
            if res.red_flags:
                st.warning("Predlog terapije preskočen zbog crvene zastavice (194).")
            elif res.candidates:
                from sda.config import MENTAL_HEALTH_DISEASES as _MH

                if res.candidates[0].disease_id in _MH:
                    st.warning(
                        "Za hipoteze iz područja mentalnog zdravlja lekovi se "
                        "ne predlažu. Javite se izabranom lekaru, psihologu ili "
                        "psihijatru (hitno: 194)."
                    )
                else:
                    st.info("Nema predloga lekova.")
            else:
                st.info("Nema predloga lekova.")
        st.info(f"Disclaimer: {res.disclaimer}")
        st.caption(
            f"Režim: {'TF-IDF offline' if not res.used_embeddings else 'embeddings'} "
            f"| Baza: {advisor.registry.source} ({len(advisor.registry)} zapisa)"
        )
    else:
        st.info(DISCLAIMER_SR)


if __name__ == "__main__":
    main()
