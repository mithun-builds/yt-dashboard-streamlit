# =============================================================================
# YouTube Channel Analytics Dashboard
# =============================================================================
# STEP 1 — IMPORTS
# We need:
#   pandas       → data manipulation
#   plotly       → interactive charts
#   streamlit    → the web app framework
#   re, Counter  → for the word-frequency analysis in Tab 3
# =============================================================================
import re
from collections import Counter

import pandas as pd
import plotly.express as px
import streamlit as st

# =============================================================================
# STEP 2 — PAGE CONFIG
# Must be the FIRST streamlit call in the script.
#   layout="wide"  → uses the full browser width (better for dashboards)
#   page_icon      → shows in the browser tab
# =============================================================================
st.set_page_config(
    page_title="YouTube Channel Dashboard",
    page_icon="📊",
    layout="wide",
)

# =============================================================================
# STEP 3 — LOAD & CLEAN DATA
#
# @st.cache_data tells Streamlit: "run this function once, then cache the
# result". Without it, the CSVs would reload on every user interaction.
#
# We fix all the data quality issues identified during analysis:
#   • Soft hyphens (\xad) in File 1 column names
#   • "Total" aggregate row in File 1
#   • "Sept" typo breaking date parsing in File 3
#   • avg_view_fraction stored as 0–1 fraction (not a true %)
#   • All-zero "User Comments Added" columns dropped
#   • Redundant "Thumbnail link" column dropped
#   • Country code "ZZ" mapped to "Unknown"
#   • Duplicate rows removed from File 2
#   • Join key standardised to "video_id" across all files
# =============================================================================
@st.cache_data
def load_data():

    # ── FILE 1: Aggregated metrics per video ──────────────────────────────────
    df_agg = pd.read_csv("Aggregated_Metrics_By_Video.csv")

    # Fix invisible soft-hyphen characters (U+00AD) baked into every column name
    df_agg.columns = [c.replace("\xad", "") for c in df_agg.columns]

    # Row 0 is a channel-level "Total" — remove it before any per-video work
    df_agg = df_agg[df_agg["Video"] != "Total"].copy()

    df_agg = df_agg.rename(columns={
        "Video":                              "video_id",
        "Video title":                        "video_title",
        "Video publish time":                 "publish_date",
        "Comments added":                     "comments_added",
        "Shares":                             "shares",
        "Dislikes":                           "dislikes",
        "Likes":                              "likes",
        "Subscribers lost":                   "subscribers_lost",
        "Subscribers gained":                 "subscribers_gained",
        "RPM (USD)":                          "rpm_usd",
        "CPM (USD)":                          "cpm_usd",
        "Average percentage viewed (%)":      "avg_pct_viewed",
        "Average view duration":              "avg_view_duration",
        "Views":                              "views",
        "Watch time (hours)":                 "watch_time_hours",
        "Subscribers":                        "subscribers_net",   # renamed: it's net, not total
        "Your estimated revenue (USD)":       "estimated_revenue_usd",
        "Impressions":                        "impressions",
        "Impressions click-through rate (%)": "impressions_ctr_pct",
    })

    # Parse publish date ("May 8, 2020" → datetime)
    df_agg["publish_date"] = pd.to_datetime(
        df_agg["publish_date"], format="%b %d, %Y", errors="coerce"
    )

    # Parse avg view duration ("H:MM:SS" string → numeric seconds)
    # Values look like "0:03:25" — we split on ":" and do the arithmetic manually
    def parse_duration_sec(s):
        if not isinstance(s, str):
            return 0
        try:
            h, m, sec = s.split(":")
            return int(h) * 3600 + int(m) * 60 + int(sec)
        except Exception:
            return 0

    df_agg["avg_view_duration_sec"] = df_agg["avg_view_duration"].apply(parse_duration_sec)

    # Strip any accidental whitespace from the video ID
    df_agg["video_id"] = df_agg["video_id"].str.strip()

    # ── FILE 2: Views by country × subscriber status ──────────────────────────
    df_country = pd.read_csv("Aggregated_Metrics_By_Country_And_Subscriber_Status.csv")

    df_country = df_country.rename(columns={
        "Video Title":                "video_title",
        "External Video ID":          "video_id",
        "Video Length":               "video_length_sec",
        "Thumbnail link":             "thumbnail_url",
        "Country Code":               "country_code",
        "Is Subscribed":              "is_subscribed",
        "Views":                      "views",
        "Video Likes Added":          "likes_added",
        "Video Dislikes Added":       "dislikes_added",
        "Video Likes Removed":        "likes_removed",
        "User Subscriptions Added":   "subscriptions_added",
        "User Subscriptions Removed": "subscriptions_removed",
        "Average View Percentage":    "avg_view_fraction",   # stored as 0–1
        "Average Watch Time":         "avg_watch_time_sec",
        "User Comments Added":        "comments_added",
    })

    df_country = df_country.drop_duplicates()
    df_country["country_code"] = df_country["country_code"].fillna("Unknown")
    df_country.loc[df_country["country_code"] == "ZZ", "country_code"] = "Unknown"

    # Drop columns that add no analytical value
    df_country = df_country.drop(columns=["comments_added", "thumbnail_url"])

    # ── FILE 3: Daily video performance over time ─────────────────────────────
    df_time = pd.read_csv("Video_Performance_Over_Time.csv")

    df_time = df_time.rename(columns={
        "Date":                       "date",
        "Video Title":                "video_title",
        "External Video ID":          "video_id",
        "Video Length":               "video_length_sec",
        "Thumbnail link":             "thumbnail_url",
        "Views":                      "views",
        "Video Likes Added":          "likes_added",
        "Video Dislikes Added":       "dislikes_added",
        "Video Likes Removed":        "likes_removed",
        "User Subscriptions Added":   "subscriptions_added",
        "User Subscriptions Removed": "subscriptions_removed",
        "Average View Percentage":    "avg_view_fraction",
        "Average Watch Time":         "avg_watch_time_sec",
        "User Comments Added":        "comments_added",
    })

    # CRITICAL: "Sept" is non-standard — pandas only recognises "Sep"
    # This affects all ~10,000 rows falling in any September
    df_time["date"] = df_time["date"].str.replace("Sept", "Sep", regex=False)
    df_time["date"] = pd.to_datetime(df_time["date"], format="%d %b %Y", errors="coerce")

    df_time = df_time.drop(columns=["comments_added", "thumbnail_url"])

    # ── FILE 4: Comments ──────────────────────────────────────────────────────
    df_comments = pd.read_csv("All_Comments_Final.csv")

    df_comments = df_comments.rename(columns={
        "Comments":   "comment_text",
        "Comment_ID": "comment_id",
        "Reply_Count":"reply_count",
        "Like_Count": "like_count",
        "Date":       "comment_date",
        "VidId":      "video_id",
        "user_ID":    "user_id",
    })

    # Dates are ISO 8601 with UTC timezone (cleanest format of all 4 files)
    df_comments["comment_date"] = pd.to_datetime(
        df_comments["comment_date"], utc=True, errors="coerce"
    )

    # Drop the single row with a deleted/null comment
    df_comments = df_comments.dropna(subset=["comment_text"])

    return df_agg, df_country, df_time, df_comments


