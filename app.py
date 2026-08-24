import streamlit as st
import requests, base64, sys, subprocess, tempfile, os, urllib.parse

st.set_page_config(page_title="CodeForge", layout="wide", page_icon="⚡")

st.markdown("""
<style>
.stApp { background: #f8fafc; }
.stTextArea textarea {
    background: #ffffff!important;
    color: #000000!important;
    font-size: 15px!important;
    border: 2px solid #3b82f6!important;
    border-radius: 10px!important;
}
.stButton>button {
    background: #3b82f6!important;
    color: white!important;
    font-weight: bold!important;
    border-radius: 10px!important;
}
section[data-testid="stSidebar"] { background: #eef2ff!important; }
</style>
""", unsafe_allow_html=True)

st.title("⚡ CodeForge - Online Compiler")

LANGS = ["Python", "JavaScript", "Java", "C++", "C"]
EXT = {"Python":"py","JavaScript":"js","Java":"java","C++":"cpp","C":"c"}

BOILER = {
    "Python": 'a=int(input())\nb=int(input())\nprint(a+b)',
    "JavaScript": 'console.log(10+20)',
    "Java": 'public class Main{public static void main(String[] a){System.out.println(10+20);}}',
    "C++": '#include<bits/stdc++.h>\nusing namespace std;\nint main(){int a,b;cin>>a>>b;cout<<a+b;return 0;}',
    "C": '#include<stdio.h>\nint main(){int a,b;scanf("%d%d",&a,&b);printf("%d",a+b);return 0;}',
}

if "selected_lang" not in st.session_state:
    st.session_state.selected_lang = "Python"
if "editor" not in st.session_state:
    st.session_state.editor = BOILER["Python"]
if "out" not in st.session_state:
    st.session_state.out = "Click RUN"
    st.session_state.is_err = False

if "code" in st.query_params and "loaded" not in st.session_state:
    try:
        st.session_state.editor = base64.urlsafe_b64decode(st.query_params["code"]).decode()
        st.session_state.loaded = True
    except: pass

def on_change():
    st.session_state.editor = BOILER[st.session_state.selected_lang]
    st.session_state.out = f"Switched to {st.session_state.selected_lang}"

with st.sidebar:
    st.header("Settings")
    st.selectbox("Language", LANGS, key="selected_lang", on_change=on_change)
    st.divider()
    if st.button("🔗 Share Link", use_container_width=True):
        enc = base64.urlsafe_b64encode(st.session_state.editor.encode()).decode()
        st.code(f"?code={enc}")
    st.download_button(f"💾 Download.{EXT[st.session_state.selected_lang]}", st.session_state.editor, f"main.{EXT[st.session_state.selected_lang]}", use_container_width=True)

c1,c2 = st.columns([2,1])
with c1:
    st.subheader(f"Editor - {st.session_state.selected_lang}")
    st.text_area("", key="editor", height=380, label_visibility="collapsed")
    b1,b2 = st.columns(2)
    with b1:
        run = st.button("▶ RUN CODE", type="primary", use_container_width=True)
    with b2:
        if st.button("🧹 Clear", use_container_width=True):
            st.session_state.editor = ""
            st.rerun()

with c2:
    st.subheader("Input")
    inp = st.text_area("", key="stdin", height=120, placeholder="10\n20", label_visibility="collapsed")
    st.subheader("Output")
    if st.session_state.is_err:
        st.error(st.session_state.out)
    else:
        st.code(st.session_state.out)

# --- RUNNERS ---
def run_local_py(code, stdin_text):
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir="/tmp") as f:
            f.write(code)
            fn=f.name
        r = subprocess.run([sys.executable, fn], input=stdin_text, capture_output=True, text=True, timeout=5)
        os.remove(fn)
        return (r.stdout if r.stdout else r.stderr), r.returncode!=0
    except Exception as e:
        return str(e), True

def run_new_api(lang, code, stdin_text):
    try:
        # NEW FREE API - No key, works in India
        # Format: https://agent-gateway-kappa.vercel.app/v1/agent-coderunner/api/run/python?code=...
        api_lang = lang.lower()
        if api_lang == "c++": api_lang = "cpp"
        if api_lang == "c": api_lang = "c"
        if api_lang == "javascript": api_lang = "javascript"

        # URL encode code
        encoded_code = urllib.parse.quote(code)
        url = f"https://agent-gateway-kappa.vercel.app/v1/agent-coderunner/api/run/{api_lang}?code={encoded_code}"
        if stdin_text:
            url += f"&stdin={urllib.parse.quote(stdin_text)}"

        r = requests.get(url, timeout=20)
        data = r.json()
        # Response format: {stdout, stderr, exitCode}
        stdout = data.get("stdout","")
        stderr = data.get("stderr","")
        if stderr:
            return stderr, True
        return stdout or "No output", False
    except Exception as e:
        return None, None # Signal to try next

def run_judge0(lang, code, stdin_text):
    try:
        ids = {"Python":71,"JavaScript":63,"Java":62,"C++":54,"C":50}
        r = requests.post("https://ce.judge0.com/submissions?base64_encoded=false&wait=true",
                          json={"source_code":code,"language_id":ids[lang],"stdin":stdin_text}, timeout=15)
        d = r.json()
        if d.get("compile_output"): return d["compile_output"], True
        if d.get("stderr"): return d["stderr"], True
        return d.get("stdout","No output"), False
    except:
        return None, None

if run:
    code = st.session_state.editor
    if not code.strip():
        st.session_state.out = "Editor empty"
        st.session_state.is_err = True
    else:
        with st.spinner(f"Running {st.session_state.selected_lang}..."):
            out, err = None, None

            # Try 1: Local Python (always works for Python)
            if st.session_state.selected_lang == "Python":
                out, err = run_local_py(code, inp)
                if not err:
                    st.session_state.out = out
                    st.session_state.is_err = err
                    st.rerun()

            # Try 2: New Free API (works in India)
            if out is None or err:
                n_out, n_err = run_new_api(st.session_state.selected_lang, code, inp)
                if n_out is not None:
                    out, err = n_out, n_err

            # Try 3: Judge0 CE
            if out is None:
                j_out, j_err = run_judge0(st.session_state.selected_lang, code, inp)
                if j_out is not None:
                    out, err = j_out, j_err
                else:
                    out = "All APIs busy. For Python it works locally. For other langs, try again after 10 sec."
                    err = True

            st.session_state.out = out
            st.session_state.is_err = err
            st.rerun()
