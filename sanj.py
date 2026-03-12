import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from yt_dlp import YoutubeDL
import json

# ---------------- TikTok Metadata ----------------

def get_tiktok_data(url):

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)

        soup = BeautifulSoup(response.content, 'html.parser')
        html = str(soup)

        play_match = re.search(r'"playCount":(\d+),', html)
        time_match = re.search(r'"createTime":"?(\d+)"?,', html)

        play = play_match.group(1) if play_match else None
        create = time_match.group(1) if time_match else None

        if create:
            utc = datetime.utcfromtimestamp(int(create))
            ist = utc + timedelta(hours=5, minutes=30)
            ist_time = ist.strftime('%Y-%m-%d %H:%M:%S')
        else:
            ist_time = None

        return {
            "URL": url,
            "Play Count": play,
            "Create Time (IST)": ist_time
        }

    except Exception:
        return {"URL": url}


# ---------------- Meta (Instagram / Facebook) ----------------

def get_meta_video_details(video_url):

    ydl_opts = {
        'quiet': True,
        'skip_download': True
    }

    try:

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

        platform = info.get("extractor_key")
        uploader = info.get("uploader")
        uploader_id = info.get("uploader_id")

        username = None
        profile_url = None

        if platform == "Instagram":

            username = info.get("channel")

            if username:
                profile_url = f"https://www.instagram.com/{username}/"

        elif platform == "Facebook":

            username = uploader_id

            if uploader_id:
                profile_url = f"https://www.facebook.com/{uploader_id}"

        upload_date = info.get("upload_date")

        if upload_date and len(upload_date) == 8:
            upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"

        return {

            "Video URL": video_url,
            "Platform": platform,
            "Title": info.get("title"),
            "Uploader Name": uploader,
            "Username": username,
            "Uploader ID": uploader_id,
            "Profile URL": profile_url,
            "Upload Date": upload_date,
            "Duration (sec)": info.get("duration"),
            "Views": info.get("view_count"),
            "Likes": info.get("like_count"),
            "Comments": info.get("comment_count"),
            "Thumbnail": info.get("thumbnail")

        }

    except Exception as e:

        return {
            "Video URL": video_url,
            "Error": str(e)
        }


# ---------------- YouTube Metadata ----------------

def get_youtube_video_details(video_url):

    ydl_opts = {'quiet': True, 'skip_download': True}

    try:

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)

        upload_date = info.get("upload_date")

        if upload_date and len(upload_date) == 8:
            upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"

        return {

            "Video URL": video_url,
            "Title": info.get("title"),
            "Uploader": info.get("uploader"),
            "Upload Date": upload_date,
            "Duration": info.get("duration"),
            "Views": info.get("view_count"),
            "Likes": info.get("like_count"),
            "Comments": info.get("comment_count"),
            "Description": info.get("description")

        }

    except Exception as e:
        return {"Video URL": video_url, "Error": str(e)}


# ---------------- Dailymotion Metadata ----------------

def get_dailymotion_video_details(video_url):

    try:

        if 'dailymotion.com/video/' in video_url:
            video_id = video_url.split('/video/')[1].split('_')[0]
        elif 'dai.ly/' in video_url:
            video_id = video_url.split('dai.ly/')[1]
        else:
            return {"Video URL": video_url, "Error": "Invalid URL"}

        api = f"https://api.dailymotion.com/video/{video_id}?fields=title,description,created_time,duration,views_total,likes_total,comments_total,owner.username,thumbnail_720_url,url"

        res = requests.get(api)

        data = res.json()

        created = datetime.fromtimestamp(data['created_time']).strftime('%Y-%m-%d %H:%M:%S')

        return {

            "Video URL": data.get("url"),
            "Title": data.get("title"),
            "Description": data.get("description"),
            "Created Time": created,
            "Duration": data.get("duration"),
            "Views": data.get("views_total"),
            "Likes": data.get("likes_total"),
            "Comments": data.get("comments_total"),
            "Owner": data.get("owner.username"),
            "Thumbnail": data.get("thumbnail_720_url")

        }

    except Exception as e:
        return {"Video URL": video_url, "Error": str(e)}


# ---------------- ShareChat Metadata ----------------

def get_sharechat_video_details(video_url):

    try:

        res = requests.get(video_url)
        soup = BeautifulSoup(res.text, 'html.parser')

        title = soup.find("meta", property="og:title")
        desc = soup.find("meta", property="og:description")
        img = soup.find("meta", property="og:image")

        return {

            "Video URL": video_url,
            "Title": title["content"] if title else None,
            "Description": desc["content"] if desc else None,
            "Thumbnail": img["content"] if img else None

        }

    except Exception as e:
        return {"Video URL": video_url, "Error": str(e)}


# ---------------- Streamlit UI ----------------

st.title("🌐 Social Media Metadata Extractor")

tabs = st.tabs([
    "TikTok",
    "Meta (Instagram / Facebook)",
    "YouTube",
    "Dailymotion",
    "ShareChat"
])


# ---------------- TikTok ----------------

with tabs[0]:

    urls = st.text_area("Enter TikTok URLs")

    if st.button("Extract TikTok Metadata"):

        url_list = [u.strip() for u in urls.splitlines() if u.strip()]

        results = [get_tiktok_data(u) for u in url_list]

        df = pd.DataFrame(results)

        st.dataframe(df)

        st.download_button(
            "Download CSV",
            df.to_csv(index=False),
            "tiktok_metadata.csv"
        )


# ---------------- Meta ----------------

with tabs[1]:

    urls = st.text_area("Enter Instagram / Facebook Reel URLs")

    if st.button("Extract Meta Metadata"):

        url_list = [u.strip() for u in urls.splitlines() if u.strip()]

        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(get_meta_video_details, url_list))

        df = pd.DataFrame(results)

        st.dataframe(df)

        st.download_button(
            "Download CSV",
            df.to_csv(index=False),
            "meta_metadata.csv"
        )


# ---------------- YouTube ----------------

with tabs[2]:

    urls = st.text_area("Enter YouTube URLs")

    if st.button("Extract YouTube Metadata"):

        url_list = [u.strip() for u in urls.splitlines() if u.strip()]

        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(get_youtube_video_details, url_list))

        df = pd.DataFrame(results)

        st.dataframe(df)

        st.download_button(
            "Download CSV",
            df.to_csv(index=False),
            "youtube_metadata.csv"
        )


# ---------------- Dailymotion ----------------

with tabs[3]:

    urls = st.text_area("Enter Dailymotion URLs")

    if st.button("Extract Dailymotion Metadata"):

        url_list = [u.strip() for u in urls.splitlines() if u.strip()]

        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(get_dailymotion_video_details, url_list))

        df = pd.DataFrame(results)

        st.dataframe(df)

        st.download_button(
            "Download CSV",
            df.to_csv(index=False),
            "dailymotion_metadata.csv"
        )


# ---------------- ShareChat ----------------

with tabs[4]:

    urls = st.text_area("Enter ShareChat URLs")

    if st.button("Extract ShareChat Metadata"):

        url_list = [u.strip() for u in urls.splitlines() if u.strip()]

        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(get_sharechat_video_details, url_list))

        df = pd.DataFrame(results)

        st.dataframe(df)

        st.download_button(
            "Download CSV",
            df.to_csv(index=False),
            "sharechat_metadata.csv"
        )
