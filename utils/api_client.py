import os
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

# Global or dynamic client instances
def get_tavily_api_key(custom_key: Optional[str] = None) -> Optional[str]:
    """Retrieve Tavily API key from argument or environment."""
    key = custom_key or os.getenv("TAVILY_API_KEY", "")
    return key.strip() if key and not key.startswith("tvly-your_") else None

def get_groq_api_key(custom_key: Optional[str] = None) -> Optional[str]:
    """Retrieve Groq API key from argument or environment."""
    key = custom_key or os.getenv("GROQ_API_KEY", "")
    return key.strip() if key and not key.startswith("gsk_your_") else None

def get_tavily_client(api_key: Optional[str] = None):
    """Instantiate TavilyClient if key is present."""
    key = get_tavily_api_key(api_key)
    if not key:
        return None
    try:
        from tavily import TavilyClient
        return TavilyClient(api_key=key)
    except Exception as e:
        print(f"[API Client] Tavily initialization warning: {e}")
        return None

def get_groq_client(api_key: Optional[str] = None):
    """Instantiate Groq client if key is present."""
    key = get_groq_api_key(api_key)
    if not key:
        return None
    try:
        from groq import Groq
        return Groq(api_key=key)
    except Exception as e:
        print(f"[API Client] Groq initialization warning: {e}")
        return None

def search_tavily_safe(query: str, api_key: Optional[str] = None, max_results: int = 8) -> List[Dict[str, Any]]:
    """Safe wrapper around Tavily search."""
    client = get_tavily_client(api_key)
    if not client:
        return []
    try:
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_domains=["youtube.com", "geeksforgeeks.org", "tutorialspoint.com", "w3schools.com", 
                            "coursera.org", "khanacademy.org", "freecodecamp.org", "sanfoundry.com", "medium.com", "wikipedia.org", "leetcode.com", "cisco.com"]
        )
        return response.get("results", [])
    except Exception as e:
        print(f"[API Client] Tavily search error: {e}")
        return []

def query_groq_safe(prompt: str, system_message: str = "You are an expert AI Learning Advisor.", api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile") -> Optional[str]:
    """Safe wrapper around Groq chat completions."""
    client = get_groq_client(api_key)
    if not client:
        return None
    try:
        # Fallback to standard 8b model if needed
        models_to_try = [model, "llama-3.1-8b-instant", "llama3-70b-8192", "mixtral-8x7b-32768"]
        for m in models_to_try:
            try:
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ],
                    model=m,
                    temperature=0.4,
                    max_tokens=1000
                )
                return chat_completion.choices[0].message.content.strip()
            except Exception as inner_err:
                print(f"[API Client] Groq model {m} failed: {inner_err}, trying next...")
                continue
        return None
    except Exception as e:
        print(f"[API Client] Groq execution error: {e}")
        return None
