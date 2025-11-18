# =============final=================
# app.py
import streamlit as st
import pandas as pd
import requests
import plotly.express as px
# import os
# API_URL = os.getenv("API_URL")

API_URL = "https://reddit-backend-n077.onrender.com"

st.set_page_config(
    page_title="Prop Firm Reddit Marketing Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Small helper ----------
def safe_get(path, params=None):
    try:
        r = requests.get(f"{API_URL}{path}", params=params, timeout=30)
        if not r.ok:
            st.error(f"API error {r.status_code} for {path}")
            return None
        return r.json()
    except Exception as e:
        st.error(f"Cannot reach API {path}: {e}")
        return None

# ---------- Sidebar ----------
st.sidebar.title("📊 Marketing Views")

view = st.sidebar.radio(
    "Choose View",
    [
        "Persona Overview",
        "Share of Voice",
        "Brand Health",
        "Sub-Topic Drivers",
        "Marketing Opportunities",
        "Competitive Snapshot",
        "Timeline & Forecast",
        "AI Narrative Summary",
    ],
)

st.sidebar.markdown("---")
topics_resp = safe_get("/analytics/share_of_voice")
topic_list = []
if topics_resp and "items" in topics_resp:
    topic_list = [it["topic"] for it in topics_resp["items"]]

# ---------- 1) Persona Overview ----------
if view == "Persona Overview":
    st.title("🧑‍💻 Trader Personas per Prop Firm")

    data = safe_get("/analytics/persona_overview")
    if not data:
        st.warning("No persona data available. Make sure enrichment script has run.")
    else:
        col1, col2 = st.columns(2)

        # Global donut
        with col1:
            st.subheader("Global Persona Mix")
            g = data["global"]
            if g:
                df_g = pd.DataFrame(g)
                fig = px.pie(
                    df_g,
                    names="persona",
                    values="count",
                    hole=0.4,
                    title="Persona Distribution Across All Topics",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No persona labels found.")

        # Per-topic stacked bar
        with col2:
            st.subheader("Persona Mix by Prop Firm / Topic")
            df_t = pd.DataFrame(data["by_topic"])
            if not df_t.empty:
                melted = df_t.melt(
                    id_vars=["topic", "total"],
                    value_vars=["beginner", "part_time", "professional", "failed"],
                    var_name="persona",
                    value_name="count",
                )
                fig2 = px.bar(
                    melted,
                    x="topic",
                    y="count",
                    color="persona",
                    title="Personas by Topic",
                    barmode="stack",
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No per-topic persona data.")

        st.markdown(
            """
            **How to read this:**  
            - High *beginner* share → build education funnels & onboarding content.  
            - High *failed* share → recovery offers, "second chance" campaigns.  
            - High *professional* share → advanced products, scaling plans, VIP support.
            """
        )

# ---------- 2) Share of Voice ----------
elif view == "Share of Voice":
    st.title("📣 Share of Voice Across Prop Firms")

    data = topics_resp
    if not data:
        st.warning("No topics data found.")
    else:
        df = pd.DataFrame(data["items"])
        col1, col2 = st.columns([2, 1])

        with col1:
            fig = px.bar(
                df,
                x="topic",
                y="count",
                color="topic",
                title="Mention Volume per Topic",
                text="count",
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig2 = px.pie(
                df,
                names="topic",
                values="percent",
                title="Share of Voice (%)",
            )
            st.plotly_chart(fig2, use_container_width=True)

        st.write(f"Total mentions: **{data['total']}** across all topics.")

# ---------- 3) Brand Health ----------
elif view == "Brand Health":
    st.title("❤️ Sentiment & Brand Health by Prop Firm")

    data = safe_get("/analytics/sentiment_summary")
    if not data:
        st.warning("No sentiment data available.")
    else:
        df = pd.DataFrame(data)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Brand Health Index (Sorted)")
            fig = px.bar(
                df,
                x="topic",
                y="brand_health_index",
                color="brand_health_index",
                title="Brand Health Index (-1 to +1)",
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Positive / Negative Volume")
            df_pn = df.melt(
                id_vars=["topic"],
                value_vars=["positive", "negative", "neutral"],
                var_name="sentiment",
                value_name="count",
            )
            fig2 = px.bar(
                df_pn,
                x="topic",
                y="count",
                color="sentiment",
                barmode="group",
                title="Sentiment Breakdown per Topic",
            )
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown(
            """
            **Tip:**  
            - High volume + low health → damage control & service fixes.  
            - Low volume + high health → scale awareness and promos.
            """
        )

# ---------- 4) Sub-Topic Drivers ----------
elif view == "Sub-Topic Drivers":
    st.title("🧩 Sub-Topic Drivers (What People Talk About)")

    if not topic_list:
        st.warning("No topics found. Can't load drivers.")
    else:
        topic = st.selectbox("Select topic / prop firm", topic_list)
        data = safe_get(f"/analytics/subtopic_drivers/{topic}")
        if not data:
            st.warning("No driver data available.")
        else:
            buckets = data["buckets"]
            df = pd.DataFrame(
                [{"Category": k.replace("_", " ").title(), "Mentions": v} for k, v in buckets.items()]
            )
            df = df.sort_values("Mentions", ascending=False)
            fig = px.bar(
                df,
                x="Category",
                y="Mentions",
                color="Category",
                title=f"Discussion Drivers for {topic.title()}",
                text="Mentions",
            )
            st.plotly_chart(fig, use_container_width=True)
            st.info(
                "Use this to see if the conversation is dominated by payouts, risk rules, fees, or promotions."
            )

# # ---------- 5) Marketing Opportunities ----------
# elif view == "Marketing Opportunities":
#     st.title("📈 Marketing Opportunity Radar")

#     weeks = st.slider("Analyze last N weeks", min_value=2, max_value=24, value=8)
#     data = safe_get("/analytics/opportunities", params={"weeks": weeks, "top": 15})
#     if not data:
#         st.warning("No opportunity data available.")
#     else:
#         st.subheader("Top Week-over-Week Risers")
#         df_risers = pd.DataFrame(data["top_risers"])
#         if not df_risers.empty:
#             fig = px.scatter(
#                 df_risers,
#                 x="wow_pct",
#                 y="question_share_pct",
#                 size="last_week",
#                 color="topic",
#                 hover_data=["last_week", "previous_week"],
#                 title="Risers: Growth vs Question Share (Intent / Needs)",
#             )
#             st.plotly_chart(fig, use_container_width=True)
#             st.dataframe(df_risers)
#         else:
#             st.info("No rising topics found.")

#         st.subheader("New Topics This Period")
#         df_new = pd.DataFrame(data["new_topics"])
#         if not df_new.empty:
#             st.dataframe(df_new)
#         else:
#             st.info("No completely new topics this week.")

# # ---------- 6) Competitive Snapshot ----------
# elif view == "Competitive Snapshot":
#     st.title("⚔ Competitive Snapshot Between Two Prop Firms")

#     if not topic_list:
#         st.warning("No topics to compare.")
#     else:
#         colA, colB = st.columns(2)
#         with colA:
#             topic_a = st.selectbox("Firm A", topic_list, index=0)
#         with colB:
#             topic_b = st.selectbox("Firm B", topic_list, index=min(1, len(topic_list) - 1))

#         if topic_a and topic_b:
#             data = safe_get(
#                 "/analytics/compare",
#                 params={"topic_a": topic_a, "topic_b": topic_b, "top_n": 20},
#             )
#             if not data:
#                 st.warning("No comparison data.")
#             else:
#                 col1, col2 = st.columns(2)
#                 with col1:
#                     st.subheader(f"Unique Terms for {topic_a}")
#                     df_a = pd.DataFrame(data["top_unique_a"])
#                     if not df_a.empty:
#                         fig_a = px.bar(
#                             df_a,
#                             x="term",
#                             y="score",
#                             title=f"Terms Over-Indexed for {topic_a}",
#                         )
#                         st.plotly_chart(fig_a, use_container_width=True)
#                     else:
#                         st.info("No unique terms for A.")

#                 with col2:
#                     st.subheader(f"Unique Terms for {topic_b}")
#                     df_b = pd.DataFrame(data["top_unique_b"])
#                     if not df_b.empty:
#                         fig_b = px.bar(
#                             df_b,
#                             x="term",
#                             y="score",
#                             title=f"Terms Over-Indexed for {topic_b}",
#                         )
#                         st.plotly_chart(fig_b, use_container_width=True)
#                     else:
#                         st.info("No unique terms for B.")

#                 st.markdown("### Sentiment Comparison")
#                 sA = data["sentiment_a"]
#                 sB = data["sentiment_b"]
#                 df_s = pd.DataFrame(
#                     [
#                         {"topic": data["topic_a"], "sentiment": k, "count": v}
#                         for k, v in sA.items()
#                     ] +
#                     [
#                         {"topic": data["topic_b"], "sentiment": k, "count": v}
#                         for k, v in sB.items()
#                     ]
#                 )
#                 fig_s = px.bar(
#                     df_s,
#                     x="topic",
#                     y="count",
#                     color="sentiment",
#                     barmode="group",
#                     title="Sentiment Volume Comparison",
#                 )
#                 st.plotly_chart(fig_s, use_container_width=True)

# ---------- 7) Timeline & Forecast ----------
elif view == "Timeline & Forecast":
    st.title("⏱ Timeline & Simple Forecast")

    if not topic_list:
        st.warning("No topics.")
    else:
        topic = st.selectbox("Select topic / prop firm", topic_list)
        if topic:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Historical Trend")
                series = safe_get(f"/analytics/timeline/{topic}")
                if series:
                    df = pd.DataFrame(series)
                    fig = px.line(
                        df,
                        x="bucket",
                        y="count",
                        markers=True,
                        title=f"Mentions Over Time for {topic}",
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No timeline data.")

            with col2:
                st.subheader("Next Weeks Forecast")
                forecast = safe_get(f"/analytics/forecast/{topic}")
                if forecast and forecast.get("forecast"):
                    df_f = pd.DataFrame(forecast["forecast"])
                    fig_f = px.bar(
                        df_f,
                        x="bucket",
                        y="forecast_count",
                        title=f"Forecasted Mentions for {topic}",
                    )
                    st.plotly_chart(fig_f, use_container_width=True)
                else:
                    st.info("No forecast available.")

# ---------- 8) AI Narrative Summary (OpenAI + cached in Mongo) ----------
elif view == "AI Narrative Summary":
    st.title("🧠 AI Marketing Report (Per Prop Firm)")

    if not topic_list:
        st.warning("No topics.")
    else:
        topic = st.selectbox("Select topic / prop firm", topic_list)
        if topic:
            with st.spinner("Generating / loading AI marketing report..."):
                data = safe_get(f"/analytics/ai_report/{topic}")
            if not data:
                st.warning("No AI report available.")
            else:
                if data.get("cached"):
                    st.caption("Loaded from cache (no new OpenAI calls).")
                else:
                    st.caption("Generated now and cached for future use.")

                st.subheader(f"AI Marketing Narrative – {topic.title()}")
                st.markdown(data.get("narrative", "_No narrative returned._"))

                metrics = data.get("metrics", {})

                with st.expander("📊 Underlying Metrics (what the AI used)", expanded=False):
                    st.markdown("**Share of Voice**")
                    sov = metrics.get("share_of_voice", {})
                    st.json(sov)

                    st.markdown("**Sentiment / Brand Health**")
                    st.json(metrics.get("sentiment", {}))

                    st.markdown("**Personas**")
                    st.json(metrics.get("personas", {}))

                    st.markdown("**Sub-Topic Buckets**")
                    st.json(metrics.get("subtopics", {}))

                    st.markdown("**Community Segments**")
                    st.json(metrics.get("segments", {}))

                    st.markdown("**Opportunity Row**")
                    st.json(metrics.get("opportunity", {}))

                    st.markdown("**Timeline (last buckets)**")
                    st.json(metrics.get("timeline", []))
