"""Run a Fusion API script through the local Fusion MCP server (http://127.0.0.1:27182/mcp). Usage: fusion_run.py <script.py> [readonly]
A line `# include: twin/geometry.py` (any repo-relative path) is replaced by that file's contents before sending."""
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
def main():
    post({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"noggin","version":"0"}}})
    post({"jsonrpc":"2.0","method":"notifications/initialized"})
    obj={"script": inline_includes(open(sys.argv[1]).read(), Path(__file__).resolve().parents[1])}
    if len(sys.argv) > 2: obj["readOnly"] = True
    r=post({"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"fusion_mcp_execute","arguments":{"featureType":"script","object":obj}}})
    res=r.get("result", r)
    for c in res.get("content", []):
        print(c.get("text", c))
    if res.get("isError"): sys.exit(1)
if __name__=="__main__": main()
