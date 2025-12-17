import streamlit as st
import requests

API_URL = "https://shl-assessment-recommender-backend-05je.onrender.com/recommend"

st.title("SHL Assessment Recommender")
st.write("Enter a Job Description, a specific query, or a URL to a JD.")

query = st.text_area("Input", height=150)

if st.button("Get Recommendations"):
    if query:
        with st.spinner("Analyzing and finding best assessments..."):
            try:
                payload = {"query": query}
                response = requests.post(API_URL, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    st.success(f"Found {len(data['recommended_assessments'])} recommendations")
                    
                    for item in data['recommended_assessments']:
                        with st.expander(f"{item['name']}"):
                            st.write(f"**URL:** [Link]({item['url']})")
                            st.write(f"**Duration:** {item['duration']} mins")
                            st.write(f"**Description:** {item['description']}")
                            st.write(f"**Type:** {', '.join(item['test_type'])}")
                else:
                    st.error("Error retrieving recommendations.")
            except Exception as e:
                st.error(f"Connection error: {e}")
    else:
        st.warning("Please enter a query.")
