# Fraud Ring Investigator

A GraphRAG chat for fraud investigators. It works on personal auto injury claims.

The tool puts claims, people, phones, addresses, repair shops, clinics, law firms, lawsuits and the claim documents into one graph database. An investigator asks a question in plain English. A team of AI agents searches the graph and the documents, and gives a short answer with sources.

The chat runs on your computer, or as a hosted agent on Microsoft Foundry (section 7).

> **All data in this project is fake.** A program made every name, claim and document. No record is about a real person or a real company.

> **The tool does not say that a person is guilty.** It shows possible links and unusual patterns. A human investigator must review each result.

---

## Contents

1. [What the tool does](#1-what-the-tool-does)
2. [Project status](#2-project-status)
3. [Words used in this README](#3-words-used-in-this-readme)
4. [What you need](#4-what-you-need)
5. [Set up the project](#5-set-up-the-project)
6. [Use the tool](#6-use-the-tool)
7. [Host the chat on Microsoft Foundry](#7-host-the-chat-on-microsoft-foundry)
8. [Run the tests](#8-run-the-tests)
9. [The data in this repository](#9-the-data-in-this-repository)
10. [Project layout](#10-project-layout)
11. [Safety rules in the code](#11-safety-rules-in-the-code)
12. [If you have a problem](#12-if-you-have-a-problem)

---

## 1. What the tool does

Fraud rings often use the same phone numbers, addresses, repair shops, clinics or lawyers again and again. One claim alone can look normal. Many claims together can show a pattern.

The tool has two parts:

1. **The pipeline** (run one time). It makes fake claims and fake PDF documents, loads them into a graph database (Neo4j), scores every claim with fixed rules, and finds the groups of linked claims (communities).
2. **The chat.** A planner agent reads the question and sends each part to the search agent that fits:

| Agent | Example question | What it does |
|-------|------------------|--------------|
| Local search | "Tell me about David Richardson." | Reads one person, business, phone, address or claim, and everything around it. |
| Document search | "Which claims mention home stretching?" | Searches all documents by meaning and by words, then adds the claim of each hit. |
| Global search | "Are there any fraud rings?" | Reads the communities (groups of linked claims) and their reports. |
| Graph query | "How many claims are in each status?" | Writes one read-only database query. Plain code checks it before it runs. |
| Scorer | "Why is C-1088 High?" | Gets the risk score of a claim from the fixed rules, with the proof. |

An answer writer then writes a short reply from the findings. Plain code checks the reply and adds the sources.

The fake data has 3 hidden fraud rings:

| Ring | Pattern |
|------|---------|
| A | Staged accidents. The claims share phones, addresses and one repair shop. The accident stories are almost the same. |
| B | One clinic and one law firm. The claims have the same treatment pattern and similar medical bills. |
| C | Lawsuits. The claims use the same law firm and the same expert. The lawyers file just before the legal deadline. |

The data also has **innocent overlaps**. Examples: family members who share an address, and a popular repair shop with many honest customers. A good tool must not mark these as fraud.

## 2. Project status

The backend (Phase 1) is complete. A web front end comes next.

| Part | Status |
|------|--------|
| Fake tables (500 claims, 50 lawsuits) and fake PDFs (2,826 documents) | Works |
| Pipeline: tables, PDFs, scores, communities and graph map in Neo4j | Works |
| Chat: planner, 5 search agents, answer writer (LangGraph) | Works, tested with a fake LLM |
| 4 MCP servers with the tools of the agents | Works |
| Hosted agent `fraud-investigator-agent` on Microsoft Foundry, graph in Neo4j AuraDB Free | Works, smoke test passed |
| Test questions with the real LLM (build step 6) | Skipped for now |
| Evaluations and continuous monitoring in Foundry | Not set up yet |

## 3. Words used in this README

| Word | Meaning | Example |
|------|---------|---------|
| Graph database | A database that keeps things (**nodes**) and the links between them (**edges**). | The node `Claim C-1037` has an edge to the node `Phone 713-555-3237`. |
| Neo4j | The graph database that this project uses. | You open it in a web browser at `http://localhost:7474`. |
| Cypher | The query language of Neo4j. | `MATCH (c:Claim) RETURN count(c)` counts the claims. |
| Docker | A program that runs other programs in a closed box (a **container**). | Docker runs Neo4j, so you do not install Neo4j yourself. |
| LLM | Large language model. An AI that reads and writes text. This project uses gpt-5.4-mini in Microsoft Foundry. | The LLM wrote the free text in the fake PDFs. |
| Agent | A part of the program that uses an LLM to decide what to do next. Plain code does the work. | The planner chooses which search agent gets a question. |
| MCP | Model Context Protocol: a standard way to offer tools to an AI program. Each MCP server is a small program with a fixed list of tools. | The scorer agent calls the tool `get_claim_score` on the claim records server. |
| GraphRAG | Retrieval-augmented generation over a graph: the LLM answers from what it finds in the graph and the documents. | The answer to "Are there rings?" comes from the communities in the graph. |
| Virtual environment | A folder that keeps the Python packages of one project apart from other projects. | The folder `.venv`. |
| `.env` file | A private file that keeps passwords and keys. You do not share it. | `NEO4J_PASSWORD=...` |
| Microsoft Foundry | The Azure service that runs AI models and AI agents. A **Foundry project** holds the model deployments and the agents. | The project has the model deployment `gpt-5.4-mini`. |
| Hosted agent | An agent whose code runs in Foundry, not on your computer. Foundry gives it versions, logs and traces. | `fraud-investigator-agent`. |
| azd | Azure Developer CLI. A command-line tool that sends the code to Foundry and starts the hosted agent. | `azd deploy`. |
| Neo4j AuraDB | Neo4j in the cloud. The hosted agent cannot reach the Neo4j on your computer, so it uses AuraDB. | The free tier, AuraDB Free. |

## 4. What you need

- A Mac, Linux or Windows computer.
- **Python 3.14.** Other Python 3 versions can also work, but we tested only 3.14.
- **Docker Desktop.** Neo4j runs in Docker.
- **A Microsoft Foundry project with a gpt-5.4-mini deployment, and `az login`.** No API key. You need it for the chat and to make new LLM text. Each LLM call costs money. See [section 9](#9-the-data-in-this-repository).
- About 3 GB of free disk space.
- **Only to host the chat on Foundry (section 7):** the Azure CLI (`az`), azd with the `azure.ai.agents` extension, and a free Neo4j AuraDB database.

## 5. Set up the project

Do the steps that follow one time.

1. Get the code.
   ```bash
   git clone https://github.com/sunilsamsons/fraud-ring-investigator-foundry-deployed.git
   cd fraud-ring-investigator-foundry-deployed
   ```
2. Make a virtual environment.
   ```bash
   python3 -m venv .venv
   ```
3. Start the virtual environment. Do this step each time that you open a new terminal.
   ```bash
   source .venv/bin/activate
   ```
   On Windows, use this command: `.venv\Scripts\activate`
4. Install the Python packages.
   ```bash
   pip install -r requirements.txt
   ```
   Note: `sentence-transformers` is large. The install can take some minutes.
5. Make your private settings file.
   ```bash
   cp .env.example .env
   ```
6. Open `.env` in a text editor. Change these two values:
   - `NEO4J_PASSWORD`: write a new password. Use 8 characters or more.
   - `FOUNDRY_PROJECT_ENDPOINT`: the endpoint of your Foundry project. Then run `az login`.

   **Do not share `.env`. Do not commit it to git.** The `.gitignore` file keeps it out of git.
7. Start Neo4j.
   ```bash
   docker compose up -d
   ```
8. Wait about 20 seconds. Then make sure that Neo4j works.
   ```bash
   python -m pytest -q tests/test_graph_connection.py
   ```
   All tests in the file must pass.

## 6. Use the tool

Start the virtual environment and Neo4j first (setup steps 3 and 7).

### See all commands

```bash
python main.py --help
```

### Make the fake data (optional)

The data is already in the repository (section 9). Make it again only if you want to.

```bash
python main.py generate-data --tables
```

This writes the CSV files to `data/tables/` and the answer key to `data/ground_truth.json`. It uses a fixed random seed (42), so each run makes the same data.

```bash
python main.py generate-data --pdfs --limit 5
```

This makes the PDFs of 5 claims. Remove `--limit 5` to make all of them. The tool asks you to confirm. The PDF text comes from the LLM, but every answer is in `data/cache/`, so the same run costs nothing.

### Build the graph

```bash
python main.py build-graph
```

This runs the pipeline in order: the tables, the PDFs (pages, chunks, mentions, findings), the scores of all claims, the communities, and the graph map. The tool asks you to confirm. You can run it again: every step uses MERGE, so it makes no copies. Add `--write-reports` to let the LLM write one report for each community (cached).

### Look at one score, or at the rules

```bash
python main.py score-claim C-1088
```

```bash
python main.py show-rules
```

### Ask questions in plain English

```bash
python main.py chat
```

Examples: `Are there any fraud rings?`, `Tell me about David Richardson`, then `Why is his top claim High?`.
The chat remembers the conversation until you type `exit`. Each message uses the strong model and costs a few cents.

To see each step of one message (the agent that ran, the tools it called, what it added), run:

```bash
python debug_chat.py "Why is C-1088 High?"
```

It uses the cheap model, so it costs about one cent.

## 7. Host the chat on Microsoft Foundry

The same chat can run as a **hosted agent** on Microsoft Foundry. Foundry runs the code, gives each deploy a new version, and keeps the logs and traces.

### How it works

```
Investigator -> Foundry hosted agent "fraud-investigator-agent"
                  foundry_agent.py (one node, out of sight)
                    -> src/workflow.py: planner -> 5 search agents -> answer writer
                         -> 4 MCP servers -> Neo4j AuraDB Free (the graph)
                         -> gpt-5.4-mini in the same Foundry project
             <- only the final, checked reply
```

| File | What it does | Who made it |
|------|--------------|-------------|
| `foundry_agent.py` | The entry point. A wrapper LangGraph graph with one node. It runs the chat out of sight and returns only the final, checked reply. | We wrote it. |
| `langgraph.json` | Tells the Foundry hosting package where the graph is (`./foundry_agent.py:graph`). | We wrote it. |
| `azure.yaml` | The azd settings: the Foundry project, the agent name, the runtime (Python 3.13), the size (2 vCPU, 4 GiB) and the settings of the agent. | `azd ai agent init` made it. We changed the size and the settings. |
| `.agentignore` | The files that `azd deploy` does not send to Foundry: `.env`, `.azure/`, tests and the large data folders. | We wrote it. |
| `.azure/<env>/.env` | The azd environment: the endpoints, the agent version and the Neo4j values. **It is not in git.** | azd makes it. You add values with `azd env set`. |

Why the wrapper graph? The hosting package shows the person every message that the hosted graph makes. That includes the notes of the planner and the tool results. Plain code checks only the reply of the answer writer, so only that reply may reach the person.

### Step 1: Put the graph in Neo4j AuraDB

The hosted agent cannot reach the Neo4j on your computer.

1. Make a free database at [console.neo4j.io](https://console.neo4j.io). Keep the connection URI, the user name and the password.
2. In `.env`, set `NEO4J_URI` (it starts with `neo4j+s://`), `NEO4J_USER` and `NEO4J_PASSWORD` to the AuraDB values.
3. Load the graph into AuraDB. This is the same command as in section 6.
   ```bash
   python main.py build-graph
   ```
4. Make sure that the chat works with AuraDB on your computer: `python main.py chat`.

### Step 2: Sign in and install the tools

The same on macOS and Windows:

```bash
az login
azd auth login
azd extension install azure.ai.agents
```

### Step 3: Set the azd environment

1. In `azure.yaml`, change `endpoint` under `aa-foundry-customcode` to the endpoint of your Foundry project.
2. Make an azd environment and set the values. The same on macOS and Windows:
   ```bash
   azd env new fraud-ring-detector-dev
   azd env set AZURE_AI_PROJECT_ENDPOINT "<your Foundry project endpoint>"
   azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME gpt-5.4-mini
   azd env set NEO4J_URI "<your AuraDB URI>"
   azd env set NEO4J_USER "<your AuraDB user>"
   azd env set NEO4J_PASSWORD "<your AuraDB password>"
   ```
   azd keeps these values in `.azure/fraud-ring-detector-dev/.env`. This folder is in `.gitignore`.
3. Make sure that the values are there: `azd env get-values`.

### Step 4: Deploy

```bash
azd deploy fraud-investigator-agent
```

Foundry gets the code, installs `requirements.txt` (remote build) and starts the agent. Each deploy makes a new agent version. azd asks for each value that is missing.

### Step 5: Give the agent identity a role

Each hosted agent has its own identity in Entra ID. The agent uses it to call gpt-5.4-mini. Give it the role **Foundry User** on the Foundry resource and on the project.

1. Get the principal ID of the agent identity: `azd env get-values`. Find `AGENT_FRAUD_INVESTIGATOR_AGENT_INSTANCE_IDENTITY_PRINCIPAL_ID`.
2. Give the role. Do this two times: one time with the ID of the Foundry resource as the scope, and one time with the ID of the project.
   ```bash
   az role assignment create --assignee-object-id "<principal ID>" --assignee-principal-type ServicePrincipal --role "Foundry User" --scope "<resource or project ID>"
   ```

A new role can take 10 to 30 minutes to work. A new agent name gives a new identity, so do this step again after a rename.

### Step 6: Ask the hosted agent a question

```bash
azd ai agent invoke fraud-investigator-agent --new-session "Are there any fraud rings?"
```

The first answer after a deploy is slow, because the agent must start (about 80 seconds in our test). Then the answers come faster.

To see the logs of the agent:

```bash
azd ai agent monitor --tail 100
```

You can also open the agent in the Foundry portal (ai.azure.com). Select your project, then **Agents**, then `fraud-investigator-agent`. The portal shows the versions and the traces, and it has a playground for questions.

## 8. Run the tests

Start Neo4j first. Then run this command:

```bash
python -m pytest -q -p no:warnings
```

The tests do not call the LLM. They use a fake LLM with scripted answers, so they cost nothing. They use the real graph and the real MCP servers.

**Caution:** the tests read the same Neo4j database as the tool. They do not change it.

Some tests load data into a second, empty Neo4j (the scratch database). They are skipped if it does not run. To start it:

```bash
docker run -d --name fraud-ring-scratch-neo4j -p 7688:7687 -e NEO4J_AUTH=neo4j/scratch-test-password neo4j:5.26-community
```

## 9. The data in this repository

The `data/` folder is in the repository. You can use the project without making the data again.

| Folder or file | What it holds |
|----------------|---------------|
| `data/tables/` | 16 CSV files: claims, claimants, incidents, policies, vehicles, addresses, providers, treatments, attorneys, law firms, lawsuits, settlements, courts, experts, payments, reserve events. |
| `data/pdfs/` | One folder for each claim, with its PDF documents. `documents.csv` lists all PDFs. `planted_conflicts.csv` lists the date errors that we put in on purpose. |
| `data/cache/` | The saved LLM answers. One JSON file for each answer. |
| `data/ground_truth.json` | The answer key: which claims are in each ring, and which claims are innocent overlaps. |
| `data/graph_map.json` | What is in the graph (labels, properties, links). The graph query agent reads it. |

Each PDF page has this text at the bottom: **SYNTHETIC TEST DOCUMENT - NOT A REAL RECORD**.

## 10. Project layout

```
fraud-ring-investigator-foundry-deployed/
  main.py                 Reads the command. Calls one function.
  debug_chat.py           Runs one chat message and prints each step.
  foundry_agent.py        The Foundry entry point. Returns only the final, checked reply.
  langgraph.json          Points the Foundry hosting package to the graph in foundry_agent.py.
  azure.yaml              The azd settings of the hosted agent.
  .agentignore            The files that azd deploy does not send to Foundry.
  docker-compose.yml      Starts Neo4j.
  requirements.txt        Python packages.
  .env.example            Settings file with fake values. Copy it to .env.
  data/                   Fake data (see section 9).
  src/
    config.py             All settings: model names, folders, seed, limits.
    llm.py                Asks gpt-5.4-mini in Foundry. The pipeline saves each answer in the cache; the chat does not.
    state.py              The shared state of the chat: the messages.
    workflow.py           The LangGraph chat graph: planner -> search agents -> answer writer.
    agents/               The planner, the 5 search agents and the answer writer.
    mcp_servers/          The 4 MCP servers, and the client that the agents use (call_server_tool.py).
    tools/                The plain code behind each tool. checks.py checks every value.
                          query_guard.py checks every generated query.
    scoring/              The facts of a claim, the 32 rules and the score engine.
    graph/                connection.py (Neo4j) and queries.py (all fixed read queries).
    data_generation/      Makes the fake tables and PDFs.
    data_loading/         The pipeline: tables, PDFs, scores, communities, graph map.
  tests/                  Automatic tests (pytest).
```

## 11. Safety rules in the code

- **Agents reach the data only through MCP tools.** Each agent has a fixed list of tools. Each tool checks its values and passes them to a fixed query as parameters. A test sends `MATCH (n) DETACH DELETE n` to every tool. Nothing runs, and the graph does not change.
- **One agent writes its own queries, and they can only read.** The graph query agent writes Cypher. Plain code refuses write words and unknown procedures, Neo4j must confirm with `EXPLAIN` that the query only reads, and the query runs in a read-only session with a time limit and a row limit.
- **Plain code checks every reply.** A reply that names a claim or a rule that no tool returned, or that uses a word like "guilty", is not shown.
- **The score is plain code.** The LLM never decides points and never decides if a rule fires.
- **Passwords and keys stay in `.env`.** The code never prints them. `.agentignore` keeps `.env` and `.azure/` out of the Foundry deploy.
- **The hosted agent shows only the final, checked reply.** `foundry_agent.py` keeps the notes of the planner and the tool results inside.
- **No API keys for the LLM.** The chat signs in with Entra ID: `az login` on your computer, the agent identity on Foundry.
- **Each pipeline LLM answer goes into the cache.** The same request does not cost money two times.

## 12. If you have a problem

| Problem | What to do |
|---------|------------|
| `Cannot reach Neo4j at bolt://localhost:7687` | Start Neo4j with `docker compose up -d`. Wait 20 seconds. Try again. |
| `Neo4j rejected the user name or password` | Make sure that `NEO4J_PASSWORD` in `.env` is the same as the password when you first started Neo4j. If you changed it, the old password is still in the Docker volume. |
| `FOUNDRY_PROJECT_ENDPOINT is empty` | Put the endpoint of your Foundry project in `.env`, then run `az login`. |
| `data/tables/claims.csv is missing` | Run `python main.py generate-data --tables`. |
| `ModuleNotFoundError` | Start the virtual environment: `source .venv/bin/activate`. |
| The hosted agent says that it has no permission to call the model | Give the agent identity the role Foundry User on the resource and on the project (section 7, step 5). Wait 10 to 30 minutes. |
| The hosted agent cannot reach Neo4j | AuraDB Free pauses after some days without use. Resume it at console.neo4j.io. Make sure that `NEO4J_URI` in the azd environment starts with `neo4j+s://`. |
| `azd ai agent delete` says that no service has the name | azd finds only the agents in `azure.yaml`. Delete an old agent in the Foundry portal. |
| The first answer takes more than 1 minute | This is normal after a deploy. The agent must start first. |
