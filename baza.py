
import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- KONFIGURACJA POŁĄCZENIA ---
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="Magazyn Supabase", layout="wide")
st.title("Zarządzanie Bazą Produktów i Magazynem 📦")

# --- SEKCJA 1: KATEGORIE ---
st.sidebar.header("Dodaj Dane")
with st.sidebar.expander("➕ Nowa kategoria"):
    with st.form("kat_form"):
        kat_nazwa = st.text_input("Nazwa kategorii")
        kat_opis = st.text_area("Opis")
        submit_kat = st.form_submit_button("Dodaj kategorię")
        
        if submit_kat and kat_nazwa:
            supabase.table("kategorie").insert({"nazwa": kat_nazwa, "opis": kat_opis}).execute()
            st.success(f"Dodano kategorię!")
            st.rerun()

# Pobieranie kategorii do listy rozwijanej (potrzebne do formularza produktu)
kategorie_res = supabase.table("kategorie").select("id, nazwa").execute()
lista_kategorii = {item['nazwa']: item['id'] for item in kategorie_res.data}

with st.sidebar.expander("➕ Nowy produkt"):
    if not lista_kategorii:
        st.warning("Najpierw dodaj kategorię!")
    else:
        with st.form("prod_form"):
            prod_nazwa = st.text_input("Nazwa produktu")
            prod_cena = st.number_input("Cena (zł)", min_value=0.0, step=0.01)
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
                st.success(f"Dodano produkt!")
                st.rerun()

# --- SEKCJA 2: WYŚWIETLANIE DANYCH ---
tab_magazyn, tab_produkty, tab_kategorie = st.tabs(["📊 Stan Magazynowy", "📦 Produkty", "📂 Kategorie"])

# Pobieranie wszystkich danych produktów z dołączoną nazwą kategorii
res = supabase.table("produkty").select("*, kategorie(nazwa)").execute()
df_produkty = pd.DataFrame(res.data)

with tab_magazyn:
    st.header("Podsumowanie magazynu")
    if not df_produkty.empty:
        # Metryki
        col1, col2, col3 = st.columns(3)
        total_items = df_produkty["liczba"].sum()
        total_value = (df_produkty["cena"] * df_produkty["liczba"]).sum()
        out_of_stock = len(df_produkty[df_produkty["liczba"] == 0])

        col1.metric("Wszystkich sztuk", int(total_items))
        col2.metric("Wartość magazynu", f"{total_value:,.2f} zł")
        col3.metric("Brak na stanie", int(out_of_stock), delta_color="inverse")

        st.subheader("Szczegółowa tabela stanów")
        # Przygotowanie tabeli do wyświetlenia
        df_display = df_produkty.copy()
        df_display["Kategoria"] = df_display["kategorie"].apply(lambda x: x["nazwa"] if isinstance(x, dict) else "Brak")
        df_display = df_display[["nazwa", "Kategoria", "cena", "liczba"]]
        df_display.columns = ["Produkt", "Kategoria", "Cena (zł)", "Ilość (szt)"]

        # Podświetlanie braków (ilość = 0)
        def highlight_zero(s):
            return ['background-color: #ff4b4b; color: white' if s["Ilość (szt)"] == 0 else '' for _ in s]

        st.dataframe(df_display.style.apply(highlight_zero, axis=1), use_container_width=True)
    else:
        st.info("Brak produktów w bazie.")

with tab_produkty:
    st.header("Zarządzanie produktami")
    if not df_produkty.empty:
        for index, p in df_produkty.iterrows():
            col1, col2 = st.columns([5, 1])
            kat_name = p['kategorie']['nazwa'] if p['kategorie'] else "Brak"
            col1.write(f"**{p['nazwa']}** | Cena: {p['cena']} zł | Stan: {p['liczba']} szt. | ({kat_name})")
            if col2.button("Usuń", key=f"del_prod_{p['id']}"):
                supabase.table("produkty").delete().eq("id", p['id']).execute()
                st.rerun()

with tab_kategorie:
    st.header("Zarządzanie kategoriami")
    for nazwa_k, k_id in lista_kategorii.items():
        col1, col2 = st.columns([5, 1])
        col1.write(f"Kategoria: **{nazwa_k}**")
        if col2.button("Usuń", key=f"del_kat_{k_id}"):
            try:
                supabase.table("kategorie").delete().eq("id", k_id).execute()
                st.rerun()
            except Exception:
                st.error("Nie można usunąć kategorii, która zawiera produkty!")
