"""Ask the LLM. Every LLM call of the project goes through this file.

Every call goes to ONE OpenAI model (gpt-5.4-mini) in Microsoft Foundry. The sign-in is Microsoft Entra ID:
az login on this computer, the agent's managed identity on Foundry. No API key.

ask_llm: one question, one text answer, cached. The data pipeline uses it.
ask_llm_with_tools: a conversation, maybe with tools. The chat uses it. Not cached.

Every answer of ask_llm is saved in data/cache/<hash>.json. The hash comes from the model, the settings and the
prompt. If the same request comes again, the saved answer is returned and nothing is paid (CLAUDE.md,
section 7). Thus, loading the PDFs again costs nothing.

If a request is not in the cache and FOUNDRY_PROJECT_ENDPOINT is empty, ask_llm stops with a clear message.
"""

import base64
import functools
import hashlib
import json

import openai
from azure.core.exceptions import ClientAuthenticationError
from langchain_azure_ai.chat_models import AzureAIOpenAIApiChatModel
from langchain_core.messages import SystemMessage

from src import config

# "low" effort: the model thinks very little. It is enough for short fake documents and for the chat,
# and thinking tokens are billed as output tokens.
DEFAULT_EFFORT = "low"


@functools.lru_cache(maxsize=None)
def foundry_chat_model(model_name, max_tokens, effort):
    """The model in Microsoft Foundry. Made one time for each setting and reused.

    model_name is the name of the model DEPLOYMENT in the Foundry resource.
    The sign-in is Microsoft Entra ID (DefaultAzureCredential): az login on this computer, the agent's
    managed identity on Foundry. No API key.
    use_responses_api=False: the plain Chat Completions API. A tool loop then sends back only the words
    and the tool calls of the model, not its hidden reasoning."""
    from azure.identity import DefaultAzureCredential

    return AzureAIOpenAIApiChatModel(
        project_endpoint=config.FOUNDRY_PROJECT_ENDPOINT,
        credential=DefaultAzureCredential(),
        model=model_name,
        max_tokens=max_tokens,
        reasoning_effort=effort,
        use_responses_api=False,
    )


def check_foundry_endpoint():
    if not config.FOUNDRY_PROJECT_ENDPOINT:
        raise RuntimeError(
            "FOUNDRY_PROJECT_ENDPOINT is empty. Set it in .env to the endpoint of the Foundry project."
        )


def make_cache_key(model_name, system_prompt, user_prompt, max_tokens, effort):
    request = {
        "model": model_name,
        "system": system_prompt,
        "prompt": user_prompt,
        "max_tokens": max_tokens,
        "effort": effort,
    }
    # sort_keys makes the same request always give the same text, and so the same hash.
    request_text = json.dumps(request, sort_keys=True)
    return hashlib.sha256(request_text.encode("utf-8")).hexdigest()


def read_cached_answer(cache_file):
    """The saved text, or None. A broken file (for example, the run stopped while writing) is a miss."""
    if not cache_file.exists():
        return None
    try:
        with open(cache_file, encoding="utf-8") as file:
            return json.load(file)["text"]
    except (json.JSONDecodeError, KeyError):
        return None


def chat_model_name(chat_model):
    """The model name, also when bind_tools() wrapped the model."""
    return getattr(getattr(chat_model, "bound", chat_model), "model", "?")


def why_the_model_stopped(response):
    """'refusal', 'cut off' or None, from the finish_reason of the answer."""
    reason = response.response_metadata.get("finish_reason")
    if reason == "content_filter":
        return "refusal"
    if reason == "length":
        return "cut off"
    return None


def foundry_identity():
    """The object ID of the identity that signs in to Foundry. It is the identity that needs the role.

    It reads the 'oid' claim of the token. It does not check the token: it only shows a name."""
    try:
        from azure.identity import DefaultAzureCredential

        token = DefaultAzureCredential().get_token("https://ai.azure.com/.default").token
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)  # base64 needs a length that is a multiple of 4
        return json.loads(base64.urlsafe_b64decode(payload)).get("oid", "?")
    except Exception:  # noqa: BLE001 (only for a message: never fail here)
        return "?"


