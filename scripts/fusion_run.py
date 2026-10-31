"""Run a Fusion API script through the local Fusion MCP server (http://127.0.0.1:27182/mcp). Usage: fusion_run.py <script.py> [readonly]
A line `# include: model/geometry.py` (any repo-relative path) is replaced by that file's contents before sending."""
import json, os, re, sys, urllib.request
from pathlib import Path
URL=os.environ.get("FUSION_MCP_URL", "http://127.0.0.1:27182/mcp"); SESSION={}   # the port moves after a Fusion restart
INCLUDE=re.compile(r"^# include: (\S+)\s*$", re.M)
def inline_includes(text, repo_root):
    return INCLUDE.sub(lambda m: (Path(repo_root)/m.group(1)).read_text(), text)
def post(p):
    h={"Content-Type":"application/json","Accept":"application/json, text/event-stream"}
    if SESSION.get("id"): h["Mcp-Session-Id"]=SESSION["id"]
    r=urllib.request.urlopen(urllib.request.Request(URL,json.dumps(p).encode(),h),timeout=1800)
    if r.headers.get("Mcp-Session-Id"): SESSION["id"]=r.headers["Mcp-Session-Id"]
    raw=r.read().decode()
    if raw.lstrip().startswith(("event:","data:")): raw="".join(l[5:] for l in raw.splitlines() if l.startswith("data:"))
    return json.loads(raw) if raw.strip() else {}
def run_script(text, readonly=False):
    """Run script text (includes inlined) in Fusion; returns the parsed result dict ({"message":..., "success":...}). Raises on error."""
    if not SESSION.get("id"):
        post({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"noggin","version":"0"}}})
        post({"jsonrpc":"2.0","method":"notifications/initialized"})
    obj={"script": inline_includes(text, Path(__file__).resolve().parents[1])}
    if readonly: obj["readOnly"] = True
    r=post({"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"fusion_mcp_execute","arguments":{"featureType":"script","object":obj}}})
    res=r.get("result", r)
    texts=[c.get("text", "") for c in res.get("content", [])]
    if res.get("isError"): raise RuntimeError("\n".join(texts))
    out=json.loads(texts[0]) if texts and texts[0].lstrip().startswith("{") else {"message": "\n".join(texts), "success": True}
    if not out.get("success", True): raise RuntimeError(out.get("error", out))
    return out
def main():
    try: out=run_script(open(sys.argv[1]).read(), readonly=len(sys.argv) > 2)
    except RuntimeError as e: print(e); sys.exit(1)
    print(out.get("message", out), end="")
if __name__=="__main__": main()
