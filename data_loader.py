
import pandas as pd
import re
from collections import Counter
from instagrapi import Client
import boto3

ACCOUNT_USERNAME = 'pedro.ch_'
ACCOUNT_PASSWORD = 'U#v0w1x2y3z4'
POST_URL = 'https://www.instagram.com/p/C7NlnFvtDX4/'
COMMENT_AMOUNT = 0
BUCKET_NAME = 'melhornutri'
FILE_NAME = 'comments.csv'

# Initialize S3 client
s3 = boto3.client('s3')

def count_mentions_in_comments(post_url, username, password):
    cl = Client()
    try:
        cl.login(username, password)
    except Exception as e:
        print(f"Failed to login: {e}")
        return {}, []

    try:
        media_id = cl.media_id(cl.media_pk_from_url(post_url))
        comments = cl.media_comments(media_id, amount=COMMENT_AMOUNT)
    except Exception as e:
        print(f"Failed to retrieve comments: {e}")
        return {}, []

    parsed_comments = []
    mentions = []

    for comment in comments:
        parsed_comment = {
            'pk': comment.pk,
            'text': comment.text,
            'user_pk': comment.user.pk,
            'username': comment.user.username,
            'full_name': comment.user.full_name,
            'profile_pic_url': comment.user.profile_pic_url,
            'created_at_utc': comment.created_at_utc,
            'content_type': comment.content_type,
            'status': comment.status,
            'has_liked': comment.has_liked,
            'like_count': comment.like_count
        }

        parsed_comments.append(parsed_comment)
        mentions_in_comment = re.findall(r'@[\S]+', comment.text)
        mentions.extend(mentions_in_comment)

    mention_counts = Counter(mentions)
    return mention_counts, parsed_comments

def upload_to_s3(file_path, bucket_name, file_name):
    s3.upload_file(file_path, bucket_name, file_name)

def main():
    _, parsed_comments = count_mentions_in_comments(POST_URL, ACCOUNT_USERNAME, ACCOUNT_PASSWORD)

    if parsed_comments:
        comments_df = pd.DataFrame(parsed_comments)
        comments_df.to_csv(FILE_NAME, index=False)
        upload_to_s3(FILE_NAME, BUCKET_NAME, FILE_NAME)

if __name__ == "__main__":
    main()
