import streamlit as st
import instaloader
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor
from yt_dlp import YoutubeDL
from datetime import datetime
from bs4 import BeautifulSoup

# ---------------- Instagram Reel Retriever ----------------
def get_reel_details(reel_url):
    L = instaloader.Instaloader()  # Create a new Instaloader instance
    try:
        # Extract the shortcode from the URL
        shortcode = (
            reel_url.rstrip("/").split("/")[-1]
            if "reel" in reel_url
            else reel_url.rstrip("/").split("/")[-2]
        )
        # Fetch post details from the shortcode
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        # Process tagged users: Instaloader may return strings or objects
        tagged_users = []
        if post.tagged_users:
            for user in post.tagged_users:
                if isinstance(user, str):
                    tagged_users.append(user)
                elif hasattr(user, "username"):
                    tagged_users.append(user.username)
                else:
                    tagged_users.append(str(user))
        else:
            tagged_users = []
    
        # Build a dictionary with all details
        reel_data = {
            "Reel URL": reel_url,
            "Username": post.owner_username,
            "Profile URL": f"https://www.instagram.com/{post.owner_username}/",
            "Reel Caption": post.caption or "No caption",
            "Hashtags": ", ".join(post.caption_hashtags) if post.caption else "",
            "Timestamp": post.date_utc.strftime("%Y-%m-%d %H:%M:%S"),
            "Views": post.video_view_count,
            "Likes": post.likes,
            "Comments": post.comments,
            "Tagged Users": ", ".join(tagged_users),
            "Mentions": ", ".join(post.caption_mentions) if post.caption else "",
            "Video URL": post.video_url if post.is_video else "Not a video",
            "Post Type": "Reel" if post.is_video else "Image Post",
            "Location": post.location.name if post.location else "No location",
        }
        return reel_data
    except Exception as e:
        return {"Reel URL": reel_url, "Error": str(e)}

# ---------------- YouTube Video Retriever ----------------
def get_youtube_video_details(video_url):
    ydl_opts = {
        'quiet': True,         # Suppress extra output for faster processing
        'skip_download': True,   # Do not download the video
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
        
        # Extract the upload date (typically in YYYYMMDD format)
        upload_date = info.get("upload_date", "N/A")
        if upload_date != "N/A" and len(upload_date) == 8:
            upload_date_formatted = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
        else:
            upload_date_formatted = upload_date

        # Build a dictionary with metadata
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

# ---------------- Dailymotion Video Retriever ----------------
def get_dailymotion_video_details(video_url):
    try:
        # Extract video ID from URL
        video_id = None
        if 'dailymotion.com/video/' in video_url:
            video_id = video_url.split('/video/')[1].split('_')[0].split('?')[0]
        elif 'dai.ly/' in video_url:
            video_id = video_url.split('dai.ly/')[1].split('?')[0]
        
        if not video_id:
            return {"Video URL": video_url, "Error": "Invalid Dailymotion URL format"}
        
        # Construct API URL with allowed fields only (removed fields requiring extra scopes)
        api_url = f"https://api.dailymotion.com/video/{video_id}?fields="
        fields = [
            'id', 'title', 'description', 'created_time', 'modified_time',
            'duration', 'views_total', 'likes_total', 'comments_total',
            'owner.username', 'owner.id', 'tags', 'country', 'explicit',
            'channel.name', 'allow_embed', 'aspect_ratio', 'language',
            'thumbnail_720_url', 'url', 'status', 'private', 'rating',
            'ratings_total', 'geoblocking', 'custom_classification',
            'is_created_for_kids', 'embed_url', 'available_formats'
        ]
        api_url += ','.join(fields)
        
        response = requests.get(api_url)
        if response.status_code != 200:
            return {"Video URL": video_url, "Error": f"API Error: {response.text}"}
        
        data = response.json()
    
        # Convert timestamps if available
        created_time = (datetime.fromtimestamp(data['created_time'])
                        .strftime('%Y-%m-%d %H:%M:%S')) if 'created_time' in data else None
        modified_time = (datetime.fromtimestamp(data['modified_time'])
                         .strftime('%Y-%m-%d %H:%M:%S')) if 'modified_time' in data else None
    
        # Retrieve nested data safely
        owner = data.get('owner', {})
        channel = data.get('channel', {})
    
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
            "Owner Username": owner.get('username', 'N/A'),
            "Owner ID": owner.get('id', 'N/A'),
            "Tags": data.get('tags', []),
            "Country": data.get('country', 'N/A'),
            "Explicit": data.get('explicit', False),
            "Channel": channel.get('name', 'N/A'),
            "Allow Embed": data.get('allow_embed', False),
            "Aspect Ratio": data.get('aspect_ratio', 'N/A'),
            "Language": data.get('language', 'N/A'),
            "Thumbnail": data.get('thumbnail_720_url', 'N/A'),
            "Status": data.get('status', 'N/A'),
            "Private": data.get('private', False),
            "Rating": data.get('rating', 'N/A'),
            "Ratings Total": data.get('ratings_total', 0),
            "Geoblocking": data.get('geoblocking', []),
            "Custom Classification": data.get('custom_classification', 'N/A'),
            "Is Created for Kids": data.get('is_created_for_kids', False),
            "Embed URL": data.get('embed_url', 'N/A'),
            "Available Formats": data.get('available_formats', [])
        }
    
    except Exception as e:
        return {"Video URL": video_url, "Error": str(e)}

import json
import re
from bs4 import BeautifulSoup
import requests

