import streamlit as st
import pandas as pd
from supabase import create_client, Client

# --- KONFIGURACJA POŁĄCZENIA ---
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.set_page_config(page_title="Magazyn Supabase", layout="wide")
st.title("System Zarządzania Magazynem 📦")

# --- POBIERANIE DANYCH ---
def get_data():
    prod_res = supabase.table("produkty").select("*, kategorie(nazwa)").execute()
    kat_res = supabase.table("kategorie").select("id, nazwa").execute()
    return prod_res.data, kat_res.data

produkty_data, kategorie_data = get_data()
lista_kategorii = {item['nazwa']: item['id'] for item in kategorie_data}
lista_produktow = {item['nazwa']: item['id'] for item in produkty_data}

# --- SIDEBAR: OPERACJE ---
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
tab_magazyn, tab_operacje, tab_admin = st.tabs(["📊 Stan Magazynowy", "🔄 Ruch Towaru", "⚙️ Administracja"])

with tab_magazyn:
    if produkty_data:
        df = pd.DataFrame(produkty_data)
        col1, col2, col3 = st.columns(3)
        total_val = (df['cena'] * df['liczba']).sum()
        col1.metric("Wartość magazynu", f"{total_val:,.2f} zł")
        col2.metric("Asortyment", len(df))
        col3.metric("Suma sztuk", int(df['liczba'].sum()))

        PROG_NISKI, PROG_SREDNI = 5, 20
        niskie_count = len(df[df['liczba'] <= PROG_NISKI])
        
        if niskie_count > 0:
            st.error(f"🚨 ALERT: {niskie_count} produktów wymaga uzupełnienia!")
        else:
            st.success("✅ Stany magazynowe są bezpieczne.")

        df['Kategoria'] = df['kategorie'].apply(lambda x: x['nazwa'] if x else "Brak")
        display_df = df[['nazwa', 'Kategoria', 'cena', 'liczba']].rename(
            columns={'nazwa': 'Produkt', 'cena': 'Cena (zł)', 'liczba': 'Ilość'}
        )

        def style_rows(row):
            if row['Ilość'] <= PROG_NISKI:
                return ['background-color: #ff4b4b22; color: #ff4b4b; font-weight: bold'] * len(row)
            elif row['Ilość'] <= PROG_SREDNI:
                return ['background-color: #ffa50022; color: #cc8400'] * len(row)
            else:
                return ['background-color: #28a74511; color: #1e7e34'] * len(row)

        st.dataframe(display_df.style.apply(style_rows, axis=1), use_container_width=True)
    else:
        st.info("Baza danych jest pusta.")

with tab_operacje:
    col_in, col_out = st.columns(2)
    
    with col_in:
        st.header("🚚 Dostawa (Przyjęcie)")
        with st.form("dostawa_form"):
            wybrany_p = st.selectbox("Produkt", options=list(lista_produktow.keys()), key="in_p")
            ilosc_in = st.number_input("Ile sztuk dodać?", min_value=1, step=1)
            if st.form_submit_button("Zatwierdź przyjęcie"):
                akt = next(item for item in produkty_data if item["nazwa"] == wybrany_p)
                supabase.table("produkty").update({"liczba": akt["liczba"] + ilosc_in}).eq("id", akt["id"]).execute()
                st.success(f"Dodano {ilosc_in} szt. {wybrany_p}")
                st.rerun()

    with col_out:
        st.header("🛒 Wydanie (Sprzedaż)")
        with st.form("wydanie_form"):
            wybrany_p_out = st.selectbox("Produkt", options=list(lista_produktow.keys()), key="out_p")
            ilosc_out = st.number_input("Ile sztuk usunąć?", min_value=1, step=1)
            if st.form_submit_button("Zatwierdź wydanie"):
                akt = next(item for item in produkty_data if item["nazwa"] == wybrany_p_out)
                if akt["liczba"] >= ilosc_out:
                    supabase.table("produkty").update({"liczba": akt["liczba"] - ilosc_out}).eq("id", akt["id"]).execute()
                    st.success(f"Wydano {ilosc_out} szt. {wybrany_p_out}")
                    st.rerun()
                else:
                    st.error(f"Błąd: Brak wystarczającej ilości! (Dostępne: {akt['liczba']})")

with tab_admin:
    st.header("Usuwanie całkowite z bazy")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🗑️ Produkty")
        for p in produkty_data:
            if st.button(f"Usuń {p['nazwa']} z bazy", key=f"delp_{p['id']}"):
                supabase.table("produkty").delete().eq("id", p['id']).execute()
                st.rerun()
    with c2:
        st.subheader("📂 Kategorie")
        for k in kategorie_data:
            if st.button(f"Usuń kategorię {k['nazwa']}", key=f"delk_{k['id']}"):
                try:
                    supabase.table("kategorie").delete().eq("id", k['id']).execute()
                    st.rerun()
                except:
                    st.error(f"Kategoria '{k['nazwa']}' nie jest pusta!")