# Load once; Streamlit caches the result across reruns
df_agg, df_country, df_time, df_comments = load_data()

# =============================================================================
# STEP 4 — SIDEBAR DATE FILTER
#
# st.sidebar.*  renders widgets in the collapsible left sidebar.
# st.date_input with value=(start, end) returns a tuple when the user picks
# a range. We guard against the in-between state where only one date is chosen.
#
# The filter applies to df_time → affects:
#   • Channel Growth Over Time chart (Tab 1)
#   • Daily Views Over Time chart (Tab 2)
# KPI cards always show all-time totals regardless of the filter.
# =============================================================================
st.sidebar.header("Filters")
st.sidebar.markdown("Applies to time-series charts.")

_min_date = df_time["date"].min().date()
_max_date = df_time["date"].max().date()

date_range = st.sidebar.date_input(
    "Date range",
    value=(_min_date, _max_date),
    min_value=_min_date,
    max_value=_max_date,
)

# Guard: date_input returns a 1-tuple while the user is mid-selection
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = _min_date, _max_date

df_time_filtered = df_time[
    (df_time["date"].dt.date >= start_date) &
    (df_time["date"].dt.date <= end_date)
]

st.sidebar.divider()
st.sidebar.caption(
    f"Showing **{df_time_filtered['date'].dt.date.nunique():,}** days  "
    f"({start_date.strftime('%b %d %Y')} → {end_date.strftime('%b %d %Y')})"
)

# =============================================================================
# STEP 5 — HEADER
# st.title()    → large H1-style heading
# st.markdown() → any markdown text (bold, italic, links, etc.)
# =============================================================================
st.title("📊 YouTube Channel Dashboard")
st.markdown(
    "Analytics for **Ken Jee's** YouTube channel — data snapshot through **Jan 2022**"
)

# =============================================================================
# STEP 5 — TABS
# st.tabs() returns a list of "tab" context managers.
# Everything inside `with tab1:` appears only when that tab is active.
# =============================================================================
tab1, tab2, tab3 = st.tabs(["📈 Aggregate Metrics", "🎬 Individual Video", "💬 Comments"])


