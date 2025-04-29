# Combined Streamlit App
import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import instaloader
from yt_dlp import YoutubeDL
import json

# ---------------- TikTok Metadata ----------------


def get_tiktok_data(url, use_vpn=False):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return {"URL": url, "Play Count": None, "Create Time (IST)": None}
        
        soup = BeautifulSoup(response.content, 'html.parser')
        html_text = str(soup)

        play_count_match = re.search(r'"playCount":(\d+),', html_text)
        create_time_match = re.search(r'"createTime":"?(\d+)"?,', html_text)

        play_count = play_count_match.group(1) if play_count_match else None
        create_time = create_time_match.group(1) if create_time_match else None

        if create_time:
            utc_time = datetime.utcfromtimestamp(int(create_time))
            ist_time = utc_time + timedelta(hours=5, minutes=30)
            ist_time_str = ist_time.strftime('%d/%m/%y %H:%M:%S')
        else:
            ist_time_str = None

        return {
            "URL": url,
            "Play Count": play_count,
            "Create Time (IST)": ist_time_str
        }
    except Exception as e:
        return {"URL": url, "Play Count": None, "Create Time (IST)": None}


# ---------------- Instagram Reel Metadata ----------------


# ---------------- YouTube Video Metadata ----------------
def get_youtube_video_details(video_url):
    ydl_opts = {'quiet': True, 'skip_download': True}
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
        
        upload_date = info.get("upload_date", "N/A")
        if upload_date != "N/A" and len(upload_date) == 8:
            upload_date_formatted = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
        else:
            upload_date_formatted = upload_date

        data = {
            "Video URL": video_url,
            "ID": info.get("id"),
            "Title": info.get("title"),
            "Description": info.get("description"),
            "Uploader": info.get("uploader"),
            "Upload Date": upload_date_formatted,
            "Duration (s)": info.get("duration"),
            "View Count": info.get("view_count"),
            "Like Count": info.get("like_count"),
            "Dislike Count": info.get("dislike_count"),
            "Average Rating": info.get("average_rating"),
            "Categories": ", ".join(info.get("categories", [])) if info.get("categories") else "",
            "Tags": ", ".join(info.get("tags", [])) if info.get("tags") else "",
            "Formats": ", ".join([f['format'] for f in info.get("formats", []) if 'format' in f]),
            "Thumbnails": ", ".join([thumb["url"] for thumb in info.get("thumbnails", []) if "url" in thumb]),
        }
        return data
    except Exception as e:
        return {"Video URL": video_url, "Error": str(e)}

# ---------------- Dailymotion Video Metadata ----------------
def get_dailymotion_video_details(video_url):
    try:
        video_id = None
        if 'dailymotion.com/video/' in video_url:
            video_id = video_url.split('/video/')[1].split('_')[0].split('?')[0]
        elif 'dai.ly/' in video_url:
            video_id = video_url.split('dai.ly/')[1].split('?')[0]
        
        if not video_id:
            return {"Video URL": video_url, "Error": "Invalid Dailymotion URL format"}
        
        api_url = f"https://api.dailymotion.com/video/{video_id}?fields=id,title,description,created_time,modified_time,duration,views_total,likes_total,comments_total,owner.username,owner.id,tags,country,explicit,channel.name,allow_embed,aspect_ratio,language,thumbnail_720_url,url,status,private,rating,ratings_total,geoblocking,custom_classification,is_created_for_kids,embed_url,available_formats"
        
        response = requests.get(api_url)
        if response.status_code != 200:
            return {"Video URL": video_url, "Error": f"API Error: {response.text}"}
        
        data = response.json()
    
        created_time = (datetime.fromtimestamp(data['created_time']).strftime('%Y-%m-%d %H:%M:%S')) if 'created_time' in data else None
        modified_time = (datetime.fromtimestamp(data['modified_time']).strftime('%Y-%m-%d %H:%M:%S')) if 'modified_time' in data else None
    
        return {
            "Video URL": data.get('url', video_url),
            "Title": data.get('title', 'N/A'),
            "Description": data.get('description', 'N/A'),
            "Created Time": created_time,
            "Modified Time": modified_time,
            "Duration": data.get('duration', 0),
            "Views": data.get('views_total', 0),
            "Likes": data.get('likes_total', 0),
            "Comments": data.get('comments_total', 0),
            "Owner Username": data.get('owner.username', 'N/A'),
            "Channel": data.get('channel.name', 'N/A'),
            "Language": data.get('language', 'N/A'),
            "Thumbnail": data.get('thumbnail_720_url', 'N/A'),
            "Embed URL": data.get('embed_url', 'N/A'),
        }
    except Exception as e:
        return {"Video URL": video_url, "Error": str(e)}

