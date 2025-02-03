import streamlit as st
from pathlib import Path
import sqlite3
from langchain.agents import create_sql_agent,AgentType
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from sqlalchemy import create_engine ## used to map what is coming through your database
from langchain_groq import ChatGroq
from langchain.callbacks import StreamlitCallbackHandler


st.title("Langchain: chat with your sql db")

LOCALDB="USE_LOCALDB"
MYSQL="USE_MYSQL"

radio_opt=["Use Sqlite3 database-student.db","Connect to your own SQL Database"]

selected_opt=st.sidebar.radio(label="which db to choose",options=radio_opt)

if radio_opt.index(selected_opt)==1:
    db_uri=MYSQL
    mysql_host=st.sidebar.text_input("Please provide the sql host")
    mysql_user=st.sidebar.text_input("MYSQL User")
    mysql_pw=st.sidebar.text_input("Mysql password",type="password")
    mysql_db=st.sidebar.text_input("MYSQL Database")
else:
    db_uri=LOCALDB


if not db_uri:
    st.info("Please enter database info and uri to proceed")


api_key=st.sidebar.text_input("Enter your GROQ API to continue")
if not api_key:
    st.error("enter your api key")
llm=ChatGroq(api_key=api_key,model="Llama3-8b-8192",streaming=True)

@st.cache_resource(ttl="2h") ##ttl=total time limit that your db will persists 
def configure_db(db_uri,mysql_host=None,mysql_user=None,mysql_pw=None,mysql_db=None):
    if db_uri==LOCALDB:
        dbfilepath=(Path(__file__).parent/"student.db").absolute()
        print(f"filepath is :{dbfilepath}")
        creator=lambda: sqlite3.connect(f"file:{dbfilepath}?mode=ro",uri=True)
        return SQLDatabase(create_engine("sqlite:///",creator=creator))

    elif db_uri==MYSQL:
        if not (mysql_host and mysql_db and mysql_pw and mysql_user):
            st.error("Please provide all connection details")
            st.stop()
    
        return SQLDatabase(create_engine(f"mysql+pymysql://{mysql_user}:{mysql_pw}@{mysql_host}/{mysql_db}"))

if db_uri==MYSQL:
    db=configure_db(db_uri,mysql_host,mysql_user,mysql_pw,mysql_db)
else:
    db=configure_db(db_uri)


##toolkit-using an llm model to create query of what we have asked such that query will interact
##with db and give us results

toolkit=SQLDatabaseToolkit(db=db,llm=llm)

agent=create_sql_agent(
    llm=llm,
    toolkit=toolkit,
    verbose=True,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION
)




if "sql_mode" not in st.session_state or st.sidebar.button("Clear message history"):
    st.session_state["sql_mode"]=[{"role":"assistant","content":"How can I help you"}]


for msg in st.session_state.sql_mode:
    st.chat_message(msg["role"]).write(msg["content"])

user_query=st.chat_input(placeholder="Askk your query from database")
if user_query:
    st.session_state.sql_mode.append({"role":"user","content":user_query})
    st.chat_message("user").write(user_query)

    with st.chat_message("assistant"):
        st_cb=StreamlitCallbackHandler(st.container())
        response=agent.run(user_query,callbacks=[st_cb])
        st.session_state.sql_mode.append({"role":"assistant","content":response})
        st.write(response)  
        