# =============================================================================
# TAB 1 — CHANNEL OVERVIEW
#
# Layout:
#   Row 1 → 5 KPI metric cards
#   Row 2 → Top-10 bar chart (left) | Views vs Retention scatter (right)
#   Row 3 → Full sortable video table
# =============================================================================
with tab1:
    st.header("Channel Overview")

    # ── KPI cards ─────────────────────────────────────────────────────────────
    # st.columns(n) divides the row into n equal-width columns.
    # st.metric(label, value) renders a bold number with a label underneath.
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Views",         f"{df_agg['views'].sum():,.0f}")
    c2.metric("Watch Time",          f"{df_agg['watch_time_hours'].sum():,.0f} hrs")
    c3.metric("Revenue",             f"${df_agg['estimated_revenue_usd'].sum():,.0f}")
    c4.metric("Subscribers Gained",  f"{df_agg['subscribers_gained'].sum():,.0f}")
    c5.metric("Videos Published",    f"{len(df_agg)}")

    st.divider()  # thin horizontal rule

    # ── Charts row ────────────────────────────────────────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Top 10 Videos by Views")

        top10 = df_agg.nlargest(10, "views")[["video_title", "views"]].copy()
        # Truncate long titles so they fit on the chart axis
        top10["video_title"] = top10["video_title"].str[:45] + "…"

        fig_top = px.bar(
            top10.sort_values("views"),          # sort ascending so largest is at top
            x="views",
            y="video_title",
            orientation="h",                     # horizontal bar chart
            labels={"views": "Views", "video_title": ""},
            color="views",
            color_continuous_scale="Reds",
        )
        fig_top.update_layout(
            coloraxis_showscale=False,
            height=420,
            margin=dict(l=0, r=20, t=20, b=20),
        )
        st.plotly_chart(fig_top, use_container_width=True)

    with col_right:
        st.subheader("Views vs. Viewer Retention")
        st.caption("Bubble size = watch time hours · Color = revenue")

        fig_scatter = px.scatter(
            df_agg.dropna(subset=["views", "avg_pct_viewed"]),
            x="views",
            y="avg_pct_viewed",
            hover_name="video_title",
            size="watch_time_hours",
            size_max=35,
            color="estimated_revenue_usd",
            color_continuous_scale="Viridis",
            labels={
                "views":            "Total Views",
                "avg_pct_viewed":   "Avg % Viewed",
                "estimated_revenue_usd": "Revenue ($)",
            },
        )
        fig_scatter.update_layout(height=420, margin=dict(l=0, r=20, t=20, b=20))
        st.plotly_chart(fig_scatter, use_container_width=True)

    st.divider()

    # ── Summary table ─────────────────────────────────────────────────────────
    # st.dataframe() with column_config lets us format each column individually:
    #   DateColumn     → renders dates nicely
    #   NumberColumn   → applies format strings (e.g. "$%.2f")
    st.subheader("All Videos — Performance Summary")

    display_cols = [
        "video_title", "publish_date", "views", "likes",
        "subscribers_net", "watch_time_hours",
        "estimated_revenue_usd", "avg_pct_viewed", "impressions_ctr_pct",
    ]

    st.dataframe(
        df_agg[display_cols]
            .sort_values("views", ascending=False)
            .reset_index(drop=True),
        use_container_width=True,
        column_config={
            "video_title":          "Title",
            "publish_date":         st.column_config.DateColumn("Published"),
            "views":                st.column_config.NumberColumn("Views",            format="%d"),
            "likes":                st.column_config.NumberColumn("Likes",            format="%d"),
            "subscribers_net":      st.column_config.NumberColumn("Net Subscribers",  format="%d"),
            "watch_time_hours":     st.column_config.NumberColumn("Watch Time (hrs)", format="%.1f"),
            "estimated_revenue_usd":st.column_config.NumberColumn("Revenue ($)",      format="$%.2f"),
            "avg_pct_viewed":       st.column_config.NumberColumn("Avg % Viewed",     format="%.1f%%"),
            "impressions_ctr_pct":  st.column_config.NumberColumn("CTR (%)",          format="%.2f%%"),
        },
    )

    st.divider()

    # ── Channel growth over time ───────────────────────────────────────────────
    # Aggregate df_time_filtered across ALL videos per day, then cumsum.
    # This shows how the channel has grown over the selected date window.
    st.subheader("Channel Growth Over Time")
    st.caption("Uses the date range set in the sidebar.")

    daily = (
        df_time_filtered
        .groupby("date", as_index=False)
        .agg(
            views           = ("views",                "sum"),
            subs_gained     = ("subscriptions_added",  "sum"),
            subs_lost       = ("subscriptions_removed","sum"),
        )
        .sort_values("date")
    )
    daily["cumulative_views"] = daily["views"].cumsum()
    daily["cumulative_subs"]  = (daily["subs_gained"] - daily["subs_lost"]).cumsum()

    growth_metric = st.radio(
        "Metric:",
        options=["cumulative_views", "cumulative_subs"],
        format_func=lambda x: {
            "cumulative_views": "Cumulative Views",
            "cumulative_subs":  "Cumulative Subscribers",
        }[x],
        horizontal=True,
        key="growth_metric_radio",
    )

    y_label = "Cumulative Views" if growth_metric == "cumulative_views" else "Cumulative Subscribers"
    fig_growth = px.line(
        daily, x="date", y=growth_metric,
        labels={"date": "Date", growth_metric: y_label},
    )
    fig_growth.update_traces(line_color="#E50914", fill="tozeroy",
                             fillcolor="rgba(229,9,20,0.08)")
    fig_growth.update_layout(height=380, margin=dict(l=0, r=10, t=10, b=10))
    st.plotly_chart(fig_growth, use_container_width=True)


