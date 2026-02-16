"""
Flask Web应用主程序
提供Web API接口和前端页面
"""

import os
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, Response, stream_with_context, send_file, session, make_response
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from urllib.parse import quote, unquote
from config import Config
from agent import IntelligentAgent
from file_processor import FileProcessor
from code_manager import CodeManager
import uuid
import secrets

app = Flask(__name__)
# 配置CORS，允许微信小程序访问
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# 配置
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB最大文件大小
app.config['SECRET_KEY'] = os.urandom(24)
# 管理员配置（默认用户名和密码，建议通过环境变量设置）
app.config['ADMIN_USERNAME'] = os.getenv('ADMIN_USERNAME', 'admin')
app.config['ADMIN_PASSWORD'] = os.getenv('ADMIN_PASSWORD', 'admin123')  # 默认密码，建议修改

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 初始化智能体和文件处理器
config = Config()
agent = IntelligentAgent(config)
file_processor = FileProcessor()

# PDF转换进度跟踪
pdf_conversion_status = {}  # {filename: {'status': 'pending'|'converting'|'completed'|'failed', 'progress': 0-100, 'message': '', 'download_url': ''}}

# 初始化验证码管理器，使用"兑换码及验码"文件夹中的文件
# 尝试多个可能的路径（支持Windows和Linux）
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
possible_code_paths = [
    # Linux服务器路径（项目目录下）
    os.path.join(current_dir, 'generated_codes.json'),
    # Windows开发环境路径
    os.path.join(current_dir, '..', '兑换码及验码', 'generated_codes.json'),
    os.path.join(current_dir, '兑换码及验码', 'generated_codes.json'),
    os.path.join('C:', 'Users', 'Abraham', 'Desktop', '兑换码及验码', 'generated_codes.json'),
]

codes_file = None
for path in possible_code_paths:
    abs_path = os.path.abspath(path)
    if os.path.exists(abs_path):
        codes_file = abs_path
        break
else:
    # 如果都不存在，使用项目目录下的路径（会在保存时创建）
    codes_file = os.path.join(current_dir, 'generated_codes.json')

code_manager = CodeManager(codes_file=codes_file)
print(f"[信息] 验证码文件路径: {code_manager.codes_file}")

# 存储对话历史（使用字典，key为session_id）
conversation_histories = {}
# 存储会话元数据（标题、创建时间等）
session_metadata = {}
# 存储用户使用次数（使用字典，key为user_id）
user_usage_count = {}
# PDF转换进度跟踪 {filename: {'status': 'pending'|'converting'|'completed'|'failed', 'progress': 0-100, 'message': '', 'download_url': ''}}
pdf_conversion_status = {}
# 存储管理员会话（使用字典，key为session_token）
admin_sessions = {}


