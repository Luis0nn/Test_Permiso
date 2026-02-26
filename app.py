import os
import random
import pandas as pd
import streamlit as st

PASS_SCORE = 16
EXAM_SIZE = 20

# Reparto por temas a 20 (T1..T7)
TOPIC_DISTRIBUTION = {1: 3, 2: 3, 3: 2, 4: 3, 5: 3, 6: 3, 7: 3}

CSV_FILENAME = "preguntas.csv"


def load_questions(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"No existe {path}. Pon preguntas.csv en la misma carpeta que app.py.")

    df = pd.read_csv(path, sep=";", dtype=str).fillna("")
    required = ["tema", "enunciado", "A", "B", "C", "correcta"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas: {missing}. Debe haber: {required}")

    df["tema"] = df["tema"].str.strip()
    df["correcta"] = df["correcta"].str.strip().str.upper()

    # Validaciones
    if not set(df["tema"]).issubset({str(i) for i in range(1, 8)}):
        raise ValueError("Hay temas inválidos. Deben ser 1..7.")

    if not set(df["correcta"]).issubset({"A", "B", "C"}):
        raise ValueError("La columna 'correcta' debe ser A/B/C (sin espacios).")

    # Quitar filas con campos vacíos básicos
    bad = df[(df["enunciado"].str.strip() == "") |
             (df["A"].str.strip() == "") |
             (df["B"].str.strip() == "") |
             (df["C"].str.strip() == "")]
    if len(bad) > 0:
        raise ValueError("Hay filas con enunciado u opciones vacías. Revisa tu Excel/CSV.")

    return df


def generate_exam(df: pd.DataFrame) -> list[dict]:
    exam = []
    for topic, n in TOPIC_DISTRIBUTION.items():
        pool = df[df["tema"] == str(topic)]
        if len(pool) < n:
            raise ValueError(f"En el tema {topic} necesitas {n} preguntas y solo tienes {len(pool)}.")
        sample = pool.sample(n=n, replace=False, random_state=random.randint(0, 10**9))
        for _, r in sample.iterrows():
            exam.append({
                "tema": int(r["tema"]),
                "enunciado": r["enunciado"],
                "opciones": {"A": r["A"], "B": r["B"], "C": r["C"]},
                "correcta": r["correcta"]
            })
    random.shuffle(exam)
    return exam


def ensure_state():
    if "exam" not in st.session_state:
        st.session_state.exam = None
    if "idx" not in st.session_state:
        st.session_state.idx = 0
    if "answers" not in st.session_state:
        st.session_state.answers = {}


def reset():
    st.session_state.exam = None
    st.session_state.idx = 0
    st.session_state.answers = {}


st.set_page_config(page_title="Test Permiso", page_icon="📝")
ensure_state()

st.title("📝 Test permiso (20 preguntas)")

# Mostrar errores SIEMPRE (esto evita pantalla negra)
try:
    df = load_questions(CSV_FILENAME)
except Exception as e:
    st.error(f"Error cargando preguntas.csv: {e}")
    st.stop()

st.success(f"Banco cargado: {len(df)} preguntas ✅")

col1, col2 = st.columns(2)
with col1:
    if st.button("🎲 Generar examen"):
        try:
            st.session_state.exam = generate_exam(df)
            st.session_state.idx = 0
            st.session_state.answers = {}
            st.rerun()
        except Exception as e:
            st.error(f"No se pudo generar el examen: {e}")

with col2:
    if st.button("🔄 Reiniciar"):
        reset()
        st.rerun()

if st.session_state.exam is None:
    st.info("Pulsa **Generar examen** para empezar.")
    st.stop()

exam = st.session_state.exam
idx = st.session_state.idx
q = exam[idx]

# st.subheader(f"Pregunta {idx+1}/{EXAM_SIZE} · Tema {q['tema']}")
st.write(f"**{q['enunciado']}**")

keys = ["A", "B", "C"]
labels = {k: f"{k}) {q['opciones'][k]}" for k in keys}

current = st.session_state.answers.get(idx, None)
default_index = keys.index(current) if current in keys else 0

choice = st.radio("Respuesta:", keys, format_func=lambda k: labels[k], index=default_index)
st.session_state.answers[idx] = choice

cprev, cnext, cfinish = st.columns([1, 1, 2])

with cprev:
    if st.button("⬅️ Anterior", disabled=(idx == 0)):
        st.session_state.idx -= 1
        st.rerun()

with cnext:
    if st.button("Siguiente ➡️", disabled=(idx == EXAM_SIZE - 1)):
        st.session_state.idx += 1
        st.rerun()

with cfinish:
    if st.button("✅ Finalizar y corregir"):
        # Corregir
        correct = 0
        wrong = 0
        for i, qq in enumerate(exam):
            if st.session_state.answers.get(i) == qq["correcta"]:
                correct += 1
            else:
                wrong += 1

        st.divider()
        st.subheader("📊 Resultado")
        st.write(f"✅ Correctas: **{correct}**")
        st.write(f"❌ Fallos: **{wrong}**")
        if correct >= PASS_SCORE:
            st.success("APROBADO ✅")
        else:
            st.error("SUSPENSO ❌")

        st.subheader("🔎 Revisión (falladas)")
        for i, qq in enumerate(exam):
            a = st.session_state.answers.get(i)
            if a != qq["correcta"]:
                with st.expander(f"Pregunta {i+1} (Tema {qq['tema']})"):
                    st.write(f"**{qq['enunciado']}**")
                    st.write(f"A) {qq['opciones']['A']}")
                    st.write(f"B) {qq['opciones']['B']}")
                    st.write(f"C) {qq['opciones']['C']}")
                    st.write(f"Tu respuesta: **{a}**")
                    st.write(f"Correcta: **{qq['correcta']}**")