# =============================================================================
# TAB 2 — INDIVIDUAL VIDEO DEEP-DIVE
#
# Layout:
#   Dropdown → select a video
#   Row 1    → 4 KPI cards for that video
#   Row 2    → Daily views line chart (left) | Subscriber split bar (right)
#   Row 3    → Top countries bar chart
# =============================================================================
with tab2:
    st.header("Individual Video Deep-Dive")

    # Populate dropdown sorted by most-viewed first so popular videos are at top
    video_options = df_agg.sort_values("views", ascending=False)["video_title"].tolist()
    selected_video = st.selectbox("Select a video", video_options)

    # Look up the row and video_id for the selected title
    video_row = df_agg[df_agg["video_title"] == selected_video].iloc[0]
    vid_id = video_row["video_id"]

    # ── Mini KPIs for selected video ──────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Views",           f"{video_row['views']:,.0f}")
    c2.metric("Likes",           f"{video_row['likes']:,.0f}")
    c3.metric("Net Subscribers", f"{video_row['subscribers_net']:,.0f}")
    c4.metric("Revenue",         f"${video_row['estimated_revenue_usd']:,.2f}")

    st.divider()

    col_a, col_b = st.columns(2)

    # ── Daily views over time ─────────────────────────────────────────────────
    with col_a:
        st.subheader("Daily Views Over Time")

        vid_time = (
            df_time_filtered[df_time_filtered["video_id"] == vid_id]
            .sort_values("date")
        )

        if not vid_time.empty:
            fig_line = px.line(
                vid_time, x="date", y="views",
                labels={"date": "Date", "views": "Daily Views"},
            )
            fig_line.update_traces(line_color="#E50914")  # YouTube red
            fig_line.update_layout(height=380, margin=dict(l=0, r=10, t=10, b=10))
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("No time-series data available for this video.")

    # ── Subscriber vs non-subscriber comparison ───────────────────────────────
    with col_b:
        st.subheader("Subscribers vs. Non-Subscribers")

        vid_country = df_country[df_country["video_id"] == vid_id]

        if not vid_country.empty:
            sub_agg = (
                vid_country
                .groupby("is_subscribed", as_index=False)
                .agg(
                    views            = ("views",            "sum"),
                    avg_watch_time   = ("avg_watch_time_sec","mean"),
                    avg_view_pct     = ("avg_view_fraction", "mean"),
                )
            )
            sub_agg["is_subscribed"] = sub_agg["is_subscribed"].map(
                {True: "Subscriber", False: "Non-Subscriber"}
            )
            # Convert fraction → % and cap at 100 (noisy values can exceed 1.0)
            sub_agg["avg_view_pct"] = (sub_agg["avg_view_pct"] * 100).clip(upper=100)

            metric_choice = st.radio(
                "Metric:",
                options=["views", "avg_watch_time", "avg_view_pct"],
                format_func=lambda x: {
                    "views":          "Views",
                    "avg_watch_time": "Avg Watch Time (sec)",
                    "avg_view_pct":   "Avg % Viewed",
                }[x],
                horizontal=True,
            )

            fig_sub = px.bar(
                sub_agg,
                x="is_subscribed",
                y=metric_choice,
                color="is_subscribed",
                color_discrete_map={
                    "Subscriber":     "#E50914",
                    "Non-Subscriber": "#888888",
                },
                labels={"is_subscribed": "", metric_choice: metric_choice},
            )
            fig_sub.update_layout(showlegend=False, height=300,
                                  margin=dict(l=0, r=10, t=10, b=10))
            st.plotly_chart(fig_sub, use_container_width=True)
        else:
            st.info("No subscriber data available for this video.")

    # ── Top countries ─────────────────────────────────────────────────────────
    st.subheader("Top Countries by Views")

    vid_cntry = (
        df_country[df_country["video_id"] == vid_id]
        .groupby("country_code", as_index=False)["views"]
        .sum()
    )
    # Exclude the "Unknown" bucket from geographic analysis
    vid_cntry = vid_cntry[vid_cntry["country_code"] != "Unknown"].nlargest(15, "views")

    if not vid_cntry.empty:
        fig_cntry = px.bar(
            vid_cntry.sort_values("views"),
            x="views", y="country_code",
            orientation="h",
            labels={"country_code": "Country", "views": "Views"},
            color="views",
            color_continuous_scale="Reds",
        )
        fig_cntry.update_layout(coloraxis_showscale=False, height=420,
                                margin=dict(l=0, r=10, t=10, b=10))
        st.plotly_chart(fig_cntry, use_container_width=True)
    else:
        st.info("No country data available for this video.")