# ---------------- ShareChat Video Metadata ----------------
def get_sharechat_video_details(video_url):
    try:
        response = requests.get(video_url)
        if response.status_code != 200:
            return {"Video URL": video_url, "Error": f"HTTP Error: {response.status_code}"}
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        meta_title = soup.find("meta", property="og:title")
        meta_description = soup.find("meta", property="og:description")
        meta_image = soup.find("meta", property="og:image")
        meta_video = soup.find("meta", property="og:video")
        meta_url = soup.find("meta", property="og:url")
        
        data = {
            "Video URL": video_url,
            "Title": meta_title["content"] if meta_title and meta_title.has_attr("content") else "N/A",
            "Description": meta_description["content"] if meta_description and meta_description.has_attr("content") else "N/A",
            "Thumbnail": meta_image["content"] if meta_image and meta_image.has_attr("content") else "N/A",
            "Video Link": meta_video["content"] if meta_video and meta_video.has_attr("content") else "N/A",
            "Page URL": meta_url["content"] if meta_url and meta_url.has_attr("content") else "N/A",
            "Upload Date": "N/A",
        }

        ld_json_scripts = soup.find_all("script", type="application/ld+json")
        for script in ld_json_scripts:
            try:
                json_content = script.string
                if not json_content:
                    continue
                ld_data = json.loads(json_content)
                if isinstance(ld_data, dict) and ld_data.get("@type") == "VideoObject":
                    data["Upload Date"] = ld_data.get("uploadDate", "N/A")
                    break
            except Exception:
                continue
        
        return data
    except Exception as e:
        return {"Video URL": video_url, "Error": str(e)}

# ---------------- Streamlit Layout ----------------
st.title("🌐 Social Media Metadata Retriever")
st.write("Select a tab to scrape metadata from different platforms.")

tabs = st.tabs([
    "TikTok Metadata",
    "YouTube Video Metadata",
    "Dailymotion Video Metadata",
    "ShareChat Video Metadata"
])

# --------------- Tab 1: TikTok ----------------
with tabs[0]:
    st.header("TikTok Metadata Retriever")
    tiktok_urls_input = st.text_area("Enter TikTok Video URLs (one per line):")
    use_vpn = st.checkbox("Check if using VPN")
    
    if st.button("Process TikTok Videos"):
        urls = [url.strip() for url in tiktok_urls_input.splitlines() if url.strip()]
        if urls:
            st.info("Processing TikTok videos...")
            progress_text = st.empty()
            results = []

            for i, url in enumerate(urls, start=1):
                result = get_tiktok_data(url, use_vpn)
                results.append(result)
                progress_text.markdown(f"**{i}/{len(urls)} URLs processed**")

            df = pd.DataFrame(results)
            st.success("Done!")
            st.dataframe(df)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", data=csv, file_name="tiktok_metadata.csv", mime="text/csv")
        else:
            st.error("Please enter at least one TikTok URL.")


# --------------- Tab 2: Instagram ----------------

# --------------- Tab 3: YouTube ----------------
with tabs[1]:
    st.header("YouTube Video Metadata Retriever")
    yt_urls_input = st.text_area("Enter YouTube Video URLs:")
    
    if st.button("Process YouTube Videos"):
        urls = [url.strip() for url in yt_urls_input.splitlines() if url.strip()]
        if urls:
            st.info("Processing YouTube videos...")
            with ThreadPoolExecutor(max_workers=10) as executor:
                results = list(executor.map(get_youtube_video_details, urls))

            df = pd.DataFrame(results)
            st.success("Done!")
            st.dataframe(df)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", data=csv, file_name="youtube_metadata.csv", mime="text/csv")
        else:
            st.error("Please enter at least one URL.")

# --------------- Tab 4: Dailymotion ----------------
with tabs[2]:
    st.header("Dailymotion Video Metadata Retriever")
    dm_urls_input = st.text_area("Enter Dailymotion URLs:")
    
    if st.button("Process Dailymotion Videos"):
        urls = [url.strip() for url in dm_urls_input.splitlines() if url.strip()]
        if urls:
            st.info("Processing Dailymotion videos...")
            with ThreadPoolExecutor(max_workers=10) as executor:
                results = list(executor.map(get_dailymotion_video_details, urls))

            df = pd.DataFrame(results)
            st.success("Done!")
            st.dataframe(df)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", data=csv, file_name="dailymotion_metadata.csv", mime="text/csv")
        else:
            st.error("Please enter at least one URL.")

# --------------- Tab 5: ShareChat ----------------
with tabs[3]:
    st.header("ShareChat Video Metadata Retriever")
    sc_urls_input = st.text_area("Enter ShareChat URLs:")
    
    if st.button("Process ShareChat Videos"):
        urls = [url.strip() for url in sc_urls_input.splitlines() if url.strip()]
        if urls:
            st.info("Processing ShareChat videos...")
            with ThreadPoolExecutor(max_workers=10) as executor:
                results = list(executor.map(get_sharechat_video_details, urls))

            df = pd.DataFrame(results)
            st.success("Done!")
            st.dataframe(df)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", data=csv, file_name="sharechat_metadata.csv", mime="text/csv")
        else:
            st.error("Please enter at least one URL.")
