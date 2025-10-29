# from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
import os
from dotenv import load_dotenv
load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", GEMINI_API_KEY)
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.output_parsers import StrOutputParser

# llm = ChatGoogleGenerativeAI(
#             model="gemini-2.0-flash",
#             temperature=0.3,
#             max_tokens=None,
#             timeout=None,
#             max_retries=2,
#             # google_api_key=self.gemini_api_key
#         )
# # --- Prompt 1: Extract Information ---
# prompt_extract = ChatPromptTemplate.from_template(
#    "Extract the technical specifications from the following text:\n\n{text_input}"
# )

# # --- Prompt 2: Transform to JSON ---
# prompt_transform = ChatPromptTemplate.from_template(
#    "Transform the following specifications into a JSON object with 'cpu', 'memory', and 'storage' as keys:\n\n{specifications}"
# )

# # --- Build the Chain using LCEL ---
# # The StrOutputParser() converts the LLM's message output to a simple string.
# extraction_chain = prompt_extract | llm | StrOutputParser()

# # The full chain passes the output of the extraction chain into the 'specifications'
# # variable for the transformation prompt.
# full_chain = (
#    {"specifications": extraction_chain}
#    | prompt_transform
#    | llm
#    | StrOutputParser()
# )

# # --- Run the Chain ---
# input_text = "The new laptop model features a 3.5 GHz octa-core processor, 16GB of RAM, and a 1TB NVMe SSD."

# # Execute the chain with the input text dictionary.
# final_result = full_chain.invoke({"text_input": input_text})

# print("\n--- Final JSON Output ---")
# print(final_result)


from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableBranch

# # --- Configuration ---
# # Ensure your API key environment variable is set (e.g., GOOGLE_API_KEY)
# try:
#    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
#    print(f"Language model initialized: {llm.model}")
# except Exception as e:
#    print(f"Error initializing language model: {e}")
#    llm = None

# # --- Define Simulated Sub-Agent Handlers (equivalent to ADK sub_agents) ---

# def seo_agent(request: str) -> str:
#    """Simulates the Booking Agent handling a request."""
#    print("\n--- DELEGATING TO SEO Agent ---")
#    return f"SEO Agent processed request: '{request}'. Result: Initiating the SEO Agent"

# def diagnosis_agent(request: str) -> str:
#    """Simulates the Info Agent handling a request."""
#    print("\n--- DELEGATING TO Diagnosis Agent ---")
#    return f"Diagnosis Agent processed request: '{request}'. Result: Initiating the Diagnosis Agent."

# def suggestions_agent(request: str) -> str:
#    """Handles requests that couldn't be delegated."""
#    print("\n--- DELEGATING TO Suggestions Agent ---")
#    return f"Suggestions Agent processed request: '{request}'. Result: Initiating the Suggestions Agent."

# # --- Define Coordinator Router Chain (equivalent to ADK coordinator's instruction) ---
# # This chain decides which handler to delegate to.
# coordinator_router_prompt = ChatPromptTemplate.from_messages([
#    ("system", """Analyze the user's request and determine which specialist agent should process it.
#     - If the request is related to analyzing the product/s or assigning SEO score, 
#       output 'seo agent'.
#     - If the request is related to diagnosing the issues in the products, 
#       output 'diagnosis agent'.
#     - If the request is related to finding solutions for some issues in the products, 
#       output 'suggestions agent'.
#     ONLY output one word: 'seo agent', 'diagnosis agent', or 'suggestions agent'."""),
#    ("user", "{request}")
# ])

# if llm:
#    coordinator_router_chain = coordinator_router_prompt | llm | StrOutputParser()

# # --- Define the Delegation Logic (equivalent to ADK's Auto-Flow based on sub_agents) ---
# # Use RunnableBranch to route based on the router chain's output.

# # Define the branches for the RunnableBranch
# branches = {
#    "seo_agent": RunnablePassthrough.assign(output=lambda x: seo_agent(x['request']['request'])),
#    "diagnosis_agent": RunnablePassthrough.assign(output=lambda x: diagnosis_agent(x['request']['request'])),
#    "suggestions_agent": RunnablePassthrough.assign(output=lambda x: suggestions_agent(x['request']['request'])),
# }

