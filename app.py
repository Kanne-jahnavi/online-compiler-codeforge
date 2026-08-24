import streamlit as st
import requests
import base64
import io
import sys
import contextlib

st.set_page_config(page_title="CodeForge - Compiler", layout="wide", page_icon="⚡")

st.markdown("""
<style>
.stApp { background: #f8fafc; }
h1, h2, h3, p, label { color: #1e293b!important; }
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
    border: none!important;
}
section[data-testid="stSidebar"] { background: #eef2ff!important; }
</style>
""", unsafe_allow_html=True)

st.title("⚡ CodeForge - Online Compiler")

WANDBOX_CORRECT = {
    "Python": "cpython-3.13.8",
    "JavaScript": "nodejs-20.17.0",
    "Java": "openjdk-jdk-22+36",
    "C++": "gcc-13.1.0",
    "C": "gcc-13.1.0",
}

BOILERPLATE = {
    "Python": 'print("Hello")',
    "JavaScript": 'console.log("Hello")',
    "Java": 'public class Main {\n public static void main(String[] args){\n System.out.println("Hello");\n }\n}',
    "C++": '#include <iostream>\nusing namespace std;\nint main(){ cout<<"Hello"; return 0; }',
    "C": '#include <stdio.h>\nint main(){ printf("Hello"); return 0; }',
}

EXT_MAP = {"Python":"py", "JavaScript":"js", "Java":"java", "C++":"cpp", "C":"c"}

if "code" in st.query_params:
    try:
        decoded = base64.urlsafe_b64decode(st.query_params["code"]).decode()
        st.session_state['code_text'] = decoded
        st.toast("Loaded from shared link!", icon="🔗")
    except:
        pass

with st.sidebar:
    st.header("Settings")
    lang = st.selectbox("Select Language", list(WANDBOX_CORRECT.keys()))

    st.divider()
    st.subheader("🔗 Share & Save")

    if st.button("🔗 Generate Share Link", use_container_width=True):
        code_to_share = st.session_state.get('code_text','')
        encoded = base64.urlsafe_b64encode(code_to_share.encode()).decode()
        st.success("Link Generated!")
        st.code(f"?code={encoded}", language="text")
        st.caption("Copy and share this part after your site URL")

    code_for_download = st.session_state.get('code_text','')
    file_ext = EXT_MAP.get(lang, "txt")
    st.download_button(
        label=f"💾 Download File (. {file_ext})",
        data=code_for_download,
        file_name=f"main.{file_ext}",
        mime="text/plain",
        use_container_width=True
    )

if 'code_text' not in st.session_state:
    st.session_state.code_text = BOILERPLATE[lang]
if 'last_lang' not in st.session_state:
    st.session_state.last_lang = lang
if st.session_state.last_lang!= lang:
    st.session_state.code_text = BOILERPLATE[lang]
    st.session_state.last_lang = lang
    st.session_state.run_output = ""
    st.rerun()

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"Editor - {lang}")
    code = st.text_area("code", value=st.session_state.code_text, height=350, key="editor", label_visibility="collapsed")
    st.session_state.code_text = code
    b1, b2, b3 = st.columns(3)
    with b1:
        run_clicked = st.button("▶ RUN CODE", type="primary", use_container_width=True)
    with b2:
        if st.button("🧹 Clear", use_container_width=True):
            st.session_state.code_text = ""
            st.session_state.run_output = ""
            st.rerun()
    with b3:
        st.download_button("💾 Download", data=st.session_state.code_text, file_name=f"code.{file_ext}", mime="text/plain", key="main_dl")

with col2:
    st.subheader("Input (stdin)")
    user_input = st.text_area("input", height=120, placeholder="Enter input...", label_visibility="collapsed")
    st.subheader("Output")
    if 'run_output' not in st.session_state:
        st.session_state.run_output = "Click RUN"
        st.session_state.run_error = False
    if st.session_state.run_error:
        st.error(st.session_state.run_output)
    else:
        st.code(st.session_state.run_output)
    if st.session_state.run_output!= "Click RUN":
        st.download_button("⬇️ Download Output", data=st.session_state.run_output, file_name="output.txt", mime="text/plain")

def run_python_server(code_text, stdin_text):
    try:
        input_lines = stdin_text.splitlines()
        input_iter = iter(input_lines)
        def mock_input(prompt=""):
            try:
                return next(input_iter)
            except StopIteration:
                return ""
        old_stdin = sys.stdin
        output = io.StringIO()
        sys.stdin = io.StringIO(stdin_text)
        import builtins
        old_input = builtins.input
        builtins.input = mock_input
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            exec(code_text, {})
        builtins.input = old_input
        sys.stdin = old_stdin
        return output.getvalue(), False
    except Exception as e:
        import traceback
        return traceback.format_exc(), True
    finally:
        try:
            builtins.input = old_input
            sys.stdin = old_stdin
        except:
            pass

def run_wandbox(lang_key, code_text, stdin_text):
    try:
        payload = {"code": code_text, "compiler": WANDBOX_CORRECT[lang_key], "stdin": stdin_text}
        if lang_key in ["C", "C++"]:
            payload["compiler-option-raw"] = "-O2 -std=c++17"
        r = requests.post("https://wandbox.org/api/compile.json", json=payload, timeout=20)
        if "application/json" not in r.headers.get("Content-Type",""):
            return f"Wandbox busy: {r.text[:300]}", True
        data = r.json()
        comp_err = data.get("compiler_error","")
        prog_err = data.get("program_error","")
        prog_out = data.get("program_output","")
        if comp_err.strip():
            return comp_err, True
        if prog_err.strip():
            return prog_err + "\n" + prog_out, True
        return prog_out or "No output", False
    except Exception as e:
        return f"Error: {str(e)}", True

if run_clicked:
    if not st.session_state.code_text.strip():
        st.session_state.run_output = "Editor empty!"
        st.session_state.run_error = True
        st.rerun()
    else:
        with st.spinner(f"Running {lang}..."):
            if lang == "Python":
                out, is_err = run_python_server(st.session_state.code_text, user_input)
            else:
                out, is_err = run_wandbox(lang, st.session_state.code_text, user_input)
            st.session_state.run_output = out
            st.session_state.run_error = is_err
            st.rerun()