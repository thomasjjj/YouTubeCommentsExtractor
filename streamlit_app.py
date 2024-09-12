import os
import googleapiclient.discovery
import csv
import re
from datetime import datetime
import streamlit as st

# Function to extract video ID from a YouTube URL
def get_video_id_from_url(url):
    video_id = None
    match = re.match(r'.*v=([a-zA-Z0-9_-]+)', url)
    if match:
        video_id = match.group(1)
    return video_id

# Function to retrieve video details (title, author)
def get_video_details(video_id, api_key):
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)

    response = youtube.videos().list(
        part="snippet",
        id=video_id
    ).execute()

    if response['items']:
        video_title = response['items'][0]['snippet']['title']
        video_author = response['items'][0]['snippet']['channelTitle']
        return video_title, video_author
    else:
        return None, None

# Function to retrieve comments from a YouTube video
def get_video_comments(video_id, api_key, max_comments=None):
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)
    all_comments = []

    request = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=100,
        textFormat="plainText"
    )

    response = request.execute()

    while response:
        for item in response['items']:
            comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
            author = item['snippet']['topLevelComment']['snippet']['authorDisplayName']
            published_at = item['snippet']['topLevelComment']['snippet']['publishedAt']

            all_comments.append({
                'comment_author': author,
                'comment_text': comment,
                'comment_published_at': published_at
            })

            if max_comments and len(all_comments) >= max_comments:
                return all_comments

        if 'nextPageToken' in response:
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                pageToken=response['nextPageToken'],
                maxResults=100,
                textFormat="plainText"
            )
            response = request.execute()
        else:
            break

    return all_comments

# Function to sanitize the filename
def sanitize_filename(filename):
    return re.sub(r'[\/:*?"<>|]', '_', filename)

# Function to save comments to a CSV file
def save_comments_to_csv(video_title, video_author, video_url, comments):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    sanitized_title = sanitize_filename(video_title.replace(' ', '_'))
    filename = f"comments_{sanitized_title}_{timestamp}.csv"

    for comment in comments:
        comment['video_title'] = video_title
        comment['video_author'] = video_author
        comment['video_url'] = video_url

    keys = comments[0].keys()
    with open(filename, 'w', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(comments)

    st.success(f"Comments saved to {filename}")

# Streamlit UI
def main():
    st.title("YouTube Comment Extractor")

    # User input for YouTube API Key
    api_key = st.text_input("Enter your YouTube API Key", type="password")

    if api_key:
        st.write("YouTube API Key is set")

        # User input for video URL or file
        choice = st.radio("Select input method:", ("Single YouTube URL", "Upload .txt file with multiple URLs"))

        max_comments = st.number_input("Number of comments to retrieve per video (Leave empty for all comments)", min_value=1, step=1, value=100)

        if choice == "Single YouTube URL":
            video_url = st.text_input("Enter YouTube video link:")
            if st.button("Retrieve Comments"):
                process_single_video(video_url, api_key, max_comments)

        elif choice == "Upload .txt file with multiple URLs":
            uploaded_file = st.file_uploader("Upload a .txt file with YouTube video links", type=['txt'])
            if uploaded_file:
                video_links = uploaded_file.read().decode("utf-8").splitlines()
                if st.button("Retrieve Comments from All Videos"):
                    for video_url in video_links:
                        process_single_video(video_url, api_key, max_comments)

def process_single_video(video_url, api_key, max_comments):
    video_id = get_video_id_from_url(video_url)

    if not video_id:
        st.error(f"Invalid YouTube link: {video_url}")
        return

    video_title, video_author = get_video_details(video_id, api_key)

    if not video_title or not video_author:
        st.error("Could not retrieve video details. Please check the video URL.")
        return

    st.write(f"**Video Title**: {video_title}")
    st.write(f"**Video Author**: {video_author}")

    comments = get_video_comments(video_id, api_key, max_comments)

    if comments:
        save_comments_to_csv(video_title, video_author, video_url, comments)
        st.write(f"Successfully retrieved {len(comments)} comments.")
        st.dataframe(comments)  # Display comments in a table format
    else:
        st.write("No comments found or an error occurred.")

if __name__ == "__main__":
    main()
