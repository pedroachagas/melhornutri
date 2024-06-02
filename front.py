import streamlit as st
import pandas as pd
import plotly.express as px
import boto3
from io import BytesIO

BUCKET_NAME = st.secrets["AWS_BUCKET_NAME"]
FILE_NAME = st.secrets["AWS_FILE_NAME"]
ACCESS_KEY = st.secrets["AWS_ACCESS_KEY_ID"]
SECRET_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]

# Initialize S3 client
s3 = boto3.client(
    's3',
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY
)

@st.cache_data(show_spinner=False)
def download_from_s3(bucket_name, file_name):
    file_obj = s3.get_object(Bucket=bucket_name, Key=file_name)
    file_content = file_obj['Body'].read()
    return pd.read_csv(BytesIO(file_content))

st.title("Melhor Nutricionarista de Macaé - Ranking de Menções")

comments_df = download_from_s3(BUCKET_NAME, FILE_NAME)
mention_counts = comments_df['text'].str.findall(r'@[\S]+').explode().value_counts().to_dict()

if mention_counts:
    df = pd.DataFrame(list(mention_counts.items()), columns=['Profissional', 'Menções'])
    df = df.sort_values(by='Menções', ascending=False).reset_index(drop=True)

    st.header("Top 3 Mais Mencionados")
    fig = px.bar(df.head(3), x='Profissional', y='Menções', color='Profissional')
    st.plotly_chart(fig)

    professional = '@' + st.text_input("Digite o nome do profissional para verificar a posição no ranking:", "_marcelasiqueira")
    if st.button("Verificar"):
        professional_mentions = mention_counts.get(professional, 0)
        if professional_mentions:
            position = df[df['Profissional'] == professional].index[0] + 1
            st.write(f"{professional} está na posição {position} com {professional_mentions} menções.")
        else:
            st.write(f"{professional} não foi mencionado.")
