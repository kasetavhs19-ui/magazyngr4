import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- KONFIGURACJA POŁĄCZENIA ---
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="Magazyn Supabase", layout="wide")
st.title("Zarządzanie Bazą i Dostawami 📦")

# --- POBIERANIE DANYCH (NA GÓRZE, BY BYŁY DOSTĘPNE W CAŁYM KODZIE) ---
def get_data():
    prod_res = supabase.table("produkty").select("*, kategorie(nazwa)").execute()
    kat_res = supabase.table("kategorie").select("id, nazwa").execute()
    return prod_res.data, kat_res.data

produkty_data, kategorie_data = get_data()
lista_kategorii = {item['nazwa']: item['id'] for item in kategorie_data}
lista_produktow = {item['nazwa']: item['id'] for item in produkty_data}

# --- SIDEBAR: DODAWANIE NOWYCH ELEMENTÓW ---
st.sidebar.header("➕ Dodaj do bazy")
with st.sidebar.expander("Nowa kategoria"):
    with st.form("kat_form"):
        kat_nazwa = st.text_input("Nazwa kategorii")
        kat_opis = st.text_area("Opis")
        if st.form_submit_button("Zapisz kategorię") and kat_nazwa:
            supabase.table("kategorie").insert({"nazwa": kat_nazwa, "opis": kat_opis}).execute()
            st.rerun()

with st.sidebar.expander("Nowy produkt"):
    if not lista_kategorii:
        st.warning("Dodaj najpierw kategorię!")
    else:
        with st.form("prod_form"):
            p_nazwa = st.text_input("Nazwa produktu")
            p_cena = st.number_input("Cena (zł)", min_value=0.0, step=0.01)
            p_liczba = st.number_input("Początkowa ilość", min_value=0, step=1)
            p_kat = st.selectbox("Kategoria", options=list(lista_kategorii.keys()))
            if st.form_submit_button("Dodaj produkt") and p_nazwa:
                supabase.table("produkty").insert({
                    "nazwa": p_nazwa, "cena": p_cena, "liczba": p_liczba, "kategoria_id": lista_kategorii[p_kat]
                }).execute()
                st.rerun()

# --- GŁÓWNY PANEL ---
tab_magazyn, tab_dostawa, tab_produkty = st.tabs(["📊 Stan Magazynowy", "🚚 Dostawa/Aktualizacja", "⚙️ Zarządzanie"])

with tab_magazyn:
    if produkty_data:
        df = pd.DataFrame(produkty_data)
        col1, col2 = st.columns(2)
        col1.metric("Łączna wartość", f"{(df['cena'] * df['liczba']).sum():,.2f} zł")
        col2.metric("Liczba asortymentu", len(df))
        
        # Wyświetlanie tabeli
        df['Kategoria'] = df['kategorie'].apply(lambda x: x['nazwa'] if x else "Brak")
        st.dataframe(df[['nazwa', 'Kategoria', 'cena', 'liczba']].rename(
            columns={'nazwa': 'Produkt', 'cena': 'Cena (zł)', 'liczba': 'Ilość'}
        ), use_container_width=True)
    else:
        st.info("Baza jest pusta.")

with tab_dostawa:
    st.header("Dodaj sztuki do istniejącego produktu")
    if not produkty_data:
        st.warning("Brak produktów w bazie.")
    else:
        with st.form("dostawa_form"):
            wybrany_p_nazwa = st.selectbox("Wybierz produkt z bazy", options=list(lista_produktow.keys()))
            ilosc_dodana = st.number_input("Ile sztuk przyszło w dostawie?", min_value=1, step=1)
            
            if st.form_submit_button("Zatwierdź dostawę"):
                # Pobieramy aktualny stan
                aktualny_produkt = next(item for item in produkty_data if item["nazwa"] == wybrany_p_nazwa)
                nowa_suma = aktualny_produkt["liczba"] + ilosc_dodana
                
                # Update w bazie
                supabase.table("produkty").update({"liczba": nowa_suma}).eq("id", aktualny_produkt["id"]).execute()
                st.success(f"Zaktualizowano! Obecny stan {wybrany_p_nazwa}: {nowa_suma} szt.")
                st.rerun()

with tab_produkty:
    st.header("Usuwanie danych")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Produkty")
        for p in produkty_data:
            if st.button(f"Usuń {p['nazwa']}", key=f"delp_{p['id']}"):
                supabase.table("produkty").delete().eq("id", p['id']).execute()
                st.rerun()
    with c2:
        st.subheader("Kategorie")
        for k in kategorie_data:
            if st.button(f"Usuń {k['nazwa']}", key=f"delk_{k['id']}"):
                try:
                    supabase.table("kategorie").delete().eq("id", k['id']).execute()
                    st.rerun()
                except:
                    st.error(f"Nie można usunąć {k['nazwa']} - zawiera produkty.")
