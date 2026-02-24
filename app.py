"""
Flask Web application entrypoint exposing API routes and web pages."""

import os
import sys
import json
import time
import re
import sqlite3
import struct
import hashlib
import html
import logging
import threading
import traceback
from functools import wraps
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from collections import deque
from flask import Flask, render_template, request, jsonify, Response, stream_with_context, send_file, session, make_response, g, redirect, has_request_context
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import HTTPException
from urllib.parse import quote, unquote
from config import Config
from agent import IntelligentAgent
from file_processor import FileProcessor
from code_manager import CodeManager
from file_registry_service import FileRegistry
import uuid
import secrets
import queue

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO').upper())
logger = logging.getLogger(__name__)

app = Flask(__name__)
# 发环境下强制模板烛新，避免页面文俔后不生效
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True
# 配置CORS，允许过变量控制来源
cors_origins = [origin.strip() for origin in os.getenv('CORS_ALLOWED_ORIGINS', '').split(',') if origin.strip()]
if not cors_origins:
    cors_origins = ['http://localhost:5000', 'http://127.0.0.1:5000']
CORS(app, resources={
    r"/api/*": {
        "origins": cors_origins,
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})


@app.after_request
def add_no_cache_headers(response):
    """Avoid browser/template stale cache during active development."""
    if response.content_type and 'text/html' in response.content_type:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# 配置
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') or os.urandom(24)
# 管理员配置（建议通过环境变量覆盖）
app.config['ADMIN_USERNAME'] = os.getenv('ADMIN_USERNAME', '')
app.config['ADMIN_PASSWORD'] = os.getenv('ADMIN_PASSWORD', '')
app.config['ADMIN_PASSWORD_HASH'] = os.getenv('ADMIN_PASSWORD_HASH', '')
COOKIE_SECURE = os.getenv('COOKIE_SECURE', 'false').lower() == 'true'
ADMIN_SESSION_TTL_SECONDS = int(os.getenv('ADMIN_SESSION_TTL_SECONDS', '86400'))
REPORT_STREAM_MIN_CHARS = int(os.getenv('REPORT_STREAM_MIN_CHARS', '15000'))
REPORT_SECTION_EXPAND_ENABLED = os.getenv('REPORT_SECTION_EXPAND_ENABLED', 'false').lower() == 'true'
REPORT_PRE_FINAL_BACKFILL_ENABLED = os.getenv('REPORT_PRE_FINAL_BACKFILL_ENABLED', 'true').lower() == 'true'
MAX_SESSION_ID_LEN = 64
DEFAULT_SESSION_ID = 'default'
SESSION_KEY_SEP = ':'
API_V1_PREFIX = '/api/v1'
STATE_FILE = os.getenv('APP_STATE_FILE', os.path.join(BASE_DIR, 'runtime_state.json'))
STATE_LOCK = threading.RLock()
APP_DEV_MODE = os.getenv('APP_DEV_MODE', '').lower() in ('1', 'true', 'yes') or os.getenv('FLASK_DEBUG', '').lower() == 'true'
DEV_ERROR_PIPELINE_ENABLED = os.getenv(
    'DEV_ERROR_PIPELINE_ENABLED',
    'true' if APP_DEV_MODE else 'false'
).lower() == 'true'
DEV_ERROR_MAX_EVENTS = max(50, int(os.getenv('DEV_ERROR_MAX_EVENTS', '300')))
DEV_ERROR_LOG_FILE = os.getenv('DEV_ERROR_LOG_FILE', os.path.join(BASE_DIR, 'logs', 'dev_error_events.jsonl'))
DEV_ERROR_LOCK = threading.RLock()
DEV_ERROR_EVENTS = deque(maxlen=DEV_ERROR_MAX_EVENTS)

if not os.getenv('SECRET_KEY'):
    logger.warning('SECRET_KEY not set; using ephemeral key. Sessions will reset on restart.')

if DEV_ERROR_PIPELINE_ENABLED:
    try:
        os.makedirs(os.path.dirname(DEV_ERROR_LOG_FILE), exist_ok=True)
    except Exception:
        logger.exception("Failed to create dev error log directory")

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 初化智能体和文件理器
config = Config()
agent = IntelligentAgent(config)
file_processor = FileProcessor()

# 初始化验证码管理器
# 尝试多个可能路径（支持 Windows / Linux）
current_dir = BASE_DIR
possible_code_paths = [
    # Linux 服务路径（项目目录下）
    os.path.join(current_dir, 'generated_codes.json'),
    # Windows 开发环境路径
    os.path.join(current_dir, '..', '兑换码及验证码', 'generated_codes.json'),
    os.path.join(current_dir, '兑换码及验证码', 'generated_codes.json'),
    os.path.join('C:', 'Users', 'Abraham', 'Desktop', '兑换码及验证码', 'generated_codes.json'),
]

codes_file = None
for path in possible_code_paths:
    abs_path = os.path.abspath(path)
    if os.path.exists(abs_path):
        codes_file = abs_path
        break
else:
    # 如果都不存在，使用项盛录下的路径（会在保存时创建）
    codes_file = os.path.join(current_dir, 'generated_codes.json')

code_manager = CodeManager(codes_file=codes_file)
logger.info("Verification code file path: %s", code_manager.codes_file)
FILE_REGISTRY_DB_PATH = os.getenv('FILE_REGISTRY_DB_PATH', os.path.join(BASE_DIR, 'db', 'app_meta.db'))
file_registry = FileRegistry(FILE_REGISTRY_DB_PATH)
logger.info("File registry DB path: %s", FILE_REGISTRY_DB_PATH)

# 存储对话历史（key: session_id）
conversation_histories = {}
# 存储会话元数据
session_metadata = {}
# 存储用户使用次数（key: user_id）
user_usage_count = {}
# 存储管理员会话（key: session_token）
admin_sessions = {}


def load_runtime_state():
    """Load persisted in-memory state if available."""
    global conversation_histories, session_metadata, user_usage_count, admin_sessions
    if not os.path.exists(STATE_FILE):
        return
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
        conversation_histories = state.get('conversation_histories', {})
        session_metadata = state.get('session_metadata', {})
        user_usage_count = state.get('user_usage_count', {})
        admin_sessions = state.get('admin_sessions', {})
        logger.info("Loaded runtime state from %s", STATE_FILE)
    except Exception:
        logger.exception("Failed to load runtime state from %s", STATE_FILE)


def save_runtime_state():
    """Persist runtime state atomically."""
    with STATE_LOCK:
        state = {
            'conversation_histories': conversation_histories,
            'session_metadata': session_metadata,
            'user_usage_count': user_usage_count,
            'admin_sessions': admin_sessions,
        }
        tmp_path = f"{STATE_FILE}.tmp"
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False)
        os.replace(tmp_path, STATE_FILE)


load_runtime_state()

@app.route('/api/v1/debug/routes', methods=['GET'])
def debug_routes():
    lines = []
    for rule in app.url_map.iter_rules():
        lines.append(f"{rule.endpoint}: {rule}")
    return "\n".join(lines)

# ==== Theme Configuration API ====
THEME_CONFIG_PATH = os.path.join(BASE_DIR, 'static', 'theme.json')