def get_or_create_session(session_id):
    """获取或创建会话历史"""
    if session_id not in conversation_histories:
        conversation_histories[session_id] = []
        # 初始化会话元数据
        if session_id not in session_metadata:
            session_metadata[session_id] = {
                'title': '新对话',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
    return conversation_histories[session_id]


def update_session_title(session_id, user_input):
    """更新会话标题（从第一条用户消息提取）"""
    if session_id in session_metadata:
        # 如果标题还是默认的"新对话"，则更新
        if session_metadata[session_id]['title'] == '新对话':
            # 提取标题（取前30个字符）
            title = user_input[:30] if len(user_input) <= 30 else user_input[:27] + '...'
            session_metadata[session_id]['title'] = title
        session_metadata[session_id]['updated_at'] = datetime.now().isoformat()


def get_user_id_from_cookie():
    """从Cookie中获取用户ID，如果不存在则生成新的"""
    user_id = request.cookies.get('user_id')
    if not user_id:
        user_id = str(uuid.uuid4())
    return user_id


def get_user_usage_count(user_id):
    """获取用户剩余使用次数"""
    return user_usage_count.get(user_id, 0)


def decrease_user_usage_count(user_id):
    """减少用户使用次数"""
    if user_id in user_usage_count and user_usage_count[user_id] > 0:
        user_usage_count[user_id] -= 1
        return True
    return False


def increase_user_usage_count(user_id, count=1):
    """增加用户使用次数"""
    if user_id not in user_usage_count:
        user_usage_count[user_id] = 0
    user_usage_count[user_id] += count


def require_admin_login(f):
    """管理员登录装饰器"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin_token = request.cookies.get('admin_token')
        if not admin_token or admin_token not in admin_sessions:
            return jsonify({'error': '需要管理员登录'}), 401
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def index():
    """主页"""
    return render_template('index_new.html')

@app.route('/old')
def index_old():
    """聊天对话页面"""
    return render_template('index.html')

@app.route('/chat')
def chat_page():
    """聊天对话页面（别名）"""
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """处理聊天请求（非流式）"""
    try:
        # 检查用户使用次数
        user_id = get_user_id_from_cookie()
        usage_count = get_user_usage_count(user_id)
        if usage_count <= 0:
            response = jsonify({'error': '使用次数已用完，请先输入验证码'})
            response.set_cookie('user_id', user_id, max_age=365*24*60*60)  # 1年
            return response, 403
        
        data = request.json
        user_input = data.get('message', '').strip()
        session_id = data.get('session_id', 'default')
        
        if not user_input:
            return jsonify({'error': '消息不能为空'}), 400
        
        # 获取会话历史
        conversation_history = get_or_create_session(session_id)
        
        # 调用智能体
        reply, usage_info = agent.chat(user_input, conversation_history)
        
        # 检查是否是报告请求，如果是则获取下载信息
        is_report = agent._is_report_request(user_input)
        report_download = None
        if is_report:
            save_info = agent._save_report(reply, user_input)
            if save_info:
                download_url = save_info.get('download_url', '')
                filename = save_info.get('filename', '')
                file_format = save_info.get('format', 'pdf')
                format_text = 'PDF' if file_format == 'pdf' else 'Markdown'
                report_download = {
                    'url': download_url,
                    'filename': filename,
                    'format': file_format
                }
                # 在回复中添加下载链接
                reply += f"\n\n---\n✅ **报告已生成并保存**\n📁 文件名: `{filename}` ({format_text}格式)\n🔗 [点击下载报告]({download_url})"
        
        # 更新对话历史
        conversation_history.append({"role": "user", "content": user_input})
        conversation_history.append({"role": "assistant", "content": reply})
        
        # 更新会话标题
        update_session_title(session_id, user_input)
        
        # 限制历史记录长度
        if len(conversation_history) > 20:
            conversation_history[:] = conversation_history[-20:]
        
        # 减少使用次数
        decrease_user_usage_count(user_id)
        remaining = get_user_usage_count(user_id)
        print(f"[聊天API] 用户 {user_id} 使用后剩余次数: {remaining}")
        
        response_data = {
            'reply': reply,
            'session_id': session_id,
            'usage': usage_info,
            'remaining_uses': remaining
        }
        
        # 如果有报告下载信息，添加到响应中
        if report_download:
            response_data['report_download'] = report_download
        
        response = jsonify(response_data)
        response.set_cookie('user_id', user_id, max_age=365*24*60*60)  # 1年
        return response
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """处理聊天请求（流式输出）"""
    try:
        # 检查用户使用次数
        user_id = get_user_id_from_cookie()
        usage_count = get_user_usage_count(user_id)
        if usage_count <= 0:
            def error_generate():
                yield f"data: {json.dumps({'content': '', 'done': True, 'error': True, 'error_message': '使用次数已用完，请先输入验证码'}, ensure_ascii=False)}\n\n"
            return Response(stream_with_context(error_generate()), mimetype='text/event-stream')
        
        data = request.json
        user_input = data.get('message', '').strip()
        session_id = data.get('session_id', 'default')
        
        if not user_input:
            return jsonify({'error': '消息不能为空'}), 400
        
        # 获取会话历史
        conversation_history = get_or_create_session(session_id)
        
        def generate():
            full_reply = ""
            try:
                import time
                stream_start_time = time.time()
                stream_timeout = 1200  # 20分钟总超时时间
                
                # 流式调用智能体
                for chunk in agent.chat_stream(user_input, conversation_history):
                    full_reply += chunk
                    yield f"data: {json.dumps({'content': chunk, 'done': False}, ensure_ascii=False)}\n\n"
                    
                    # 检查总时间是否超时（作为额外保护）
                    if time.time() - stream_start_time > stream_timeout:
                        timeout_msg = '\n\n[警告] 流式输出总时间超时（超过20分钟），已停止接收数据。'
                        yield f"data: {json.dumps({'content': timeout_msg, 'done': False}, ensure_ascii=False)}\n\n"
                        break
                
                # 检测是否被截断，如果是报告请求则自动续写
                # 注意：只有在finish_reason为"length"或内容明显不完整时才续写，避免误判
                is_report = agent._is_report_request(user_input)
                finish_reason_from_stream = getattr(agent, '_last_finish_reason', None)
                
                # 更严格的截断检测：只有明确被截断（finish_reason为length）或内容明显不完整时才续写
                should_continue = False
                if is_report:
                    # 【修复】首先检查是否包含报告完成标记和未完成标记
                    completion_markers = [
                        "【报告已完成】",  # 新的完成标记（优先级最高）
                        "综上所述", "建议尽快批准实施", "建议批准实施", "建议尽快实施",
                        "报告撰写完成", "全文完成", "报告结束", "全文结束", "撰写完毕"
                    ]
                    incomplete_markers = [
                        "【报告未完成，待续写】",  # 新的未完成标记（优先级最高）
                        "（待续……）", "待续", "未完待续"
                    ]
                    
                    last_3000 = full_reply[-3000:] if len(full_reply) > 3000 else full_reply
                    has_completion_marker = any(marker in last_3000 for marker in completion_markers)
                    has_incomplete_marker = any(marker in last_3000 for marker in incomplete_markers)
                    
                    # 【重要修复】如果检测到【报告未完成，待续写】标记，强制触发续写
                    if has_incomplete_marker:
                        should_continue = True
                        print(f"[续写检测] 检测到【报告未完成，待续写】标记，内容{len(full_reply)}字符，触发续写", flush=True)
                    # 如果有完成标记且内容超过1万字，不续写
                    elif has_completion_marker and len(full_reply) >= 10000:
                        should_continue = False
                        print(f"[续写检测] 检测到报告完成标记，内容{len(full_reply)}字符，不续写", flush=True)
                    # 使用 agent 的截断检测方法（已更新，包含新标记检测）
                    elif agent._is_content_truncated(full_reply, finish_reason_from_stream, is_report=True):
                        should_continue = True
                        print(f"[续写检测] 检测到内容被截断，内容{len(full_reply)}字符，触发续写", flush=True)
                    elif finish_reason_from_stream == "length":
                        should_continue = True
                        print(f"[续写检测] finish_reason为length，内容{len(full_reply)}字符，触发续写", flush=True)
                    elif finish_reason_from_stream and finish_reason_from_stream != "length":
                        should_continue = False
                        print(f"[续写检测] finish_reason为{finish_reason_from_stream}，不续写", flush=True)
                    elif has_completion_marker:
                        should_continue = False
                        print(f"[续写检测] 检测到完成标记，不续写", flush=True)
                    elif len(full_reply) < 10000:
                        should_continue = True
                        print(f"[续写检测] 内容长度不足({len(full_reply)}字符)，触发续写", flush=True)
                    elif not ("第十章" in full_reply or "研究结论及建议" in full_reply):
                        should_continue = True
                        print(f"[续写检测] 缺少第十章，触发续写", flush=True)
                    else:
                        should_continue = False
                        print(f"[续写检测] 其他情况，不续写", flush=True)

                if should_continue:  # 已恢复续写
                    try:
                        continuation_msg = '\n\n[续写] 检测到报告未完成，开始自动续写...\n'
                        yield f"data: {json.dumps({'content': continuation_msg, 'done': False}, ensure_ascii=False)}\n\n"
                        print(f"[续写] 开始续写，当前内容长度: {len(full_reply)}字符", flush=True)
                        
                        # 初始化续写token累计
                        if agent.last_usage:
                            agent._continuation_usage = {
                                'prompt_tokens': agent.last_usage.get('prompt_tokens', 0),
                                'completion_tokens': agent.last_usage.get('completion_tokens', 0),
                                'total_tokens': agent.last_usage.get('total_tokens', 0)
                            }
                        
                        continuation_text = ""
                        chunk_count = 0
                        for chunk in agent._continue_writing_stream(full_reply, user_input, conversation_history):
                            chunk_count += 1
                            # 检测是否是状态信息
                            is_status = (chunk.startswith('[') and any(keyword in chunk for keyword in 
                                ['续写', '完成', '报告已完成', '警告', '信息', '错误', '中断', '耗时', '新增', '字符']))
                            
                            if is_status:
                                yield f"data: {json.dumps({'content': chunk, 'done': False}, ensure_ascii=False)}\n\n"
                            else:
                                continuation_text += chunk
                                yield f"data: {json.dumps({'content': chunk, 'done': False}, ensure_ascii=False)}\n\n"
                        
                        print(f"[续写] 续写完成，收到{chunk_count}个chunk，续写内容长度: {len(continuation_text)}字符", flush=True)
                        
                        if continuation_text.strip():
                            full_reply += "\n\n" + continuation_text.strip()
                            print(f"[续写] 内容已追加，总长度: {len(full_reply)}字符", flush=True)
                        else:
                            print(f"[续写警告] 续写内容为空，可能续写失败", flush=True)
                    except Exception as e:
                        error_msg = f"\n\n[续写错误] 续写过程中发生错误: {str(e)}\n"
                        print(f"[续写错误] {error_msg}", flush=True)
                        yield f"data: {json.dumps({'content': error_msg, 'done': False}, ensure_ascii=False)}\n\n"
                        import traceback
                        print(f"[续写错误] 详细错误: {traceback.format_exc()}", flush=True)
                    
                    # 更新token使用信息为累计值
                    if hasattr(agent, '_continuation_usage'):
                        agent.last_usage = agent._continuation_usage.copy() if agent._continuation_usage else {}
                
                # 如果是报告请求，保存为文件（先快速保存Markdown，PDF在后台转换）
                print(f'[调试] is_report={is_report}, user_input前50字={user_input[:50] if user_input else None}', flush=True)
                print(f'[调试] full_reply长度={len(full_reply)}', flush=True)
                save_info = None
                if is_report:
                    print('[调试] 开始保存报告...', flush=True)
                    try:
                        # 先快速保存Markdown文件（不等待PDF转换）
                        import os
                        import re
                        from datetime import datetime
                        from urllib.parse import quote
                        
                        reports_dir = 'reports'
                        os.makedirs(reports_dir, exist_ok=True)
                        
                        # 提取项目名称
                        project_name = agent._extract_project_name(user_input, full_reply)
                        project_name = re.sub(r'[<>:"/\\|?*]', '', project_name).strip()
                        if not project_name or len(project_name) > 50:
                            project_name = "项目"
                        
                        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                        base_filename = f"{project_name}-可行性研究报告-{timestamp}"
                        md_filename = f"{base_filename}.md"
                        md_filepath = os.path.join(reports_dir, md_filename)
                        
                        # 确保文件名唯一
                        counter = 1
                        while os.path.exists(md_filepath):
                            base_filename = f"{project_name}-可行性研究报告-{timestamp}-{counter}"
                            md_filename = f"{base_filename}.md"
                            md_filepath = os.path.join(reports_dir, md_filename)
                            counter += 1
                        
                        # 快速保存Markdown文件
                        with open(md_filepath, 'w', encoding='utf-8') as f:
                            f.write(full_reply)
                        
                        # 立即返回Markdown下载链接
                        encoded_filename = quote(md_filename, safe='')
                        save_info = {
                            'filename': md_filename,
                            'filepath': md_filepath,
                            'download_url': f'/api/download/report/{encoded_filename}',
                            'format': 'md'
                        }
                        
                        print(f'[调试] Markdown文件已保存: {md_filename}', flush=True)
                        
                        # 发送保存信息（Markdown版本）
                        download_url = save_info.get('download_url', '')
                        filename = save_info.get('filename', '')
                        # 准备PDF文件名用于进度跟踪
                        pdf_filename = f"{base_filename}.pdf"
                        
                        # 初始化PDF转换状态
                        pdf_conversion_status[pdf_filename] = {
                            'status': 'pending',
                            'progress': 0,
                            'message': '等待开始转换...'
                        }
                        
                        save_msg = f"\n\n---\n✅ **报告已生成并保存**\n📁 文件名: `{filename}` (Markdown格式)\n🔗 [点击下载报告]({download_url})\n\n⏳ PDF版本正在后台生成中，完成后可通过相同链接下载..."
                        full_reply += save_msg
                        yield f"data: {json.dumps({'content': save_msg, 'done': False, 'report_download': {'url': download_url, 'filename': filename, 'format': 'md', 'pdf_filename': pdf_filename}}, ensure_ascii=False)}\n\n"
                        
                        # 在后台异步生成PDF（不阻塞）
                        pdf_filepath = os.path.join(reports_dir, pdf_filename)
                        
                        def generate_pdf_async():
                            try:
                                pdf_conversion_status[pdf_filename]['status'] = 'converting'
                                pdf_conversion_status[pdf_filename]['progress'] = 10
                                pdf_conversion_status[pdf_filename]['message'] = '开始转换PDF...'
                                print(f'[PDF转换] 开始后台转换PDF: {pdf_filename}', flush=True)
                                
                                # 更新进度：转换Mermaid图表
                                pdf_conversion_status[pdf_filename]['progress'] = 30
                                pdf_conversion_status[pdf_filename]['message'] = '正在转换图表...'
                                
                                # 执行PDF转换
                                agent._convert_markdown_to_pdf(full_reply, pdf_filepath)
                                
                                # 转换完成
                                pdf_conversion_status[pdf_filename]['status'] = 'completed'
                                pdf_conversion_status[pdf_filename]['progress'] = 100
                                pdf_conversion_status[pdf_filename]['message'] = 'PDF转换完成！'
                                pdf_conversion_status[pdf_filename]['download_url'] = f'/api/download/report/{quote(pdf_filename, safe="")}'
                                print(f'[PDF转换] PDF转换完成: {pdf_filename}', flush=True)
                            except Exception as e:
                                pdf_conversion_status[pdf_filename]['status'] = 'failed'
                                pdf_conversion_status[pdf_filename]['progress'] = 0
                                pdf_conversion_status[pdf_filename]['message'] = f'转换失败: {str(e)}'
                                print(f'[PDF转换] PDF转换失败: {e}', flush=True)
                        
                        import threading
                        pdf_thread = threading.Thread(target=generate_pdf_async, daemon=True)
                        pdf_thread.start()
                        print('[调试] PDF转换已在后台启动', flush=True)
                        
                        # 在保存信息中包含PDF文件名，用于前端查询进度
                        save_info['pdf_filename'] = pdf_filename
                        
                    except Exception as e:
                        print(f'[调试] 保存报告异常: {e}', flush=True)
                        import traceback
                        traceback.print_exc()
                        # 即使保存失败，也继续执行，确保发送done信号
                
                # 更新对话历史（无论保存是否成功，都要执行）
                conversation_history.append({"role": "user", "content": user_input})
                conversation_history.append({"role": "assistant", "content": full_reply})
                
                # 更新会话标题
                update_session_title(session_id, user_input)
                
                # 限制历史记录长度
                if len(conversation_history) > 20:
                    conversation_history[:] = conversation_history[-20:]
                
                # 获取token使用信息（从最后一次API调用中获取）
                usage_info = agent.get_last_usage()
                
                # 如果没有获取到token信息，尝试从续写累计中获取
                if (not usage_info or usage_info.get('total_tokens', 0) == 0) and hasattr(agent, '_continuation_usage'):
                    usage_info = agent._continuation_usage.copy() if agent._continuation_usage else {}
                
                # 如果还是没有，尝试手动计算（估算）
                if not usage_info or usage_info.get('total_tokens', 0) == 0:
                    # 简单估算：中文大约1.5字符=1token，英文大约4字符=1token
                    # 这里使用一个简单的估算：总字符数/2作为token数
                    estimated_tokens = len(full_reply) // 2
                    usage_info = {
                        'prompt_tokens': 0,  # 无法准确计算
                        'completion_tokens': estimated_tokens,
                        'total_tokens': estimated_tokens,
                        'estimated': True  # 标记为估算值
                    }
                    print(f"[信息] 未获取到token信息，使用估算值: {estimated_tokens}", flush=True)
                else:
                    # 确保所有字段都存在
                    usage_info = {
                        'prompt_tokens': usage_info.get('prompt_tokens', 0),
                        'completion_tokens': usage_info.get('completion_tokens', 0),
                        'total_tokens': usage_info.get('total_tokens', 0)
                    }
                
                # 减少使用次数
                decrease_user_usage_count(user_id)
                
                yield f"data: {json.dumps({'content': '', 'done': True, 'usage': usage_info, 'remaining_uses': get_user_usage_count(user_id)}, ensure_ascii=False)}\n\n"
            
            except Exception as e:
                error_msg = f"错误: {str(e)}"
                yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True}, ensure_ascii=False)}\n\n"
        
        response = Response(stream_with_context(generate()), mimetype='text/event-stream')
        response.set_cookie('user_id', user_id, max_age=365*24*60*60)  # 1年
        return response
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """处理文件上传"""
    try:
        # 检查用户使用次数
        user_id = get_user_id_from_cookie()
        usage_count = get_user_usage_count(user_id)
        if usage_count <= 0:
            response = jsonify({'error': '使用次数已用完，请先输入验证码'})
            response.set_cookie('user_id', user_id, max_age=365*24*60*60)  # 1年
            return response, 403
        
        if 'file' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400
        
        file = request.files['file']
        user_query = request.form.get('query', '')
        session_id = request.form.get('session_id', 'default')
        
        if file.filename == '':
            return jsonify({'error': '文件名为空'}), 400
        
        # 检查文件类型
        if not file_processor.is_supported_file(file.filename):
            ext = os.path.splitext(file.filename)[1]
            return jsonify({'error': f'不支持的文件类型: {ext}'}), 400
        
        # 保存文件
        filename = secure_filename(file.filename)
        # 添加唯一标识符避免冲突
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        # 获取会话历史
        conversation_history = get_or_create_session(session_id)
        
        # 处理文件并获取格式化的文件提示词（包含文件内容）
        try:
            # 处理文件
            content, file_type = file_processor.process_file(filepath)
            
            # 格式化文件内容为提示词（包含完整文件内容）
            file_prompt = file_processor.format_file_content_for_prompt(
                filepath, content, file_type, user_query if user_query else None
            )
            
            # 构建完整的用户输入（包含文件内容）
            if user_query:
                full_user_input = f"{file_prompt}\n\n请根据上述文件内容回答：{user_query}"
            else:
                full_user_input = f"{file_prompt}\n\n请分析这个文件的内容。"
            
            # 调用chat方法（而不是chat_with_file，以便文件内容被正确传递）
            reply, usage_info = agent.chat(full_user_input, conversation_history)
            
            # 更新对话历史（保存完整的文件内容，以便续写时使用）
            conversation_history.append({"role": "user", "content": full_user_input})
            conversation_history.append({"role": "assistant", "content": reply})
        except Exception as e:
            # 如果处理失败，回退到原来的方法
            reply = agent.chat_with_file(filepath, user_query if user_query else None, conversation_history)
            
            # 更新对话历史
            file_msg = f"[上传文件: {filename}]"
            if user_query:
                file_msg += f" {user_query}"
            conversation_history.append({"role": "user", "content": file_msg})
            conversation_history.append({"role": "assistant", "content": reply})
        
        # 更新会话标题
        title_text = user_query if user_query else f"分析文件: {filename}"
        update_session_title(session_id, title_text)
        
        # 限制历史记录长度
        if len(conversation_history) > 20:
            conversation_history[:] = conversation_history[-20:]
        
        # 减少使用次数
        decrease_user_usage_count(user_id)
        
        response = jsonify({
            'reply': reply,
            'filename': filename,
            'session_id': session_id,
            'remaining_uses': get_user_usage_count(user_id)
        })
        response.set_cookie('user_id', user_id, max_age=365*24*60*60)  # 1年
        return response
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    """清空对话历史"""
    try:
        data = request.json
        session_id = data.get('session_id', 'default')
        
        if session_id in conversation_histories:
            conversation_histories[session_id] = []
            # 重置会话标题
            if session_id in session_metadata:
                session_metadata[session_id]['title'] = '新对话'
                session_metadata[session_id]['updated_at'] = datetime.now().isoformat()
        
        return jsonify({'success': True, 'message': '对话历史已清空'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/history', methods=['GET'])
def get_history():
    """获取对话历史"""
    try:
        session_id = request.args.get('session_id', 'default')
        conversation_history = get_or_create_session(session_id)
        
        # 获取会话元数据
        metadata = session_metadata.get(session_id, {
            'title': '新对话',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        })
        
        return jsonify({
            'history': conversation_history,
            'session_id': session_id,
            'metadata': metadata
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """获取所有会话列表"""
    try:
        sessions = []
        for session_id, history in conversation_histories.items():
            if len(history) > 0:  # 只返回有历史记录的会话
                metadata = session_metadata.get(session_id, {
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
        
        # 按更新时间倒序排列
        sessions.sort(key=lambda x: x['updated_at'], reverse=True)
        
        return jsonify({
            'sessions': sessions
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/config', methods=['GET'])
def get_config():
    """获取配置信息"""
    try:
        return jsonify({
            'provider': config.provider.value,
            'model_name': config.model_name,
            'temperature': config.temperature,
            'max_tokens': config.max_tokens
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== 验证码相关API ====================

@app.route('/api/verify-code', methods=['POST'])
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
            # 验证成功，增加用户使用次数
            user_id = get_user_id_from_cookie()
            increase_user_usage_count(user_id, count=1)
            remaining = get_user_usage_count(user_id)
            print(f"[验证码API] 用户 {user_id} 兑换后剩余次数: {remaining}")
            
            response = jsonify({
                'success': True,
                'message': message,
                'remaining_uses': remaining
            })
            response.set_cookie('user_id', user_id, max_age=365*24*60*60)  # 1年
            # 禁用缓存
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        else:
            return jsonify({'error': message}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pdf/status/<path:filename>', methods=['GET'])
def get_pdf_status(filename):
    """获取PDF转换状态"""
    try:
        # URL解码文件名
        filename = unquote(filename)
        if filename in pdf_conversion_status:
            status = pdf_conversion_status[filename].copy()
            return jsonify(status)
        else:
            return jsonify({
                'status': 'not_found',
                'progress': 0,
                'message': '未找到转换任务'
            }), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/usage', methods=['GET'])
def get_user_usage():
    """获取用户剩余使用次数"""
    try:
        user_id = get_user_id_from_cookie()
        usage_count = get_user_usage_count(user_id)
        
        # 添加调试日志
        print(f"[使用次数API] 用户ID: {user_id}, 剩余次数: {usage_count}")
        
        response = jsonify({
            'remaining_uses': usage_count,
            'user_id': user_id  # 用于调试
        })
        response.set_cookie('user_id', user_id, max_age=365*24*60*60)  # 1年
        # 禁用缓存
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        import traceback
        print(f"[使用次数API] 错误: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


# ==================== 管理员相关API ====================

@app.route('/admin')
def admin_login_page():
    """管理员登录页面"""
    return render_template('admin_login.html')


@app.route('/admin/dashboard')
def admin_dashboard():
    """管理员后台页面"""
    return render_template('admin_dashboard.html')


@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """管理员登录"""
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        # 验证用户名和密码
        if username == app.config['ADMIN_USERNAME'] and password == app.config['ADMIN_PASSWORD']:
            # 生成管理员token
            admin_token = secrets.token_urlsafe(32)
            admin_sessions[admin_token] = {
                'username': username,
                'login_time': datetime.now().isoformat()
            }
            
            response = jsonify({'success': True, 'message': '登录成功'})
            response.set_cookie('admin_token', admin_token, max_age=24*60*60)  # 24小时
            return response
        else:
            return jsonify({'error': '用户名或密码错误'}), 401
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    """管理员登出"""
    try:
        admin_token = request.cookies.get('admin_token')
        if admin_token and admin_token in admin_sessions:
            del admin_sessions[admin_token]
        
        response = jsonify({'success': True, 'message': '已登出'})
        response.set_cookie('admin_token', '', expires=0)
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/check', methods=['GET'])
def admin_check():
    """检查管理员登录状态"""
    try:
        admin_token = request.cookies.get('admin_token')
        if admin_token and admin_token in admin_sessions:
            return jsonify({'logged_in': True})
        else:
            return jsonify({'logged_in': False}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/codes', methods=['GET'])
@require_admin_login
def admin_get_codes():
    """获取所有验证码列表"""
    try:
        codes = code_manager.get_all_codes()
        statistics = code_manager.get_statistics()
        
        # 转换为列表格式，方便前端显示
        codes_list = [{'code': code, 'uses': uses} for code, uses in codes.items()]
        
        # 按验证码排序
        codes_list.sort(key=lambda x: x['code'])
        
        return jsonify({
            'codes': codes_list,
            'statistics': statistics
        })
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/api/admin/codes/generate', methods=['POST'])
@require_admin_login
def admin_generate_codes():
    """生成验证码"""
    try:
        data = request.json
        count = int(data.get('count', 1))
        uses = int(data.get('uses', 1))
        
        if count < 1 or count > 100:
            return jsonify({'error': '生成数量必须在1-100之间'}), 400
        
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
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/codes/update', methods=['POST'])
@require_admin_login
def admin_update_code():
    """更新验证码使用次数"""
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
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/codes/delete', methods=['POST'])
@require_admin_login
def admin_delete_code():
    """删除验证码"""
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
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/statistics', methods=['GET'])
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
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/api/download/report/<path:filename>', methods=['GET'])
def download_report(filename):
    """下载生成的报告文件（支持PDF和MD格式）"""
    try:
        # 解码URL编码的文件名
        filename = unquote(filename)
        
        # 安全检查：只允许下载reports目录下的文件
        reports_dir = 'reports'
        
        # 移除路径分隔符，防止路径遍历攻击
        filename = os.path.basename(filename)
        
        # 检查文件扩展名
        file_ext = os.path.splitext(filename)[1].lower()
        
        # 清理文件名中的HTML标签（防止解析错误）
        filename = filename.replace('<em>', '').replace('</em>', '').replace('<strong>', '').replace('</strong>', '').replace('<', '').replace('>', '').strip()
        
        # 构建文件路径
        filepath = os.path.join(reports_dir, filename)
        
        # 检查文件是否存在
        if not os.path.exists(filepath):
            # 返回友好的错误信息，提示用户使用客户端PDF生成
            error_msg = f'服务器上的文件不存在: {filename}。\n\n💡 提示：请使用页面上的"导出报告"按钮，系统会在浏览器中直接生成PDF文件，无需从服务器下载。'
            return jsonify({'error': error_msg}), 404
        
        # 检查文件路径是否在reports目录内（防止路径遍历攻击）
        abs_reports_dir = os.path.abspath(reports_dir)
        abs_filepath = os.path.abspath(filepath)
        if not abs_filepath.startswith(abs_reports_dir):
            return jsonify({'error': '非法文件路径'}), 403
        
        # 根据文件类型设置MIME类型
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
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


if __name__ == '__main__':
    # 确保reports目录存在
    os.makedirs('reports', exist_ok=True)
    
    # 从环境变量或命令行参数获取端口
    import sys
    port = 5001
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
    
    print("=" * 50)
    print("智能体Web服务已启动")
    print("=" * 50)
    print(f"访问地址: http://0.0.0.0:{port}")
    print(f"本地访问: http://localhost:{port}")
    print("按 Ctrl+C 停止服务")
    print("-" * 50)
    app.run(debug=debug, host='0.0.0.0', port=port, threaded=True)

