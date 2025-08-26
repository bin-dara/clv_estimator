
import streamlit as st
import altair as alt
import snowflake.connector
import pandas as pd
from cryptography.hazmat.primitives import serialization

# ------------------------
# SNOWFLAKE CONNECTION (cached)
# ------------------------
@st.cache_resource
def get_connection():
    private_key_bytes = st.secrets["snowflake"]["private_key"].encode()
    private_key = serialization.load_pem_private_key(private_key_bytes, password=None)
    conn = snowflake.connector.connect(
        account=st.secrets["snowflake"]["account"],
        user=st.secrets["snowflake"]["user"],
        role=st.secrets["snowflake"]["role"],
        warehouse=st.secrets["snowflake"]["warehouse"],
        database=st.secrets["snowflake"]["database"],
        schema=st.secrets["snowflake"]["schema"],
        private_key=private_key,
    )
    return conn

# --- Initialize connection
conn = get_connection()

# --- Run SQL query
cursor = conn.cursor()
cursor.execute("SELECT * FROM CLV.CLV_SCHEMA.CLV_TABLE LIMIT 1000")
df = cursor.fetch_pandas_all()   # ✅ this gives you a pandas DataFrame

st.dataframe(df)



st.markdown("""
<style>
    /* Sidebar as full-height flex column */
    section[data-testid="stSidebar"] > div:first-child {
        height: 100vh; 
        display: flex;
        flex-direction: column;
    }
 
    /* Top (logo) */
    .sidebar-top {
        flex: 0 0 auto;   /* fixed at top */
        text-align: center;
        padding: 10px 0;
    }
 
    /* Middle (About Us) */
    .sidebar-middle {
        flex: 1 0 auto;   /* take remaining space */
        display: flex;
        justify-content: center;  /* center horizontally */
        align-items: center;      /* center vertically */
        text-align: center;
        padding: 50px;
    }
 
    /* Bottom (social icons) */
    .sidebar-bottom {
        flex: 0 0 auto;   /* fixed at bottom */
        text-align: center;
        padding: 30px 30px;
        display: flex;
        justify-content: center;
        gap: 15px;
    }
</style>
""", unsafe_allow_html=True)
 
with st.sidebar:
    st.markdown("""
    <div class="sidebar-top">
        <img src="https://booleandata.com/wp-content/uploads/2022/09/Boolean-logo_Boolean-logo-USA-1-980x316.png" style="max-width:100%;">
    </div>
 
    <div class="sidebar-middle">
        <div>
            <h5>🚀 About Us</h5>
            <p>We are a data-driven company helping businesses unlock insights
        from their Customer Lifetime Value (CLV) data. Our mission is to make analytics "
        simple, actionable, and impactful.</p>
        </div>
    </div>
    
    <div class="sidebar-bottom">
        <a href="https://booleandata.ai/" target="_blank">🌐</a>
        <a href="https://www.facebook.com/Booleandata" target="_blank">
            <img src="https://cdn-icons-png.flaticon.com/24/1384/1384005.png" width="24">
        </a>
        <a href="https://www.youtube.com/channel/UCd4PC27NqQL5v9-1jvwKE2w" target="_blank">
            <img src="https://cdn-icons-png.flaticon.com/24/1384/1384060.png" width="24">
        </a>
        <a href="https://www.linkedin.com/company/boolean-data-systems" target="_blank">
            <img src="https://cdn-icons-png.flaticon.com/24/145/145807.png" width="24">
        </a>
    </div>

   """, unsafe_allow_html=True)

   

       





# --- Load CLV Data (preview only) ---
df = conn.query("SELECT * FROM clv.clv_schema.clv_table LIMIT 1000", ttl=600)

# --- App Title ---
st.title("💬 CLV Chatbot")


# --- Chat History ---
if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- User Input ---
prompt = st.chat_input("Ask about CLV data or request a chart...")
if prompt:
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    chart_keywords = ["plot", "chart", "graph", "visualize", "distribution", "trend", "compare"]
    wants_chart = any(word in prompt.lower() for word in chart_keywords)

    # --- Chart Example ---
    if wants_chart and "SEGMENT" in df.columns and "CLV" in df.columns:
        chart = (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x="SEGMENT:N",
                y="mean(CLV):Q",
                tooltip=["SEGMENT", "mean(CLV)"]
            )
            .properties(title="Average CLV by Segment")
        )
        with st.chat_message("assistant"):
            st.markdown("📊 Here’s the chart you requested:")
            st.altair_chart(chart, use_container_width=True)
        st.session_state["messages"].append(
            {"role": "assistant", "content": "📊 Chart generated: Average CLV by Segment"}
        )

    # --- Crisp Analytical Answer with Business Insight ---
    else:
        sql = f"""
        SELECT
          RESPONSE:"choices"[0]:"messages"::string AS ANSWER
        FROM (
          SELECT SNOWFLAKE.CORTEX.COMPLETE(
            'gemma-7b',
            ARRAY_CONSTRUCT(
              OBJECT_CONSTRUCT('role','system','content',
                'You are an expert analytics assistant. \
                Always answer in clear, crisp language (2–3 sentences). \
                Use plain English so business users can easily understand. \
                When providing numbers or trends, also explain why it matters in business terms.'),
              OBJECT_CONSTRUCT('role','user','content',{repr(prompt)})
            ),
            OBJECT_CONSTRUCT('temperature',0.2,'max_tokens',200)
          ) AS RESPONSE
        )
        """
        result = conn.query(sql)
        answer = result["ANSWER"][0]

        with st.chat_message("assistant"):
            st.markdown(answer)
        st.session_state["messages"].append({"role": "assistant", "content": answer})