# =============================================================================
# TAB 3 — COMMENT ANALYSIS
#
# Layout:
#   Row 1 → Top 10 most-liked comments (left) | Monthly comment volume (right)
#   Row 2 → Top 20 most frequent words (bar chart)
# =============================================================================
with tab3:
    st.header("Comment Analysis")

    col_left, col_right = st.columns(2)

    # ── Most liked comments ───────────────────────────────────────────────────
    with col_left:
        st.subheader("Top 10 Most Liked Comments")

        top_comments = (
            df_comments
            .nlargest(10, "like_count")[["comment_text", "like_count", "reply_count"]]
            .reset_index(drop=True)
        )
        top_comments.index += 1  # start ranking at 1

        st.dataframe(
            top_comments,
            use_container_width=True,
            column_config={
                "comment_text": "Comment",
                "like_count":   st.column_config.NumberColumn("Likes",   format="%d"),
                "reply_count":  st.column_config.NumberColumn("Replies", format="%d"),
            },
        )

    # ── Monthly comment volume ────────────────────────────────────────────────
    with col_right:
        st.subheader("Comment Volume Over Time")

        # Resample to monthly buckets
        # dt.to_period('M') → period like "2021-06"
        # .dt.to_timestamp() → converts back to a plottable datetime
        df_comments["month"] = (
            df_comments["comment_date"].dt.to_period("M").dt.to_timestamp()
        )
        monthly = df_comments.groupby("month").size().reset_index(name="comment_count")

        fig_vol = px.line(
            monthly, x="month", y="comment_count",
            labels={"month": "Month", "comment_count": "Comments Posted"},
        )
        fig_vol.update_traces(line_color="#E50914")
        fig_vol.update_layout(height=380, margin=dict(l=0, r=10, t=10, b=10))
        st.plotly_chart(fig_vol, use_container_width=True)

    st.divider()

    # ── Word frequency ────────────────────────────────────────────────────────
    # Simple approach: tokenise every comment, remove stop words, count.
    # No NLP library needed — just regex + Counter from the standard library.
    st.subheader("Top 20 Most Common Words in Comments")

    STOP_WORDS = {
        "the","a","an","i","you","and","to","of","is","it","in","that","for",
        "my","on","this","your","with","was","are","me","be","have","but","so",
        "do","as","not","he","she","we","they","at","by","or","if","up","just",
        "like","very","how","had","has","from","what","more","about","its",
        "been","would","could","will","one","out","get","all","also","re","s",
        "t","dont","im","ive","ur","its","am","can","did","got","when","then",
        "them","their","there","here","this","than","too","even","know","really",
        "think","great","good","video","ken","data","science","thank","thanks",
    }

    word_list = []
    for text in df_comments["comment_text"].dropna():
        tokens = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        word_list.extend(w for w in tokens if w not in STOP_WORDS)

    word_freq = pd.DataFrame(
        Counter(word_list).most_common(20),
        columns=["word", "count"],
    )

    fig_words = px.bar(
        word_freq.sort_values("count"),
        x="count", y="word",
        orientation="h",
        labels={"count": "Frequency", "word": ""},
        color="count",
        color_continuous_scale="Reds",
    )
    fig_words.update_layout(
        coloraxis_showscale=False,
        height=520,
        margin=dict(l=0, r=10, t=10, b=10),
    )
    st.plotly_chart(fig_words, use_container_width=True)
