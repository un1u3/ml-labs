import streamlit as st 
from src.oxylabs_client import scrape_product_details
import os 

def render_header():
    st.title("Amzon Competitior analysis")
    st.caption("ENter your asin to get your product instights")


def render_inputs():
    asin = st.text_input("ASIN", placeholder ="DHHAKDAS")
    geo = st.text_input("Zip/Postal Code", placeholder ="444800")
    domain = st.selectbox("Domain", [
        "com","np",
    ])
    return asin.strip(), geo.strip(), domain



def render_product_card(product):
    with st.container(border = True):
        cols = st.columns([1,2])

        try:
            images = product.get('images',[])
            if images and len(images) > 0:
                cols[0].image(images[0], width = 200)
            else:
                cols[0].write("No image found.")
        except:
            cols[0].write("error loading image")

        with cols[1]:
            st.subheader(product.get('title') or product['asin'])
            info_cols = st.columns(3)
            currency = product.get('currency',"")
            price = product.get('price',"--")
            label = "Price"
            value = f"{currency} {price}" if currency else price
            info_cols[0].metric(label, value)
            info_cols[1].write(f"Brand {product.get('brand','--')}")
            info_cols[2].write(f"product {product.get('product','--')}")

            domain_info = f"amazon.{product.get('amazon_domain', 'com')}"            
            geo_info = product.get("geo_location", "-")
            st.caption(f"Domain:{domain_info}, Geo Location {geo_info}")

            st.write(product.get("url",""))

            if st.button("Start analyzing competitots", key= f"analyze_{product['asin']}"):
                st.session_state['analyzing_asin'] = product["asin"]


def main():
    st.set_page_config(page_title = "Amazon Competitor analysis")
    render_header()
    asin, geo, domain = render_inputs()


    if st.button("Scrape Product ") and asin:
        with st.spinner("SCraping product......."):
            st.write("SCrape")
            product = scrape_product_details(asin, geo, domain)

        st.success("Pridcuct scraped sucessfully ")
        # st.write(product)
        render_product_card(product)


if __name__ == "__main__":
    main()
