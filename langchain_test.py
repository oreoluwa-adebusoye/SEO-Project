import os
from dotenv import load_dotenv
from langchain.agents import Tool, initialize_agent
from langchain.chat_models import ChatOpenAI
from langchain.utilities import GoogleSearchAPIWrapper
from langchain.memory import ConversationBufferMemory

# Load keys
load_dotenv()
openai_key = os.getenv("OPENAI_API_KEY")
serp_key = os.getenv("GOOGLE_API_KEY")

# Setup search tool
search = GoogleSearchAPIWrapper(google_api_key=os.getenv("GOOGLE_API_KEY"))

tools = [
    Tool(
        name="Search",
        func=search.run,
        description="Use this to search for events happening now"
    )
]

# Setup agent
llm = ChatOpenAI(temperature=0, openai_api_key=openai_key)
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent="chat-conversational-react-description",
    verbose=True,
    memory=memory
)

# Example query
response = agent.run("What events are happening in NYC this weekend?")
print(response)