@app.route('/api/v1/theme', methods=['GET'])
def get_theme_config():
    """Return the current theme configuration."""
    try:
        with open(THEME_CONFIG_PATH, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({"error": "Theme config not found"}), 404

@app.route('/api/v1/theme', methods=['POST'])
def set_theme_config():
    """Update the theme configuration (admin only)."""
    # Basic auth check
    session_token = request.cookies.get('admin_session')
    if not session_token or session_token not in admin_sessions:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        with open(THEME_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return jsonify({"success": True, "message": "Theme updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/theme/active', methods=['POST'])
def set_active_theme():
    """Switch the active theme by name."""
    data = request.get_json()
    theme_name = data.get('theme') if data else None
    if not theme_name:
        return jsonify({"error": "Missing 'theme' field"}), 400
    
    try:
        with open(THEME_CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        if theme_name not in config.get('themes', {}):
            return jsonify({"error": f"Theme '{theme_name}' not found"}), 404
        
        config['active'] = theme_name
        with open(THEME_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return jsonify({"success": True, "active": theme_name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==== End Theme API ====





@app.before_request
def reject_legacy_api_routes():
    path = request.path or ''
    if path.startswith('/api/') and not path.startswith(f'{API_V1_PREFIX}/'):
        return jsonify({
            'error': {
                'code': 'API_VERSION_MIGRATED',
                'message': 'Use /api/v1/* endpoints',
            }
        }), 410


def _safe_extra_json(raw):
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def register_and_annotate_file(path, kind, origin_name='', source_ref='', extra=None):
    rec = file_registry.register_file(
        stored_path=path,
        kind=kind,
        origin_name=origin_name,
        source_ref=source_ref or '',
        extra=extra or {},
    )
    return rec


def build_file_download_url(file_id):
    return f'{API_V1_PREFIX}/files/{quote(file_id, safe="")}/download'


def annotate_report_save_info(save_info, source_ref=''):
    if not isinstance(save_info, dict):
        return save_info
    reports_dir = 'reports'
    md_filename = save_info.get('md_filename') or ''
    pdf_filename = save_info.get('pdf_filename') or ''
    md_file_id = ''
    pdf_file_id = ''

    if md_filename:
        md_path = os.path.join(reports_dir, md_filename)
        if os.path.exists(md_path):
            md_rec = register_and_annotate_file(
                md_path,
                kind='report_md',
                origin_name=md_filename,
                source_ref=source_ref,
                extra={'paired_pdf_filename': pdf_filename or ''},
            )
            md_file_id = md_rec.get('file_id', '')

    if pdf_filename:
        pdf_path = os.path.join(reports_dir, pdf_filename)
        if os.path.exists(pdf_path):
            pdf_rec = register_and_annotate_file(
                pdf_path,
                kind='report_pdf',
                origin_name=pdf_filename,
                source_ref=source_ref,
                extra={'paired_md_filename': md_filename or ''},
            )
            pdf_file_id = pdf_rec.get('file_id', '')

    preferred_file_id = pdf_file_id or md_file_id
    if preferred_file_id:
        save_info['download_url'] = build_file_download_url(preferred_file_id)
    save_info['file_id'] = preferred_file_id
    save_info['pdf_file_id'] = pdf_file_id
    save_info['md_file_id'] = md_file_id
    if pdf_file_id:
        save_info['pdf_url'] = build_file_download_url(pdf_file_id)
    if md_file_id:
        save_info['md_url'] = build_file_download_url(md_file_id)
    return save_info


def get_or_create_session(session_id):
    """Get or create session conversation history."""
    with STATE_LOCK:
        if session_id not in conversation_histories:
            conversation_histories[session_id] = []
            # 初始化会话元数据
            if session_id not in session_metadata:
                session_metadata[session_id] = {
                    'title': 'New Chat',
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
            save_runtime_state()
        return conversation_histories[session_id]


def sanitize_session_id(session_id):
    """Normalize and validate client-provided session id."""
    if not isinstance(session_id, str):
        return DEFAULT_SESSION_ID
    session_id = session_id.strip()
    if not session_id:
        return DEFAULT_SESSION_ID
    if len(session_id) > MAX_SESSION_ID_LEN:
        session_id = session_id[:MAX_SESSION_ID_LEN]
    if not re.fullmatch(r'[A-Za-z0-9_-]+', session_id):
        return DEFAULT_SESSION_ID
    return session_id


def get_scoped_session_id(user_id, session_id):
    return f"{user_id}{SESSION_KEY_SEP}{sanitize_session_id(session_id)}"


def unscoped_session_id(user_id, scoped_session_id):
    prefix = f"{user_id}{SESSION_KEY_SEP}"
    if scoped_session_id.startswith(prefix):
        return scoped_session_id[len(prefix):]
    return None


def set_secure_cookie(response, key, value, max_age=None, expires=None, httponly=True):
    response.set_cookie(
        key,
        value,
        max_age=max_age,
        expires=expires,
        httponly=httponly,
        secure=COOKIE_SECURE,
        samesite='Lax'
    )


def fail_response(status_code=500, public_message='Internal server error', exc=None):
    if exc is not None:
        logger.exception("Unhandled error: %s", exc)
        report_dev_error(
            event_type='backend_exception',
            message=public_message,
            exc=exc,
            status_code=status_code,
        )
    return jsonify({'error': public_message}), status_code


def _clip_text(value, limit=1000):
    text = '' if value is None else str(value)
    if len(text) <= limit:
        return text
    return text[:limit] + f"...(truncated {len(text) - limit} chars)"


def _is_local_request():
    ip = (request.headers.get('X-Forwarded-For') or request.remote_addr or '').split(',')[0].strip()
    if ip in ('127.0.0.1', '::1', 'localhost'):
        return True
    if ip.startswith('10.') or ip.startswith('192.168.'):
        return True
    if ip.startswith('172.'):
        try:
            second = int(ip.split('.')[1])
            if 16 <= second <= 31:
                return True
        except Exception:
            pass
    return False


def _mask_sensitive(data):
    if isinstance(data, dict):
        masked = {}
        for k, v in data.items():
            key = str(k).lower()
            if any(token in key for token in ('password', 'passwd', 'token', 'secret', 'api_key', 'authorization', 'cookie')):
                masked[k] = '***'
            else:
                masked[k] = _mask_sensitive(v)
        return masked
    if isinstance(data, list):
        return [_mask_sensitive(x) for x in data[:20]]
    if isinstance(data, str):
        return _clip_text(data, 1200)
    return data


def report_dev_error(event_type='error', message='', exc=None, extra=None, status_code=500):
    """
    Development-only error reporting pipeline.
    Captures structured backend/frontend errors for quick troubleshooting.
    """
    if not DEV_ERROR_PIPELINE_ENABLED:
        return None

    now = datetime.now().isoformat()
    event_id = f"evt_{int(time.time() * 1000)}_{secrets.token_hex(3)}"
    payload = {
        'id': event_id,
        'ts': now,
        'type': event_type,
        'message': _clip_text(message, 1500),
        'status_code': int(status_code or 0),
    }

    if has_request_context():
        try:
            req_json = request.get_json(silent=True)
        except Exception:
            req_json = None
        payload['request'] = _mask_sensitive({
            'method': request.method,
            'path': request.path,
            'query': dict(request.args),
            'remote_addr': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'session_id': (req_json or {}).get('session_id') if isinstance(req_json, dict) else None,
        })

    if extra is not None:
        payload['extra'] = _mask_sensitive(extra)

    if exc is not None:
        payload['exception'] = {
            'class': exc.__class__.__name__,
            'text': _clip_text(str(exc), 2000),
            'traceback': _clip_text(traceback.format_exc(), 20000),
        }

    with DEV_ERROR_LOCK:
        DEV_ERROR_EVENTS.append(payload)
        try:
            with open(DEV_ERROR_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(payload, ensure_ascii=False) + '\n')
        except Exception:
            logger.exception("Failed to persist dev error event")
    return payload


def normalize_usage_info(usage):
    """Normalize usage payload to stable integer fields for frontend."""
    if not isinstance(usage, dict):
        return {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
    prompt = int(usage.get('prompt_tokens', 0) or 0)
    completion = int(usage.get('completion_tokens', 0) or 0)
    total = int(usage.get('total_tokens', 0) or 0)
    if total <= 0:
        total = max(0, prompt + completion)
    return {
        'prompt_tokens': max(0, prompt),
        'completion_tokens': max(0, completion),
        'total_tokens': max(0, total),
    }


def estimate_tokens_from_text(text):
    """
    Rough local token estimation for mixed Chinese/English text.
    Heuristic:
    - CJK char ~= 1 token
    - Latin word ~= 1 token
    - Number block ~= 1 token
    - Punctuation ~= 0.3 token
    """
    if not text:
        return 0
    cjk_count = len(re.findall(r'[\u4e00-\u9fff]', text))
    latin_words = len(re.findall(r'[A-Za-z]+', text))
    number_blocks = len(re.findall(r'\d+(?:\.\d+)?', text))
    punct_count = len(re.findall(r'[^\w\s\u4e00-\u9fff]', text))
    estimate = cjk_count + latin_words + number_blocks + int(punct_count * 0.3)
    return max(0, int(estimate))


def estimate_usage_info(user_input, assistant_output, conversation_history=None):
    """Fallback local usage estimation when model usage is unavailable."""
    prompt_parts = [user_input or '']
    if isinstance(conversation_history, list) and conversation_history:
        for msg in conversation_history[-12:]:
            if not isinstance(msg, dict):
                continue
            prompt_parts.append(str(msg.get('content', '') or ''))
    prompt_text = "\n".join(prompt_parts)
    completion_text = assistant_output or ''
    prompt_tokens = estimate_tokens_from_text(prompt_text)
    completion_tokens = estimate_tokens_from_text(completion_text)
    return {
        'prompt_tokens': prompt_tokens,
        'completion_tokens': completion_tokens,
        'total_tokens': prompt_tokens + completion_tokens,
        'estimated': True,
    }


def build_runtime_info():
    """Build runtime model metadata for frontend display."""
    provider = ''
    model_name = ''
    try:
        provider = getattr(getattr(config, 'provider', None), 'value', '') or ''
        model_name = getattr(config, 'model_name', '') or ''
    except Exception:
        pass

    context_tokens = None
    for env_key in (
        'MODEL_CONTEXT_TOKENS',
        'MODEL_CONTEXT_SIZE',
        'CONTEXT_WINDOW_TOKENS',
        'MAX_CONTEXT_TOKENS',
    ):
        raw = (os.getenv(env_key, '') or '').strip()
        if not raw:
            continue
        try:
            parsed = int(raw)
            if parsed > 0:
                context_tokens = parsed
                break
        except (TypeError, ValueError):
            continue

    return {
        'provider': provider,
        'model_name': model_name,
        'context_tokens': context_tokens,
    }


def contains_mermaid_output(text):
    """Detect whether assistant output includes Mermaid code."""
    if not text:
        return False
    block_regex = re.compile(r"```(?:mermaid)?\s*\n([\s\S]*?)```", re.IGNORECASE)
    diagram_starts = (
        'graph',
        'flowchart',
        'sequencediagram',
        'classdiagram',
        'statediagram',
        'erdiagram',
        'journey',
        'gantt',
        'pie',
        'gitgraph',
        'mindmap',
        'timeline',
        'xychart-beta',
    )
    for match in block_regex.finditer(text):
        candidate = (match.group(1) or '').strip().lower()
        if candidate.startswith(diagram_starts):
            return True
    return False


def has_chapter10_heading(text):
    """Detect whether chapter 10 heading already exists in body content."""
    if not text:
        return False
    for raw_line in str(text).replace('\r\n', '\n').split('\n'):
        line = raw_line.strip().lstrip('#').strip()
        if line.startswith('第十章') or line.startswith('第10章'):
            return True
        if line.startswith('10.') or line.startswith('10、') or line.startswith('10 '):
            return True
    return False


def update_session_title(session_id, user_input):
    """Update session title from the first user message."""
    with STATE_LOCK:
        if session_id in session_metadata:
            # Keep existing custom title; only replace default placeholder.
            if session_metadata[session_id]['title'] == '新对话':
                # Trim very long titles for sidebar display.
                title = user_input[:30] if len(user_input) <= 30 else user_input[:27] + '...'
                session_metadata[session_id]['title'] = title
            session_metadata[session_id]['updated_at'] = datetime.now().isoformat()
            save_runtime_state()


def get_user_id_from_cookie():
    """Get user ID from cookie, creating a new UUID when missing."""
    user_id = request.cookies.get('user_id')
    if not user_id or not re.fullmatch(r'[a-f0-9-]{36}', user_id):
        user_id = str(uuid.uuid4())
    return user_id


def get_user_usage_count(user_id):
    """获取用户剩余使用次数"""
    with STATE_LOCK:
        return user_usage_count.get(user_id, 0)


def decrease_user_usage_count(user_id):
    """减少用户使用次数"""
    with STATE_LOCK:
        if user_id in user_usage_count and user_usage_count[user_id] > 0:
            user_usage_count[user_id] -= 1
            save_runtime_state()
            return True
        return False


def increase_user_usage_count(user_id, count=1):
    """增加用户使用次数"""
    with STATE_LOCK:
        if user_id not in user_usage_count:
            user_usage_count[user_id] = 0
        user_usage_count[user_id] += count
        save_runtime_state()


def get_valid_admin_session():
    admin_token = request.cookies.get('admin_token')
    if not admin_token:
        return None, None
    with STATE_LOCK:
        session_info = admin_sessions.get(admin_token)
        if not session_info:
            return None, None
        login_time_str = session_info.get('login_time')
        try:
            login_time = datetime.fromisoformat(login_time_str)
        except Exception:
            admin_sessions.pop(admin_token, None)
            save_runtime_state()
            return None, None
        if datetime.now() - login_time > timedelta(seconds=ADMIN_SESSION_TTL_SECONDS):
            admin_sessions.pop(admin_token, None)
            save_runtime_state()
            return None, None
        return admin_token, session_info


def require_admin_login(f):
    """绠＄悊鍛樼櫥褰曡楗板櫒"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin_token, session_info = get_valid_admin_session()
        if not admin_token or not session_info:
            return jsonify({'error': '要理员登录'}), 401
        g.admin_token = admin_token
        g.admin_session = session_info
        return f(*args, **kwargs)
    return decorated_function


def require_admin_csrf(f):
    """Admin write-operation CSRF guard."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin_token, session_info = get_valid_admin_session()
        if not admin_token or not session_info:
            return jsonify({'error': '要理员登录'}), 401
        header_token = request.headers.get('X-CSRF-Token', '')
        cookie_token = request.cookies.get('admin_csrf', '')
        session_token = session_info.get('csrf_token', '')
        if not header_token or not cookie_token or not session_token:
            return jsonify({'error': 'CSRF validation failed'}), 403
        if not (
            secrets.compare_digest(header_token, cookie_token)
            and secrets.compare_digest(header_token, session_token)
        ):
            return jsonify({'error': 'CSRF validation failed'}), 403
        return f(*args, **kwargs)
    return decorated_function


def require_admin_page_login(f):
    """Admin-page login guard."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin_token, session_info = get_valid_admin_session()
        if not admin_token or not session_info:
            return redirect('/admin')
        g.admin_token = admin_token
        g.admin_session = session_info
        return f(*args, **kwargs)
    return decorated_function


# ==== LLM Configuration API ====

from config import save_llm_settings, ModelProvider

_RELOAD_LOCK = threading.Lock()

def _reload_agent():
    """重建全局 config / agent，使新 LLM 配置即时生效（线程安全）。"""
    global config, agent
    with _RELOAD_LOCK:
        try:
            new_config = Config()
            new_agent = IntelligentAgent(new_config)
            config = new_config
            agent = new_agent
            logger.info("LLM 配置热更新成功: %s", repr(config))
            return True, None
        except Exception as e:
            logger.exception("LLM 配置热更新失败")
            return False, str(e)


@app.route('/api/v1/admin/config/llm', methods=['GET'])
@require_admin_login
def get_llm_config():
    """读取当前大模型配置（敏感字段脱敏）。"""
    return jsonify({
        'success': True,
        'config': config.to_dict(),
    })


@app.route('/api/v1/admin/config/llm', methods=['POST'])
@require_admin_login
def set_llm_config():
    """更新大模型配置并热重载 agent。"""
    data = request.get_json(silent=True) or {}

    provider_val = str(data.get('provider', '')).strip().lower()
    if provider_val not in [p.value for p in ModelProvider]:
        return jsonify({'error': f'不支持的 provider：{provider_val}'}), 400

    api_key_raw = str(data.get('api_key', '')).strip()
    base_url = str(data.get('base_url', '')).strip()
    model_name = str(data.get('model_name', '')).strip()

    try:
        temperature = float(data.get('temperature', 0.7))
        max_tokens = int(data.get('max_tokens', 32000))
    except (TypeError, ValueError) as e:
        return jsonify({'error': f'参数格式错误: {e}'}), 400

    if not model_name:
        return jsonify({'error': '模型名称不能为空'}), 400

    # 如果 api_key 是脱敏占位符（全是 *），则保留旧的 key
    if api_key_raw and all(c == '*' for c in api_key_raw):
        from config import _load_llm_settings as _load_raw
        api_key_raw = _load_raw().get('api_key', config.api_key)

    new_settings = {
        'provider': provider_val,
        'api_key': api_key_raw,
        'base_url': base_url,
        'model_name': model_name,
        'temperature': temperature,
        'max_tokens': max_tokens,
    }

    try:
        save_llm_settings(new_settings)
    except Exception as e:
        return jsonify({'error': f'保存配置失败: {e}'}), 500

    # 热重载
    ok, err = _reload_agent()
    if not ok:
        return jsonify({'success': False, 'warning': f'配置已保存，但热重载失败: {err}。请重启服务。'}), 200

    return jsonify({'success': True, 'message': '配置已更新并立即生效', 'config': config.to_dict()})

# ==== End LLM Configuration API ====


@app.route('/')
def index():
    """落地页"""
    return render_template('landing.html')

@app.route('/product-form')
def product_form():
    """产品信息收集页"""
    return render_template('product_form.html')

@app.route('/app')
def application():
    """主应用（现代化版本）"""
    return render_template('index_modern.html')

@app.route('/workspace')
def workspace_page():
    """工作空间页面"""
    return render_template('index.html')

@app.route('/chat')
def chat_page():
    """聊天页面（别名路由）"""
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
@app.route('/api/v1/chat', methods=['POST'])
def chat():
    """Handle non-stream chat request."""
    try:
        # 检查用户可用次数
        user_id = get_user_id_from_cookie()
        usage_count = get_user_usage_count(user_id)
        if usage_count <= 0:
            response = jsonify({'error': '使用次数已用完，请先输入验证码'})
            set_secure_cookie(response, 'user_id', user_id, max_age=365 * 24 * 60 * 60)  # 1 year
            return response, 403
        
        data = request.json
        user_input = data.get('message', '').strip()
        session_id = sanitize_session_id(data.get('session_id', DEFAULT_SESSION_ID))
        scoped_session_id = get_scoped_session_id(user_id, session_id)
        
        if not user_input:
            return jsonify({'error': '消息不能为空'}), 400
        
        # 获取会话历史
        conversation_history = get_or_create_session(scoped_session_id)
        
        request_start_time = time.time()
        # 调用智能体
        reply, usage_info = agent.chat(user_input, conversation_history)
        usage_info = normalize_usage_info(usage_info)
        if usage_info.get('total_tokens', 0) == 0:
            usage_info = estimate_usage_info(user_input, reply, conversation_history)
        model_done_time = time.time()
        rag_sources = getattr(agent, '_last_rag_sources', []) or []
        
        # 检查是否是报告请求
        is_report = agent._is_report_request(user_input)
        report_status = 'none'
        report_quality = None
        if is_report:
            report_len = len((reply or '').strip())
            ch10_complete, _ = agent._is_chapter_10_complete(reply)
            if REPORT_PRE_FINAL_BACKFILL_ENABLED and ch10_complete and report_len < REPORT_STREAM_MIN_CHARS:
                reply = agent._expand_pre_final_sections(reply, user_input)
            if REPORT_SECTION_EXPAND_ENABLED and ch10_complete:
                reply = agent._expand_underdeveloped_sections(reply, user_input)
            reply = agent._postprocess_report_output(reply)
            report_quality = agent.validate_report_completeness(reply, min_body_chars=REPORT_STREAM_MIN_CHARS)
            report_done_marker = "【报告已完成】" in (reply or "")
            if report_done_marker:
                report_status = 'complete'
                if isinstance(report_quality, dict):
                    report_quality['is_complete'] = True
                    report_quality['forced_complete_by_marker'] = True
            else:
                report_status = 'complete' if report_quality.get('is_complete') else 'incomplete'

        report_download = None
        if is_report and report_status == 'complete':
            save_info = agent._save_report(reply, user_input)
            if not save_info:
                report_dev_error(
                    event_type='report_save_failed',
                    message='agent._save_report returned empty in /api/chat',
                    extra={'session_id': session_id, 'path': '/api/chat'}
                )
                save_info = emergency_save_report_markdown(reply, user_input)
            if save_info:
                save_info = annotate_report_save_info(save_info, source_ref=scoped_session_id)
                download_url = save_info.get('download_url', '')
                filename = save_info.get('filename', '')
                pdf_filename = save_info.get('pdf_filename')
                md_filename = save_info.get('md_filename')
                file_format = save_info.get('format', 'pdf')
                format_text = 'PDF' if file_format == 'pdf' else 'Markdown'
                pdf_url = save_info.get('pdf_url', '')
                md_url = save_info.get('md_url', '')
                report_download = {
                    'url': download_url,
                    'filename': filename,
                    'format': file_format,
                    'file_id': save_info.get('file_id', ''),
                    'pdf_file_id': save_info.get('pdf_file_id', ''),
                    'md_file_id': save_info.get('md_file_id', ''),
                    'pdf_filename': pdf_filename,
                    'md_filename': md_filename,
                    'pdf_url': pdf_url,
                    'md_url': md_url,
                }
                reply += f"\n\n---\n✅ **报告已生成并保存**\n📁 文件名: `{filename}` ({format_text}格式)\n🔗 [点击下载报告]({download_url})"
        elif is_report and report_status == 'incomplete':
            missing = report_quality.get('missing_sections', []) if isinstance(report_quality, dict) else []
            missing_text = '、'.join(missing) if missing else '结构未达完整标准'
            reply += f"\n\n---\n⚠️ **报告尚未完成，已阻止下载**\n缺失或未完成章节：{missing_text}"

        conversation_history.append({"role": "user", "content": user_input})
        conversation_history.append({"role": "assistant", "content": reply})
        
        # 更新会话标题
        update_session_title(scoped_session_id, user_input)
        
        # 限制历史记录长度
        if len(conversation_history) > 20:
            conversation_history[:] = conversation_history[-20:]
        save_runtime_state()
        
        # 减少使用次数
        decrease_user_usage_count(user_id)
        remaining = get_user_usage_count(user_id)
        logger.info("[聊天API] 用户 %s 使用后剩余次数: %s", user_id, remaining)
        
        response_data = {
            'reply': reply,
            'session_id': session_id,
            'usage': usage_info,
            'remaining_uses': remaining,
            'rag_sources': rag_sources,
            'runtime': build_runtime_info(),
            'entities': getattr(agent, '_last_entities', []) or [],
            'flow_source': 'assistant_mermaid' if contains_mermaid_output(reply) else 'none',
            'model_latency_ms': int((model_done_time - request_start_time) * 1000),
            'total_latency_ms': int((time.time() - request_start_time) * 1000),
            'report_status': report_status,
            'report_quality': report_quality,
        }
        
        # 如果有报告下载信恼添加到响应中
        if report_download:
            response_data['report_download'] = report_download
        
        response = jsonify(response_data)
        set_secure_cookie(response, 'user_id', user_id, max_age=365 * 24 * 60 * 60)  # 1 year
        return response
    
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/chat/stream', methods=['POST'])
@app.route('/api/v1/chat/stream', methods=['POST'])
def chat_stream():
    """Handle streaming chat request."""
    try:
        user_id = get_user_id_from_cookie()
        usage_count = get_user_usage_count(user_id)
        if usage_count <= 0:
            response = jsonify({'error': '使用次数已用完，请先输入验证码'})
            set_secure_cookie(response, 'user_id', user_id, max_age=365 * 24 * 60 * 60)
            return response, 403

        data = request.json or {}
        user_input = (data.get('message') or '').strip()
        session_id = sanitize_session_id(data.get('session_id', DEFAULT_SESSION_ID))
        scoped_session_id = get_scoped_session_id(user_id, session_id)

        if not user_input:
            return jsonify({'error': '消息不能为空'}), 400

        conversation_history = get_or_create_session(scoped_session_id)

        def generate():
            full_reply = ""
            report_status = 'none'
            report_quality = None
            model_done_time = None
            try:
                stream_start_time = time.time()

                # Run chat_stream in a background thread so we can send SSE keepalive
                # comments while waiting for long API calls (prevents proxy read-timeout).
                _chunk_q = queue.Queue()

                def _stream_producer():
                    try:
                        for _c in agent.chat_stream(user_input, conversation_history):
                            _chunk_q.put(_c)
                    except Exception as _e:
                        _chunk_q.put(_e)
                    finally:
                        _chunk_q.put(None)  # sentinel

                _producer_thread = threading.Thread(target=_stream_producer, daemon=True)
                _producer_thread.start()

                while True:
                    try:
                        item = _chunk_q.get(timeout=30)
                    except queue.Empty:
                        # No data for 30 s – send SSE comment to keep connection alive
                        yield ": keepalive\n\n"
                        continue
                    if item is None:
                        break
                    if isinstance(item, Exception):
                        raise item
                    full_reply += item
                    yield f"data: {json.dumps({'content': item, 'done': False}, ensure_ascii=False)}\n\n"
                    sys.stdout.flush()

                model_done_time = time.time()

                is_report = agent._is_report_request(user_input)
                finish_reason_from_stream = getattr(agent, '_last_finish_reason', None)
                should_continue = False
                if is_report:
                    text_len = len(full_reply.strip())
                    ch10_complete_before_finalize, _ = agent._is_chapter_10_complete(full_reply)
                    ch10_started_before_finalize = has_chapter10_heading(full_reply)
                    if text_len < REPORT_STREAM_MIN_CHARS:
                        # Prevent the common loop: after chapter 10 appears, do not trigger generic continuation.
                        should_continue = (not ch10_complete_before_finalize) and (not ch10_started_before_finalize)
                    else:
                        should_continue = agent._is_content_truncated(
                            full_reply,
                            finish_reason_from_stream,
                            is_report=True,
                        )
                        if (ch10_complete_before_finalize or ch10_started_before_finalize) and should_continue:
                            should_continue = False

                if should_continue:
                    continuation_text = ""
                    for chunk in agent._continue_writing_stream(full_reply, user_input, conversation_history):
                        continuation_text += chunk
                        yield f"data: {json.dumps({'content': chunk, 'done': False}, ensure_ascii=False)}\n\n"
                    if continuation_text.strip():
                        full_reply += "\n\n" + continuation_text.strip()

                if is_report:
                    yield f"data: {json.dumps({'content': '\\n\\n[信息] 正在进行报告收尾处理...', 'done': False}, ensure_ascii=False)}\n\n"
                    current_len = len((full_reply or '').strip())
                    ch10_complete, _ = agent._is_chapter_10_complete(full_reply)
                    if REPORT_PRE_FINAL_BACKFILL_ENABLED and ch10_complete and current_len < REPORT_STREAM_MIN_CHARS:
                        yield f"data: {json.dumps({'content': '\\n\\n[信息] 第十章已完成，正在回填前置章节内容...', 'done': False}, ensure_ascii=False)}\n\n"
                        full_reply = agent._expand_pre_final_sections(full_reply, user_input)
                    if REPORT_SECTION_EXPAND_ENABLED and ch10_complete:
                        improved_reply = agent._expand_underdeveloped_sections(full_reply, user_input)
                        if improved_reply != full_reply:
                            yield f"data: {json.dumps({'content': '\\n\\n[信息] 已对过短章节进行补写并回填到原章节。', 'done': False}, ensure_ascii=False)}\n\n"
                            full_reply = improved_reply

                    full_reply = agent._postprocess_report_output(full_reply)
                    report_quality = agent.validate_report_completeness(
                        full_reply,
                        min_body_chars=REPORT_STREAM_MIN_CHARS,
                    )
                    report_done_marker = "【报告已完成】" in (full_reply or "")
                    if report_done_marker:
                        report_status = 'complete'
                        if isinstance(report_quality, dict):
                            report_quality['is_complete'] = True
                            report_quality['forced_complete_by_marker'] = True
                    else:
                        report_status = 'complete' if report_quality.get('is_complete') else 'incomplete'

                    if report_status == 'complete':
                        yield f"data: {json.dumps({'content': '\\n\\n[信息] 正在保存报告并转换格式，请稍候...', 'done': False}, ensure_ascii=False)}\n\n"
                        save_info = agent._save_report(full_reply, user_input)
                        if not save_info:
                            report_dev_error(
                                event_type='report_save_failed',
                                message='agent._save_report returned empty in /api/chat/stream',
                                extra={'session_id': session_id, 'path': '/api/chat/stream'}
                            )
                            save_info = emergency_save_report_markdown(full_reply, user_input)
                        if save_info:
                            save_info = annotate_report_save_info(save_info, source_ref=scoped_session_id)
                            download_url = save_info.get('download_url', '')
                            filename = save_info.get('filename', '')
                            pdf_filename = save_info.get('pdf_filename')
                            md_filename = save_info.get('md_filename')
                            file_format = save_info.get('format', 'pdf')
                            format_text = 'PDF' if file_format == 'pdf' else 'Markdown'
                            pdf_url = save_info.get('pdf_url', '')
                            md_url = save_info.get('md_url', '')
                            save_msg = (
                                f"\n\n---\n✅ **报告已生成并保存**\n📁 文件名: `{filename}` ({format_text}格式)\n"
                                f"🔗 [点击下载报告]({download_url})"
                            )
                            full_reply += save_msg
                            yield f"data: {json.dumps({'content': save_msg, 'done': False, 'report_download': {'url': download_url, 'filename': filename, 'format': file_format, 'file_id': save_info.get('file_id', ''), 'pdf_file_id': save_info.get('pdf_file_id', ''), 'md_file_id': save_info.get('md_file_id', ''), 'pdf_filename': pdf_filename, 'md_filename': md_filename, 'pdf_url': pdf_url, 'md_url': md_url}}, ensure_ascii=False)}\n\n"
                    else:
                        missing = report_quality.get('missing_sections', []) if isinstance(report_quality, dict) else []
                        missing_text = "、".join(missing) if missing else "结构未达完整标准"
                        incomplete_msg = f"\\n\\n[警告] 报告尚未完成，已阻止下载。缺失或未完成章节：{missing_text}"
                        full_reply += incomplete_msg.replace("\\n\\n", "\n\n")
                        yield f"data: {json.dumps({'content': incomplete_msg, 'done': False}, ensure_ascii=False)}\n\n"

                conversation_history.append({"role": "user", "content": user_input})
                conversation_history.append({"role": "assistant", "content": full_reply})
                update_session_title(scoped_session_id, user_input)
                if len(conversation_history) > 20:
                    conversation_history[:] = conversation_history[-20:]
                save_runtime_state()

                usage_info = normalize_usage_info(agent.get_last_usage())
                usage_unavailable = usage_info.get('total_tokens', 0) == 0
                if usage_unavailable:
                    usage_info = estimate_usage_info(user_input, full_reply, conversation_history)
                    usage_unavailable = False

                decrease_user_usage_count(user_id)

                rag_sources = getattr(agent, '_last_rag_sources', []) or []
                runtime = build_runtime_info()
                entities = getattr(agent, '_last_entities', []) or []
                flow_source = 'assistant_mermaid' if contains_mermaid_output(full_reply) else 'none'
                done_payload = {
                    'content': '',
                    'done': True,
                    'usage': usage_info,
                    'usage_unavailable': usage_unavailable,
                    'remaining_uses': get_user_usage_count(user_id),
                    'rag_sources': rag_sources,
                    'runtime': runtime,
                    'entities': entities,
                    'flow_source': flow_source,
                    'model_latency_ms': int(((model_done_time or time.time()) - stream_start_time) * 1000),
                    'total_latency_ms': int((time.time() - stream_start_time) * 1000),
                    'report_status': report_status,
                    'report_quality': report_quality,
                }
                yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"

            except Exception as e:
                report_dev_error(
                    event_type='stream_exception',
                    message='chat stream failed',
                    exc=e,
                    extra={'session_id': session_id, 'scoped_session_id': scoped_session_id},
                )
                error_msg = f"错误: {str(e)}"
                yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True}, ensure_ascii=False)}\n\n"

        response = Response(stream_with_context(generate()), mimetype='text/event-stream')
        set_secure_cookie(response, 'user_id', user_id, max_age=365 * 24 * 60 * 60)
        return response

    except Exception as e:
        return fail_response(exc=e)
@app.route('/api/upload', methods=['POST'])
@app.route('/api/v1/files/upload', methods=['POST'])
def upload_file():
    """Handle file upload and query."""
    try:
        # 检查用户可用次数
        user_id = get_user_id_from_cookie()
        usage_count = get_user_usage_count(user_id)
        if usage_count <= 0:
            response = jsonify({'error': '使用次数已用完，请先输入验证码'})
            set_secure_cookie(response, 'user_id', user_id, max_age=365 * 24 * 60 * 60)
            return response, 403
        
        if 'file' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400
        
        file = request.files['file']
        user_query = request.form.get('query', '')
        session_id = sanitize_session_id(request.form.get('session_id', DEFAULT_SESSION_ID))
        scoped_session_id = get_scoped_session_id(user_id, session_id)
        
        if file.filename == '':
            return jsonify({'error': '文件名不能为空'}), 400
        
        # 检查文件类型
        if not file_processor.is_supported_file(file.filename):
            ext = os.path.splitext(file.filename)[1]
            return jsonify({'error': f'不支持的文件类型: {ext}'}), 400
        
        # 保存文件
        filename = secure_filename(file.filename)
        # 添加唯一标识，避免重名冲突
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        file_record = register_and_annotate_file(
            filepath,
            kind='upload',
            origin_name=filename,
            source_ref=scoped_session_id,
            extra={'user_id': user_id},
        )
        
        # 获取会话历史
        conversation_history = get_or_create_session(scoped_session_id)
        
        # 处理文件并获取格式化的文件提示词（包含文件内容）
        try:
            # 处理文件
            content, file_type = file_processor.process_file(filepath)
            
            # 格式化文件内容为提示词
            file_prompt = file_processor.format_file_content_for_prompt(
                filepath, content, file_type, user_query if user_query else None
            )
            
            # 构建完整用户输入（包含文件内容）
            if user_query:
                full_user_input = f"{file_prompt}\n\n请根据上述文件内容回答：{user_query}"
            else:
                full_user_input = f"{file_prompt}\n\n请分析这个文件的主要内容。"
            
            # 调用 chat（而不是 chat_with_file），确保文件内容被正确传递
            reply = agent.chat(full_user_input, conversation_history)
            
            # 更新对话历史（保留完整文件上下文，便于续写）
            conversation_history.append({"role": "user", "content": full_user_input})
            conversation_history.append({"role": "assistant", "content": reply})
        except Exception as e:
            # 如果处理失败，回到原来的方法
            reply = agent.chat_with_file(filepath, user_query if user_query else None, conversation_history)
            
        # 更新对话历史
            file_msg = f"[上传文件: {filename}]"
            if user_query:
                file_msg += f" {user_query}"
            conversation_history.append({"role": "user", "content": file_msg})
            conversation_history.append({"role": "assistant", "content": reply})
        
        # 更新会话标题
        title_text = user_query if user_query else f"分析文件: {filename}"
        update_session_title(scoped_session_id, title_text)
        
        # 限制历史记录长度
        if len(conversation_history) > 20:
            conversation_history[:] = conversation_history[-20:]
        save_runtime_state()
        
        # 减少使用次数
        decrease_user_usage_count(user_id)
        
        response = jsonify({
            'reply': reply,
            'filename': filename,
            'file_id': file_record.get('file_id', ''),
            'stored_name': unique_filename,
            'session_id': session_id,
            'remaining_uses': get_user_usage_count(user_id),
            'rag_sources': getattr(agent, '_last_rag_sources', []) or [],
            'runtime': build_runtime_info(),
            'entities': getattr(agent, '_last_entities', []) or [],
            'flow_source': 'assistant_mermaid' if contains_mermaid_output(reply) else 'none',
        })
        set_secure_cookie(response, 'user_id', user_id, max_age=365 * 24 * 60 * 60)
        return response
    
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/history/clear', methods=['POST'])
@app.route('/api/v1/sessions/clear', methods=['POST'])
def clear_history():
    """Clear conversation history for a session."""
    try:
        user_id = get_user_id_from_cookie()
        data = request.json
        session_id = sanitize_session_id(data.get('session_id', DEFAULT_SESSION_ID))
        scoped_session_id = get_scoped_session_id(user_id, session_id)
        
        if scoped_session_id in conversation_histories:
            conversation_histories[scoped_session_id] = []
            # 重置会话标题
            if scoped_session_id in session_metadata:
                session_metadata[scoped_session_id]['title'] = '新对话'
                session_metadata[scoped_session_id]['updated_at'] = datetime.now().isoformat()
            save_runtime_state()
        
        response = jsonify({'success': True, 'message': '对话历史已清空'})
        set_secure_cookie(response, 'user_id', user_id, max_age=365 * 24 * 60 * 60)
        return response
    
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/history', methods=['GET'])
@app.route('/api/v1/sessions/history', methods=['GET'])
def get_history():
    """获取对话历史"""
    try:
        user_id = get_user_id_from_cookie()
        session_id = sanitize_session_id(request.args.get('session_id', DEFAULT_SESSION_ID))
        scoped_session_id = get_scoped_session_id(user_id, session_id)
        conversation_history = get_or_create_session(scoped_session_id)
        
        # 获取会话元数据
        metadata = session_metadata.get(scoped_session_id, {
            'title': '新对话',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        })
        
        response = jsonify({
            'history': conversation_history,
            'session_id': session_id,
            'metadata': metadata
        })
        set_secure_cookie(response, 'user_id', user_id, max_age=365*24*60*60)
        return response
    
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/sessions', methods=['GET'])
@app.route('/api/v1/sessions', methods=['GET'])
def get_sessions():
    """Get all sessions for current user."""
    try:
        user_id = get_user_id_from_cookie()
        sessions = []
        for scoped_session_id, history in conversation_histories.items():
            session_id = unscoped_session_id(user_id, scoped_session_id)
            if session_id is None:
                continue
            if len(history) > 0:  # 仅返回有历史记录的会话
                metadata = session_metadata.get(scoped_session_id, {
                    'title': '新对话',
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                })
                sessions.append({
                    'session_id': session_id,
                    'title': metadata['title'],
                    'created_at': metadata['created_at'],
                    'updated_at': metadata['updated_at'],
                    'message_count': len(history)
                })
        
        # 按更新时间序排列
        sessions.sort(key=lambda x: x['updated_at'], reverse=True)
        
        response = jsonify({
            'sessions': sessions
        })
        set_secure_cookie(response, 'user_id', user_id, max_age=365*24*60*60)
        return response
    
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/workspace/explorer', methods=['GET'])
@app.route('/api/v1/workspace/explorer', methods=['GET'])
def workspace_explorer():
    """Return real explorer data for frontend workspace panel."""
    try:
        limit = int(request.args.get('limit', 30))
        limit = max(1, min(limit, 200))

        # Uploaded files from uploads directory
        uploads = []
        uploads_dir = app.config.get('UPLOAD_FOLDER', 'uploads')
        if os.path.isdir(uploads_dir):
            for name in os.listdir(uploads_dir):
                path = os.path.join(uploads_dir, name)
                if not os.path.isfile(path):
                    continue
                try:
                    stat = os.stat(path)
                    uploads.append({
                        'name': name,
                        'size': int(stat.st_size),
                        'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })
                except Exception:
                    continue
            uploads.sort(key=lambda x: x.get('modified_at', ''), reverse=True)
            uploads = uploads[:limit]

        # RAG document list from sqlite rag db
        rag_documents = []
        if rag_db_exists():
            conn = rag_db_connect(query_only=True)
            try:
                cur = conn.cursor()
                rows = cur.execute(
                    """
                    SELECT id, title, filename, source_path
                    FROM documents
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,)
                ).fetchall()
                for r in rows:
                    rag_documents.append({
                        'id': int(r['id']) if r['id'] is not None else None,
                        'title': r['title'] or '',
                        'filename': r['filename'] or '',
                        'source_path': r['source_path'] or '',
                    })
            except Exception:
                logger.exception("Failed to query rag documents for explorer panel")
            finally:
                conn.close()

        return jsonify({
            'success': True,
            'uploads': uploads,
            'rag_documents': rag_documents,
        })
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/config', methods=['GET'])
@app.route('/api/v1/config', methods=['GET'])
def get_config():
    """获取配置信息"""
    try:
        return jsonify({
            'provider': config.provider.value,
            'model_name': config.model_name,
            'temperature': config.temperature,
            'max_tokens': config.max_tokens,
            'dev_error_pipeline_enabled': DEV_ERROR_PIPELINE_ENABLED,
        })
    
    except Exception as e:
        return fail_response(exc=e)


def _can_access_dev_error_feed():
    if not DEV_ERROR_PIPELINE_ENABLED:
        return False
    if _is_local_request():
        return True
    admin_token, session_info = get_valid_admin_session()
    return bool(admin_token and session_info)


@app.route('/api/dev/errors/report', methods=['POST'])
@app.route('/api/v1/dev/errors/report', methods=['POST'])
def report_client_error():
    """Frontend -> backend dev error sink."""
    if not DEV_ERROR_PIPELINE_ENABLED:
        return jsonify({'success': False, 'disabled': True}), 200
    try:
        data = request.get_json(silent=True) or {}
        report_dev_error(
            event_type='frontend_error',
            message=data.get('message', 'frontend error'),
            extra={
                'kind': data.get('kind', 'unknown'),
                'stack': data.get('stack', ''),
                'source': data.get('source', ''),
                'lineno': data.get('lineno'),
                'colno': data.get('colno'),
                'url': data.get('url', ''),
                'session_id': data.get('session_id', ''),
                'component': data.get('component', ''),
            },
            status_code=0,
        )
        return jsonify({'success': True}), 200
    except Exception as e:
        return fail_response(exc=e)


def emergency_save_report_markdown(report_content: str, user_input: str = "") -> dict:
    """
    Emergency save path when agent._save_report fails.
    Guarantees at least a markdown download is available.
    """
    reports_dir = 'reports'
    os.makedirs(reports_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base_name = f"报告-紧急保存-{timestamp}"
    md_filename = f"{base_name}.md"
    md_path = os.path.join(reports_dir, md_filename)
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(report_content or '')
    encoded = quote(md_filename, safe='')
    return {
        'filename': md_filename,
        'filepath': md_path,
        'download_url': f'/api/v1/download/report/{encoded}',
        'format': 'md',
        'pdf_filename': '',
        'md_filename': md_filename,
        'pdf_url': '',
        'md_url': f'/api/v1/download/report/{encoded}',
    }


@app.route('/api/dev/errors', methods=['GET'])
@app.route('/api/v1/dev/errors', methods=['GET'])
def get_dev_errors():
    """Read recent dev error events for troubleshooting."""
    if not _can_access_dev_error_feed():
        return jsonify({'error': 'forbidden or disabled'}), 403
    try:
        limit = int(request.args.get('limit', 50) or 50)
        limit = max(1, min(200, limit))
        with DEV_ERROR_LOCK:
            items = list(DEV_ERROR_EVENTS)[-limit:]
        return jsonify({
            'success': True,
            'enabled': DEV_ERROR_PIPELINE_ENABLED,
            'count': len(items),
            'events': items,
            'log_file': DEV_ERROR_LOG_FILE,
        })
    except Exception as e:
        return fail_response(exc=e)


# ==================== 验证码相关 API ====================

@app.route('/api/verify-code', methods=['POST'])
@app.route('/api/v1/verify-code', methods=['POST'])
def verify_code():
    """验证验证码并增加用户使用次数"""
    try:
        data = request.json
        code = data.get('code', '').strip()
        
        if not code:
            return jsonify({'error': '验证码不能为空'}), 400
        
        # 验证验证码
        is_valid, message = code_manager.verify_code(code, remove_after_verify=True)
        
        if is_valid:
            # 验证成功，增加使用次数
            user_id = get_user_id_from_cookie()
            increase_user_usage_count(user_id, count=1)
            remaining = get_user_usage_count(user_id)
            logger.info("[验证码API] 用户 %s 兑换后剩余次数: %s", user_id, remaining)
            
            response = jsonify({
                'success': True,
                'message': message,
                'remaining_uses': remaining
            })
            set_secure_cookie(response, 'user_id', user_id, max_age=365 * 24 * 60 * 60)  # 1 year
            # Disable cache
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        else:
            return jsonify({'error': message}), 400
    
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/user/usage', methods=['GET'])
@app.route('/api/v1/user/usage', methods=['GET'])
def get_user_usage():
    """获取用户剩余使用次数"""
    try:
        user_id = get_user_id_from_cookie()
        usage_count = get_user_usage_count(user_id)
        
        # 娣诲姞璋冭瘯鏃ュ織
        logger.info("[使用次数API] 用户ID: %s, 剩余次数: %s", user_id, usage_count)
        
        response = jsonify({
            'remaining_uses': usage_count
        })
        set_secure_cookie(response, 'user_id', user_id, max_age=365 * 24 * 60 * 60)  # 1 year
        # Disable cache
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        return fail_response(exc=e)


# ==================== 绠＄悊鍛樼浉鍏矨PI ====================

@app.route('/admin')
def admin_login_page():
    """Admin login page."""
    admin_token, session_info = get_valid_admin_session()
    if admin_token and session_info:
        return redirect('/admin/dashboard')
    return render_template('admin_login_modern.html')


@app.route('/admin/dashboard')
@require_admin_page_login
def admin_dashboard():
    """Admin dashboard page."""
    return render_template('admin_dashboard_modern.html')


@app.route('/api/admin/login', methods=['POST'])
@app.route('/api/v1/admin/login', methods=['POST'])
def admin_login():
    """Admin login API."""
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        configured_username = app.config['ADMIN_USERNAME']
        configured_password = app.config['ADMIN_PASSWORD']
        configured_password_hash = app.config['ADMIN_PASSWORD_HASH']
        if not configured_username or (not configured_password_hash and not configured_password):
            return fail_response(
                status_code=500,
                public_message='Admin credentials are not configured'
            )

        # 验证用户名和密码
        password_ok = (
            check_password_hash(configured_password_hash, password)
            if configured_password_hash
            else password == configured_password
        )
        if username == configured_username and password_ok:
            # 生成管理员 token
            admin_token = secrets.token_urlsafe(32)
            csrf_token = secrets.token_urlsafe(32)
            with STATE_LOCK:
                admin_sessions[admin_token] = {
                    'username': username,
                    'login_time': datetime.now().isoformat(),
                    'csrf_token': csrf_token,
                }
                save_runtime_state()
            
            response = jsonify({'success': True, 'message': '登录成功', 'csrf_token': csrf_token})
            set_secure_cookie(response, 'admin_token', admin_token, max_age=24*60*60)  # 24灏忔椂
            set_secure_cookie(response, 'admin_csrf', csrf_token, max_age=24*60*60, httponly=False)
            return response
        else:
            return jsonify({'error': '用户名或密码错误'}), 401
    
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/admin/logout', methods=['POST'])
@app.route('/api/v1/admin/logout', methods=['POST'])
@require_admin_login
@require_admin_csrf
def admin_logout():
    """Admin logout API."""
    try:
        admin_token = request.cookies.get('admin_token')
        with STATE_LOCK:
            if admin_token and admin_token in admin_sessions:
                del admin_sessions[admin_token]
                save_runtime_state()
        
        response = jsonify({'success': True, 'message': '已登出'})
        set_secure_cookie(response, 'admin_token', '', expires=0)
        set_secure_cookie(response, 'admin_csrf', '', expires=0, httponly=False)
        return response
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/admin/check', methods=['GET'])
@app.route('/api/v1/admin/check', methods=['GET'])
def admin_check():
    """Check admin login status."""
    try:
        admin_token, _ = get_valid_admin_session()
        if admin_token:
            return jsonify({'logged_in': True})
        else:
            return jsonify({'logged_in': False}), 401
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/admin/codes', methods=['GET'])
@app.route('/api/v1/admin/codes', methods=['GET'])
@require_admin_login
def admin_get_codes():
    """获取有验证码列表"""
    try:
        codes = code_manager.get_all_codes()
        statistics = code_manager.get_statistics()

        # 轍为列表格式，方便前显示
        codes_list = [{'code': code, 'uses': uses} for code, uses in codes.items()]

        # 按验证码排序
        codes_list.sort(key=lambda x: x['code'])

        return jsonify({
            'codes': codes_list,
            'statistics': statistics
        })
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/admin/stats', methods=['GET'])
@app.route('/api/v1/admin/stats', methods=['GET'])
@require_admin_login
def admin_stats():
    """获取验证码统计信息"""
    try:
        stats = code_manager.get_statistics()

        # 计算已使用和未使用的数量
        codes = code_manager.get_all_codes()
        used_count = sum(1 for uses in codes.values() if uses <= 0)
        unused_count = sum(1 for uses in codes.values() if uses > 0)

        # 计算今日生成的数量（简化版，从总数量中估算）
        total = stats.get('total_codes', 0)

        return jsonify({
            'total': total,
            'used': used_count,
            'unused': unused_count,
            'today': total  # 简化版，实际可以记录生成时间
        })
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/admin/codes/generate', methods=['POST'])
@app.route('/api/v1/admin/codes/generate', methods=['POST'])
@require_admin_login
@require_admin_csrf
def admin_generate_codes():
    """Generate verification codes."""
    try:
        data = request.json
        count = int(data.get('count', 1))
        uses = int(data.get('uses', 1))
        
        if count < 1 or count > 100:
            return jsonify({'error': 'count must be between 1 and 100'}), 400
        
        if uses < 1:
            return jsonify({'error': '使用次数必须大于0'}), 400
        
        codes = code_manager.generate_multiple_codes(count, uses)
        
        return jsonify({
            'success': True,
            'codes': codes,
            'count': len(codes),
            'uses': uses
        })
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/admin/codes/update', methods=['POST'])
@app.route('/api/v1/admin/codes/update', methods=['POST'])
@require_admin_login
@require_admin_csrf
def admin_update_code():
    """Update verification code usage count."""
    try:
        data = request.json
        code = data.get('code', '').strip()
        uses = int(data.get('uses', 0))
        
        if not code:
            return jsonify({'error': '验证码不能为空'}), 400
        
        if uses < 0:
            return jsonify({'error': '使用次数不能为负数'}), 400
        
        success = code_manager.update_code_uses(code, uses)
        
        if success:
            return jsonify({'success': True, 'message': '更新成功'})
        else:
            return jsonify({'error': '更新失败，验证码可能不存在'}), 400
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/admin/codes/delete', methods=['POST'])
@app.route('/api/v1/admin/codes/delete', methods=['POST'])
@require_admin_login
@require_admin_csrf
def admin_delete_code():
    """Delete a verification code."""
    try:
        data = request.json
        code = data.get('code', '').strip()
        
        if not code:
            return jsonify({'error': '验证码不能为空'}), 400
        
        success = code_manager.delete_code(code)
        
        if success:
            return jsonify({'success': True, 'message': '删除成功'})
        else:
            return jsonify({'error': '删除失败，验证码可能不存在'}), 400
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/admin/statistics', methods=['GET'])
@app.route('/api/v1/admin/statistics', methods=['GET'])
@require_admin_login
def admin_statistics():
    """获取统计信息"""
    try:
        statistics = code_manager.get_statistics()
        # 添加用户使用统计
        total_users = len(user_usage_count)
        active_users = len([uid for uid, count in user_usage_count.items() if count > 0])
        
        statistics['total_users'] = total_users
        statistics['active_users'] = active_users
        
        return jsonify(statistics)
    except Exception as e:
        return fail_response(exc=e)


# ==================== RAG 缁狅紕鎮婇惄绋垮彠 API ====================

def get_rag_db_path():
    default_path = os.path.join(BASE_DIR, 'knowledge_base', 'rag.db')
    return os.getenv('SQLITE_RAG_DB_PATH', default_path)


def rag_db_exists():
    return os.path.exists(get_rag_db_path())


def rag_db_connect(query_only=False):
    conn = sqlite3.connect(get_rag_db_path())
    conn.row_factory = sqlite3.Row
    if query_only:
        conn.execute("PRAGMA query_only = ON")
    return conn


def rag_chunk_text(content, chunk_size=1200, overlap=160):
    text = (content or '').strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks


def rag_vector_to_blob_float16(vector):
    return struct.pack('<' + ('e' * len(vector)), *vector)


def rag_insert_document(title, content, source_path='', filename=''):
    from sqlite_rag_adapter import text_to_vector

    embed_dim = int(os.getenv('SQLITE_RAG_EMBED_DIM', '2048'))
    title = (title or '').strip() or 'Untitled'
    content = (content or '').strip()
    source_path = (source_path or '').strip()
    filename = (filename or '').strip()
    if not content:
        return None

    if not filename and source_path:
        filename = os.path.basename(source_path)
    if not filename:
        filename = f'manual_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'

    content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
    chunks = rag_chunk_text(content)
    if not chunks:
        return None

    conn = rag_db_connect(query_only=False)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO documents (title, filename, source_path, file_hash, char_count)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title, filename, source_path, content_hash, len(content))
        )
        document_id = cur.lastrowid

        for idx, chunk in enumerate(chunks):
            cur.execute(
                """
                INSERT INTO chunks (document_id, chunk_index, chunk_text, char_count)
                VALUES (?, ?, ?, ?)
                """,
                (document_id, idx, chunk, len(chunk))
            )
            chunk_id = cur.lastrowid

            vector = text_to_vector(chunk, dim=embed_dim)
            embedding_blob = rag_vector_to_blob_float16(vector)
            cur.execute(
                """
                INSERT INTO chunk_vectors (chunk_id, dim, vector_dtype, embedding)
                VALUES (?, ?, ?, ?)
                """,
                (chunk_id, embed_dim, 'float16', embedding_blob)
            )
            cur.execute(
                """
                INSERT INTO chunks_fts (rowid, chunk_text, title, filename, source_path, chunk_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (chunk_id, chunk, title, filename, source_path, chunk_id)
            )

        conn.commit()
        try:
            if source_path and os.path.isfile(source_path):
                register_and_annotate_file(
                    source_path,
                    kind='rag_source',
                    origin_name=(filename or os.path.basename(source_path)),
                    source_ref=f"rag_document:{document_id}",
                    extra={'title': title},
                )
        except Exception:
            logger.exception("Failed to register rag source file: %s", source_path)
        return int(document_id)
    finally:
        conn.close()


def rag_strip_html(raw_html):
    html_text = re.sub(r'(?is)<script.*?>.*?</script>', ' ', raw_html)
    html_text = re.sub(r'(?is)<style.*?>.*?</style>', ' ', html_text)
    html_text = re.sub(r'(?is)<[^>]+>', ' ', html_text)
    html_text = html.unescape(html_text)
    return re.sub(r'\s+', ' ', html_text).strip()


@app.route('/rag')
@require_admin_page_login
def rag_admin_page():
    return render_template('rag_admin.html')


@app.route('/api/rag/stats', methods=['GET'])
@app.route('/api/v1/rag/stats', methods=['GET'])
@require_admin_login
def rag_stats():
    try:
        if not rag_db_exists():
            return jsonify({
                'success': False,
                'error': f'RAG database not found: {get_rag_db_path()}'
            }), 404

        conn = rag_db_connect(query_only=True)
        try:
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) FROM documents')
            doc_count = int(cur.fetchone()[0])
            cur.execute('SELECT COUNT(*) FROM chunks')
            chunk_count = int(cur.fetchone()[0])
            cur.execute('SELECT MAX(dim) FROM chunk_vectors')
            embed_dim = cur.fetchone()[0] or int(os.getenv('SQLITE_RAG_EMBED_DIM', '2048'))
            cur.execute('SELECT SUM(char_count) FROM documents')
            total_chars = int(cur.fetchone()[0] or 0)

            # Calculate database file size
            db_path = get_rag_db_path()
            total_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
        finally:
            conn.close()

        return jsonify({
            'success': True,
            'stats': {
                'collection_name': 'sqlite_rag',
                'total_documents': doc_count,
                'total_chunks': chunk_count,
                'status': 'ready',
                'embedding_model': os.getenv('SQLITE_RAG_EMBEDDING_MODEL', 'sqlite_char_ngram'),
                'embedding_dimension': int(embed_dim),
                'db_path': get_rag_db_path(),
                'total_chars': total_chars,
                'total_size': total_size,
            }
        })
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/rag/search', methods=['POST'])
@app.route('/api/v1/rag/search', methods=['POST'])
@require_admin_login
def rag_search():
    try:
        if not rag_db_exists():
            return jsonify({'success': False, 'error': 'RAG database not found'}), 404

        data = request.json or {}
        query = (data.get('query') or '').strip()
        strategy = (data.get('strategy') or 'hybrid').strip() or 'hybrid'
        category = (data.get('category') or '').strip()
        top_k = int(data.get('top_k') or os.getenv('RAG_TOP_K', '5'))

        if not query:
            return jsonify({'success': False, 'error': 'query is required'}), 400

        from sqlite_rag_adapter import SQLiteRAGRetriever
        retriever = SQLiteRAGRetriever(
            db_path=get_rag_db_path(),
            embed_dim=int(os.getenv('SQLITE_RAG_EMBED_DIM', '2048')),
            top_k=top_k,
            vector_candidate_limit=int(os.getenv('SQLITE_RAG_VECTOR_CANDIDATE_LIMIT', '300')),
        )
        results = retriever.retrieve(query=query, strategy=strategy, category=category, top_k=top_k)
        for item in results:
            payload = item.setdefault('payload', {})
            if not payload.get('category'):
                payload['category'] = 'general'

        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/rag/add', methods=['POST'])
@app.route('/api/v1/rag/add', methods=['POST'])
@require_admin_login
def rag_add():
    try:
        if not rag_db_exists():
            return jsonify({'success': False, 'error': 'RAG database not found'}), 404

        data = request.json or {}
        documents = data.get('documents') or []
        if not isinstance(documents, list) or not documents:
            return jsonify({'success': False, 'error': 'documents is required'}), 400

        document_ids = []
        for doc in documents:
            title = (doc.get('title') or '').strip()
            content = (doc.get('content') or '').strip()
            source = (doc.get('source') or '').strip()
            if not title or not content:
                continue
            doc_id = rag_insert_document(
                title=title,
                content=content,
                source_path=source,
                filename=os.path.basename(source) if source else ''
            )
            if doc_id is not None:
                document_ids.append(doc_id)

        if not document_ids:
            return jsonify({'success': False, 'error': 'no valid document to add'}), 400

        return jsonify({'success': True, 'document_ids': document_ids})
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/rag/add/url', methods=['POST'])
@app.route('/api/v1/rag/add/url', methods=['POST'])
@require_admin_login
def rag_add_url():
    try:
        if not rag_db_exists():
            return jsonify({'success': False, 'error': 'RAG database not found'}), 404

        data = request.json or {}
        url = (data.get('url') or '').strip()
        if not url:
            return jsonify({'success': False, 'error': 'url is required'}), 400

        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urlopen(req, timeout=20) as resp:
                raw = resp.read()
        except (HTTPError, URLError) as e:
            return jsonify({'success': False, 'error': f'fetch failed: {e}'}), 400

        text = raw.decode('utf-8', errors='ignore')
        title_match = re.search(r'(?is)<title[^>]*>(.*?)</title>', text)
        title = title_match.group(1).strip() if title_match else url
        content = rag_strip_html(text)
        if not content:
            return jsonify({'success': False, 'error': 'empty content fetched from url'}), 400

        doc_id = rag_insert_document(
            title=title,
            content=content,
            source_path=url,
            filename=f"url_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        )
        if doc_id is None:
            return jsonify({'success': False, 'error': 'failed to add fetched content'}), 500

        return jsonify({'success': True, 'document_ids': [doc_id]})
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/rag/add/directory', methods=['POST'])
@app.route('/api/v1/rag/add/directory', methods=['POST'])
@require_admin_login
def rag_add_directory():
    try:
        if not rag_db_exists():
            return jsonify({'success': False, 'error': 'RAG database not found'}), 404

        data = request.json or {}
        directory = (data.get('directory') or '').strip()
        if not directory:
            return jsonify({'success': False, 'error': 'directory is required'}), 400
        if not os.path.isdir(directory):
            return jsonify({'success': False, 'error': f'directory does not exist: {directory}'}), 400

        exts = {'.txt', '.md', '.pdf', '.docx'}
        total = 0
        imported_files = []
        max_files = int(os.getenv('RAG_IMPORT_MAX_FILES', '200'))
        for root, _, files in os.walk(directory):
            for name in files:
                if total >= max_files:
                    break
                ext = os.path.splitext(name)[1].lower()
                if ext not in exts:
                    continue
                path = os.path.join(root, name)
                try:
                    content, _ = file_processor.process_file(path)
                    doc_id = rag_insert_document(
                        title=os.path.splitext(name)[0],
                        content=content,
                        source_path=path,
                        filename=name
                    )
                    if doc_id is not None:
                        total += 1
                        imported_files.append(path)
                except Exception:
                    logger.exception("Failed to import file into RAG: %s", path)
            if total >= max_files:
                break

        return jsonify({'success': True, 'count': total, 'files': imported_files})
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/rag/clear', methods=['POST'])
@app.route('/api/v1/rag/clear', methods=['POST'])
@require_admin_login
def rag_clear():
    try:
        if not rag_db_exists():
            return jsonify({'success': False, 'error': 'RAG database not found'}), 404

        conn = rag_db_connect(query_only=False)
        try:
            cur = conn.cursor()
            cur.execute('DELETE FROM chunk_vectors')
            cur.execute('DELETE FROM chunks')
            cur.execute('DELETE FROM documents')
            cur.execute('DELETE FROM chunks_fts')
            conn.commit()
        finally:
            conn.close()

        return jsonify({'success': True})
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/rag/export', methods=['GET'])
@app.route('/api/v1/rag/export', methods=['GET'])
@require_admin_login
def rag_export():
    try:
        if not rag_db_exists():
            return jsonify({'success': False, 'error': 'RAG database not found'}), 404

        os.makedirs('reports', exist_ok=True)
        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        out_file = os.path.join('reports', f'rag_export_{now}.json')

        conn = rag_db_connect(query_only=True)
        try:
            cur = conn.cursor()
            rows = cur.execute(
                """
                SELECT
                    d.id AS document_id,
                    d.title,
                    d.filename,
                    d.source_path,
                    d.file_hash,
                    d.char_count,
                    c.id AS chunk_id,
                    c.chunk_index,
                    c.chunk_text
                FROM documents d
                LEFT JOIN chunks c ON c.document_id = d.id
                ORDER BY d.id, c.chunk_index
                """
            ).fetchall()
        finally:
            conn.close()

        export_rows = []
        for r in rows:
            export_rows.append({
                'document_id': r['document_id'],
                'title': r['title'],
                'filename': r['filename'],
                'source_path': r['source_path'],
                'file_hash': r['file_hash'],
                'char_count': r['char_count'],
                'chunk_id': r['chunk_id'],
                'chunk_index': r['chunk_index'],
                'chunk_text': r['chunk_text'],
            })

        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(
                {
                    'export_time': datetime.now().isoformat(),
                    'db_path': get_rag_db_path(),
                    'row_count': len(export_rows),
                    'rows': export_rows,
                },
                f,
                ensure_ascii=False,
                indent=2
            )

        return jsonify({'success': True, 'file': out_file, 'count': len(export_rows)})
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/v1/admin/sessions/<string:session_id>', methods=['DELETE'])
@require_admin_login
def admin_delete_session(session_id):
    """Admin: delete any session by its unscoped session_id."""
    try:
        suffix = f"{SESSION_KEY_SEP}{sanitize_session_id(session_id)}"
        keys_to_delete = [k for k in list(conversation_histories.keys()) if k.endswith(suffix)]
        if not keys_to_delete:
            return jsonify({'error': 'session not found'}), 404
        for k in keys_to_delete:
            conversation_histories.pop(k, None)
            session_metadata.pop(k, None)
        save_runtime_state()
        return jsonify({'success': True, 'deleted': len(keys_to_delete)})
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/v1/files', methods=['GET'])
@require_admin_login
def list_files():
    """Admin: list all active files from the file registry."""
    try:
        conn = file_registry._connect()
        try:
            rows = conn.execute(
                """
                SELECT file_id, origin_name, kind, mime_type, size_bytes, created_at, updated_at, status
                FROM file_registry
                WHERE status = 'active'
                ORDER BY created_at DESC
                LIMIT 200
                """
            ).fetchall()
        finally:
            conn.close()
        files = [
            {
                'file_id': r['file_id'],
                'filename': r['origin_name'],
                'file_type': r['kind'],
                'mime_type': r['mime_type'],
                'file_size': int(r['size_bytes'] or 0),
                'upload_time': r['created_at'],
                'updated_at': r['updated_at'],
                'status': r['status'],
            }
            for r in rows
        ]
        return jsonify({'files': files})
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/v1/files/<string:file_id>', methods=['GET'])
def file_detail(file_id):
    try:
        record = file_registry.get_file(file_id)
        if not record or record.get('status') != 'active':
            return jsonify({'error': 'file not found'}), 404
        return jsonify({
            'file_id': record.get('file_id', ''),
            'kind': record.get('kind', ''),
            'origin_name': record.get('origin_name', ''),
            'stored_name': record.get('stored_name', ''),
            'mime_type': record.get('mime_type', ''),
            'size_bytes': int(record.get('size_bytes', 0) or 0),
            'created_at': record.get('created_at', ''),
            'updated_at': record.get('updated_at', ''),
            'source_ref': record.get('source_ref', ''),
            'extra': _safe_extra_json(record.get('extra_json', '{}')),
        })
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/v1/files/<string:file_id>/download', methods=['GET'])
def download_file_by_id(file_id):
    try:
        record = file_registry.get_file(file_id)
        if not record or record.get('status') != 'active':
            return jsonify({'error': 'file not found'}), 404
        filepath = record.get('stored_path', '')
        if not filepath or not os.path.exists(filepath):
            return jsonify({'error': 'file is missing on server'}), 404
        return send_file(
            filepath,
            mimetype=(record.get('mime_type') or 'application/octet-stream'),
            as_attachment=True,
            download_name=record.get('origin_name') or record.get('stored_name') or os.path.basename(filepath),
        )
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/download/report/<path:filename>', methods=['GET'])
@app.route('/api/v1/download/report/<path:filename>', methods=['GET'])
def download_report(filename):
    """Download generated report files (PDF/MD)."""
    try:
        # 解码URL编码的文件名
        filename = unquote(filename)
        
        # 安全查：叅许下载reports盽下的文件
        reports_dir = 'reports'
        
        # 移除路径分隔符，防止路径遍历攻击
        filename = os.path.basename(filename)
        
        # 查文件扩展名
        file_ext = os.path.splitext(filename)[1].lower()
        
        # 清理文件名中的HTML标（防止解析错诼
        filename = filename.replace('<em>', '').replace('</em>', '').replace('<strong>', '').replace('</strong>', '').replace('<', '').replace('>', '').strip()
        
        # 构建文件路径
        filepath = os.path.join(reports_dir, filename)

        # 检查文件是否存在
        if not os.path.exists(filepath):
            error_msg = (
                f'服务器上文件不存在: {filename}。\n\n'
                '请使用页面上的“导出报告”按钮在浏览器端生成并下载 PDF。'
            )
            return jsonify({'error': error_msg}), 404

        # 检查文件路径是否在 reports 目录内（防路径遍历攻击）
        abs_reports_dir = os.path.abspath(reports_dir)
        abs_filepath = os.path.abspath(filepath)
        if not abs_filepath.startswith(abs_reports_dir):
            return jsonify({'error': '非法文件路径'}), 403
        
        # 根据文件类型设置 MIME 类型
        if file_ext == '.pdf':
            mimetype = 'application/pdf'
        elif file_ext == '.md':
            mimetype = 'text/markdown; charset=utf-8'
        else:
            mimetype = 'application/octet-stream'
        
        # 返回文件下载
        return send_file(
            filepath,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/v1/reports/<string:file_id>/pdf-status', methods=['GET'])
def pdf_status_by_file_id(file_id):
    try:
        record = file_registry.get_file(file_id)
        if not record or record.get('status') != 'active':
            return jsonify({'error': 'file not found'}), 404

        kind = record.get('kind', '')
        base_name = os.path.splitext(record.get('stored_name', '') or '')[0]
        report_id = record.get('source_ref', '')

        if kind == 'report_pdf':
            return jsonify({
                'status': 'completed',
                'progress': 100,
                'message': 'PDF转换完成',
                'download_url': build_file_download_url(file_id),
                'file_id': file_id,
            })

        if kind != 'report_md':
            return jsonify({'error': 'only report file status is supported'}), 400

        # Locate paired PDF by source_ref then fallback filename pairing.
        pdf_candidate = None
        if report_id:
            with sqlite3.connect(FILE_REGISTRY_DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                pdf_candidate = conn.execute(
                    """
                    SELECT * FROM file_registry
                    WHERE source_ref = ? AND kind = 'report_pdf' AND status = 'active'
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (report_id,),
                ).fetchone()
        if not pdf_candidate:
            with sqlite3.connect(FILE_REGISTRY_DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                pdf_candidate = conn.execute(
                    """
                    SELECT * FROM file_registry
                    WHERE kind = 'report_pdf' AND status = 'active' AND stored_name LIKE ?
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (f"{base_name}.pdf",),
                ).fetchone()
        if pdf_candidate:
            pdf_file_id = dict(pdf_candidate).get('file_id', '')
            return jsonify({
                'status': 'completed',
                'progress': 100,
                'message': 'PDF转换完成',
                'download_url': build_file_download_url(pdf_file_id),
                'file_id': pdf_file_id,
            })
        return jsonify({
            'status': 'failed',
            'progress': 100,
            'message': 'PDF不存在，可重新转换或下载Markdown',
            'file_id': file_id,
        })
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/pdf/status/<path:filename>', methods=['GET'])
@app.route('/api/v1/pdf/status/<path:filename>', methods=['GET'])
def pdf_status(filename):
    """Query server-side PDF conversion status by filename."""
    try:
        reports_dir = 'reports'
        os.makedirs(reports_dir, exist_ok=True)

        filename = os.path.basename(unquote(filename))
        if not filename:
            return jsonify({'error': 'invalid filename'}), 400

        pdf_path = os.path.join(reports_dir, filename)
        if os.path.exists(pdf_path):
            encoded = quote(filename, safe='')
            return jsonify({
                'status': 'completed',
                'progress': 100,
                'message': 'PDF杞崲瀹屾垚',
                'download_url': f'/api/v1/download/report/{encoded}',
            })

        # If PDF is missing but markdown exists, return failed status for clear UX.
        base, ext = os.path.splitext(filename)
        md_name = f'{base}.md' if ext.lower() == '.pdf' else filename
        md_path = os.path.join(reports_dir, md_name)
        if os.path.exists(md_path):
            return jsonify({
                'status': 'failed',
                'progress': 100,
                'message': 'PDF不存圼叇新转换或下载Markdown',
                'markdown_filename': md_name,
            })

        return jsonify({'error': 'task not found'}), 404
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/v1/reports/<string:file_id>/convert-pdf', methods=['POST'])
def convert_pdf_by_file_id(file_id):
    try:
        md_record = file_registry.get_file(file_id)
        if not md_record or md_record.get('status') != 'active':
            return jsonify({'error': 'file not found'}), 404
        if md_record.get('kind') != 'report_md':
            return jsonify({'error': 'only markdown report can be converted'}), 400

        md_path = md_record.get('stored_path', '')
        if not md_path or not os.path.exists(md_path):
            return jsonify({'error': 'markdown file not found'}), 404
        with open(md_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()

        reports_dir = 'reports'
        os.makedirs(reports_dir, exist_ok=True)
        base_name = os.path.splitext(md_record.get('stored_name') or '')[0]
        pdf_name = f"{base_name}.pdf"
        pdf_path = os.path.join(reports_dir, pdf_name)
        agent._convert_markdown_to_pdf(markdown_content, pdf_path)
        pdf_rec = register_and_annotate_file(
            pdf_path,
            kind='report_pdf',
            origin_name=os.path.basename(pdf_name),
            source_ref=md_record.get('source_ref', ''),
            extra={'paired_md_file_id': file_id},
        )
        pdf_file_id = pdf_rec.get('file_id', '')
        return jsonify({
            'success': True,
            'file_id': pdf_file_id,
            'download_url': build_file_download_url(pdf_file_id),
            'status': 'completed',
            'progress': 100,
            'message': 'PDF转换完成',
        })
    except Exception as e:
        return fail_response(exc=e)


@app.route('/api/pdf/convert/<path:filename>', methods=['POST'])
@app.route('/api/v1/pdf/convert/<path:filename>', methods=['POST'])
def convert_pdf(filename):
    """Convert an existing markdown report file to PDF on demand."""
    try:
        reports_dir = 'reports'
        os.makedirs(reports_dir, exist_ok=True)

        filename = os.path.basename(unquote(filename))
        if not filename.lower().endswith('.md'):
            return jsonify({'error': 'only .md file is supported'}), 400

        md_path = os.path.join(reports_dir, filename)
        if not os.path.exists(md_path):
            return jsonify({'error': 'markdown file not found'}), 404

        with open(md_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()

        pdf_name = f"{os.path.splitext(filename)[0]}.pdf"
        pdf_path = os.path.join(reports_dir, pdf_name)
        agent._convert_markdown_to_pdf(markdown_content, pdf_path)

        encoded = quote(pdf_name, safe='')
        return jsonify({
            'success': True,
            'filename': pdf_name,
            'download_url': f'/api/v1/download/report/{encoded}',
            'status': 'completed',
            'progress': 100,
            'message': 'PDF杞崲瀹屾垚',
        })
    except Exception as e:
        return fail_response(exc=e)


@app.errorhandler(Exception)
def handle_unexpected_exception(e):
    """Final safety net for uncaught exceptions."""
    if isinstance(e, HTTPException):
        return e
    return fail_response(exc=e)


if __name__ == '__main__':
    # 确保 reports 目录存在
    os.makedirs('reports', exist_ok=True)

    # 从环境变量或命令行参数获取端口
    import sys
    port = 5000
    debug = False

    # 检查命令行参数
    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv[1:], 1):
            if arg == '--port' and i < len(sys.argv) - 1:
                try:
                    port = int(sys.argv[i + 1])
                except (ValueError, IndexError):
                    pass
            elif arg == '--debug':
                debug = True
            elif arg.startswith('--port='):
                try:
                    port = int(arg.split('=')[1])
                except (ValueError, IndexError):
                    pass
    
    # 从环境变量获取端口
    port = int(os.getenv('FLASK_RUN_PORT', os.getenv('PORT', port)))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true' or debug
    use_reloader = os.getenv('FLASK_USE_RELOADER', 'false').lower() == 'true'
    if not debug:
        use_reloader = False
    
    logger.info("=" * 50)
    logger.info("智能体 Web 服务已启动")
    logger.info("=" * 50)
    logger.info("访问地址: http://0.0.0.0:%s", port)
    logger.info("本地访问: http://localhost:%s", port)
    logger.info("开发模式: %s, 自动重载: %s", debug, use_reloader)
    logger.info("按 Ctrl+C 停止服务")
    logger.info("-" * 50)
    import pprint
    logger.info("DEBUG URL MAP:")
    logger.info(pprint.pformat(list(app.url_map.iter_rules())))
    app.run(debug=debug, host='0.0.0.0', port=port, threaded=True, use_reloader=use_reloader)