def call_model(chat_model, messages, max_tokens):
    """Call the model one time. Turn API errors into RuntimeError with a clear message."""
    try:
        response = chat_model.invoke(messages)
    except ClientAuthenticationError:
        raise RuntimeError(
            "Cannot sign in to Microsoft Foundry. On this computer, run: az login"
        )
    except (openai.AuthenticationError, openai.PermissionDeniedError) as error:
        # The server's own message tells the cause, for example a missing role. It holds no secret.
        raise RuntimeError(
            "Microsoft Foundry refused the request. The signed-in identity needs the role 'Foundry User' "
            "(old name: 'Azure AI User') on the Foundry project. A new role can take some minutes to work. "
            f"Details: {error.message} Signed-in identity (object ID): {foundry_identity()}"
        )
    except openai.NotFoundError:
        raise RuntimeError(
            f"The model {chat_model_name(chat_model)} was not found. The Foundry resource must have "
            "a model deployment with this name."
        )
    except openai.RateLimitError:
        raise RuntimeError(
            "Rate limit reached. Wait a minute and run again. Saved answers are kept."
        )
    except openai.APIConnectionError:
        raise RuntimeError("Cannot reach the model API. Check the internet connection.")
    except openai.APIStatusError as error:
        raise RuntimeError(f"Model API error {error.status_code}: {error.message}")
    stop_reason = why_the_model_stopped(response)
    if stop_reason == "refusal":
        raise RuntimeError("The model declined this request.")
    if stop_reason == "cut off":
        # Do not save a cut-off answer. It would be reused forever.
        raise RuntimeError(
            f"The answer was cut off at {max_tokens} tokens. Raise max_tokens."
        )
    return response


def ask_llm(
    user_prompt, model_name, system_prompt, max_tokens=1500, effort=DEFAULT_EFFORT
):
    """Return the text answer of the model. Use the cache when possible.

    Raises RuntimeError with a clear message when the call fails."""
    cache_key = make_cache_key(
        model_name, system_prompt, user_prompt, max_tokens, effort
    )
    cache_file = config.CACHE_DIR / f"{cache_key}.json"
    cached_text = read_cached_answer(cache_file)
    if cached_text is not None:
        return cached_text

    check_foundry_endpoint()
    chat_model = foundry_chat_model(model_name, max_tokens, effort)
    response = call_model(
        chat_model, [("system", system_prompt), ("human", user_prompt)], max_tokens
    )
    answer_text = response.text.strip()
    if answer_text == "":
        raise RuntimeError("The model returned an empty answer.")

    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    usage = response.usage_metadata or {}
    with open(cache_file, "w", encoding="utf-8") as file:
        json.dump(
            {
                "model": model_name,
                "prompt": user_prompt,
                "text": answer_text,
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
            },
            file,
            indent=2,
        )
    return answer_text


def ask_llm_with_tools(
    messages,
    tools,
    system_prompt,
    one_tool_at_a_time=False,
    max_tokens=8000,
    effort=DEFAULT_EFFORT,
):
    """Send a conversation (and maybe a tool list) to the STRONG model. Return its answer as an AIMessage.

    The answer has .tool_calls (the tools the model wants, maybe none) and .text (its words).
    tools: a list of {"name", "description", "input_schema"} dicts. An empty list means: no tools, only words.
    one_tool_at_a_time=True: the model may ask for at most one tool per answer (the planner uses it).
    The chat is NOT cached: every message is a new question. Raises RuntimeError with a clear message."""
    check_foundry_endpoint()
    # LangChain turns the tool dicts (input_schema) into the OpenAI function format itself,
    # and gives back the same AIMessage. So the agents do not change.
    chat_model = foundry_chat_model(config.STRONG_MODEL_NAME, max_tokens, effort)
    if tools:
        chat_model = chat_model.bind_tools(
            tools, parallel_tool_calls=not one_tool_at_a_time
        )
    response = call_model(
        chat_model, [SystemMessage(system_prompt)] + list(messages), max_tokens
    )
    if not response.tool_calls and response.text.strip() == "":
        raise RuntimeError("The model returned an empty answer.")
    return response