# # Create the RunnableBranch. It takes the output of the router chain
# # and routes the original input ('request') to the corresponding handler.
# delegation_branch = RunnableBranch(
#    (lambda x: x['decision'].strip() == 'seo agent', branches["seo_agent"]), # Added .strip()
#    (lambda x: x['decision'].strip() == 'diagnosis agent', branches["diagnosis_agent"]),     # Added .strip()
#    branches["suggestions_agent"],
# )

# # Combine the router chain and the delegation branch into a single runnable
# # The router chain's output ('decision') is passed along with the original input ('request')
# # to the delegation_branch.
# coordinator_agent = {
#    "decision": coordinator_router_chain,
#    "request": RunnablePassthrough()
# } | delegation_branch | (lambda x: x['output']) # Extract the final output

# # --- Example Usage ---
# def main():
#    if not llm:
#        print("\nSkipping execution due to LLM initialization failure.")
#        return

#    print("--- Running with a SEO request ---")
#    request_a = "Assign SEO score to the products."
#    result_a = coordinator_agent.invoke({"request": request_a})
#    print(f"Final Result A: {result_a}")

#    # print("\n--- Running with an Diagnosis request ---")
#    # request_b = "What can be the reason of low organic traffic?"
#    # result_b = coordinator_agent.invoke({"request": request_b})
#    # print(f"Final Result B: {result_b}")

#    # print("\n--- Running with a suggestion request ---")
#    # request_c = "How can I improve low organic traffic?"
#    # result_c = coordinator_agent.invoke({"request": request_c})
#    # print(f"Final Result C: {result_c}")

# if __name__ == "__main__":
#    main()

import os, getpass
import asyncio

from typing import List
from dotenv import load_dotenv
import logging

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool as langchain_tool
from langchain.agents import create_tool_calling_agent, AgentExecutor

# # UNCOMMENT
# # Prompt the user securely and set API keys as an environment variables
# os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter your Google API key: ")
# os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter your OpenAI API key: ")

try:
  # A model with function/tool calling capabilities is required.
  llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
  print(f"✅ Language model initialized: {llm.model}")
except Exception as e:
  print(f"🛑 Error initializing language model: {e}")
  llm = None

# --- Define a Tool ---
@langchain_tool
def search_information(query: str) -> str:
  """
  Provides factual information on a given topic. Use this tool to find answers to phrases
  like 'capital of France' or 'weather in London?'.
  """
  print(f"\n--- 🛠️ Tool Called: search_information with query: '{query}' ---")
  # Simulate a search tool with a dictionary of predefined results.
  simulated_results = {
      "weather in london": "The weather in London is currently cloudy with a temperature of 15°C.",
      "capital of france": "The capital of France is Paris.",
      "population of earth": "The estimated population of Earth is around 8 billion people.",
      "tallest mountain": "Mount Everest is the tallest mountain above sea level.",
      "default": f"Simulated search result for '{query}': No specific information found, but the topic seems interesting."
  }
  result = simulated_results.get(query.lower(), simulated_results["default"])
  print(f"--- TOOL RESULT: {result} ---")
  return result

tools = [search_information]

# --- Create a Tool-Calling Agent ---
if llm:
  # This prompt template requires an `agent_scratchpad` placeholder for the agent's internal steps.
  agent_prompt = ChatPromptTemplate.from_messages([
      ("system", "You are a helpful assistant."),
      ("human", "{input}"),
      ("placeholder", "{agent_scratchpad}"),
  ])

  # Create the agent, binding the LLM, tools, and prompt together.
  agent = create_tool_calling_agent(llm, tools, agent_prompt)

  # AgentExecutor is the runtime that invokes the agent and executes the chosen tools.
  # The 'tools' argument is not needed here as they are already bound to the agent.
  agent_executor = AgentExecutor(agent=agent, verbose=True, tools=tools)

async def run_agent_with_tool(query: str):
  """Invokes the agent executor with a query and prints the final response."""
  print(f"\n--- 🏃 Running Agent with Query: '{query}' ---")
  try:
      response = await agent_executor.ainvoke({"input": query})
      print("\n--- ✅ Final Agent Response ---")
      print(response["output"])
  except Exception as e:
      print(f"\n🛑 An error occurred during agent execution: {e}")

async def main():
  """Runs all agent queries concurrently."""
  tasks = [
      run_agent_with_tool("What is the capital of France?"),
      run_agent_with_tool("What's the weather like in London?"),
      run_agent_with_tool("Tell me something about dogs.") # Should trigger the default tool response
  ]
  await asyncio.gather(*tasks)

# asyncio.run(main())

