import streamlit as st
import pandas as pd
import plotly.express as px
import boto3
from io import BytesIO

st.set_page_config(page_title="Melhor Nutri de Macaé", page_icon="🍎")
BUCKET_NAME = st.secrets["AWS_BUCKET_NAME"]
ACCESS_KEY = st.secrets["AWS_ACCESS_KEY_ID"]
SECRET_KEY = st.secrets["AWS_SECRET_ACCESS_KEY"]

df_business_types = pd.read_csv('business_types.csv')
business_types = df_business_types['business_type'].tolist()

with st.sidebar:
    st.title("Melhores do Ano 2024 - Macaé, RJ")
    st.markdown(f"""
        Este é um dashboard para analisar os comentários dos posts de votação de melhores negócios de Macaé, RJ.
        """)
    business_type = st.selectbox(
        "Selecione o tipo de negócio:",
        business_types,
        index=business_types.index('Nutricionista')
        )
    st.markdown(f"""
        **Instruções:**
        1. Digite o nome do profissional para verificar a posição no ranking.
        2. Selecione o número de profissionais para visualizar no ranking.
        3. Selecione os profissionais para visualizar o número de menções ao longo do tempo.

        **Dica:** Clique no nome do profissional na legenda para ocultar/mostrar a linha correspondente no gráfico.

        """)
    df_business = df_business_types[df_business_types['business_type'] == business_type]
    FILE_NAME = f'posts_final/comments_{business_type}.csv'
    # url = df_business['url'].values[0]
    # st.markdown(f"[Acesse o post de votação]({url})")

# Initialize S3 client
s3 = boto3.client(
    's3',
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY
)

@st.cache_data(show_spinner=False)
def download_from_s3(bucket_name, file_name):
    try:
        file_obj = s3.get_object(Bucket=bucket_name, Key=file_name)
        file_content = file_obj['Body'].read()
        return pd.read_csv(BytesIO(file_content))
    except Exception as e:
        st.error(f"Erro ao baixar o arquivo: {file_name}")
        return pd.DataFrame()


st.title(business_type.upper())
comments_df = download_from_s3(BUCKET_NAME, FILE_NAME)
comments_df = comments_df.drop_duplicates(subset=['username'])

if comments_df.empty:
    st.warning("Nenhum comentário encontrado.")
    st.stop()

mention_counts = comments_df['text'].str.findall(r'@[\S]+').explode().value_counts().to_dict()

if mention_counts:
    df = pd.DataFrame(list(mention_counts.items()), columns=['Profissional', 'Menções'])
    df = df.sort_values(by='Menções', ascending=False).reset_index(drop=True)
    st.subheader("Verificar Posição no Ranking")
    professional = '@' + st.text_input("Digite o nome do profissional para verificar a posição no ranking:")
    if st.button("Verificar"):
        professional_mentions = mention_counts.get(professional, 0)
        if professional_mentions:
            position = df[df['Profissional'] == professional].index[0] + 1
            st.write(f"{professional} está na posição {position} com {professional_mentions} menções.")
        else:
            st.write(f"{professional} não foi mencionado.")

    # st.divider()
    st.header("Ranking de Menções")
    topn = st.number_input("Selecione o número de profissionais para visualizar no ranking:", 1, 15, 3)
    fig = px.bar(df.head(topn), x='Profissional', y='Menções', color='Profissional', title=f'Top {topn} Profissionais Mais Mencionados')
    st.plotly_chart(fig)

    # st.divider()
    st.header("Número de Curtidas ao Longo do Tempo")
    selected_professionals = st.multiselect("Selecione os profissionais:", df['Profissional'].tolist(), default=df['Profissional'].head(topn).tolist())

    if selected_professionals:
        mentions_df = comments_df.loc[comments_df['text'].str.contains('|'.join(selected_professionals))]
        mentions_df.loc[:, 'created_at_utc'] = pd.to_datetime(mentions_df['created_at_utc'])

        mentions_df = mentions_df.groupby([mentions_df['created_at_utc'], 'text']).size().reset_index(name='mentions')
        mentions_df['Profissional'] = mentions_df['text'].str.findall(r'@[\S]+').apply(lambda x: next((prof for prof in x if prof in selected_professionals), None))

        mentions_df = mentions_df.groupby(['created_at_utc', 'Profissional'])['mentions'].sum().groupby(level=1).cumsum().reset_index()

        # Pivot the dataframe to have professionals as columns and dates as index
        pivot_df = mentions_df.pivot(index='created_at_utc', columns='Profissional', values='mentions')

        # Forward fill the NaN values
        pivot_df = pivot_df.ffill()

        # Now melt the dataframe back to the original shape
        mentions_df = pivot_df.reset_index().melt(id_vars='created_at_utc', value_name='mentions')

        # Plot the chart
        fig_mentions = px.line(mentions_df, x='created_at_utc', y='mentions', color='Profissional', title='Menções por Profissional ao Longo do Tempo')
        fig_mentions.update_layout(
            yaxis_title="Menções",
            xaxis_title="Tempo"
        )
        st.plotly_chart(fig_mentions)