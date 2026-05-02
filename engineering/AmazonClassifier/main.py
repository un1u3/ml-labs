import streamlit as st
from src.llm import analyze_competitors
from src.services import fetch_and_store_competitors, scrape_and_store_product


def render_header():
    st.title("Amazon Competitor Analysis")
    st.caption("Enter your ASIN to get product insights")


def render_inputs():
    asin = st.text_input("ASIN", placeholder="B0XXXXXXX")
    geo = st.text_input("Zip/Postal Code", placeholder="44600")
    domain = st.selectbox("Domain", ["com", "np"])
    return asin.strip(), geo.strip(), domain


def render_product_card(product):
    with st.container(border=True):
        cols = st.columns([1, 2])

        images = product.get("images", [])
        if images:
            cols[0].image(images[0], width=200)
        else:
            cols[0].write("No image found.")

        with cols[1]:
            st.subheader(product.get("title") or product.get("asin", "Unknown ASIN"))

            info_cols = st.columns(3)
            currency = product.get("currency", "")
            price = product.get("price", "--")

            value = f"{currency} {price}" if currency else price
            info_cols[0].metric("Price", value)
            info_cols[1].write(f"Brand: {product.get('brand', '--')}")
            info_cols[2].write(f"ASIN: {product.get('asin', '--')}")

            domain_info = f"amazon.{product.get('amazon_domain', 'com')}"
            geo_info = product.get("geo_location", "-")

            st.caption(f"Domain: {domain_info} | Geo Location: {geo_info}")

            url = product.get("url", "")
            if url:
                st.markdown(f"[Open on Amazon]({url})")

            if st.button(
                "Start analyzing competitors",
                key=f"analyze_{product.get('asin')}",
            ):
                st.session_state["analyzing_asin"] = product.get("asin")


def main():
    st.set_page_config(page_title="Amazon Competitor Analysis")

    render_header()
    asin, geo, domain = render_inputs()

    if st.button("Scrape Product") and asin:
        with st.spinner("Scraping product..."):
            try:
                product = scrape_and_store_product(asin, geo, domain)
            except Exception as exc:
                st.error(f"Product scrape failed: {exc}")
            else:
                st.session_state["product"] = product
                st.success("Product scraped successfully")

    if "product" in st.session_state:
        render_product_card(st.session_state["product"])

    if "analyzing_asin" in st.session_state:
        analysis_asin = st.session_state.pop("analyzing_asin")
        with st.spinner(f"Analyzing competitors for ASIN: {analysis_asin}"):
            competitors = fetch_and_store_competitors(analysis_asin, domain, geo)
            if competitors:
                try:
                    st.session_state["analysis"] = analyze_competitors(analysis_asin)
                except Exception as exc:
                    st.error(f"LLM analysis failed: {exc}")
            else:
                st.warning("No competitors were scraped, so LLM analysis was skipped.")

    if "analysis" in st.session_state:
        st.markdown(st.session_state["analysis"])


if __name__ == "__main__":
    main()