def get_sharechat_video_details(video_url):
    try:
        response = requests.get(video_url)
        if response.status_code != 200:
            return {"Video URL": video_url, "Error": f"HTTP Error: {response.status_code}"}
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract standard Open Graph meta tags
        meta_title = soup.find("meta", property="og:title")
        meta_description = soup.find("meta", property="og:description")
        meta_image = soup.find("meta", property="og:image")
        meta_video = soup.find("meta", property="og:video")
        meta_url = soup.find("meta", property="og:url")
        
        # Initialize data using OG tags
        data = {
            "Video URL": video_url,
            "Title": meta_title["content"] if meta_title and meta_title.has_attr("content") else "N/A",
            "Description": meta_description["content"] if meta_description and meta_description.has_attr("content") else "N/A",
            "Thumbnail": meta_image["content"] if meta_image and meta_image.has_attr("content") else "N/A",
            "Video Link": meta_video["content"] if meta_video and meta_video.has_attr("content") else "N/A",
            "Page URL": meta_url["content"] if meta_url and meta_url.has_attr("content") else "N/A",
            "Upload Date": "N/A",
        }
        
        # --- JSON‑LD Extraction for Upload Date (if available) ---
        ld_json_scripts = soup.find_all("script", type="application/ld+json")
        for script in ld_json_scripts:
            try:
                json_content = script.string
                if not json_content:
                    continue
                ld_data = json.loads(json_content)
                video_object = None
                if isinstance(ld_data, list):
                    for item in ld_data:
                        if isinstance(item, dict) and item.get("@type") == "VideoObject":
                            video_object = item
                            break
                elif isinstance(ld_data, dict) and ld_data.get("@type") == "VideoObject":
                    video_object = ld_data

                if video_object and "uploadDate" in video_object:
                    data["Upload Date"] = video_object["uploadDate"]
                    break  # Use the first found VideoObject
            except Exception:
                continue
        
        return data
    except Exception as e:
        return {"Video URL": video_url, "Error": str(e)}








# ---------------- Streamlit App Layout ----------------
st.title("Social Media Metadata Retriever")
st.write("Select a tab to retrieve metadata from different platforms.")

# Create four tabs for each platform
tabs = st.tabs([
    "Instagram Reel Metadata",
    "YouTube Video Metadata",
    "Dailymotion Video Metadata",
    "ShareChat Video Metadata"
])

with tabs[0]:
    st.header("Instagram Reel Metadata")
    st.write("Paste your Instagram Reel URLs (one per line) to fetch metadata for each reel.")
    urls_input = st.text_area("Enter Instagram Reel URLs:")
    
    if st.button("Process Instagram Reels"):
        urls = [url.strip() for url in urls_input.splitlines() if url.strip()]
        if not urls:
            st.error("Please enter at least one valid reel URL.")
        else:
            st.info("Processing reels, please wait...")
            with ThreadPoolExecutor(max_workers=10) as executor:
                results = list(executor.map(get_reel_details, urls))
            df = pd.DataFrame(results)
            st.success("Processing complete!")
            st.dataframe(df)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="reel_metadata.csv",
                mime="text/csv"
            )

with tabs[1]:
    st.header("YouTube Video Metadata")
    st.write("Paste your YouTube Video URLs (one per line) to fetch metadata for each video.")
    yt_urls_input = st.text_area("Enter YouTube Video URLs:")
    
    if st.button("Process YouTube Videos"):
        yt_urls = [url.strip() for url in yt_urls_input.splitlines() if url.strip()]
        if not yt_urls:
            st.error("Please enter at least one valid video URL.")
        else:
            st.info("Processing YouTube videos, please wait...")
            with ThreadPoolExecutor(max_workers=10) as executor:
                yt_results = list(executor.map(get_youtube_video_details, yt_urls))
            df_yt = pd.DataFrame(yt_results)
            st.success("Processing complete!")
            st.dataframe(df_yt)
            csv_yt = df_yt.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download CSV",
                data=csv_yt,
                file_name="youtube_metadata.csv",
                mime="text/csv"
            )

with tabs[2]:
    st.header("Dailymotion Video Metadata")
    st.write("Paste Dailymotion Video URLs (one per line) to fetch metadata.")
    dm_urls_input = st.text_area("Enter Dailymotion URLs:")
    
    if st.button("Process Dailymotion Videos"):
        dm_urls = [url.strip() for url in dm_urls_input.splitlines() if url.strip()]
        if not dm_urls:
            st.error("Please enter at least one valid Dailymotion URL.")
        else:
            st.info("Processing Dailymotion videos...")
            with ThreadPoolExecutor(max_workers=10) as executor:
                dm_results = list(executor.map(get_dailymotion_video_details, dm_urls))
            df_dm = pd.DataFrame(dm_results)
            st.success("Processing complete!")
            st.dataframe(df_dm)
            csv_dm = df_dm.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download CSV",
                data=csv_dm,
                file_name="dailymotion_metadata.csv",
                mime="text/csv"
            )

with tabs[3]:
    st.header("ShareChat Video Metadata")
    st.write("Paste ShareChat Video URLs (one per line) to fetch metadata.")
    sc_urls_input = st.text_area("Enter ShareChat URLs:")
    
    if st.button("Process ShareChat Videos"):
        sc_urls = [url.strip() for url in sc_urls_input.splitlines() if url.strip()]
        if not sc_urls:
            st.error("Please enter at least one valid ShareChat URL.")
        else:
            st.info("Processing ShareChat videos...")
            with ThreadPoolExecutor(max_workers=10) as executor:
                sc_results = list(executor.map(get_sharechat_video_details, sc_urls))
            df_sc = pd.DataFrame(sc_results)
            st.success("Processing complete!")
            st.dataframe(df_sc)
            csv_sc = df_sc.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download CSV",
                data=csv_sc,
                file_name="sharechat_metadata.csv",
                mime="text/csv"
            )
