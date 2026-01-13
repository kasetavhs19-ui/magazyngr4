import streamlit as st
from supabase import create_client, Client

# --- KONFIGURACJA POŁĄCZENIA ---
# Dane pobierane ze Streamlit Secrets (na GitHubie nie przechowujemy kluczy!)
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("Zarządzanie Baza Produktów 📦")

# --- SEKCJA 1: KATEGORIE ---
st.header("1. Kategorie")
with st.expander("Dodaj nową kategorię"):
    with st.form("kat_form"):
        kat_nazwa = st.text_input("Nazwa kategorii")
        kat_opis = st.text_area("Opis")
        submit_kat = st.form_submit_button("Dodaj kategorię")
        
        if submit_kat and kat_nazwa:
            data, count = supabase.table("kategorie").insert({"nazwa": kat_nazwa, "opis": kat_opis}).execute()
            st.success(f"Dodano kategorię: {kat_nazwa}")
            st.rerun()

# --- SEKCJA 2: PRODUKTY ---
st.header("2. Produkty")

# Pobieranie kategorii do listy rozwijanej
kategorie_res = supabase.table("kategorie").select("id, nazwa").execute()
lista_kategorii = {item['nazwa']: item['id'] for item in kategorie_res.data}

with st.expander("Dodaj nowy produkt"):
    with st.form("prod_form"):
        prod_nazwa = st.text_input("Nazwa produktu")
        prod_cena = st.number_input("Cena", min_value=0.0, step=0.01)
        prod_liczba = st.number_input("Liczba sztuk", min_value=0, step=1)
        wybrana_kat = st.selectbox("Kategoria", options=list(lista_kategorii.keys()))
        
        submit_prod = st.form_submit_button("Dodaj produkt")
        
        if submit_prod and prod_nazwa:
            nowy_produkt = {
                "nazwa": prod_nazwa,
                "cena": prod_cena,
                "liczba": prod_liczba,
                "kategoria_id": lista_kategorii[wybrana_kat]
            }
            supabase.table("produkty").insert(nowy_produkt).execute()
            st.success(f"Dodano produkt: {prod_nazwa}")
            st.rerun()

# --- SEKCJA 3: LISTA I USUWANIE ---
st.header("3. Twoje Dane")

tab1, tab2 = st.tabs(["Produkty", "Kategorie"])

with tab1:
    produkty = supabase.table("produkty").select("*, kategorie(nazwa)").execute()
    for p in produkty.data:
        col1, col2 = st.columns([4, 1])
        col1.write(f"**{p['nazwa']}** - {p['cena']} zł (Kat: {p['kategorie']['nazwa']})")
        if col2.button("Usuń", key=f"del_prod_{p['id']}"):
            supabase.table("produkty").delete().eq("id", p['id']).execute()
            st.rerun()

with tab2:
    for k_id in lista_kategorii.values():
        col1, col2 = st.columns([4, 1])
        nazwa_k = [n for n, i in lista_kategorii.items() if i == k_id][0]
        col1.write(f"Kategoria: **{nazwa_k}**")
        if col2.button("Usuń", key=f"del_kat_{k_id}"):
            # Uwaga: Usunięcie kategorii może się nie udać, jeśli są do niej przypisane produkty (klucz obcy)
            try:
                supabase.table("kategorie").delete().eq("id", k_id).execute()
                st.rerun()
            except Exception as e:
                st.error("Nie można usunąć kategorii, która zawiera produkty!")
