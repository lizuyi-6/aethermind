"""
智能体主程序
支持通过API调用大模型，对用户的自然语言做出回复
"""

import os
import sys
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from config import Config, ModelProvider
from openai import OpenAI
import anthropic
from file_processor import FileProcessor
import json
import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

# 加载.env文件
load_dotenv()


class IntelligentAgent:
    """智能体类，负责处理用户输入并调用大模型API"""
    
    def __init__(self, config: Config):
        """
        初始化智能体
        
        Args:
            config: 配置对象，包含API密钥和模型信息
        """
        self.config = config
        self.client = None
        self.file_processor = FileProcessor()
        self.report_template = None
        self.last_usage = None  # 存储最后一次API调用的token使用信息
        self._last_finish_reason = None  # 存储最后一次API调用的finish_reason
        self._continuation_fail_count = 0  # 续写失败计数
        self._empty_content_count = 0  # 空内容计数
        self._continuation_usage = None  # 续写token使用信息
        self._initialize_client()
        self._load_report_template()
    
    def _initialize_client(self):
        """根据配置初始化API客户端"""
        # 设置超时参数（秒）
        timeout = 3600.0  # 60分钟超时（无限制）
        
        if self.config.provider == ModelProvider.OPENAI:
            api_key = os.getenv('OPENAI_API_KEY') or self.config.api_key
            base_url = self.config.base_url or "https://api.openai.com/v1"
            self.client = OpenAI(
                api_key=api_key, 
                base_url=base_url,
                timeout=timeout,
                max_retries=2
            )
        elif self.config.provider == ModelProvider.TONGYI:
            # 通义千问使用OpenAI兼容的SDK
            api_key = os.getenv('DASHSCOPE_API_KEY') or self.config.api_key
            base_url = self.config.base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
            self.client = OpenAI(
                api_key=api_key, 
                base_url=base_url,
                timeout=timeout,
                max_retries=2
            )
        elif self.config.provider == ModelProvider.ANTHROPIC:
            api_key = os.getenv('ANTHROPIC_API_KEY') or self.config.api_key
            base_url = self.config.base_url
            # 如果没设 base_url，Anthropic 官方库默认会连 api.anthropic.com
            kwargs = {"api_key": api_key, "max_retries": 2}
            if base_url:
                kwargs["base_url"] = base_url
            self.client = anthropic.Anthropic(**kwargs)
            print(f"[信息] Anthropic 客户端已初始化: {base_url or '默认官方地址'}", flush=True)
            
        elif self.config.provider == ModelProvider.CUSTOM:
            api_key = os.getenv('CUSTOM_API_KEY') or self.config.api_key
            base_url = self.config.base_url
            if not base_url:
                raise ValueError("自定义模型必须提供base_url")
            
            # 如果API在同一台服务器上，优先使用localhost
            # 检查base_url是否包含服务器IP，如果是则尝试localhost
            if '60.10.230.156' in base_url:
                # 尝试使用localhost（如果API在同一台服务器上）
                localhost_url = base_url.replace('60.10.230.156', 'localhost')
                print(f"[信息] 检测到API在同一服务器，尝试使用localhost: {localhost_url}", flush=True)
                # 优先使用localhost
                base_url = localhost_url
            
            self.client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout,
                max_retries=2
            )
            print(f"[信息] API客户端已初始化: {base_url}", flush=True)
        else:
            raise ValueError(f"不支持的模型提供商: {self.config.provider}")
        
        # 测试连接
        self._test_connection()
    
    def _test_connection(self):
        """测试API连接（不实际调用，只验证配置）"""
        try:

            print(f"[信息] API配置: provider={self.config.provider.value}, base_url={self.config.base_url}, model={self.config.model_name}", flush=True)
            if not self.config.base_url:
                print("[警告] API base_url 未设置", flush=True)
        except Exception as e:
            print(f"[警告] 连接测试失败: {e}", flush=True)
    
    def _load_report_template(self):
        """加载可行性研究报告模板"""
        template_file = "可行性研究报告模板.md"
        if os.path.exists(template_file):
            try:

                with open(template_file, 'r', encoding='utf-8') as f:
                    self.report_template = f.read()
            except Exception as e:
                print(f"警告: 加载报告模板失败: {e}")
                self.report_template = None
        else:
            self.report_template = None
    
    def _is_report_request(self, user_input: str) -> bool:
        """
        检测用户输入是否涉及撰写报告（可行性研究报告或商业计划书）

        Args:
            user_input: 用户输入文本

        Returns:
            如果是报告撰写请求，返回True
        """
        keywords = [
            '可行性研究报告', '可行性报告', '撰写报告', '写报告',
            '编制报告', '编写报告', '生成报告', '制作报告',
            '项目可行性', '可行性分析报告',
            '商业计划书', '创业计划书', '项目计划书', '项目计划'
        ]
        user_input_lower = user_input.lower()
        return any(keyword in user_input_lower for keyword in keywords)

    def _get_report_type(self, user_input: str) -> str:
        """
        检测报告类型（可行性研究报告或商业计划书）

        Args:
            user_input: 用户输入文本

        Returns:
            'feasibility' (可行性研究报告) 或 'business' (商业计划书)
        """
        if '商业计划书' in user_input or '创业计划书' in user_input:
            return 'business'
        return 'feasibility'  # 默认为可行性研究报告

    def _get_report_type_from_content(self, content: str) -> str:
        """
        从报告内容或已存储的类型中检测报告类型

        Args:
            content: 报告内容

        Returns:
            'feasibility' (可行性研究报告) 或 'business' (商业计划书)
        """
        # 优先使用已存储的报告类型（从用户输入中检测的）
        stored_type = getattr(self, '_current_report_type', None)
        if stored_type:
            print(f'[DEBUG] 使用已存储的报告类型: {stored_type}')
            return stored_type

        # 如果没有存储的类型，从内容中推断（向后兼容）
        print('[DEBUG] 未找到已存储的报告类型，从内容中推断')

        # 优先检查用户输入提示词（通常在开头）
        if '商业计划书' in content[:500] or '创业计划书' in content[:500]:
            print('[DEBUG] 检测到商业计划书（前500字符）')
            return 'business'

        # 检查是否包含商业计划书的关键词
        business_keywords = ['商业计划书', '创业计划书', '执行摘要', '商业模式', '融资需求', '投资回报']
        feasibility_keywords = ['可行性研究报告', '可行性研究', '项目总论', '建设方案', '环境影响']

        business_score = sum(1 for keyword in business_keywords if keyword in content)
        feasibility_score = sum(1 for keyword in feasibility_keywords if keyword in content)

        print(f'[DEBUG] 商业计划书得分: {business_score}, 可行性研究报告得分: {feasibility_score}')

        if business_score > feasibility_score:
            print('[DEBUG] 判定为商业计划书')
            return 'business'
        print('[DEBUG] 判定为可行性研究报告')
        return 'feasibility'
    
    def _extract_project_name(self, user_input: str, report_content: str = "") -> str:
        """
        从用户输入或报告内容中提取项目名称
        
        Args:
            user_input: 用户输入文本
            report_content: 报告内容（可选）
            
        Returns:
            项目名称
        """
        # 尝试从用户输入中提取项目名称
        patterns = [
            r'关于(.+?)的可行性研究报告',
            r'(.+?)项目的可行性研究报告',
            r'(.+?)可行性研究报告',
            r'项目名称[：:]\s*(.+?)(?:\n|$|，|。|,|\.)',
            r'项目[：:]\s*(.+?)(?:\n|$|，|。|,|\.)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, user_input)
            if match:
                name = match.group(1).strip()
                if name and len(name) < 50:  # 限制长度
                    return name
        
        # 尝试从报告内容中提取项目名称
        if report_content:
            title_match = re.search(r'《(.+?)可行性研究报告》', report_content)
            if title_match:
                return title_match.group(1).strip()
            
            name_match = re.search(r'项目名称[：:]\s*(.+?)(?:\n|$|，|。|,|\.)', report_content)
            if name_match:
                return name_match.group(1).strip()
        
        # 如果无法提取，使用默认名称
        return "项目"
    
    def _is_content_truncated(self, content: str, finish_reason: str = None, is_report: bool = False) -> bool:
        """
        检测内容是否被截断
        
        Args:
            content: 生成的内容
            finish_reason: API返回的finish_reason
            is_report: 是否是报告请求
            
        Returns:
            如果内容被截断返回True
        """
        # 检查是否包含报告完成的总结语句
        completion_markers = [
            "【报告已完成】",  # 新的完成标记（优先级最高）
            "综上所述", "建议尽快批准实施", "建议批准实施", "建议尽快实施", "字数已达到", "总字数已达到", "已达到48", "满足48,000", "满足48000",
            "所有章节内容完整", "无任何占位符", "报告撰写完成", "全文完成",
            "以上为完整报告", "报告全文结束", "本报告共计",
            "研究报告完", "可行性研究报告完", "总字数统计:", "总行数统计:",
            "Mermaid图表数量:", "报告结束", "全文结束", "撰写完毕"
        ]
        
        # 检查未完成标记（优先级最高）
        incomplete_markers = [
            "【报告未完成，待续写】",  # 新的未完成标记
            "（待续……）", "待续", "未完待续"
        ]
        
        # 计算排除 Mermaid 图表后的文本长度
        text_length = self._get_text_length_without_mermaid(content)
        
        # 如果包含未完成标记，肯定被截断
        last_3000 = content[-3000:] if text_length > 3000 else content
        if any(marker in last_3000 for marker in incomplete_markers):
            return True
        last_3000 = content[-3000:] if text_length > 3000 else content
        # 优先检查新的完成标记
        if "【报告已完成】" in last_3000:
            # 分章节生成模式会在全部章节完成后主动写入该标记。
            # 这里直接判定完成，避免外层旧逻辑再次触发续写。
            return False
        
        # 检查其他完成标记
        if any(marker in last_3000 for marker in completion_markers):
            if text_length >= 40000:
                return False
        
        # 检查API的finish_reason
        if finish_reason == "length":
            return True
        
        # 对于报告，检查是否包含所有必需的章节
        if is_report:
            # 报告要求至少4.8-5万字，所以必须更严格地检查
            # 如果finish_reason不是"length"（说明正常完成），但内容长度不足，仍需续写
            if finish_reason and finish_reason != "length":
                # 即使finish_reason不是length，如果内容少于4.5万字，仍需续写
                if text_length < 45000:
                    return True
                # 如果内容超过4.5万字，再检查是否完整
            
            # 首先检查内容长度，如果明显不足（少于4.5万字），肯定需要续写
            if text_length < 45000:
                return True
            
            # 使用改进的章节检测方法
            missing_sections = self._get_missing_sections(content)
            
            # 如果缺少任何章节，说明被截断
            # 即使内容很长，如果缺少章节，也需要续写
            if missing_sections:
                # 如果内容超过4.5万字但仍有缺失章节，可能是格式问题，需要更宽松的判断
                if text_length > 45000:
                    # 内容很长，即使检测到缺失章节，也可能是格式不同导致的误判
                    # 检查是否至少包含一些关键章节标记
                    has_some_sections = any(marker in content for marker in [
                        "第一章", "第二章", "第三章", "第四章", "第五章",
                        "一、", "二、", "三、", "四、", "五、",
                        "结论", "建议", "研究结论"
                    ])
                    if has_some_sections:
                        # 有章节标记，可能只是格式不同，不强制续写
                        # 但如果缺少超过3个章节，还是需要续写
                        if len(missing_sections) <= 3:
                            # 即使格式不同，如果内容达到4.8万字以上，才认为可能完成
                            if text_length >= 48000:
                                return False  # 内容足够长且有章节，可能只是格式不同
                return True
            
            # 检查最后章节（根据报告类型判断）
            report_type = self._get_report_type(content)

            if report_type == 'business':
                # 商业计划书：检查第十三章或第十二章
                final_section_markers = ["第十三章", "第十三章 附录", "第十二章 风险", "第十二章 风险因素", "风险因素与应对"]
                # 商业计划书不需要检查10.1和10.2子章节
                check_subsections = False
            else:
                # 可行性研究报告：检查第十章
                final_section_markers = ["第十章", "第十章 研究结论及建议", "研究结论及建议"]
                check_subsections = True

            has_final_section = any(marker in content for marker in final_section_markers)

            if has_final_section:
                # 检查最后章节部分是否有实质性内容
                final_section_start = -1
                for marker in final_section_markers:
                    pos = content.rfind(marker)
                    if pos > final_section_start:
                        final_section_start = pos

                if final_section_start >= 0:
                    final_section = content[final_section_start:]
                    final_section_length = self._get_text_length_without_mermaid(final_section)
                    # 如果结论部分太短（少于500字符），可能未完成
                    if final_section_length < 500:
                        return True

                    # 对于可行性研究报告，检查10.1和10.2子章节
                    if check_subsections:
                        if "10.1" not in final_section or "10.2" not in final_section:
                            return True
                        # 如果第十章内容超过2000字符，且包含10.1和10.2，且最后有结束标记，认为已完成
                        if final_section_length > 2000 and "10.1" in final_section and "10.2" in final_section:
                            # 检查10.1和10.2是否有实质性内容（不只是标题）
                            section_101_text = final_section.split("10.1")[1].split("10.2")[0] if "10.2" in final_section else final_section.split("10.1")[1]
                            section_102_text = final_section.split("10.2")[1] if "10.2" in final_section else ""
                            has_substantial_101 = "10.1" in final_section and self._get_text_length_without_mermaid(section_101_text) > 500
                            has_substantial_102 = "10.2" in final_section and self._get_text_length_without_mermaid(section_102_text) > 1000

                            if has_substantial_101 and has_substantial_102:
                                # 检查是否有明确的结束标记（放宽条件，只要有句号等标点即可）
                                if any(end_marker in final_section[-300:] for end_marker in ['附件', '附录', '---', '**附件**', '。', '.', '！', '!']):
                                    # 如果最后部分包含"目录"，可能是重复生成，需要继续
                                    if "目录" in final_section[-1000:]:
                                        return True
                                    # 检查总长度是否足够（至少4.8万字，这是硬性要求）
                                    if text_length >= 48000:
                                        # 内容达到要求，认为已完成
                                        return False
                                    else:
                                        # 内容长度不足，继续
                                        return True
            else:
                # 没有最后章节，肯定被截断
                return True
        
        # 对于非报告内容，只在finish_reason明确为length时才认为被截断
        # 避免误判导致循环生成
        if not is_report:
            # 如果finish_reason明确为length，肯定被截断
            if finish_reason == "length":
                return True
            # 否则，对于非报告内容，不自动判断为截断（避免循环）
            return False
        
        # 对于报告内容，检查是否以不完整的句子结束（简单启发式）
        # 但这个检查只在没有明确的finish_reason时使用
        if content and text_length > 1000 and not finish_reason:
            last_500 = content[-500:]
            # 如果最后500字符中没有句号、问号、感叹号，可能被截断
            if not any(punct in last_500 for punct in ['。', '.', '！', '!', '？', '?', '\n\n']):
                return True
        
        return False
    
    def _get_text_length_without_mermaid(self, content: str) -> int:
        """
        计算文本长度，排除 Mermaid 代码块
        
        Args:
            content: 报告内容
            
        Returns:
            排除 Mermaid 代码块后的文本长度
        """
        if not content:
            return 0
        
        # 使用正则表达式匹配所有 Mermaid 代码块
        # 匹配 ```mermaid ... ``` 或 ``` mermaid ... ```
        import re
        pattern = r'```\s*mermaid\s*[\s\S]*?```'
        content_without_mermaid = re.sub(pattern, '', content)
        
        return len(content_without_mermaid)
    
    def _validate_mermaid_syntax(self, mermaid_code: str) -> Tuple[bool, str]:
        """
        验证Mermaid图表语法是否正确
        
        Args:
            mermaid_code: Mermaid代码字符串
            
        Returns:
            (is_valid, error_message): 是否有效和错误信息
        """
        if not mermaid_code or not mermaid_code.strip():
            return False, "Mermaid代码为空"
        
        code = mermaid_code.strip()
        
        # 基本语法检查
        valid_chart_types = [
            'xychart-beta', 'pie', 'flowchart', 'graph', 'gantt', 
            'sequenceDiagram', 'classDiagram', 'stateDiagram', 'erDiagram',
            'gitgraph', 'journey', 'requirement', 'quadrantChart', 'mindmap',
            'timeline', 'C4Context', 'C4Container', 'C4Component'
        ]
        
        # 检查是否包含有效的图表类型
        has_valid_type = any(chart_type in code for chart_type in valid_chart_types)
        
        if not has_valid_type:
            # 检查是否是简单的流程图语法
            if not (code.startswith('graph') or code.startswith('flowchart') or 
                   code.startswith('pie') or 'xychart' in code):
                return False, "未找到有效的Mermaid图表类型"
        
        # 检查基本语法结构
        if 'xychart-beta' in code:
            # 检查xychart语法
            if 'title' not in code and '"' not in code:
                return False, "xychart缺少title或数据"
            if 'x-axis' not in code:
                return False, "xychart缺少x-axis定义"
            if 'y-axis' not in code:
                return False, "xychart缺少y-axis定义"
            if 'bar' not in code and 'line' not in code and 'area' not in code and 'scatter' not in code:
                return False, "xychart缺少图表类型（bar/line/area/scatter）"
        
        elif 'pie' in code:
            # 检查pie语法
            if 'title' not in code:
                return False, "pie图表缺少title"
            if ':' not in code:
                return False, "pie图表缺少数据定义（使用:分隔标签和数值）"
        
        elif 'flowchart' in code or code.startswith('graph'):
            # 检查流程图语法
            if '-->' not in code and '---' not in code and '->' not in code:
                return False, "流程图缺少连接符（-->或---）"
        
        # 检查是否有未闭合的括号或引号
        if code.count('(') != code.count(')'):
            return False, "括号未闭合"
        if code.count('[') != code.count(']'):
            return False, "方括号未闭合"
        if code.count('{') != code.count('}'):
            return False, "花括号未闭合"

        # 新增：实际渲染验证（使用mermaid.ink API）
        try:
            import base64
            import urllib.request

            encoded_code = base64.urlsafe_b64encode(code.encode('utf-8')).decode('utf-8')
            verify_url = f'https://mermaid.ink/img/{encoded_code}'

            # 使用HEAD请求验证（不下载完整图片，节省带宽）
            req = urllib.request.Request(verify_url, method='HEAD')
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    print("[Mermaid] 渲染验证通过")
                    return True, ""
                return False, f"渲染服务错误: HTTP {response.status}"

        except urllib.error.HTTPError as e:
            return False, f"图表语法错误: HTTP {e.code}"
        except Exception as e:
            # 网络超时不阻塞生成流程
            print(f"[Mermaid] 渲染验证超时或失败，跳过: {e}")
            return True, ""
    
    # ---- Mermaid sanitizer ----

    _VALID_MERMAID_TYPES = frozenset([
        'xychart-beta', 'pie', 'flowchart', 'graph', 'gantt',
        'sequencediagram', 'classdiagram', 'statediagram', 'erdiagram',
        'gitgraph', 'journey', 'quadrantchart', 'mindmap', 'timeline',
        'c4context', 'c4container', 'c4component', 'requirementdiagram',
        '%%{init',
    ])

    def _sanitize_mermaid_code(self, code: str) -> str:
        """Fix common LLM-generated Mermaid syntax errors before rendering/saving."""
        if not code or not code.strip():
            return code
        lines = code.strip().split('\n')
        first_line = lines[0].strip()
        first_token = first_line.lower().split()[0] if first_line.split() else ''
        # If chart type is not recognised by Mermaid, replace with a simple flowchart note
        is_valid = any(first_token.startswith(t) for t in self._VALID_MERMAID_TYPES)
        if not is_valid and first_token:
            label = first_line.replace('"', "'")
            return f'flowchart LR\n    A["{label}（图表类型不支持直接渲染）"]'
        # Fix xychart-beta issues
        if first_token == 'xychart-beta':
            fixed = []
            for line in lines:
                stripped = line.strip().lower()
                # Auto-quote unquoted x-axis string labels: x-axis [a, b, c] → x-axis ["a", "b", "c"]
                if stripped.startswith('x-axis') and '[' in line and '"' not in line:
                    def _quote_vals(m):
                        parts = [v.strip() for v in m.group(1).split(',')]
                        quoted = ', '.join(
                            p if re.match(r'^[\d.]+$', p) else f'"{p}"'
                            for p in parts
                        )
                        return f'[{quoted}]'
                    line = re.sub(r'\[([^\]]+)\]', _quote_vals, line)
                # Replace unsupported series types: scatter→line, area→bar
                if re.match(r'^\s*scatter\s', line):
                    line = re.sub(r'scatter', 'line', line, count=1)
                elif re.match(r'^\s*area\s', line):
                    line = re.sub(r'area', 'bar', line, count=1)
                fixed.append(line)
            return '\n'.join(fixed)
        return code

    def _sanitize_mermaid_blocks(self, content: str) -> str:
        """Apply _sanitize_mermaid_code to every mermaid code block in a markdown string."""
        def _fix_block(m):
            fixed = self._sanitize_mermaid_code(m.group(1).strip())
            return f'```mermaid\n{fixed}\n```'
        return re.sub(r'```mermaid\s*\n([\s\S]*?)\n```', _fix_block, content)

    # ---- end Mermaid sanitizer ----

    def _is_chapter_10_complete(self, content: str) -> Tuple[bool, str]:
        """
        检查最后一章是否完整（根据报告类型检查不同章节）
        - 可行性研究报告：检查"第十章 结论与建议"
        - 商业计划书：检查"第十三章 附录"或"第十二章 风险因素与应对"

        Args:
            content: 报告内容

        Returns:
            (是否完整, 最后一章内容)
        """
        # 【重要】如果存在占位符，说明报告明显未完成，不应该认为最后一章完成
        has_placeholder = any(placeholder in content for placeholder in [
            "（因篇幅限制", "后续章节继续展开", "待续", "待补充", "详见下文",
            "（待续……）", "未完待续", "精简示例", "此处为精简", "因篇幅限制"
        ])
        if has_placeholder:
            return False, ""

        # 检测报告类型
        report_type = self._get_report_type_from_content(content)

        # 根据报告类型设置不同的最后一章检测模式
        if report_type == 'business':
            # 商业计划书：检查"第十三章 附录"或"第十二章 风险因素与应对"
            final_ch_patterns = ["\n第十三章", "\r\n第十三章", "## 第十三章", "# 第十三章", "第十三章 ", "第十三章　", "第十三章：", "第十三章:", "第十三章 附录"]
            alt_final_ch_patterns = ["\n第十二章", "\r\n第十二章", "## 第十二章", "# 第十二章", "第十二章 ", "第十二章　", "第十二章：", "第十二章:", "第十二章 风险"]
        else:
            # 可行性研究报告：检查"第十章 结论与建议"
            final_ch_patterns = ["\n第十章", "\r\n第十章", "## 第十章", "# 第十章", "第十章 ", "第十章　", "第十章：", "第十章:", "第十章 研究结论", "第十章 研究结论及建议"]
            alt_final_ch_patterns = []

        final_ch_found = False
        final_ch_start = -1
        final_ch_name = ""

        # 先尝试查找主要的最后一章
        for pattern in final_ch_patterns:
            pos = content.rfind(pattern)
            if pos >= 0:
                # 检查前面是否是换行符或章节标记，确保是真正的章节标题
                before_text = content[max(0, pos-30):pos]
                if any(marker in before_text for marker in ['\n', '\r', '##', '#', '第', '章', '目录', '目 录']):
                    after_text = content[pos:pos+50]
                    if any(marker in after_text for marker in ['附录', '风险', '结论', '建议', ' ', '　', '：', ':', '\n']):
                        final_ch_found = True
                        final_ch_start = pos + (1 if pattern.startswith('\n') or pattern.startswith('\r') else 0)
                        final_ch_name = "最后一章"
                        break

        # 如果没找到主要最后一章，尝试找备选的最后一章（仅限商业计划书）
        if not final_ch_found and alt_final_ch_patterns:
            for pattern in alt_final_ch_patterns:
                pos = content.rfind(pattern)
                if pos >= 0:
                    before_text = content[max(0, pos-30):pos]
                    if any(marker in before_text for marker in ['\n', '\r', '##', '#', '第', '章']):
                        after_text = content[pos:pos+50]
                        if any(marker in after_text for marker in ['风险', '因素', '应对', ' ', '　', '：', ':', '\n']):
                            final_ch_found = True
                            final_ch_start = pos + (1 if pattern.startswith('\n') or pattern.startswith('\r') else 0)
                            final_ch_name = "最后一章"
                            break

        if not final_ch_found or final_ch_start < 0:
            return False, ""

        final_ch_content = content[final_ch_start:]
        final_ch_text_length = self._get_text_length_without_mermaid(final_ch_content)

        # 如果最后一章内容少于2000字符，认为不完整
        if final_ch_text_length < 2000:
            return False, final_ch_content

        # 对于可行性研究报告，检查10.1和10.2子章节
        if report_type == 'feasibility':
            # 【重要】必须确保10.1和10.2是在第十章内容中，且是子章节标题格式
            has_101 = False
            has_102 = False

            for pattern in ["\n10.1", "\r\n10.1", " 10.1", "　10.1", "10.1 ", "10.1　", "10.1：", "10.1:"]:
                pos_101 = final_ch_content.find(pattern)
                if pos_101 >= 0:
                    before_101 = final_ch_content[max(0, pos_101-10):pos_101]
                    if any(marker in before_101 for marker in ['\n', '\r', ' ', '　', '##', '#']):
                        has_101 = True
                        break

            for pattern in ["\n10.2", "\r\n10.2", " 10.2", "　10.2", "10.2 ", "10.2　", "10.2：", "10.2:"]:
                pos_102 = final_ch_content.find(pattern)
                if pos_102 >= 0:
                    before_102 = final_ch_content[max(0, pos_102-10):pos_102]
                    if any(marker in before_102 for marker in ['\n', '\r', ' ', '　', '##', '#']):
                        has_102 = True
                        break

            if has_101 and has_102:
                try:
                    section_101 = final_ch_content.split("10.1")[1].split("10.2")[0] if "10.2" in final_ch_content else final_ch_content.split("10.1")[1]
                    section_102 = final_ch_content.split("10.2")[1] if "10.2" in final_ch_content else ""
                    section_101_length = self._get_text_length_without_mermaid(section_101.strip())
                    section_102_length = self._get_text_length_without_mermaid(section_102.strip())
                    if section_101_length > 500 and section_102_length > 1000:
                        return True, final_ch_content
                except:
                    pass

            if final_ch_text_length > 2000 and has_101 and has_102:
                return True, final_ch_content

            return False, final_ch_content
        else:
            # 对于商业计划书，只要最后一章有足够内容就认为完成
            return True, final_ch_content
    
    def _get_missing_sections(self, content: str) -> list:
        """
        获取缺失的章节列表（改进版：支持多种章节格式）
        
        Args:
            content: 报告内容
            
        Returns:
            缺失的章节列表
        """
        # 定义章节的多种可能格式
        required_sections = [
            {
                'name': '第一章',
                'patterns': [
                    "第一章", "第一章 概述", "第一章 项目概述", 
                    "一、", "一、项目概述", "一、概述",
                    "1.", "1. 项目概述", "1. 概述"
                ],
                'keywords': ['项目概述', '概述', '项目基本信息']
            },
            {
                'name': '第二章',
                'patterns': [
                    "第二章", "第二章 项目建设背景及必要性", 
                    "二、", "二、背景", "二、项目建设背景",
                    "2.", "2. 背景", "2. 项目建设背景"
                ],
                'keywords': ['背景', '必要性', '建设背景']
            },
            {
                'name': '第三章',
                'patterns': [
                    "第三章", "第三章 项目需求分析与产出方案",
                    "三、", "三、需求", "三、项目需求",
                    "3.", "3. 需求", "3. 项目需求"
                ],
                'keywords': ['需求分析', '产出方案', '需求']
            },
            {
                'name': '第四章',
                'patterns': [
                    "第四章", "第四章 项目选址与要素保障",
                    "四、", "四、选址", "四、项目选址",
                    "4.", "4. 选址", "4. 项目选址"
                ],
                'keywords': ['选址', '要素保障', '选址与要素']
            },
            {
                'name': '第五章',
                'patterns': [
                    "第五章", "第五章 项目建设方案",
                    "五、", "五、建设方案", "五、项目建设方案",
                    "5.", "5. 建设方案", "5. 项目建设方案"
                ],
                'keywords': ['建设方案', '项目建设方案', '建设']
            },
            {
                'name': '第六章',
                'patterns': [
                    "第六章", "第六章 项目运营方案",
                    "六、", "六、运营", "六、项目运营",
                    "6.", "6. 运营", "6. 项目运营"
                ],
                'keywords': ['运营方案', '项目运营', '运营']
            },
            {
                'name': '第七章',
                'patterns': [
                    "第七章", "第七章 项目投融资与财务方案",
                    "七、", "七、财务", "七、投融资",
                    "7.", "7. 财务", "7. 投融资"
                ],
                'keywords': ['财务', '投融资', '财务方案', '投资']
            },
            {
                'name': '第八章',
                'patterns': [
                    "第八章", "第八章 项目影响效果分析",
                    "八、", "八、影响", "八、效果分析",
                    "8.", "8. 影响", "8. 效果分析"
                ],
                'keywords': ['影响效果', '效果分析', '影响', '效益']
            },
            {
                'name': '第九章',
                'patterns': [
                    "第九章", "第九章 项目风险管控方案",
                    "九、", "九、风险", "九、项目风险",
                    "9.", "9. 风险", "9. 项目风险"
                ],
                'keywords': ['风险', '风险管控', '项目风险', '风险分析']
            },
            {
                'name': '第十章',
                'patterns': [
                    "第十章", "第十章 研究结论及建议",
                    "十、", "十、结论", "十、研究结论",
                    "10.", "10. 结论", "10. 研究结论"
                ],
                'keywords': ['结论', '研究结论', '建议', '结论及建议']
            }
        ]
        
        missing = []
        for section in required_sections:
            # 检查是否匹配任何模式
            found_pattern = any(pattern in content for pattern in section['patterns'])
            
            # 如果模式没找到，检查关键词（更宽松的匹配）
            if not found_pattern:
                found_keyword = any(keyword in content for keyword in section['keywords'])
                if not found_keyword:
                    missing.append(section['name'])
        
        return missing

    def _get_report_body_start(self, content: str) -> int:
        """Best-effort body start locator to reduce TOC interference."""
        if not content:
            return 0
        text = str(content).replace('\r\n', '\n')
        m = re.search(r'(?m)^\s*(?:#{1,4}\s*)?(?:第[一二三四五六七八九十\d]+章|[1-9]|10[\.、\s]).*$', text)
        return m.start() if m else 0

    def _slice_report_body(self, content: str) -> str:
        if not content:
            return ""
        start = self._get_report_body_start(content)
        return str(content)[start:]

    def _has_chapter_10_heading(self, content: str) -> bool:
        if not content:
            return False
        body = self._slice_report_body(content)
        for raw_line in str(body).replace('\r\n', '\n').split('\n'):
            line = raw_line.strip().lstrip('#').strip()
            if line.startswith('第十章') or line.startswith('第10章'):
                return True
            if line.startswith('10.') or line.startswith('10、') or line.startswith('10 '):
                return True
        return False

    def validate_report_completeness(self, report_content: str, min_body_chars: int = 12000) -> Dict[str, Any]:
        """Validate report completeness before saving/downloading."""
        text = str(report_content or '')
        body = self._slice_report_body(text)
        body_char_count = self._get_text_length_without_mermaid(body)
        missing_sections = self._get_missing_sections(text)
        chapter10_complete, _ = self._is_chapter_10_complete(text)
        is_complete = bool(len(missing_sections) == 0 and chapter10_complete and body_char_count >= int(min_body_chars))
        return {
            'is_complete': is_complete,
            'missing_sections': missing_sections,
            'chapter10_complete': bool(chapter10_complete),
            'body_char_count': int(body_char_count),
        }

    def _postprocess_report_output(self, report_content: str) -> str:
        """
        报告收尾后处理（轻量兜底实现）。
        """
        text = str(report_content or "")
        if not text:
            return ""

        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # 清理占位符
        for marker in ("（待续……）", "待续", "待补充", "因篇幅限制"):
            text = text.replace(marker, "")

        # 过滤AI自我指涉和免责声明
        ai_refusal_patterns = [
            r'作为+(?:AI)?(?:语言模型|人工智能|助手)[,:：]?.*?(?:\n|$)',
            r'我?(?:无法|不能|不)(?:提供|给出|确保|保证)[,:：]?.*?(?:\n|$)',
            r'请注意[,:：].*?(?:\n|$)',
            r'(?:建议|请|应当|最好).*?咨询.*?(?:专业|律师|专家).*?(?:\n|$)',
            r'本(?:回答|内容).*?仅供参考.*?(?:\n|$)',
            r'我?(?:认为|觉得|建议)[,:：]?.*?(?:\n|$)',
            r'作为AI.*?(?:\n|$)',
            r'请注意.*?(?:\n|$)',
            r'需要.*?注意.*?(?:\n|$)',
        ]

        for pattern in ai_refusal_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)

        # 清理多余空行（超过2个连续换行符替换为2个）
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    def _expand_pre_final_sections(self, report_content: str, user_input: str = "") -> str:
        """
        结论前章节回填（当前为兼容兜底：不修改原文）。
        """
        return str(report_content or "")

    def _expand_underdeveloped_sections(self, report_content: str, user_input: str = "") -> str:
        """
        过短章节补写（当前为兼容兜底：不修改原文）。
        """
        return str(report_content or "")
    
    def _continue_writing(self, existing_content: str, user_input: str, conversation_history: Optional[list] = None, max_continuations: int = 20) -> str:
        """
        续写被截断的内容，持续续写直到报告完整
        
        Args:
            existing_content: 已生成的内容
            user_input: 原始用户输入（可能包含文件内容）
            conversation_history: 对话历史
            max_continuations: 最大续写次数（增加到20次，确保完整）
            
        Returns:
            续写后的完整内容
        """
        full_content = existing_content
        continuation_count = 0
        # Defensive init: avoid UnboundLocalError in legacy continuation branches.
        repeated_ch10_hits = 0
        
        # 提取原始用户输入中的文件内容（如果有）
        file_context = ""
        if "【文件内容】" in user_input:
            # 提取文件内容部分
            file_start = user_input.find("【文件内容】")
            if file_start >= 0:
                file_context = user_input[file_start:file_start+5000]  # 保留前5000字符的文件内容作为上下文
        
        while continuation_count < max_continuations:
            # 【修复】硬性超时检测
            if not hasattr(self, '_stream_start_time'):
                self._stream_start_time = time.time()
            elif time.time() - self._stream_start_time > 1800:
                print(f' [硬性超时] 强制终止', flush=True)
                yield '[硬性超时] 强制终止'
                break
            
            # 【修复】先检查是否有占位符，如果有占位符，说明报告明显未完成，不应该因为第十章检测而停止
            has_placeholder = any(placeholder in full_content for placeholder in [
                "（因篇幅限制", "后续章节继续展开", "待续", "待补充", "详见下文",
                "（待续……）", "未完待续", "精简示例", "此处为精简", "因篇幅限制"
            ])
            
            # 【修复】强制终止条件：如果第十章已存在且有实质内容，立即停止（在续写开始前检查）
            # 但如果存在占位符，说明报告明显未完成，应该继续续写
            if not has_placeholder:
                is_ch10_complete, ch10_content = self._is_chapter_10_complete(full_content)
                if is_ch10_complete:
                    ch10_text_length = self._get_text_length_without_mermaid(ch10_content)
                    yield f"\n[强制终止] 第十章已完成({ch10_text_length}字符，已排除图表)，停止续写\n"
                    break
            else:
                # 如果有占位符，输出提示信息，继续续写
                print(f" [检测到占位符，报告明显未完成，继续续写...]", flush=True)
            
            # 计算排除图表后的文本长度
            text_length = self._get_text_length_without_mermaid(full_content)
            
            # 【修复】如果续写次数超过8次，且内容已达4万字，强制停止
            if continuation_count >= 8 and text_length >= 40000:
                print(f" [强制终止] 续写次数过多({continuation_count}次)且内容已足够({text_length}字符，已排除图表)，停止续写", flush=True)
                break
            
            # 检查缺失的章节
            missing_sections = self._get_missing_sections(full_content)
            
            # 提取最后一部分作为上下文（保留最后6000字符，增加上下文以包含更多信息）
            context = full_content[-6000:] if text_length > 6000 else full_content
            
            # 构建续写提示
            missing_text = ""
            if missing_sections:
                missing_text = f"\n\n**重要：以下章节尚未完成，必须全部完成：**\n" + "\n".join(f"- {section}" for section in missing_sections)
            
            # 检查是否已经包含目录，避免重复生成
            has_cover = "封面" in full_content or "可行性研究报告" in full_content[:500]
            has_toc = "目录" in full_content or "第一章" in full_content[:2000]
            
            no_repeat_warning = ""
            if has_cover or has_toc:
                no_repeat_warning = "\n\n**⚠️ 重要警告：报告中已经包含封面和目录，请不要再重复生成封面和目录！直接继续正文内容即可。**\n"
            
            # 如果有文件内容，在续写提示中包含
            file_context_prompt = ""
            if file_context:
                file_context_prompt = f"\n\n**重要：请参考以下文件内容来完善报告：**\n{file_context}\n\n"
            
            continue_prompt = f"""请继续完成上述可行性研究报告。当前报告已生成到以下位置：

{context}
{file_context_prompt}
{missing_text}
{no_repeat_warning}

请从上述内容的末尾继续，完成报告的剩余部分。**必须确保：**

1. **完成所有缺失的章节**（如果上面列出了缺失章节，必须全部完成）
2. **⚠️ 严禁使用"（待续……）"、"待续"、"待补充"、"详见下文"等占位符，必须直接生成完整的章节内容**
3. **每个章节必须包含完整的详细内容**，不能只有标题，每个章节至少4000-5000字
4. **内容与前面部分连贯衔接**，保持逻辑连贯
5. **如果提供了文件内容，请充分参考文件内容来完善报告，确保报告内容与文件信息一致**
6. **确保报告有完整的"第十章 研究结论及建议"部分**，包含：
   - 10.1 主要研究结论（技术可行性、经济可行性、政策可行性），每个结论至少500-800字，必须详细展开，不能简略
   - 10.2 问题与建议（优先级、时间节点、具体措施、资源配置、风险控制），至少包含10-20条详细建议，每条建议至少200-300字，必须详细说明实施步骤、责任人、时间安排、所需资源、预期效果、风险控制等
7. **保持与前面部分相同的格式和风格**
8. **如果报告已经包含所有章节，请确保每个章节都完整，特别是最后章节要有明确的结束**
9. **报告总字数必须达到48000-50000字（约4.8-5万字），每个主要章节至少4000-5000字，总行数达到1700-1800行，这是硬性要求，绝对不能少于这个字数**
10. **每个子章节至少包含5-10个详细要点，每个要点至少200-400字，必须详细展开，不能简略**
11. **⚠️ 严禁只写标题不写内容，每个部分都必须详细展开，每个段落至少100-200字**
12. **⚠️ 如果某个部分内容不够详细，必须继续展开，直到达到要求的字数**
13. **⚠️ 不要因为输出限制而简化回答，请完整详细地生成所有内容，即使内容很长也要完整输出**
14. **⚠️⚠️⚠️ 极其重要：如果第十章已经存在且内容完整（包含10.1和10.2子章节，且10.1和10.2都有实质性内容：10.1超过500字符，10.2超过1000字符），请立即结束报告，不要继续优化、不要重复生成、不要添加新内容、不要重复生成目录或重新开始！如果第十章已完整，请立即停止，不要输出任何新内容！**
15. **⚠️ 如果发现报告中有"（待续……）"、"待续"等占位符，必须立即替换为完整的章节内容**
16. **⚠️ 当前报告长度：{self._get_text_length_without_mermaid(full_content)}字符（已排除图表），但如果第十章已完整（包含10.1和10.2，且10.1和10.2都有实质性内容），即使未达到目标长度也要立即结束，不要继续生成任何内容！**
17. **⚠️ 每个续写段落必须至少500-1000字，不能只有几句话，必须详细展开每个要点（但如果第十章已完整，请忽略此要求，立即停止）**
18. **⚠️⚠️⚠️ 绝对禁止：如果第十章包含10.1和10.2，且有实质性内容（10.1超过500字符，10.2超过1000字符），说明报告已完成，必须立即停止，不要再生成任何内容、不要继续优化、不要添加图表、不要添加文字、不要做任何修改！立即结束！**

**⚠️⚠️⚠️ 图表要求（续写时也必须严格遵守）⚠️⚠️⚠️：**
19. **⚠️ 绝对要求：在续写每个章节时，必须立即生成该章节要求的图表，不能只写文字！生成图表后必须检查Mermaid语法是否正确！（但如果第十章已完整，请忽略此要求，立即停止）**
20. **⚠️ 续写时，每写2-3段文字后，必须插入1-2个图表，然后再继续写文字，确保图表均匀分布在整个章节中**
21. **⚠️ 整个报告必须包含至少30-50个图表，如果当前图表数量不足，续写时必须增加更多图表**
22. **⚠️ 每个章节必须包含至少3-5个图表（第七章必须包含8-10个图表），如果某个章节图表不足，续写时必须补充**
23. **⚠️ 图表必须使用正确的Mermaid语法，每个图表都要有详细的说明文字（至少200-300字），生成后必须检查语法是否正确！**

**⚠️⚠️⚠️ 极其重要的截断标记要求（续写时必须严格遵守）⚠️⚠️⚠️：**
24. **如果续写完成（包含所有10个章节且字数达到48000字以上），必须在续写内容最后明确输出：**
   ```
   【报告已完成】
   
   总字数：[实际字符数]字符
   总行数：[实际行数]行
   包含章节：第一章至第十章（全部完成）
   图表数量：[实际图表数量]个
   ```
25. **如果续写后仍未完成，必须在续写内容最后明确输出：**
   ```
   【报告未完成，待续写】
   
   当前已完成章节：[列出已完成的章节编号]
   当前内容长度：[当前实际字符数]字符
   待续写章节：[列出待续写的章节编号]
   ```
26. **⚠️ 绝对禁止：不能在没有明确标记的情况下结束续写！必须明确标注报告状态！**

**请继续撰写，确保每个部分都详细展开，直到报告完整，达到4.8-5万字的详细要求。**⚠️⚠️⚠️ 但如果第十章已经完成（包含10.1和10.2，且10.1超过500字符，10.2超过1000字符），请立即停止，不要继续生成任何内容，明确结束报告并输出【报告已完成】标记。绝对不要使用任何占位符！当前内容长度：{self._get_text_length_without_mermaid(full_content)}字符（已排除图表），但如果第十章已完整，即使未达到48000字符也要立即停止！续写时必须包含大量图表，并确保Mermaid语法正确！续写完成后必须输出明确的完成标记！**"""
            
            continuation_count += 1
            
            # 显示续写进度（在API调用前）
            missing_sections = self._get_missing_sections(full_content)
            
            # 在API调用前，只检查是否达到最大次数，不提前停止
            # 让API调用后的检查逻辑来决定是否停止
            
            if missing_sections:
                print(f"\n[续写 {continuation_count}/{max_continuations}] 正在生成缺失章节: {', '.join(missing_sections)}...", flush=True)
            else:
                current_length = self._get_text_length_without_mermaid(full_content)
                print(f"\n[续写 {continuation_count}/{max_continuations}] 正在继续完善报告... (当前长度: {current_length}字符，已排除图表)", flush=True)
            
            try:

                messages = []
                
                # 添加系统提示词
                if self.config.system_prompt:
                    messages.append({
                        "role": "system",
                        "content": self.config.system_prompt
                    })
                
                # 添加对话历史（改进：保留包含文件内容的原始用户输入）
                if conversation_history:
                    # 查找包含文件内容的用户消息
                    file_user_msg = None
                    for msg in conversation_history:
                        if msg.get("role") == "user" and ("【文件内容】" in msg.get("content", "") or "[上传文件:" in msg.get("content", "")):
                            file_user_msg = msg
                            break
                    
                    # 保留系统提示词后的最近5条历史（增加数量以保留更多上下文）
                    recent_history = conversation_history[-5:] if len(conversation_history) > 5 else conversation_history
                    
                    # 如果找到了包含文件的消息，确保它被包含
                    if file_user_msg and file_user_msg not in recent_history:
                        # 将文件消息添加到历史中
                        messages.append(file_user_msg)
                    
                    messages.extend(recent_history)
                
                # 添加续写请求
                messages.append({
                    "role": "user",
                    "content": continue_prompt
                })
                
                # 调用API续写（添加超时处理）
                start_time = time.time()
                
                try:

                    # 调用API续写，添加超时和重试机制
                    max_retries = 3
                    retry_count = 0
                    response = None
                    
                    while retry_count < max_retries:
                        try:

                            # 续写时使用更大的max_tokens，确保能生成足够长的内容
                            continuation_max_tokens = max(self.config.max_tokens, 16000)
                            # 如果是自定义模型，进一步增加
                            if self.config.provider == ModelProvider.CUSTOM:
                                continuation_max_tokens = max(continuation_max_tokens, 20000)
                            
                            # 尝试调用API（某些SDK版本可能不支持timeout参数）
                            try:
                                if self.config.provider == ModelProvider.ANTHROPIC:
                                    # Extract system prompt for anthropic
                                    system_prompt = ""
                                    anthropic_messages = []
                                    for msg in messages:
                                        if msg.get("role") == "system":
                                            system_prompt = msg.get("content", "")
                                        else:
                                            anthropic_messages.append(msg)
                                            
                                    response = self.client.messages.create(
                                        model=self.config.model_name,
                                        system=system_prompt,
                                        messages=anthropic_messages,
                                        temperature=self.config.temperature,
                                        max_tokens=continuation_max_tokens,
                                        timeout=300.0  # 5分钟超时
                                    )
                                else:
                                    response = self.client.chat.completions.create(
                                        model=self.config.model_name,
                                        messages=messages,
                                        temperature=self.config.temperature,
                                        max_tokens=continuation_max_tokens,
                                        timeout=300.0  # 5分钟超时
                                    )
                                break  # 成功则退出重试循环
                            except TypeError:
                                # 如果SDK不支持timeout参数，不使用timeout
                                if self.config.provider == ModelProvider.ANTHROPIC:
                                    system_prompt = ""
                                    anthropic_messages = []
                                    for msg in messages:
                                        if msg.get("role") == "system":
                                            system_prompt = msg.get("content", "")
                                        else:
                                            anthropic_messages.append(msg)
                                            
                                    response = self.client.messages.create(
                                        model=self.config.model_name,
                                        system=system_prompt,
                                        messages=anthropic_messages,
                                        temperature=self.config.temperature,
                                        max_tokens=continuation_max_tokens
                                    )
                                else:
                                    response = self.client.chat.completions.create(
                                        model=self.config.model_name,
                                        messages=messages,
                                        temperature=self.config.temperature,
                                        max_tokens=continuation_max_tokens
                                    )
                                break  # 成功则退出重试循环
                        except Exception as retry_error:
                            retry_count += 1
                            if retry_count < max_retries:
                                wait_time = retry_count * 2  # 递增等待时间：2秒、4秒、6秒
                                print(f" [重试 {retry_count}/{max_retries}，等待 {wait_time}秒...]", end="", flush=True)
                                time.sleep(wait_time)
                            else:
                                raise retry_error  # 最后一次重试失败，抛出异常
                    
                except Exception as api_error:
                    elapsed = time.time() - start_time
                    error_msg = str(api_error)
                    
                    # 检查错误类型并记录失败次数
                    if not hasattr(self, '_continuation_fail_count'):
                        self._continuation_fail_count = 0
                    self._continuation_fail_count += 1
                    
                    # 检查错误类型
                    if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                        print(f"\n[错误] 续写API调用超时 (耗时 {elapsed:.1f}秒，失败次数: {self._continuation_fail_count}): {error_msg}", flush=True)
                    elif "connection" in error_msg.lower() or "network" in error_msg.lower():
                        print(f"\n[错误] 续写API网络连接失败 (耗时 {elapsed:.1f}秒，失败次数: {self._continuation_fail_count}): {error_msg}", flush=True)
                    elif "429" in error_msg or "rate limit" in error_msg.lower():
                        print(f"\n[错误] 续写API调用频率限制 (耗时 {elapsed:.1f}秒，失败次数: {self._continuation_fail_count}): {error_msg}", flush=True)
                        # 频率限制时等待更长时间
                        wait_time = min(10 + self._continuation_fail_count * 2, 30)
                        print(f"[提示] 等待 {wait_time} 秒后重试...", flush=True)
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"\n[错误] 续写API调用失败 (耗时 {elapsed:.1f}秒，失败次数: {self._continuation_fail_count}): {error_msg}", flush=True)
                        import traceback
                        print(f"[错误详情] {traceback.format_exc()[:500]}", flush=True)
                    
                    # 如果连续失败5次（增加容错），停止续写
                    if self._continuation_fail_count >= 5:
                        print(f"[错误] 连续{self._continuation_fail_count}次API调用失败，停止续写", flush=True)
                        text_length = self._get_text_length_without_mermaid(full_content)
                        print(f"[提示] 已生成内容长度: {text_length}字符（已排除图表），报告可能不完整", flush=True)
                        break
                    
                    # 等待一段时间后重试（根据失败次数增加等待时间）
                    wait_time = min(3 + self._continuation_fail_count, 10)
                    print(f"[提示] 等待 {wait_time} 秒后重试...", flush=True)
                    time.sleep(wait_time)
                    continue
                
                elapsed = time.time() - start_time
                
                # 获取响应内容（兼容多种API格式）
                continuation = None
                finish_reason = None
                
                if self.config.provider == ModelProvider.ANTHROPIC:
                    if response and hasattr(response, 'content') and len(response.content) > 0:
                        continuation = response.content[0].text
                    if response and hasattr(response, 'stop_reason'):
                        finish_reason = response.stop_reason
                else:
                    if response and hasattr(response, 'choices') and len(response.choices) > 0:
                        choice = response.choices[0]
                        if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                            continuation = choice.message.content
                        elif hasattr(choice, 'content'):
                            continuation = choice.content
                        
                        if hasattr(choice, 'finish_reason'):
                            finish_reason = choice.finish_reason
                
                # 输出API响应信息
                if continuation:
                    print(f" [API响应] 获取到内容: {len(continuation)}字符, finish_reason: {finish_reason}", flush=True)
                else:
                    print(f" [API响应] 未获取到内容, finish_reason: {finish_reason}, response类型: {type(response)}", flush=True)
                    if response:
                        print(f" [API响应详情] response对象: {str(response)[:500]}", flush=True)
                
                # 累计token使用信息
                if hasattr(response, 'usage') and response.usage:
                    if not hasattr(self, '_continuation_usage'):
                        self._continuation_usage = {
                            'prompt_tokens': 0,
                            'completion_tokens': 0,
                            'total_tokens': 0
                        }
                    self._continuation_usage['prompt_tokens'] += getattr(response.usage, 'prompt_tokens', 0)
                    self._continuation_usage['completion_tokens'] += getattr(response.usage, 'completion_tokens', 0)
                    self._continuation_usage['total_tokens'] += getattr(response.usage, 'total_tokens', 0)
                
                # 追加续写内容
                if continuation and len(continuation.strip()) > 0:
                    # 检查续写内容中是否包含"（待续……）"等占位符
                    if "（待续" in continuation or "待续" in continuation or "待补充" in continuation:
                        print(f" [警告：续写内容包含占位符，需要继续续写]", flush=True)
                        # 不追加包含占位符的内容，继续续写
                        if continuation_count < max_continuations - 1:
                            print(f" [继续续写以替换占位符...]", flush=True)
                            continue
                    
                    full_content += "\n\n" + continuation
                    print(f" [完成，耗时 {elapsed:.1f}秒，新增 {len(continuation)} 字符]", flush=True)
                    # 成功后重置失败计数器
                    if hasattr(self, '_continuation_fail_count'):
                        self._continuation_fail_count = 0
                    
                    # 检查续写内容是否真正增加了新章节（防止重复生成相同内容）
                    new_sections_found = []
                    content_before = full_content[:len(full_content) - len(continuation)]
                    for section_name in ['第一章', '第二章', '第三章', '第四章', '第五章', '第六章', '第七章', '第八章', '第九章', '第十章']:
                        if section_name in continuation:
                            # 检查这个章节是否在续写内容中是新出现的（不在之前的full_content中）
                            if section_name not in content_before:
                                new_sections_found.append(section_name)
                    
                    # 如果续写内容很少（少于100字符），可能是重复或无效内容
                    if len(continuation.strip()) < 100:
                        print(f" [警告：续写内容过短({len(continuation)}字符)，可能是重复内容]", flush=True)
                        # 如果连续3次续写内容都很短，停止续写
                        if not hasattr(self, '_short_continuation_count'):
                            self._short_continuation_count = 0
                        self._short_continuation_count += 1
                        if self._short_continuation_count >= 3:
                            print(f" [连续3次续写内容过短，停止续写]", flush=True)
                            break
                    else:
                        # 重置短续写计数
                        if hasattr(self, '_short_continuation_count'):
                            self._short_continuation_count = 0
                    
                    # 如果续写内容没有新增任何章节，且内容长度没有显著增加，可能是重复
                    if not new_sections_found and len(continuation.strip()) < 500:
                        print(f" [警告：续写内容未包含新章节且内容较短，可能是重复生成]", flush=True)
                        # 如果连续2次都是这样，停止续写
                        if not hasattr(self, '_no_new_section_count'):
                            self._no_new_section_count = 0
                        self._no_new_section_count += 1
                        if self._no_new_section_count >= 2:
                            print(f" [连续2次续写未包含新章节，停止续写]", flush=True)
                            break
                    else:
                        # 重置无新章节计数
                        if hasattr(self, '_no_new_section_count'):
                            self._no_new_section_count = 0
                else:
                    print(f" [警告：未获取到内容或内容为空，finish_reason={finish_reason}]", flush=True)
                    # 如果API返回空内容，可能是API问题，继续尝试
                    if continuation_count < 3:
                        print(f" [重试续写...]", flush=True)
                        time.sleep(2)  # 等待2秒后重试
                        continue
                    else:
                        print(f" [连续3次未获取到内容，停止续写]", flush=True)
                        break
                
                # 检查完整内容中是否还有"（待续……）"等占位符
                if "（待续" in full_content or "待续" in full_content:
                    print(f" [检测到内容中仍有占位符，继续续写以替换...]", flush=True)
                    # 继续续写以替换占位符
                    continue
                
                # 检查是否还需要继续
                # 先检查是否重复生成了目录（如果最后4000字符中包含"目录"且之前也有，可能是重复）
                last_part = full_content[-4000:] if len(full_content) > 4000 else full_content
                earlier_part = full_content[:-4000] if len(full_content) > 4000 else ""
                
                # 如果最后部分包含目录，且之前部分也包含目录，可能是重复生成
                if "目录" in last_part and "目录" in earlier_part:
                    # 检查是否是重复的目录（简单启发式：如果最后部分以"目录"开头且很短）
                    if last_part.strip().startswith("目录") and len(last_part.strip()) < 2000:
                        print(" [检测到可能重复生成目录，停止续写]", flush=True)
                        break
                
                # 检查内容中是否包含占位符
                has_placeholder = "（待续" in full_content or "待续" in full_content or "待补充" in full_content
                
                # 重新检查截断状态和缺失章节
                is_still_truncated = self._is_content_truncated(full_content, finish_reason, is_report=True)
                missing_sections_after = self._get_missing_sections(full_content)
                
                # 检查报告长度（如果太短，肯定未完成）- 排除Mermaid图表
                content_length = self._get_text_length_without_mermaid(full_content)
                is_too_short = content_length < 45000  # 如果少于4.5万字，肯定未完成
                
                # 如果有占位符，必须继续续写
                if has_placeholder:
                    print(f" [检测到占位符，必须继续续写以生成完整内容]", flush=True)
                    continue
                
                # 输出详细的续写状态信息
                print(f" [续写状态] 内容长度: {content_length}字符, 是否截断: {is_still_truncated}, 缺失章节: {missing_sections_after if missing_sections_after else '无'}, finish_reason: {finish_reason}", flush=True)
                
                # 【重要修复】优先检查第十章是否完整，如果完整则立即停止，避免无限续写
                has_complete_final = False
                if "第十章" in full_content:
                    final_section_start = full_content.rfind("第十章")
                    if final_section_start >= 0:
                        final_section = full_content[final_section_start:]
                        final_section_length = self._get_text_length_without_mermaid(final_section)
                        # 检查第十章是否完整：内容超过2000字符，且包含10.1和10.2
                        if final_section_length > 2000 and "10.1" in final_section and "10.2" in final_section:
                            # 检查10.1和10.2是否有实质性内容（不只是标题）
                            try:
                                section_101 = final_section.split("10.1")[1].split("10.2")[0] if "10.2" in final_section else final_section.split("10.1")[1]
                                section_102 = final_section.split("10.2")[1] if "10.2" in final_section else ""
                                section_101_length = self._get_text_length_without_mermaid(section_101.strip())
                                section_102_length = self._get_text_length_without_mermaid(section_102.strip())
                                has_substantial_101 = section_101_length > 500
                                has_substantial_102 = section_102_length > 1000
                                
                                if has_substantial_101 and has_substantial_102:
                                    # 检查是否有明确的结束标记（只要有句号等即可）
                                    has_end_marker = any(end_marker in final_section[-500:] for end_marker in ['附件', '附录', '---', '**附件**', '。', '.', '！', '!', '？', '?'])
                                    # 检查是否包含完成标记
                                    has_completion_marker = any(marker in final_section[-1000:] for marker in [
                                        "综上所述", "建议尽快批准实施", "建议批准实施", 
                                        "报告撰写完成", "全文完成", "报告结束", "全文结束"
                                    ])
                                    
                                    # 如果第十章内容完整，且有结束标记或完成标记，立即停止
                                    if has_end_marker or has_completion_marker or final_section_length > 3000:
                                        has_complete_final = True
                                        print(f" [第十章已完整] 内容: {final_section_length}字符（已排除图表）, 10.1: {section_101_length}字符, 10.2: {section_102_length}字符, 立即停止续写", flush=True)
                                        break
                            except Exception as e:
                                # 如果解析出错，只要第十章内容足够长且有10.1和10.2，也认为完整
                                if final_section_length > 3000:
                                    has_complete_final = True
                                    print(f" [第十章已完整] 内容: {final_section_length}字符（已排除图表），立即停止续写", flush=True)
                                    break
                
                # 如果第十章已完整，立即停止，不再检查其他条件（包括字数检查）
                if has_complete_final:
                    print(f" [第十章已完整，停止续写，不再检查字数要求]", flush=True)
                    break
                
                # 【重要修复】在检查字数之前，再次确认第十章是否完整
                # 如果第十章已完整，即使总字数不足，也应该停止续写
                # 【重要】必须严格检查"第十章"是作为章节标题出现的，而不是文本中的提及
                if not has_complete_final:
                    ch10_patterns = ["\n第十章", "\r\n第十章", "## 第十章", "# 第十章", "第十章 ", "第十章　", "第十章：", "第十章:", "第十章 研究结论", "第十章 研究结论及建议"]
                    ch10_found = False
                    ch10_start = -1
                    
                    for pattern in ch10_patterns:
                        pos = full_content.rfind(pattern)
                        if pos >= 0:
                            # 检查前面是否是换行符或章节标记，确保是真正的章节标题
                            before_text = full_content[max(0, pos-30):pos]
                            # 如果前面是换行符、数字、或者章节标记，说明是章节标题
                            if any(marker in before_text for marker in ['\n', '\r', '##', '#', '第', '章', '目录', '目 录']):
                                # 进一步验证：检查"第十章"后面是否跟着章节名称或内容
                                after_text = full_content[pos:pos+50]
                                if any(marker in after_text for marker in ['研究结论', '结论', '建议', ' ', '　', '：', ':', '\n']):
                                    ch10_found = True
                                    ch10_start = pos + (1 if pattern.startswith('\n') or pattern.startswith('\r') else 0)
                                    break
                    
                    if ch10_found and ch10_start >= 0:
                        ch10_content = full_content[ch10_start:]
                        
                        # 【重要】必须确保10.1和10.2是在第十章内容中，且是子章节标题格式
                        # 检查10.1和10.2是否作为子章节标题出现（前面有换行或空格）
                        has_101 = False
                        has_102 = False
                        
                        # 查找10.1，必须是在第十章之后，且是子章节格式
                        for pattern in ["\n10.1", "\r\n10.1", " 10.1", "　10.1", "10.1 ", "10.1　", "10.1：", "10.1:"]:
                            pos_101 = ch10_content.find(pattern)
                            if pos_101 >= 0:
                                # 检查前面是否是换行符或空格，确保是子章节标题
                                before_101 = ch10_content[max(0, pos_101-10):pos_101]
                                if any(marker in before_101 for marker in ['\n', '\r', ' ', '　', '##', '#']):
                                    has_101 = True
                                    break
                        
                        # 查找10.2，必须是在第十章之后，且是子章节格式
                        for pattern in ["\n10.2", "\r\n10.2", " 10.2", "　10.2", "10.2 ", "10.2　", "10.2：", "10.2:"]:
                            pos_102 = ch10_content.find(pattern)
                            if pos_102 >= 0:
                                # 检查前面是否是换行符或空格，确保是子章节标题
                                before_102 = ch10_content[max(0, pos_102-10):pos_102]
                                if any(marker in before_102 for marker in ['\n', '\r', ' ', '　', '##', '#']):
                                    has_102 = True
                                    break
                        
                        if has_101 and has_102:
                            try:
                                section_101 = ch10_content.split("10.1")[1].split("10.2")[0] if "10.2" in ch10_content else ch10_content.split("10.1")[1]
                                section_102 = ch10_content.split("10.2")[1] if "10.2" in ch10_content else ""
                                ch10_text_length = self._get_text_length_without_mermaid(ch10_content)
                                section_101_length = self._get_text_length_without_mermaid(section_101.strip())
                                section_102_length = self._get_text_length_without_mermaid(section_102.strip())
                                # 如果10.1超过500字符，10.2超过1000字符，认为完成
                                if section_101_length > 500 and section_102_length > 1000:
                                    print(f" [第十章已完成，内容{ch10_text_length}字符（已排除图表）(10.1: {section_101_length}字符, 10.2: {section_102_length}字符)，即使总字数不足也停止续写]", flush=True)
                                    break
                            except:
                                pass
                        
                        # 放宽条件：第十章内容超过2000字符，且有10.1和10.2，就停止
                        ch10_text_length = self._get_text_length_without_mermaid(ch10_content)
                        if ch10_text_length > 2000 and has_101 and has_102:
                            print(f" [第十章已完成，内容{ch10_text_length}字符（已排除图表），包含10.1和10.2，即使总字数不足也停止续写]", flush=True)
                            break
                
                # 如果内容太短，检查是否应该继续续写
                if is_too_short:
                    # 【修复】添加多重保护，防止死循环
                    # 1. 如果续写次数已超过10次，降低字数要求到35000
                    if continuation_count >= 10 and content_length >= 35000:
                        print(f" [续写次数过多({continuation_count}次)，内容已达{content_length}字符，强制完成]", flush=True)
                        break
                    # 2. 如果续写次数超过15次，无论字数多少都停止
                    if continuation_count >= 15:
                        print(f" [续写次数达到上限({continuation_count}次)，强制停止]", flush=True)
                        break
                    # 4. 检查内容是否还在增长（防止API返回空内容导致死循环）
                    if not hasattr(self, "_last_content_length"):
                        self._last_content_length = 0
                    if content_length <= self._last_content_length + 100:
                        if not hasattr(self, "_no_growth_count"):
                            self._no_growth_count = 0
                        self._no_growth_count += 1
                        if self._no_growth_count >= 3:
                            print(f" [内容未增长，连续{self._no_growth_count}次，强制停止]", flush=True)
                            break
                    else:
                        self._no_growth_count = 0
                    self._last_content_length = content_length
                    
                    print(f" [内容长度不足({content_length}字符，需要至少45000字符)，继续续写... (第{continuation_count}次)]", flush=True)
                    continue
                
                # 检查完成条件（按优先级）
                # 1. 如果内容达到4.8万字，且没有缺失章节，且第十章完整，说明完成
                if content_length >= 48000 and not missing_sections_after:
                    if has_complete_final:
                        print(f" [报告已完成] 内容长度: {content_length}字符, 无缺失章节, 第十章完整", flush=True)
                        break
                    # 如果第十章存在但不够完整，检查是否至少包含10.1和10.2
                    elif "第十章" in full_content:
                        final_section_start = full_content.rfind("第十章")
                        if final_section_start >= 0:
                            final_section = full_content[final_section_start:]
                            final_section_length = self._get_text_length_without_mermaid(final_section)
                            if final_section_length > 1500 and "10.1" in final_section and "10.2" in final_section:
                                # 放宽要求：只要有10.1和10.2，且内容达到要求，就认为完成
                                print(f" [报告已完成] 内容长度: {content_length}字符（已排除图表）, 无缺失章节, 第十章包含10.1和10.2", flush=True)
                    break
                
                # 2. 如果仍然被截断或有缺失章节，继续续写
                if is_still_truncated or missing_sections_after:
                    missing_info = f"缺失章节: {', '.join(missing_sections_after)}" if missing_sections_after else "内容被截断"
                    print(f" [仍有问题，继续续写...] {missing_info}", flush=True)
                    
                    # 检查缺失章节是否在最近几次续写中一直存在（可能是检测错误）
                    if not hasattr(self, '_missing_sections_history'):
                        self._missing_sections_history = []
                    self._missing_sections_history.append(set(missing_sections_after) if missing_sections_after else set())
                    
                    # 只保留最近5次的记录
                    if len(self._missing_sections_history) > 5:
                        self._missing_sections_history.pop(0)
                    
                    # 如果最近3次续写都检测到相同的缺失章节，可能是检测错误，放宽要求
                    if len(self._missing_sections_history) >= 3:
                        recent_missing = self._missing_sections_history[-3:]
                        if all(s == recent_missing[0] for s in recent_missing) and recent_missing[0]:
                            print(f" [警告：连续3次检测到相同的缺失章节，可能是检测错误，放宽要求继续...]", flush=True)
                            # 如果内容已经足够长（超过4万字），即使有缺失章节也停止
                            if content_length >= 40000:
                                print(f" [内容已足够长({content_length}字符)，停止续写]", flush=True)
                                break
                    
                    # 继续循环
                    continue
                
                # 3. 如果内容达到4.8万字，且finish_reason不是length，且没有缺失章节，说明可能完成
                if content_length >= 48000 and finish_reason and finish_reason != "length" and not missing_sections_after:
                    # 即使第十章不够完整，如果内容足够长且API返回完成，也认为完成
                    print(f" [报告已完成] 内容长度: {content_length}字符, 无缺失章节, API返回完成标记", flush=True)
                    break
                
                # 如果达到最大次数但仍有缺失，给出警告
                if continuation_count >= max_continuations:
                    if missing_sections_after:
                        print(f"\n[警告] 已达到最大续写次数({max_continuations})，但仍有章节未完成: {', '.join(missing_sections_after)}", flush=True)
                    else:
                        print(f"\n[信息] 已达到最大续写次数({max_continuations})，报告可能已基本完成", flush=True)
                    break
                
            except KeyboardInterrupt:
                print("\n[中断] 用户中断续写", flush=True)
                break
            except Exception as e:
                elapsed = time.time() - start_time if 'start_time' in locals() else 0
                err_text = str(e)
                print(f"\n[错误] 续写时出错 (耗时 {elapsed:.1f}秒): {err_text}", flush=True)
                if "repeated_ch10_hits" in err_text:
                    # Self-heal legacy local-variable state mismatch and retry.
                    repeated_ch10_hits = 0
                    print("[警告] 检测到 repeated_ch10_hits 变量状态异常，已自动重置并继续续写", flush=True)
                    continue
                import traceback
                print(f"[错误详情] {traceback.format_exc()}", flush=True)
                # 如果错误严重，停止续写
                if continuation_count >= 3:
                    print("[错误] 连续多次出错，停止续写", flush=True)
                    break
                # 否则继续尝试
                continue
        
        return full_content
    
    def _continue_writing_stream(self, existing_content: str, user_input: str, conversation_history: Optional[list] = None, max_continuations: int = 20):
        """
        续写被截断的内容（流式模式），持续续写直到报告完整
        
        Args:
            existing_content: 已生成的内容
            user_input: 原始用户输入（可能包含文件内容）
            conversation_history: 对话历史
            max_continuations: 最大续写次数
            
        Yields:
            续写内容的文本片段
        """
        full_content = existing_content
        continuation_count = 0
        # Defensive init: avoid UnboundLocalError in legacy continuation branches.
        repeated_ch10_hits = 0
        
        # 提取原始用户输入中的文件内容（如果有）
        file_context = ""
        if "【文件内容】" in user_input:
            # 提取文件内容部分
            file_start = user_input.find("【文件内容】")
            if file_start >= 0:
                file_context = user_input[file_start:file_start+5000]  # 保留前5000字符的文件内容作为上下文
        
        while continuation_count < max_continuations:
            # 【修复】硬性超时检测
            if not hasattr(self, '_stream_start_time'):
                self._stream_start_time = time.time()
            elif time.time() - self._stream_start_time > 1800:
                print(f' [硬性超时] 强制终止', flush=True)
                yield '[硬性超时] 强制终止'
                break
            
            # 【修复】先检查是否有占位符，如果有占位符，说明报告明显未完成，不应该因为第十章检测而停止
            has_placeholder = any(placeholder in full_content for placeholder in [
                "（因篇幅限制", "后续章节继续展开", "待续", "待补充", "详见下文",
                "（待续……）", "未完待续", "精简示例", "此处为精简", "因篇幅限制"
            ])
            
            # 【修复】强制终止条件：如果第十章已存在且有实质内容，立即停止（在续写开始前检查）
            # 但如果存在占位符，说明报告明显未完成，应该继续续写
            if not has_placeholder:
                is_ch10_complete, ch10_content = self._is_chapter_10_complete(full_content)
                if is_ch10_complete:
                    ch10_text_length = self._get_text_length_without_mermaid(ch10_content)
                    yield f"\n[强制终止] 第十章已完成({ch10_text_length}字符，已排除图表)，停止续写\n"
                    break
            else:
                # 如果有占位符，输出提示信息，继续续写
                print(f" [检测到占位符，报告明显未完成，继续续写...]", flush=True)
            
            # 计算排除图表后的文本长度
            text_length = self._get_text_length_without_mermaid(full_content)
            
            # 【修复】如果续写次数超过8次，且内容已达4万字，强制停止
            if continuation_count >= 8 and text_length >= 40000:
                print(f" [强制终止] 续写次数过多({continuation_count}次)且内容已足够({text_length}字符，已排除图表)，停止续写", flush=True)
                break
            
            # 检查缺失的章节
            missing_sections = self._get_missing_sections(full_content)
            
            # 提取最后一部分作为上下文（保留最后6000字符，增加上下文）
            context = full_content[-6000:] if text_length > 6000 else full_content
            
            # 构建续写提示
            missing_text = ""
            if missing_sections:
                missing_text = f"\n\n**重要：以下章节尚未完成，必须全部完成：**\n" + "\n".join(f"- {section}" for section in missing_sections)
            
            # 检查是否已经包含目录，避免重复生成
            has_cover = "封面" in full_content or "可行性研究报告" in full_content[:500]
            has_toc = "目录" in full_content or "第一章" in full_content[:2000]
            
            no_repeat_warning = ""
            if has_cover or has_toc:
                no_repeat_warning = "\n\n**⚠️ 重要警告：报告中已经包含封面和目录，请不要再重复生成封面和目录！直接继续正文内容即可。**\n"
            
            # 如果有文件内容，在续写提示中包含
            file_context_prompt = ""
            if file_context:
                file_context_prompt = f"\n\n**重要：请参考以下文件内容来完善报告：**\n{file_context}\n\n"
            
            continue_prompt = f"""请继续完成上述可行性研究报告。当前报告已生成到以下位置：

{context}
{file_context_prompt}
{missing_text}
{no_repeat_warning}

请从上述内容的末尾继续，完成报告的剩余部分。**必须确保：**

1. **完成所有缺失的章节**（如果上面列出了缺失章节，必须全部完成）
2. **⚠️ 严禁使用"（待续……）"、"待续"、"待补充"、"详见下文"等占位符，必须直接生成完整的章节内容**
3. **每个章节必须包含完整的详细内容**，不能只有标题，每个章节至少4000-5000字
4. **内容与前面部分连贯衔接**，保持逻辑连贯
5. **如果提供了文件内容，请充分参考文件内容来完善报告，确保报告内容与文件信息一致**
6. **确保报告有完整的"第十章 研究结论及建议"部分**，包含：
   - 10.1 主要研究结论（技术可行性、经济可行性、政策可行性），每个结论至少500-800字，必须详细展开，不能简略
   - 10.2 问题与建议（优先级、时间节点、具体措施、资源配置、风险控制），至少包含10-20条详细建议，每条建议至少200-300字，必须详细说明实施步骤、责任人、时间安排、所需资源、预期效果、风险控制等
7. **保持与前面部分相同的格式和风格**
8. **如果报告已经包含所有章节，请确保每个章节都完整，特别是最后章节要有明确的结束**
9. **报告总字数必须达到48000-50000字（约4.8-5万字），每个主要章节至少4000-5000字，总行数达到1700-1800行，这是硬性要求，绝对不能少于这个字数**
10. **每个子章节至少包含5-10个详细要点，每个要点至少200-400字，必须详细展开，不能简略**
11. **⚠️ 严禁只写标题不写内容，每个部分都必须详细展开，每个段落至少100-200字**
12. **⚠️ 如果某个部分内容不够详细，必须继续展开，直到达到要求的字数**
13. **⚠️ 不要因为输出限制而简化回答，请完整详细地生成所有内容，即使内容很长也要完整输出**
14. **⚠️⚠️⚠️ 极其重要：如果第十章已经存在且内容完整（包含10.1和10.2子章节，且10.1和10.2都有实质性内容：10.1超过500字符，10.2超过1000字符），请立即结束报告，不要继续优化、不要重复生成、不要添加新内容、不要重复生成目录或重新开始！如果第十章已完整，请立即停止，不要输出任何新内容！**
15. **⚠️ 如果发现报告中有"（待续……）"、"待续"等占位符，必须立即替换为完整的章节内容**
16. **⚠️ 当前报告长度：{self._get_text_length_without_mermaid(full_content)}字符（已排除图表），但如果第十章已完整（包含10.1和10.2，且10.1和10.2都有实质性内容），即使未达到目标长度也要立即结束，不要继续生成任何内容！**
17. **⚠️ 每个续写段落必须至少500-1000字，不能只有几句话，必须详细展开每个要点（但如果第十章已完整，请忽略此要求，立即停止）**
18. **⚠️⚠️⚠️ 绝对禁止：如果第十章包含10.1和10.2，且有实质性内容（10.1超过500字符，10.2超过1000字符），说明报告已完成，必须立即停止，不要再生成任何内容、不要继续优化、不要添加图表、不要添加文字、不要做任何修改！立即结束！**

**⚠️⚠️⚠️ 极其重要的截断标记要求（续写时必须严格遵守）⚠️⚠️⚠️：**
19. **如果续写完成（包含所有10个章节且字数达到48000字以上），必须在续写内容最后明确输出：**
   ```
   【报告已完成】
   
   总字数：[实际字符数]字符
   总行数：[实际行数]行
   包含章节：第一章至第十章（全部完成）
   图表数量：[实际图表数量]个
   ```
20. **如果续写后仍未完成，必须在续写内容最后明确输出：**
   ```
   【报告未完成，待续写】
   
   当前已完成章节：[列出已完成的章节编号]
   当前内容长度：[当前实际字符数]字符
   待续写章节：[列出待续写的章节编号]
   ```
21. **⚠️ 绝对禁止：不能在没有明确标记的情况下结束续写！必须明确标注报告状态！**

**请继续撰写，确保每个部分都详细展开，直到报告完整，达到4.8-5万字的详细要求。**⚠️⚠️⚠️ 但如果第十章已经完成（包含10.1和10.2，且10.1超过500字符，10.2超过1000字符），请立即停止，不要继续生成任何内容，明确结束报告并输出【报告已完成】标记。绝对不要使用任何占位符！当前内容长度：{len(full_content)}字符，但如果第十章已完整，即使未达到48000字符也要立即停止！续写完成后必须输出明确的完成标记！**"""
            
            continuation_count += 1
            
            # 显示续写进度
            # 如果内容已经很长，即使检测到缺失章节，也可能是格式问题
            if len(full_content) > 30000 and missing_sections:
                # 检查是否至少有一些章节标记
                has_sections = any(marker in full_content for marker in [
                    "第一章", "第二章", "第三章", "第四章", "第五章",
                    "一、", "二、", "三、", "四、", "五、",
                    "结论", "建议", "研究结论", "第十章"
                ])
                if has_sections and len(missing_sections) <= 5:
                    # 内容足够长且有章节标记，可能只是格式不同，停止续写
                    yield f"\n[信息] 内容已足够长（{len(full_content)}字符），且包含章节内容，停止续写\n"
                    break
            
            if missing_sections:
                yield f"\n[续写 {continuation_count}/{max_continuations}] 正在生成缺失章节: {', '.join(missing_sections)}...\n"
            else:
                yield f"\n[续写 {continuation_count}/{max_continuations}] 正在继续完善报告...\n"
            
            # 初始化变量
            timeout_break = False  # 标记是否因超时而中断
            continuation_text = ""
            finish_reason = None
            
            try:

                messages = []
                
                # 添加系统提示词
                if self.config.system_prompt:
                    messages.append({
                        "role": "system",
                        "content": self.config.system_prompt
                    })
                
                # 添加对话历史（改进：保留包含文件内容的原始用户输入）
                if conversation_history:
                    # 查找包含文件内容的用户消息
                    file_user_msg = None
                    for msg in conversation_history:
                        if msg.get("role") == "user" and ("【文件内容】" in msg.get("content", "") or "[上传文件:" in msg.get("content", "")):
                            file_user_msg = msg
                            break
                    
                    # 保留系统提示词后的最近5条历史（增加数量以保留更多上下文）
                    recent_history = conversation_history[-5:] if len(conversation_history) > 5 else conversation_history
                    
                    # 如果找到了包含文件的消息，确保它被包含
                    if file_user_msg and file_user_msg not in recent_history:
                        # 将文件消息添加到历史中
                        messages.append(file_user_msg)
                    
                    messages.extend(recent_history)
                
                # 添加续写请求
                messages.append({
                    "role": "user",
                    "content": continue_prompt
                })
                
                # 调用API续写（流式模式）
                start_time = time.time()
                continuation_text = ""
                finish_reason = None
                # 使用列表以便在线程中正确共享状态（闭包问题修复）
                last_chunk_time = [time.time()]
                timeout_occurred = [False]
                
                # 超时检测函数
                def check_timeout():
                    while not timeout_occurred[0]:
                        time.sleep(2)
                        current_time = time.time()
                        if (current_time - last_chunk_time[0] > 60) or (current_time - start_time > 600):
                            timeout_occurred[0] = True
                            print(' [超时触发]', flush=True)
                            break
                
                # 启动超时检测线程
                timeout_thread = threading.Thread(target=check_timeout, daemon=True)
                timeout_thread.start()
                
                try:

                    # 续写时使用更大的max_tokens，确保能生成足够长的内容
                    continuation_max_tokens = max(self.config.max_tokens, 16000)
                    # 如果是自定义模型，进一步增加
                    if self.config.provider == ModelProvider.CUSTOM:
                        continuation_max_tokens = max(continuation_max_tokens, 20000)
                    
                    if self.config.provider == ModelProvider.ANTHROPIC:
                        system_prompt = ""
                        anthropic_messages = []
                        for msg in messages:
                            if msg.get("role") == "system":
                                system_prompt = msg.get("content", "")
                            else:
                                anthropic_messages.append(msg)
                                
                        stream = self.client.messages.create(
                            model=self.config.model_name,
                            system=system_prompt,
                            messages=anthropic_messages,
                            temperature=self.config.temperature,
                            max_tokens=continuation_max_tokens,
                            stream=True
                        )
                    else:
                        stream = self.client.chat.completions.create(
                            model=self.config.model_name,
                            messages=messages,
                            temperature=self.config.temperature,
                            max_tokens=continuation_max_tokens,
                            stream=True
                        )
                    
                    timeout_break = False  # 重置超时标记
                    for chunk in stream:
                        # 检查是否超时
                        if timeout_occurred[0]:
                            yield "\n\n[警告] 续写流式输出超时（90秒内未收到数据），可能网络连接中断或API响应缓慢。将保存已生成内容并继续续写..."
                            timeout_break = True
                            break
                        
                        current_time = time.time()
                        last_chunk_time[0] = current_time  # 更新最后收到数据的时间
                        
                        if self.config.provider == ModelProvider.ANTHROPIC:
                            # Anthropic Stream Event handling
                            if chunk.type == "content_block_delta" and hasattr(chunk.delta, "text"):
                                content = chunk.delta.text
                                continuation_text += content
                                yield content
                                
                                # 实时检测完成标记
                                _stream_markers = ["研究报告完", "可行性研究报告完", "总字数统计:", "总行数统计:", "Mermaid图表数量:"]
                                _check = continuation_text[-1000:] if len(continuation_text) > 1000 else continuation_text
                                if any(m in _check for m in _stream_markers) and len(full_content + continuation_text) >= 40000:
                                    pass  # print("[实时检测] 续写检测到完成标记，停止", flush=True)
                                    finish_reason = "stop"
                                    break
                            elif chunk.type == "message_delta" and hasattr(chunk.delta, "stop_reason") and chunk.delta.stop_reason:
                                finish_reason = chunk.delta.stop_reason
                                break
                            elif chunk.type == "message_start" and hasattr(chunk.message, "usage"):
                                if not hasattr(self, '_continuation_usage'):
                                    self._continuation_usage = {
                                        'prompt_tokens': 0,
                                        'completion_tokens': 0,
                                        'total_tokens': 0
                                    }
                                self._continuation_usage['prompt_tokens'] += getattr(chunk.message.usage, 'input_tokens', 0)
                                self._continuation_usage['total_tokens'] += getattr(chunk.message.usage, 'input_tokens', 0)
                            elif chunk.type == "message_delta" and hasattr(chunk, "usage"):
                                if not hasattr(self, '_continuation_usage'):
                                    self._continuation_usage = {
                                        'prompt_tokens': 0,
                                        'completion_tokens': 0,
                                        'total_tokens': 0
                                    }
                                self._continuation_usage['completion_tokens'] += getattr(chunk.usage, 'output_tokens', 0)
                                self._continuation_usage['total_tokens'] += getattr(chunk.usage, 'output_tokens', 0)
                        else:
                            if chunk.choices[0].delta.content is not None:
                                content = chunk.choices[0].delta.content
                                continuation_text += content
                                yield content
                                
                                # 实时检测完成标记
                                _stream_markers = ["研究报告完", "可行性研究报告完", "总字数统计:", "总行数统计:", "Mermaid图表数量:"]
                                _check = continuation_text[-1000:] if len(continuation_text) > 1000 else continuation_text
                                if any(m in _check for m in _stream_markers) and len(full_content + continuation_text) >= 40000:
                                    pass  # print("[实时检测] 续写检测到完成标记，停止", flush=True)
                                    finish_reason = "stop"
                                    break
                            
                            # 累计续写时的token使用信息
                            if hasattr(chunk, 'usage') and chunk.usage:
                                if not hasattr(self, '_continuation_usage'):
                                    self._continuation_usage = {
                                        'prompt_tokens': 0,
                                        'completion_tokens': 0,
                                        'total_tokens': 0
                                    }
                                self._continuation_usage['prompt_tokens'] += getattr(chunk.usage, 'prompt_tokens', 0)
                                self._continuation_usage['completion_tokens'] += getattr(chunk.usage, 'completion_tokens', 0)
                                self._continuation_usage['total_tokens'] += getattr(chunk.usage, 'total_tokens', 0)
                            
                            if chunk.choices[0].finish_reason:
                                finish_reason = chunk.choices[0].finish_reason
                                # 如果这个chunk有usage信息，立即累计
                                if hasattr(chunk, 'usage') and chunk.usage:
                                    if not hasattr(self, '_continuation_usage'):
                                        self._continuation_usage = {
                                            'prompt_tokens': 0,
                                            'completion_tokens': 0,
                                            'total_tokens': 0
                                        }
                                    self._continuation_usage['prompt_tokens'] += getattr(chunk.usage, 'prompt_tokens', 0)
                                    self._continuation_usage['completion_tokens'] += getattr(chunk.usage, 'completion_tokens', 0)
                                    self._continuation_usage['total_tokens'] += getattr(chunk.usage, 'total_tokens', 0)
                                break
                    
                    # 如果超时线程还在运行，停止它
                    if timeout_thread.is_alive():
                        timeout_occurred[0] = True
                    
                    # 如果因超时而中断，确保已生成的内容被保存，然后继续下一次续写
                    if timeout_break and continuation_text:
                        # 超时后，保存已生成的内容，然后继续下一次续写
                        elapsed = time.time() - start_time
                        print(f" [超时中断，已保存 {len(continuation_text)} 字符，耗时 {elapsed:.1f}秒]", end="", flush=True)
                        # continuation_text会在后面被追加到full_content
                        # 不break，继续下一次续写循环
                    
                except Exception as api_error:
                    elapsed = time.time() - start_time
                    error_msg = str(api_error)
                    
                    # 检查错误类型并给出更详细的提示
                    if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                        yield f"\n\n[错误] 续写API调用超时 (耗时 {elapsed:.1f}秒): {error_msg}\n[提示] API响应时间过长，可能是网络问题或模型负载较高"
                    elif "connection" in error_msg.lower() or "network" in error_msg.lower():
                        yield f"\n\n[错误] 续写API网络连接失败 (耗时 {elapsed:.1f}秒): {error_msg}\n[提示] 请检查网络连接和API服务状态"
                    elif "rate limit" in error_msg.lower() or "429" in error_msg:
                        yield f"\n\n[错误] 续写API调用频率限制 (耗时 {elapsed:.1f}秒): {error_msg}\n[提示] API调用过于频繁，请稍后重试"
                    else:
                        yield f"\n\n[错误] 续写API调用失败 (耗时 {elapsed:.1f}秒): {error_msg}\n[提示] 如果问题持续，请检查API配置和服务状态"
                    
                    # 如果连续失败3次，停止续写
                    if continuation_count >= 3:
                        yield "\n[错误] 连续多次API调用失败，停止续写\n[提示] 报告可能不完整，但已保存当前内容"
                        break
                    
                    # 等待一段时间后重试
                    time.sleep(2)
                    continue
                
                elapsed = time.time() - start_time
                
                # 追加续写内容
                if continuation_text:
                    full_content += "\n\n" + continuation_text
                    print(f" [完成，耗时 {elapsed:.1f}秒，新增 {len(continuation_text)} 字符]", end="", flush=True)
                    self._empty_content_count = 0  # 成功获取内容，重置空内容计数
                else:
                    print(' [警告：未获取到内容]', end='', flush=True)
                    if not hasattr(self, '_empty_content_count'):
                        self._empty_content_count = 0
                    self._empty_content_count += 1
                    if self._empty_content_count >= 2:
                        yield '[错误] 连续2次未获取内容，停止'
                        break
                    text_length = self._get_text_length_without_mermaid(full_content)
                    if text_length >= 40000:
                        yield '[信息] 内容足够，停止'
                        break
                    continue
                
                # 检查是否还需要继续
                # 先检查是否重复生成了目录（如果最后4000字符中包含"目录"且之前也有，可能是重复）
                last_part = full_content[-4000:] if len(full_content) > 4000 else full_content
                earlier_part = full_content[:-4000] if len(full_content) > 4000 else ""
                
                # 如果最后部分包含目录，且之前部分也包含目录，可能是重复生成
                if "目录" in last_part and "目录" in earlier_part:
                    # 检查是否是重复的目录（简单启发式：如果最后部分以"目录"开头且很短）
                    if last_part.strip().startswith("目录") and len(last_part.strip()) < 2000:
                        print(" [检测到可能重复生成目录，停止续写]", flush=True)
                        break
                
                # 重新检查截断状态和缺失章节
                missing_sections_after = self._get_missing_sections(full_content)
                
                # 检查报告长度（排除Mermaid图表）
                content_length = self._get_text_length_without_mermaid(full_content)
                
                # 检查第十章是否完整
                has_complete_final = False
                if "第十章" in full_content:
                    final_section_start = full_content.rfind("第十章")
                    if final_section_start >= 0:
                        final_section = full_content[final_section_start:]
                        final_section_length = self._get_text_length_without_mermaid(final_section)
                        # 提高完成标准：第十章内容超过2000字符，且包含10.1和10.2，且内容详细
                        if final_section_length > 2000 and "10.1" in final_section and "10.2" in final_section:
                            # 检查10.1和10.2是否有实质性内容
                            section_101_text = final_section.split("10.1")[1].split("10.2")[0] if "10.2" in final_section else final_section.split("10.1")[1]
                            section_102_text = final_section.split("10.2")[1] if "10.2" in final_section else ""
                            section_101_length = self._get_text_length_without_mermaid(section_101_text)
                            section_102_length = self._get_text_length_without_mermaid(section_102_text)
                            has_substantial_101 = "10.1" in final_section and section_101_length > 500
                            has_substantial_102 = "10.2" in final_section and section_102_length > 1000
                            
                            if has_substantial_101 and has_substantial_102:
                                # 检查是否有明确的结束标记
                                if any(end_marker in final_section[-500:] for end_marker in ['附件', '附录', '---', '**附件**', '。', '.']):
                                    has_complete_final = True
                
                # 【重要修复】在检查字数之前，先检查第十章是否完整
                # 如果第十章已完整，即使总字数不足，也应该停止续写
                # 【重要】必须严格检查"第十章"是作为章节标题出现的，而不是文本中的提及
                ch10_patterns = ["\n第十章", "\r\n第十章", "## 第十章", "# 第十章", "第十章 ", "第十章　", "第十章：", "第十章:", "第十章 研究结论", "第十章 研究结论及建议"]
                ch10_found = False
                ch10_start = -1
                
                for pattern in ch10_patterns:
                    pos = full_content.rfind(pattern)
                    if pos >= 0:
                        # 检查前面是否是换行符或章节标记，确保是真正的章节标题
                        before_text = full_content[max(0, pos-30):pos]
                        # 如果前面是换行符、数字、或者章节标记，说明是章节标题
                        if any(marker in before_text for marker in ['\n', '\r', '##', '#', '第', '章', '目录', '目 录']):
                            # 进一步验证：检查"第十章"后面是否跟着章节名称或内容
                            after_text = full_content[pos:pos+50]
                            if any(marker in after_text for marker in ['研究结论', '结论', '建议', ' ', '　', '：', ':', '\n']):
                                ch10_found = True
                                ch10_start = pos + (1 if pattern.startswith('\n') or pattern.startswith('\r') else 0)
                                break
                
                if ch10_found and ch10_start >= 0:
                    ch10_content = full_content[ch10_start:]
                    
                    # 【重要】必须确保10.1和10.2是在第十章内容中，且是子章节标题格式
                    # 检查10.1和10.2是否作为子章节标题出现（前面有换行或空格）
                    has_101 = False
                    has_102 = False
                    
                    # 查找10.1，必须是在第十章之后，且是子章节格式
                    for pattern in ["\n10.1", "\r\n10.1", " 10.1", "　10.1", "10.1 ", "10.1　", "10.1：", "10.1:"]:
                        pos_101 = ch10_content.find(pattern)
                        if pos_101 >= 0:
                            # 检查前面是否是换行符或空格，确保是子章节标题
                            before_101 = ch10_content[max(0, pos_101-10):pos_101]
                            if any(marker in before_101 for marker in ['\n', '\r', ' ', '　', '##', '#']):
                                has_101 = True
                                break
                    
                    # 查找10.2，必须是在第十章之后，且是子章节格式
                    for pattern in ["\n10.2", "\r\n10.2", " 10.2", "　10.2", "10.2 ", "10.2　", "10.2：", "10.2:"]:
                        pos_102 = ch10_content.find(pattern)
                        if pos_102 >= 0:
                            # 检查前面是否是换行符或空格，确保是子章节标题
                            before_102 = ch10_content[max(0, pos_102-10):pos_102]
                            if any(marker in before_102 for marker in ['\n', '\r', ' ', '　', '##', '#']):
                                has_102 = True
                                break
                    
                    if has_101 and has_102:
                        try:
                            section_101 = ch10_content.split("10.1")[1].split("10.2")[0] if "10.2" in ch10_content else ch10_content.split("10.1")[1]
                            section_102 = ch10_content.split("10.2")[1] if "10.2" in ch10_content else ""
                            ch10_text_length = self._get_text_length_without_mermaid(ch10_content)
                            section_101_length = self._get_text_length_without_mermaid(section_101.strip())
                            section_102_length = self._get_text_length_without_mermaid(section_102.strip())
                            # 如果10.1超过500字符，10.2超过1000字符，认为完成
                            if section_101_length > 500 and section_102_length > 1000:
                                print(f" [第十章已完成，内容{ch10_text_length}字符（已排除图表）(10.1: {section_101_length}字符, 10.2: {section_102_length}字符)，即使总字数不足也停止续写]", flush=True)
                                yield f"\n[第十章已完成，停止续写]\n"
                                break
                        except:
                            pass
                        
                        # 放宽条件：第十章内容超过2000字符，且有10.1和10.2，就停止
                        ch10_text_length = self._get_text_length_without_mermaid(ch10_content)
                        if ch10_text_length > 2000 and has_101 and has_102:
                            print(f" [第十章已完成，内容{ch10_text_length}字符（已排除图表），包含10.1和10.2，即使总字数不足也停止续写]", flush=True)
                            yield f"\n[第十章已完成，停止续写]\n"
                            break
                
                # 检查内容是否太短（少于4.5万字，肯定未完成）
                is_too_short = content_length < 45000
                
                # 如果内容太短，继续续写（但前提是第十章未完成，如果第十章已完成，上面已经break了）
                if is_too_short:
                    print(f" [内容长度不足({content_length}字符，需要至少45000字符)，继续续写...]", end="", flush=True)
                    yield f"\n[内容长度不足({content_length}字符，需要至少45000字符)，继续续写...]\n"
                    # 继续循环，不break
                    continue
                
                # 如果有缺失章节，继续续写
                if missing_sections_after:
                    print(f" [仍有缺失章节: {', '.join(missing_sections_after)}，继续续写...]", end="", flush=True)
                    yield f"\n[仍有缺失章节: {', '.join(missing_sections_after)}，继续续写...]\n"
                    # 继续循环
                    continue
                
                # 检查完成条件（按优先级）
                # 1. 如果内容达到4.8万字，且没有缺失章节，且第十章完整，说明完成
                if content_length >= 48000 and not missing_sections_after:
                    if has_complete_final:
                        print(f" [报告已完成] 内容长度: {content_length}字符, 无缺失章节, 第十章完整", end="", flush=True)
                        yield f"\n[报告已完成] 内容长度: {content_length}字符, 无缺失章节, 第十章完整\n"
                        break
                    # 如果第十章存在但不够完整，检查是否至少包含10.1和10.2
                    elif "第十章" in full_content:
                        final_section_start = full_content.rfind("第十章")
                        if final_section_start >= 0:
                            final_section = full_content[final_section_start:]
                            if len(final_section) > 1500 and "10.1" in final_section and "10.2" in final_section:
                                # 放宽要求：只要有10.1和10.2，且内容达到要求，就认为完成
                                print(f" [报告已完成] 内容长度: {content_length}字符, 无缺失章节, 第十章包含10.1和10.2", end="", flush=True)
                                yield f"\n[报告已完成] 内容长度: {content_length}字符, 无缺失章节, 第十章包含10.1和10.2\n"
                                break
                
                # 2. 如果因超时而中断，且内容长度不足，继续续写
                if timeout_break and content_length < 48000:
                    print(f" [超时中断后内容长度不足({content_length}字符，需要至少48000字符)，继续续写...]", end="", flush=True)
                    yield f"\n[超时中断后内容长度不足({content_length}字符)，继续续写...]\n"
                    continue
                
                # 3. 如果finish_reason不是"length"（说明正常完成），但内容长度不足4.8万字，仍需续写
                if finish_reason and finish_reason != "length":
                    if content_length < 48000:
                        print(f" [API返回完成标记但内容长度不足({content_length}字符，需要至少48000字符)，继续续写...]", end="", flush=True)
                        yield f"\n[API返回完成标记但内容长度不足({content_length}字符)，继续续写...]\n"
                        continue
                    # 如果内容达到4.8万字，且没有缺失章节，即使第十章不够完整也认为完成
                    if content_length >= 48000 and not missing_sections_after:
                        print(f" [报告已完成] 内容长度: {content_length}字符, 无缺失章节, API返回完成标记", end="", flush=True)
                        yield f"\n[报告已完成]\n"
                    break
                
                # 如果达到最大次数但仍有缺失，给出警告
                if continuation_count >= max_continuations:
                    if missing_sections_after:
                        print(f"\n[警告] 已达到最大续写次数({max_continuations})，但仍有章节未完成: {', '.join(missing_sections_after)}", flush=True)
                    else:
                        print(f"\n[信息] 已达到最大续写次数({max_continuations})，报告可能已基本完成", flush=True)
                    break
                
            except KeyboardInterrupt:
                print("\n[中断] 用户中断续写", flush=True)
                break
            except Exception as e:
                elapsed = time.time() - start_time if 'start_time' in locals() else 0
                err_text = str(e)
                print(f"\n[错误] 续写时出错 (耗时 {elapsed:.1f}秒): {err_text}", flush=True)
                if "repeated_ch10_hits" in err_text:
                    # Self-heal legacy local-variable state mismatch and retry.
                    repeated_ch10_hits = 0
                    print("[警告] 检测到 repeated_ch10_hits 变量状态异常，已自动重置并继续续写", flush=True)
                    continue
                if continuation_count >= 3:
                    print("[错误] 连续多次出错，停止续写", flush=True)
                    break
                continue
    
    def _save_report(self, report_content: str, user_input: str) -> Optional[dict]:
        """
        保存可行性研究报告为MD和PDF文件到服务器，返回文件信息用于网页下载
        
        Args:
            report_content: 报告内容
            user_input: 用户输入（用于提取项目名称）
            
        Returns:
            包含filename和download_url的字典，如果保存失败返回None
        """
        try:

            # 创建reports目录（如果不存在）
            reports_dir = 'reports'
            os.makedirs(reports_dir, exist_ok=True)
            
            # 提取项目名称
            project_name = self._extract_project_name(user_input, report_content)
            
            # 清理项目名称，移除不允许的字符
            project_name = re.sub(r'[<>:"/\\|?*]', '', project_name)
            project_name = project_name.strip()
            if not project_name or len(project_name) > 50:
                project_name = "项目"
            
            # 生成文件名（包含时间戳）
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            base_filename = f"{project_name}-可行性研究报告-{timestamp}"
            
            # 确保文件名唯一
            md_filename = f"{base_filename}.md"
            pdf_filename = f"{base_filename}.pdf"
            md_filepath = os.path.join(reports_dir, md_filename)
            pdf_filepath = os.path.join(reports_dir, pdf_filename)
            
            counter = 1
            while os.path.exists(md_filepath) or os.path.exists(pdf_filepath):
                base_filename = f"{project_name}-可行性研究报告-{timestamp}-{counter}"
                md_filename = f"{base_filename}.md"
                pdf_filename = f"{base_filename}.pdf"
                md_filepath = os.path.join(reports_dir, md_filename)
                pdf_filepath = os.path.join(reports_dir, pdf_filename)
                counter += 1
            
            # 清理Mermaid代码块中的语法错误
            report_content = self._sanitize_mermaid_blocks(report_content)

            # 保存Markdown文件
            with open(md_filepath, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            # 生成PDF文件（使用超时机制，防止卡住）
            pdf_success = False
            pdf_timeout = 300  # PDF转换超时时间（秒）
            try:
                print(f"[PDF转换] 开始转换，超时时间: {pdf_timeout}秒...", flush=True)
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self._convert_markdown_to_pdf, report_content, pdf_filepath)
                    try:
                        future.result(timeout=pdf_timeout)
                        pdf_success = True
                        print(f"[PDF转换] 转换成功", flush=True)
                    except FuturesTimeoutError:
                        print(f"[PDF转换] 超时（{pdf_timeout}秒），将返回Markdown文件", flush=True)
                        pdf_success = False
                        pdf_filename = None
            except Exception as pdf_error:
                print(f"PDF生成失败: {str(pdf_error)}，仅保存Markdown文件", flush=True)
                pdf_success = False
                pdf_filename = None
            
            # 返回文件信息（优先返回PDF，如果没有PDF则返回MD）
            from urllib.parse import quote
            if pdf_success:
                encoded_filename = quote(pdf_filename, safe='')
                encoded_md_filename = quote(md_filename, safe='')
                return {
                    'filename': pdf_filename,
                    'filepath': pdf_filepath,
                    'download_url': f'/api/download/report/{encoded_filename}',
                    'format': 'pdf',
                    'pdf_filename': pdf_filename,
                    'md_filename': md_filename,
                    'pdf_url': f'/api/download/report/{encoded_filename}',
                    'md_url': f'/api/download/report/{encoded_md_filename}',
                }
            else:
                encoded_filename = quote(md_filename, safe='')
                pdf_url = ''
                if pdf_filename and os.path.exists(pdf_filepath):
                    pdf_url = f"/api/download/report/{quote(pdf_filename, safe='')}"
                return {
                    'filename': md_filename,
                    'filepath': md_filepath,
                    'download_url': f'/api/download/report/{encoded_filename}',
                    'format': 'md',
                    'pdf_filename': pdf_filename if (pdf_filename and os.path.exists(pdf_filepath)) else '',
                    'md_filename': md_filename,
                    'pdf_url': pdf_url,
                    'md_url': f'/api/download/report/{encoded_filename}',
                }
            
        except Exception as e:
            print(f"保存报告时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _convert_mermaid_to_images(self, markdown_content: str) -> str:
        """
        将Markdown中的Mermaid代码块转换为图片（并行下载优化版）
        使用 mermaid.ink 在线服务渲染图表

        Args:
            markdown_content: 包含Mermaid代码块的Markdown内容

        Returns:
            Mermaid代码块被替换为图片标签的Markdown内容
        """
        import base64
        import zlib
        import urllib.request
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed

        mermaid_pattern = r'```mermaid\s*\n([\s\S]*?)\n```'

        matches = list(re.finditer(mermaid_pattern, markdown_content))
        if not matches:
            return markdown_content

        print(f"[Mermaid] 发现 {len(matches)} 个图表，开始并行下载...")

        def encode_mermaid_code(mermaid_code: str) -> str:
            json_str = '{"code":"' + mermaid_code.replace('\\', '\\\\').replace('\n', '\\n').replace('"', '\\"') + '","mermaid":{"theme":"default"}}'
            compressed = zlib.compress(json_str.encode('utf-8'), 9)
            deflated = compressed[2:-4]
            encoded = base64.urlsafe_b64encode(deflated).decode('utf-8').rstrip('=')
            return encoded

        def download_mermaid_image(match):
            start, end = match.span()
            mermaid_code = match.group(1).strip()

            if not mermaid_code:
                return start, end, ''

            encoded_code = encode_mermaid_code(mermaid_code)
            img_url = f'https://mermaid.ink/img/pako:{encoded_code}'

            max_retries = 3
            last_error = None

            for attempt in range(max_retries):
                try:
                    req = urllib.request.Request(
                        img_url,
                        headers={'User-Agent': 'Mozilla/5.0'}
                    )
                    with urllib.request.urlopen(req, timeout=15) as response:
                        img_data = response.read()
                        img_base64 = base64.b64encode(img_data).decode('utf-8')
                        img_tag = f'<img src="data:image/png;base64,{img_base64}" alt="Mermaid Diagram" style="max-width: 100%; height: auto;" />'
                        return start, end, img_tag

                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        print(f"[Mermaid] 图表下载失败(尝试 {attempt + 1}/{max_retries}): {e}")

            print(f"[Mermaid] 图表下载最终失败: {last_error}")
            return start, end, f'<pre><code class="language-mermaid">{mermaid_code}</code></pre>'

        results = {}
        completed_count = 0

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(download_mermaid_image, match): match for match in matches}

            for future in as_completed(futures):
                try:
                    start, end, replacement = future.result()
                    results[start] = (start, end, replacement)
                    completed_count += 1
                    print(f"[Mermaid] 进度: {completed_count}/{len(matches)}")
                except Exception as e:
                    print(f"[Mermaid] 并发任务异常: {e}")

        result = markdown_content
        for start, end, replacement in sorted(results.values(), key=lambda x: x[0], reverse=True):
            result = result[:start] + replacement + result[end:]

        print(f"[Mermaid] 所有图表转换完成")
        return result

    def _convert_markdown_to_pdf(self, markdown_content: str, pdf_filepath: str):
        """
        将Markdown内容转换为PDF文件
        
        Args:
            markdown_content: Markdown格式的内容
            pdf_filepath: PDF文件保存路径
        """
        try:
            # 先将Mermaid代码块转换为图片
            markdown_content = self._convert_mermaid_to_images(markdown_content)

            # 优先使用weasyprint（支持中文和样式更好）
            try:

                import markdown
                from weasyprint import HTML, CSS
                from weasyprint.text.fonts import FontConfiguration
                import os
                
                font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'fonts', 'HarmonyOS_Sans_Regular.ttf')
                font_path_abs = os.path.abspath(font_path)
                font_url = f'file:///{font_path_abs.replace(os.sep, "/")}'
                
                print(f"[PDF字体] 检查字体文件: {font_path_abs}")
                if os.path.exists(font_path_abs):
                    print(f"[PDF字体] 字体文件存在，大小: {os.path.getsize(font_path_abs)} bytes")
                else:
                    print(f"[PDF字体] 字体文件不存在，尝试查找其他字体")
                    alt_fonts = [
                        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'fonts', 'simhei.ttf'),
                        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'fonts', 'simsun.ttc'),
                    ]
                    for alt_font in alt_fonts:
                        alt_abs = os.path.abspath(alt_font)
                        if os.path.exists(alt_abs):
                            font_path_abs = alt_abs
                            font_url = f'file:///{alt_abs.replace(os.sep, "/")}'
                            print(f"[PDF字体] 使用备用字体: {alt_abs}")
                            break
                
                html_content = markdown.markdown(
                    markdown_content, 
                    extensions=['extra', 'codehilite', 'tables', 'fenced_code']
                )
                
                styled_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <style>
                        @font-face {{
                            font-family: 'HarmonyOS';
                            src: url('{font_url}');
                            font-weight: normal;
                            font-style: normal;
                        }}
                        @page {{
                            size: A4;
                            margin: 2cm;
                        }}
                        body {{
                            font-family: 'HarmonyOS', 'Microsoft YaHei', 'SimSun', 'Arial Unicode MS', Arial, sans-serif;
                            line-height: 1.8;
                            color: #333;
                            font-size: 12pt;
                        }}
                        h1, h2, h3, h4, h5, h6 {{
                            font-family: 'HarmonyOS', 'Microsoft YaHei', 'SimSun', 'Arial Unicode MS', Arial, sans-serif;
                            color: #2c3e50;
                            margin-top: 1.5em;
                            margin-bottom: 0.8em;
                            page-break-after: avoid;
                        }}
                        h1 {{ font-size: 24pt; border-bottom: 2px solid #3498db; padding-bottom: 0.3em; }}
                        h2 {{ font-size: 20pt; border-bottom: 1px solid #95a5a6; padding-bottom: 0.2em; }}
                        h3 {{ font-size: 16pt; }}
                        h4 {{ font-size: 14pt; }}
                        p {{ margin: 0.8em 0; text-align: justify; }}
                        table {{
                            border-collapse: collapse;
                            width: 100%;
                            margin: 1.5em 0;
                            page-break-inside: avoid;
                        }}
                        table th, table td {{
                            border: 1px solid #ddd;
                            padding: 8px;
                            text-align: left;
                        }}
                        table th {{
                            background-color: #f2f2f2;
                            font-weight: bold;
                        }}
                        code {{
                            background-color: #f4f4f4;
                            padding: 2px 6px;
                            border-radius: 3px;
                            font-family: "Courier New", monospace;
                        }}
                        pre {{
                            background-color: #f4f4f4;
                            padding: 15px;
                            border-radius: 5px;
                            overflow-x: auto;
                            page-break-inside: avoid;
                        }}
                        ul, ol {{
                            margin: 1em 0;
                            padding-left: 2em;
                        }}
                        li {{
                            margin: 0.5em 0;
                        }}
                        blockquote {{
                            border-left: 4px solid #3498db;
                            margin: 1em 0;
                            padding-left: 1em;
                            color: #555;
                        }}
                    </style>
                </head>
                <body>
                    {html_content}
                </body>
                </html>
                """
                
                font_config = FontConfiguration()
                print(f"[PDF字体] FontConfiguration已创建，开始生成PDF")
                HTML(string=styled_html).write_pdf(pdf_filepath, font_config=font_config)
                return
            except Exception as _wp_err:
                print(f"[PDF转换] weasyprint失败（将尝试reportlab）: {_wp_err}", flush=True)
            
            # 如果weasyprint不可用，尝试使用reportlab
            try:

                from reportlab.lib.pagesizes import A4
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.units import inch
                from reportlab.pdfbase import pdfmetrics
                from reportlab.pdfbase.ttfonts import TTFont
                import markdown
                from html.parser import HTMLParser
                import re
                
                # 创建PDF文档
                doc = SimpleDocTemplate(pdf_filepath, pagesize=A4)
                styles = getSampleStyleSheet()
                story = []
                
                import os
                
                chinese_font = 'Helvetica'
                font_registered = False
                
                project_font = 'x:/test_2/static/fonts/HarmonyOS_Sans_Regular.ttf'
                if os.path.exists(project_font):
                    try:
                        pdfmetrics.registerFont(TTFont('HarmonyOS', project_font))
                        chinese_font = 'HarmonyOS'
                        font_registered = True
                        print(f"[PDF] 使用项目字体: {project_font}")
                    except Exception as e:
                        print(f"[PDF] 项目字体注册失败: {e}")
                
                if not font_registered:
                    windows_fonts = [
                        ('C:/Windows/Fonts/msyh.ttc', 'MicrosoftYaHei'),
                        ('C:/Windows/Fonts/simsun.ttc', 'SimSun'),
                    ]
                    for font_path, font_name in windows_fonts:
                        if os.path.exists(font_path):
                            try:
                                pdfmetrics.registerFont(TTFont(font_name, font_path))
                                chinese_font = font_name
                                font_registered = True
                                print(f"[PDF] 使用Windows字体: {font_path}")
                                break
                            except Exception as e:
                                print(f"[PDF] Windows字体注册失败: {e}")
                
                if not font_registered:
                    linux_fonts = [
                        ('/usr/share/fonts/truetype/wqy/wqy-microhei.ttc', 'WQY'),
                        ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 'DejaVu'),
                    ]
                    for font_path, font_name in linux_fonts:
                        if os.path.exists(font_path):
                            try:
                                pdfmetrics.registerFont(TTFont(font_name, font_path))
                                chinese_font = font_name
                                font_registered = True
                                print(f"[PDF] 使用Linux字体: {font_path}")
                                break
                            except Exception as e:
                                print(f"[PDF] Linux字体注册失败: {e}")
                
                if not font_registered:
                    print("[PDF] 警告: 未找到可用的中文字体，PDF可能无法正确显示中文")
                
                # 创建自定义样式
                normal_style = ParagraphStyle(
                    'CustomNormal',
                    parent=styles['Normal'],
                    fontName=chinese_font,
                    fontSize=11,
                    leading=16,
                    spaceAfter=12
                )
                
                heading1_style = ParagraphStyle(
                    'CustomHeading1',
                    parent=styles['Heading1'],
                    fontName=chinese_font,
                    fontSize=18,
                    leading=22,
                    spaceAfter=12,
                    spaceBefore=12
                )
                
                heading2_style = ParagraphStyle(
                    'CustomHeading2',
                    parent=styles['Heading2'],
                    fontName=chinese_font,
                    fontSize=16,
                    leading=20,
                    spaceAfter=10,
                    spaceBefore=10
                )
                
                # 简单处理Markdown：移除代码块和特殊格式，保留基本结构
                lines = markdown_content.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        story.append(Spacer(1, 0.1*inch))
                        continue
                    
                    # 处理标题
                    if line.startswith('# '):
                        p = Paragraph(line[2:], heading1_style)
                    elif line.startswith('## '):
                        p = Paragraph(line[3:], heading2_style)
                    elif line.startswith('### '):
                        p = Paragraph(line[4:], styles['Heading3'])
                    elif line.startswith('**') and line.endswith('**'):
                        # 粗体文本
                        text = line.replace('**', '')
                        p = Paragraph(f'<b>{text}</b>', normal_style)
                    else:
                        # 普通段落，转义HTML特殊字符
                        text = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        p = Paragraph(text, normal_style)
                    
                    story.append(p)
                    story.append(Spacer(1, 0.1*inch))
                
                doc.build(story)
                return
            except Exception as _rl_err:
                print(f"[PDF转换] reportlab失败: {_rl_err}", flush=True)
            
            # 如果都不可用，抛出异常
            raise ImportError("需要安装PDF生成库。请运行: pip install weasyprint 或 pip install reportlab")
            
        except Exception as e:
            raise Exception(f"PDF转换失败: {str(e)}")
    
    def chat_with_file(self, file_path: str, user_query: Optional[str] = None, conversation_history: Optional[list] = None) -> str:
        """
        处理文件并基于文件内容进行对话
        
        Args:
            file_path: 文件路径
            user_query: 用户的问题（可选）
            conversation_history: 可选的对话历史记录
            
        Returns:
            模型的回复文本
        """
        try:

            # 处理文件
            content, file_type = self.file_processor.process_file(file_path)
            
            # 格式化文件内容为提示词
            file_prompt = self.file_processor.format_file_content_for_prompt(
                file_path, content, file_type, user_query
            )
            
            # 如果没有用户问题，使用默认问题
            if not user_query:
                user_query = "请分析这个文件的内容。"
            
            # 组合用户输入
            full_input = f"{file_prompt}\n\n请根据上述文件内容回答：{user_query}"
            
            return self.chat(full_input, conversation_history)
            
        except Exception as e:
            return f"处理文件时出错: {str(e)}"
    
    def get_last_usage(self):
        """获取最后一次API调用的token使用信息"""
        return self.last_usage

    def _get_report_chapter_plan(self) -> list:
        """报告章节规划（固定10章，按章生成）"""
        return [
            (1, "项目概述"),
            (2, "项目建设背景及必要性"),
            (3, "项目需求分析与产出方案"),
            (4, "项目选址与要素保障"),
            (5, "项目建设方案"),
            (6, "项目运营方案"),
            (7, "项目投融资与财务方案"),
            (8, "项目影响效果分析"),
            (9, "项目风险管控方案"),
            (10, "研究结论及建议"),
        ]

    def _extract_toc_from_content(self, content: str) -> list:
        if not content:
            return []
        titles = []
        chapter_pattern = r'^第[一二三四五六七八九十0-9]+章\s+.+$'
        section_pattern = r'^[一二三四五六七八九十]+、.+$'
        subsection_pattern = r'^（[一二三四五六七八九十]+）.+$'
        alt_section_pattern = r'^\d+\.\d+\s+.+$'
        alt_subsection_pattern = r'^\d+\.\d+\.\d+\s+.+$'
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
            if re.match(chapter_pattern, line):
                titles.append(('chapter', line))
            elif re.match(section_pattern, line):
                titles.append(('section', line))
            elif re.match(subsection_pattern, line):
                titles.append(('subsection', line))
            elif re.match(alt_section_pattern, line):
                titles.append(('section', line))
            elif re.match(alt_subsection_pattern, line):
                titles.append(('subsection', line))
        return titles

    def _generate_toc(self, content: str) -> str:
        titles = self._extract_toc_from_content(content)
        if not titles:
            return ""
        toc_lines = ["## 目录", ""]
        page_num = 1
        for level, title in titles:
            if level == 'chapter':
                indent = ""
                page_num = max(1, page_num)
            elif level == 'section':
                indent = "    "
                page_num += 2
            else:
                indent = "        "
                page_num += 1
            dots = "." * (50 - len(title) - len(indent))
            toc_lines.append(f"{indent}{title} {dots} {page_num}")
        toc_lines.append("")
        return "\n".join(toc_lines)

    def _chapter_heading(self, chapter_no: int, chapter_title: str) -> str:
        cn = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
        if 1 <= chapter_no <= 10:
            return f"第{cn[chapter_no - 1]}章 {chapter_title}"
        return f"第{chapter_no}章 {chapter_title}"

    def _extract_single_chapter(self, text: str, chapter_no: int, chapter_title: str) -> str:
        """
        从模型输出中提取单章内容，避免跨章串写。
        """
        if not text:
            return ""
        expected = self._chapter_heading(chapter_no, chapter_title)
        block = text.strip()

        # 定位本章起点
        start_match = re.search(rf"(^|\n)\s*第[一二三四五六七八九十0-9]+章[^\n]*", block)
        if start_match:
            block = block[start_match.start():].strip()
        else:
            # 没有章节头时强制补齐，避免后续完整性检测失败
            block = f"{expected}\n\n{block}"

        # 截断到下一章，避免一次输出多章
        next_head = re.search(r"\n\s*第[一二三四五六七八九十0-9]+章[^\n]*", block[1:])
        if next_head:
            block = block[: next_head.start() + 1].strip()

        # 确保章节头一致
        if not block.startswith(expected):
            # 保留原内容但统一标题
            lines = block.splitlines()
            if lines and re.match(r"^\s*第[一二三四五六七八九十0-9]+章", lines[0]):
                lines[0] = expected
                block = "\n".join(lines).strip()
            else:
                block = f"{expected}\n\n{block}"
        return self._clean_chapter_content(block)

    def _clean_chapter_content(self, content: str) -> str:
        if not content:
            return ""
        lines = content.split('\n')
        title_line = ""
        body_start = 0
        for i, line in enumerate(lines):
            if re.match(r'^\s*第[一二三四五六七八九十0-9]+章', line):
                title_line = line
                body_start = i + 1
                break
        body_lines = lines[body_start:]
        cleaned_lines = []
        for line in body_lines:
            stripped = line.strip()
            if re.match(r'^(好的[，,。]?|好的$)', stripped):
                continue
            if re.match(r'^(好的[，,]\s*我来|我将为您|我来为您|我将为您撰写|我来为您撰写)', stripped):
                continue
            if re.match(r'^(以下[是为]|下面[是为]|以下是第|下面是第)', stripped):
                continue
            if re.match(r'^(开始生成|正在生成|开始撰写|正在撰写)', stripped):
                continue
            if re.match(r'^第[一二三四五六七八九十0-9]+章[的内容如下：:]*', stripped):
                continue
            if re.match(r'^请看下面的内容[：:]?$', stripped):
                continue
            if re.match(r'^请看下文[：:]?$', stripped):
                continue
            if re.match(r'^内容如下[：:]?$', stripped):
                continue
            cleaned_lines.append(line)
        result_lines = []
        empty_count = 0
        for line in cleaned_lines:
            if line.strip() == '':
                empty_count += 1
                if empty_count <= 2:
                    result_lines.append(line)
            else:
                empty_count = 0
                result_lines.append(line)
        while result_lines and result_lines[-1].strip() == '':
            result_lines.pop()
        if title_line:
            result_lines.insert(0, title_line)
        return '\n'.join(result_lines)

    def _check_chapter_completeness(self, chapter_block: str, min_length: int = 1500) -> dict:
        """
        检测章节完整性。
        返回: {'is_complete': bool, 'needs_continuation': bool, 'reason': str}
        """
        if not chapter_block:
            return {'is_complete': False, 'needs_continuation': True, 'reason': '章节内容为空'}
        
        lines = chapter_block.strip().split('\n')
        body_lines = [l for l in lines if l.strip() and not re.match(r'^\s*第[一二三四五六七八九十0-9]+章', l)]
        body_text = '\n'.join(body_lines)
        
        chapter_len = len(body_text.replace('\n', '').replace(' ', ''))
        if chapter_len < min_length:
            return {'is_complete': False, 'needs_continuation': True, 'reason': f'章节内容过短({chapter_len}字符<{min_length})'}
        
        has_subsection = bool(re.search(r'^\s*##\s+.+', chapter_block, re.MULTILINE))
        has_subsubsection = bool(re.search(r'^\s*###\s+.+', chapter_block, re.MULTILINE))
        has_numbered_section = bool(re.search(r'^\s*[（(][一二三四五六七八九十\d]+[)）]\s*.+', chapter_block, re.MULTILINE))
        has_bullet_section = bool(re.search(r'^\s*[\d]+\.\s+.+', chapter_block, re.MULTILINE))
        
        if not (has_subsection or has_subsubsection or has_numbered_section or has_bullet_section):
            return {'is_complete': False, 'needs_continuation': True, 'reason': '章节缺少二级/三级标题结构'}
        
        last_line = ''
        for line in reversed(lines):
            stripped = line.strip()
            if stripped and not re.match(r'^\s*第[一二三四五六七八九十0-9]+章', stripped):
                last_line = stripped
                break
        
        if last_line:
            ends_with_punctuation = bool(re.search(r'[。！？.!?]$', last_line))
            ends_with_incomplete = bool(re.search(r'[，、；：,;:]$', last_line))
            
            if ends_with_incomplete:
                return {'is_complete': False, 'needs_continuation': True, 'reason': '章节以非终结标点结尾'}
            if not ends_with_punctuation:
                incomplete_patterns = [
                    r'包括以下',
                    r'具体如下',
                    r'如下[：:]?$',
                    r'如下所示',
                    r'主要包括',
                    r'分为以下',
                    r'详见',
                ]
                for pattern in incomplete_patterns:
                    if re.search(pattern, last_line):
                        return {'is_complete': False, 'needs_continuation': True, 'reason': '章节结尾不完整'}
        
        return {'is_complete': True, 'needs_continuation': False, 'reason': '章节完整'}

    def _call_chat_once(self, messages: list, max_tokens: Optional[int] = None) -> Tuple[str, dict, Optional[str]]:
        """统一的单次非流式调用，便于按章节累计token。"""
        temperature = self.config.temperature
        use_max_tokens = max_tokens if max_tokens is not None else 8000

        if self.config.provider == ModelProvider.CUSTOM:
            temperature = min(temperature * 1.1, 0.95)
            if use_max_tokens < 16000:
                use_max_tokens = 16000

        if self.config.provider == ModelProvider.ANTHROPIC:
            sys_msg = ""
            anthropic_messages = []
            for msg in messages:
                if msg.get("role") == "system":
                    sys_msg = msg.get("content", "")
                else:
                    anthropic_messages.append(msg)
            
            response = self.client.messages.create(
                model=self.config.model_name,
                system=sys_msg,
                messages=anthropic_messages,
                temperature=temperature,
                max_tokens=use_max_tokens
            )
            content = response.content[0].text if response and hasattr(response, 'content') and len(response.content) > 0 else ""
            finish_reason = response.stop_reason if hasattr(response, 'stop_reason') else None
            usage = {
                'prompt_tokens': getattr(response.usage, 'input_tokens', 0) if hasattr(response, 'usage') and response.usage else 0,
                'completion_tokens': getattr(response.usage, 'output_tokens', 0) if hasattr(response, 'usage') and response.usage else 0,
                'total_tokens': (getattr(response.usage, 'input_tokens', 0) + getattr(response.usage, 'output_tokens', 0)) if hasattr(response, 'usage') and response.usage else 0
            }
            return content, usage, finish_reason
        else:
            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=use_max_tokens
            )
        content = response.choices[0].message.content or ""
        finish_reason = response.choices[0].finish_reason
        usage = {
            'prompt_tokens': getattr(response.usage, 'prompt_tokens', 0) if hasattr(response, 'usage') and response.usage else 0,
            'completion_tokens': getattr(response.usage, 'completion_tokens', 0) if hasattr(response, 'usage') and response.usage else 0,
            'total_tokens': getattr(response.usage, 'total_tokens', 0) if hasattr(response, 'usage') and response.usage else 0
        }
        return content, usage, finish_reason

    def _acc_usage(self, total: dict, delta: dict) -> dict:
        total['prompt_tokens'] += int(delta.get('prompt_tokens', 0))
        total['completion_tokens'] += int(delta.get('completion_tokens', 0))
        total['total_tokens'] += int(delta.get('total_tokens', 0))
        return total

    def _build_report_context_guide(
        self,
        user_input: str,
        current_heading: str,
        completed_heads: list,
        chapter_plan_heads: list,
        report_parts: list
    ) -> str:
        """
        构造稳定的上下文指引，防止章节续写时遗忘目标与边界。
        """
        completed_text = "、".join(completed_heads) if completed_heads else "无"
        pending = [h for h in chapter_plan_heads if h not in completed_heads and h != current_heading]
        pending_text = "、".join(pending) if pending else "无"
        recent_text = ("\n\n".join(report_parts))[-1800:] if report_parts else ""

        return f"""
【上下文指引-必须遵守】
用户原始任务：{user_input}
当前目标章节：{current_heading}
已完成章节：{completed_text}
后续待完成章节：{pending_text}

约束边界：
1. 只输出当前目标章节，不得越界到其它章节。
2. 不得改写已完成章节标题。
3. 禁止出现“待续/略/后文再述/占位符”。
4. 内容不足时，只能在当前章节内补充深度，不得切换主题。

上文摘要（用于保持一致性）：
{recent_text}
"""

    def _generate_report_by_chapter(self, user_input: str, conversation_history: Optional[list] = None) -> Tuple[str, dict]:
        """
        按章节生成报告：封面/目录 + 第1~10章逐章生成，避免整篇被模型自动压缩或跨章循环。
        """
        usage_total = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
        base_messages = []

        if self.config.system_prompt:
            base_messages.append({"role": "system", "content": self.config.system_prompt})
        if conversation_history:
            base_messages.extend(conversation_history[-6:])

        chapter_plan = self._get_report_chapter_plan()
        chapter_names = [self._chapter_heading(no, title) for no, title in chapter_plan]

        cover_prompt = f"""
你是专业可研报告编制助手。请只生成封面，不要生成目录和正文章节。
用户需求：{user_input}

硬性要求：
1. 输出报告封面，包含报告标题、编制单位、编制日期等基本信息。
2. 不得出现"待续/待补充/详见下文"等占位词。
3. 不要输出目录和任何正文段落。
"""
        cover_text, u1, _ = self._call_chat_once(base_messages + [{"role": "user", "content": cover_prompt}], max_tokens=2500)
        self._acc_usage(usage_total, u1)

        report_parts = [cover_text.strip()] if cover_text.strip() else []
        generated_heads = []

        for chapter_no, chapter_title in chapter_plan:
            heading = self._chapter_heading(chapter_no, chapter_title)
            generated_heads.append(heading)
            context_guide = self._build_report_context_guide(
                user_input=user_input,
                current_heading=heading,
                completed_heads=generated_heads[:-1],
                chapter_plan_heads=chapter_names,
                report_parts=report_parts
            )
            chapter_prompt = f"""
请只生成当前这一章：{heading}

用户需求：{user_input}
已完成章节：{", ".join(generated_heads[:-1]) if len(generated_heads) > 1 else "无"}

约束：
1. 只输出“{heading}”这一章的完整内容，禁止输出下一章标题。
2. 必须有二级/三级小节、数据分析、实施细节，内容要充分展开。
3. 严禁使用“待续/略/后文再述”等占位缩写。
4. 优先补足文字深度，避免只有清单式短句。

{context_guide}
"""
            chapter_text, u2, _ = self._call_chat_once(base_messages + [{"role": "user", "content": chapter_prompt}])
            self._acc_usage(usage_total, u2)
            chapter_block = self._extract_single_chapter(chapter_text, chapter_no, chapter_title)

            chapter_len = self._get_text_length_without_mermaid(chapter_block)
            completeness = self._check_chapter_completeness(chapter_block)
            
            if chapter_len < 1800 or completeness['needs_continuation']:
                enrich_guide = self._build_report_context_guide(
                    user_input=user_input,
                    current_heading=heading,
                    completed_heads=generated_heads[:-1],
                    chapter_plan_heads=chapter_names,
                    report_parts=report_parts + [chapter_block]
                )
                enrich_prompt = f"""
请对下面这一章进行深化扩写，仅限这一章，不得新增其它章节标题：

{chapter_block}

{enrich_guide}

要求：
1. 保留当前章节标题"{heading}"不变。
2. 增加方法、步骤、约束、数据口径、风险控制、实施节奏等细节。
3. 输出完整章节正文。
"""
                if chapter_len >= 1800:
                    last_200_chars = chapter_block[-200:] if len(chapter_block) > 200 else chapter_block
                    enrich_prompt = f"""
上一章内容被截断，请继续完成"{heading}"的剩余内容。

已生成内容摘要：{last_200_chars}

{enrich_guide}

要求：
1. 只输出剩余内容，不要重复已输出的部分。
2. 继续完成当前章节，不得新增其它章节标题。
3. 确保内容完整，以完整句子结尾。
"""
                enriched, u3, _ = self._call_chat_once(base_messages + [{"role": "user", "content": enrich_prompt}], max_tokens=6000)
                self._acc_usage(usage_total, u3)
                if chapter_len < 1800:
                    chapter_block = self._extract_single_chapter(enriched, chapter_no, chapter_title)
                else:
                    continuation = enriched.strip()
                    if continuation:
                        chapter_block = chapter_block.rstrip() + "\n\n" + continuation

            report_parts.append(chapter_block.strip())

        final_report = "\n\n".join([p for p in report_parts if p]).strip()
        toc_content = self._generate_toc(final_report)
        if toc_content:
            cover_only = report_parts[0] if report_parts else ""
            chapters_only = "\n\n".join([p for p in report_parts[1:] if p]).strip()
            final_report = cover_only + "\n\n" + toc_content + "\n\n" + chapters_only
        total_chars = self._get_text_length_without_mermaid(final_report)
        final_report += f"\n\n【报告已完成】\n总字数：{total_chars}字符\n包含章节：第一章至第十章（全部完成）"
        self.last_usage = usage_total
        return final_report, usage_total

    def _generate_report_by_chapter_stream(self, user_input: str, conversation_history: Optional[list] = None):
        """
        流式按章节生成：每章完成后立即推送，避免整篇长请求导致的自动缩减。
        """
        usage_total = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
        base_messages = []
        if self.config.system_prompt:
            base_messages.append({"role": "system", "content": self.config.system_prompt})
        if conversation_history:
            base_messages.extend(conversation_history[-6:])

        chapter_plan = self._get_report_chapter_plan()
        yield "[按章节生成] 已切换为章节级生成模式\n"

        def _stream_once(messages: list, max_tokens: Optional[int] = None, state: Optional[dict] = None):
            """单次流式调用：边产出chunk边累积文本和usage到state。"""
            if state is None:
                state = {}
            state['text'] = ''
            state['finish_reason'] = None
            state['usage'] = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}

            temperature = self.config.temperature
            use_max_tokens = max_tokens if max_tokens is not None else 8000
            if self.config.provider == ModelProvider.CUSTOM:
                temperature = min(temperature * 1.1, 0.95)
                if use_max_tokens < 16000:
                    use_max_tokens = 16000

            if self.config.provider == ModelProvider.ANTHROPIC:
                sys_msg = ""
                anthropic_messages = []
                for msg in messages:
                    if msg.get("role") == "system":
                        sys_msg = msg.get("content", "")
                    else:
                        anthropic_messages.append(msg)
                
                stream = self.client.messages.create(
                    model=self.config.model_name,
                    system=sys_msg,
                    messages=anthropic_messages,
                    temperature=temperature,
                    max_tokens=use_max_tokens,
                    stream=True
                )
            else:
                stream = self.client.chat.completions.create(
                    model=self.config.model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=use_max_tokens,
                    stream=True
                )

            for chunk in stream:
                if self.config.provider == ModelProvider.ANTHROPIC:
                    # Anthropic stream handling
                    if chunk.type == "message_start":
                        uso = chunk.message.usage
                        if uso:
                            state['usage'] = {'prompt_tokens': getattr(uso, 'input_tokens', 0), 'completion_tokens': getattr(uso, 'output_tokens', 0), 'total_tokens': getattr(uso, 'input_tokens', 0) + getattr(uso, 'output_tokens', 0)}
                    elif chunk.type == "content_block_delta" and hasattr(chunk.delta, "text"):
                        content = chunk.delta.text
                        if content:
                            state['text'] += content
                            yield content
                    elif chunk.type == "message_delta":
                        uso = chunk.usage
                        if uso and hasattr(uso, 'output_tokens'):
                            state['usage']['completion_tokens'] += uso.output_tokens
                            state['usage']['total_tokens'] += uso.output_tokens
                        if hasattr(chunk.delta, "stop_reason"):
                            state['finish_reason'] = chunk.delta.stop_reason
                else:
                    # usage（若模型支持在流中返回）
                    try:
                        if hasattr(chunk, 'usage') and chunk.usage:
                            state['usage'] = {
                                'prompt_tokens': int(getattr(chunk.usage, 'prompt_tokens', 0) or 0),
                                'completion_tokens': int(getattr(chunk.usage, 'completion_tokens', 0) or 0),
                                'total_tokens': int(getattr(chunk.usage, 'total_tokens', 0) or 0),
                            }
                    except Exception:
                        pass
    
                    if chunk.choices and len(chunk.choices) > 0:
                        try:
                            fr = getattr(chunk.choices[0], 'finish_reason', None)
                            if fr:
                                state['finish_reason'] = fr
                        except Exception:
                            pass
    
                        delta = getattr(chunk.choices[0], 'delta', None)
                        content = getattr(delta, 'content', None) if delta else None
                        if content:
                            state['text'] += content
                            yield content

        cover_prompt = f"""
请只生成报告封面，不生成目录和正文章节。
用户需求：{user_input}
"""
        cover_state = {}
        for chunk in _stream_once(base_messages + [{"role": "user", "content": cover_prompt}], max_tokens=2500, state=cover_state):
            yield chunk
        cover_text = (cover_state.get('text') or '').strip()
        u1 = cover_state.get('usage') or {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
        self._acc_usage(usage_total, u1)
        if cover_text:
            yield "\n\n"

        generated_parts = [cover_text] if cover_text else []
        generated_heads = []
        chapter_plan_heads = [self._chapter_heading(no, title) for no, title in chapter_plan]

        for chapter_no, chapter_title in chapter_plan:
            heading = self._chapter_heading(chapter_no, chapter_title)
            generated_heads.append(heading)
            yield f"[按章节生成] 正在生成：{heading}\n"
            context_guide = self._build_report_context_guide(
                user_input=user_input,
                current_heading=heading,
                completed_heads=generated_heads[:-1],
                chapter_plan_heads=chapter_plan_heads,
                report_parts=generated_parts
            )
            chapter_prompt = f"""
请只生成当前这一章：{heading}
用户需求：{user_input}
已完成章节：{", ".join(generated_heads[:-1]) if len(generated_heads) > 1 else "无"}
禁止输出下一章标题；严禁待续和占位词。
{context_guide}
"""
            chapter_state = {}
            chapter_text_raw = ""
            for chunk in _stream_once(base_messages + [{"role": "user", "content": chapter_prompt}], state=chapter_state):
                chapter_text_raw += chunk
                yield chunk
            chapter_text = chapter_text_raw
            u2 = chapter_state.get('usage') or {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
            self._acc_usage(usage_total, u2)
            chapter_block = self._extract_single_chapter(chapter_text, chapter_no, chapter_title)
            
            chapter_len = self._get_text_length_without_mermaid(chapter_block)
            completeness = self._check_chapter_completeness(chapter_block)
            
            if chapter_len < 1800 or completeness['needs_continuation']:
                yield "\n[章节续写] 检测到内容不完整，正在续写...\n"
                enrich_guide = self._build_report_context_guide(
                    user_input=user_input,
                    current_heading=heading,
                    completed_heads=generated_heads[:-1],
                    chapter_plan_heads=chapter_plan_heads,
                    report_parts=generated_parts + [chapter_block]
                )
                
                if chapter_len < 1800:
                    enrich_prompt = f"""
请对下面这一章进行深化扩写，仅限这一章，不得新增其它章节标题：

{chapter_block}

{enrich_guide}

要求：
1. 保留当前章节标题"{heading}"不变。
2. 增加方法、步骤、约束、数据口径、风险控制、实施节奏等细节。
3. 输出完整章节正文。
"""
                else:
                    last_200_chars = chapter_block[-200:] if len(chapter_block) > 200 else chapter_block
                    enrich_prompt = f"""
上一章内容被截断，请继续完成"{heading}"的剩余内容。

已生成内容摘要：{last_200_chars}

{enrich_guide}

要求：
1. 只输出剩余内容，不要重复已输出的部分。
2. 继续完成当前章节，不得新增其它章节标题。
3. 确保内容完整，以完整句子结尾。
"""
                enrich_state = {}
                for chunk in _stream_once(base_messages + [{"role": "user", "content": enrich_prompt}], max_tokens=6000, state=enrich_state):
                    yield chunk
                u3 = enrich_state.get('usage') or {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
                self._acc_usage(usage_total, u3)
                enriched = enrich_state.get('text', '')
                if chapter_len < 1800:
                    chapter_block = self._extract_single_chapter(enriched, chapter_no, chapter_title)
                else:
                    continuation = enriched.strip()
                    if continuation:
                        chapter_block = chapter_block.rstrip() + "\n\n" + continuation
            
            generated_parts.append(chapter_block.strip())
            yield "\n\n"
            if chapter_state.get('finish_reason'):
                self._last_finish_reason = chapter_state.get('finish_reason')

        yield "[按章节生成] 正在生成目录...\n"
        all_chapters_text = "\n\n".join([p for p in generated_parts if p])
        toc_text = self._generate_toc(all_chapters_text)
        if toc_text:
            for char in toc_text:
                yield char
            yield "\n\n"

        final_report = "\n\n".join([p for p in generated_parts if p]).strip()
        if toc_text:
            cover_only = generated_parts[0] if generated_parts else ""
            chapters_only = "\n\n".join([p for p in generated_parts[1:] if p]).strip()
            final_report = cover_only + "\n\n" + toc_text + "\n\n" + chapters_only
        total_chars = self._get_text_length_without_mermaid(final_report)
        done_mark = f"【报告已完成】\n总字数：{total_chars}字符\n包含章节：第一章至第十章（全部完成）"
        yield done_mark
        self.last_usage = usage_total

    def _retrieve_rag_context(self, query: str, top_k: int = 3) -> list:
        """
        从RAG知识库检索相关上下文

        Args:
            query: 查询文本
            top_k: 返回前K个结果

        Returns:
            检索结果列表，每个元素包含chunk_text, score, title, filename, chunk_index
        """
        try:
            from query_rag import query as rag_query
            from pathlib import Path

            rag_db_path = Path(__file__).parent / 'knowledge_base' / 'rag.db'
            if not rag_db_path.exists():
                print(f"[RAG] 知识库不存在: {rag_db_path}")
                return []

            print(f"[RAG] 检索查询: {query[:100]}...")
            results = rag_query(str(rag_db_path), query, top_k=top_k)

            formatted_results = []
            for row in results:
                formatted_results.append({
                    'chunk_text': row.get('chunk_text', ''),
                    'score': float(row.get('score', 0.0)),
                    'title': row.get('title', ''),
                    'filename': row.get('filename', ''),
                    'chunk_index': row.get('chunk_index', 0)
                })

            print(f"[RAG] 检索到 {len(formatted_results)} 个相关文档")
            return formatted_results

        except Exception as e:
            print(f"[RAG] 检索失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def chat(self, user_input: str, conversation_history: Optional[list] = None) -> Tuple[str, dict]:
        """
        处理用户输入并返回模型回复

        Args:
            user_input: 用户的自然语言输入
            conversation_history: 可选的对话历史记录

        Returns:
            (模型的回复文本, token使用信息字典)
        """
        try:
            # 【新增】在处理开始时检测并存储报告类型
            report_type = self._get_report_type(user_input)
            setattr(self, '_current_report_type', report_type)
            print(f'[DEBUG] 检测到报告类型: {report_type}')

            # RAG检索：优先从知识库获取相关上下文
            rag_sources = self._retrieve_rag_context(user_input, top_k=3)
            setattr(self, '_last_rag_sources', rag_sources)

            # 报告请求优先走"按章节生成"链路，避免整篇一次生成导致自动缩减和循环续写。
            if self._is_report_request(user_input):
                reply, usage_info = self._generate_report_by_chapter(user_input, conversation_history)
                return reply, usage_info

            messages = []

            # 添加系统提示词（可选）
            if self.config.system_prompt:
                messages.append({
                    "role": "system",
                    "content": self.config.system_prompt
                })

            # 添加对话历史
            if conversation_history:
                messages.extend(conversation_history)

            # 构建增强输入（集成RAG上下文）
            enhanced_input = user_input
            if rag_sources:
                context_parts = []
                for i, source in enumerate(rag_sources, 1):
                    chunk_preview = source['chunk_text'][:500]
                    context_parts.append(f"【参考文档{i}】{source['title']}\n内容: {chunk_preview}...")
                rag_context = "\n\n".join(context_parts)
                enhanced_input = f"""参考以下文档回答用户问题：\n\n{rag_context}\n\n用户问题: {user_input}"""
            
            # 针对自定义模型，增强提示词以生成更详细的内容
            is_custom_model = self.config.provider == ModelProvider.CUSTOM
            
            if self._is_report_request(user_input) and self.report_template:
                template_context = f"""
【重要提示】请严格按照以下《可行性研究报告模板》的格式和结构来撰写报告：

{self.report_template}

---

现在请根据用户的要求，严格按照上述模板的格式和结构撰写可行性研究报告。请将模板中的`{{}}`占位符替换为实际的项目信息，并参考模板中的注释说明确保内容完整和专业。

**⚠️ 重要要求 - 必须严格遵守：**

**首先，必须生成封面和目录：**

1. **封面格式**：
   - 居中显示项目名称和"可行性研究报告"（格式：`{{项目名称}}可行性研究报告`）
   - 右下角显示编制单位和编制日期
   - 封面要简洁、专业、规范

2. **目录格式**（必须极其详细）：
   - 目录标题为"目录"
   - 每个章节格式为：`章节名称................................................................页码`
   - 使用点号（.）连接章节名称和页码，点号数量要足够，使页码右对齐
   - **⚠️ 目录必须包含所有层级：一级标题（章节）、二级标题（节）、三级标题（小节）、四级标题（要点），这是硬性要求**
   - **⚠️ 每个主要章节下必须列出所有子章节（如1.1、1.2、1.3等），每个子章节下必须列出所有小节（如1.1.1、1.1.2等），每个小节下必须列出主要要点（如1.1.1.1、1.1.1.2等）**
   - **⚠️ 目录条目总数必须达到150-200条以上，确保每个章节都有详细的子条目**
   - **⚠️ 每个主要章节（第一章到第十章）在目录中至少要有15-25个子条目**
   - 页码从正文第一章开始编号（第一章为第1页）
   - 目录要完整、准确，与实际章节结构完全一致
   - **⚠️ 目录必须反映报告的完整结构，不能简略，必须详细到每个要点**

**然后，生成报告正文：**

3. **报告总字数必须达到48000-50000字（约4.8-5万字），每个主要章节至少4000-5000字，总行数达到1700-1800行，这是硬性要求**
4. **每个章节都必须有详细内容，严禁只有目录标题而没有具体内容**
5. **每个一级标题（章节）下必须包含至少5-8个二级标题（节），每个二级标题下必须包含至少3-5个三级标题（小节），每个三级标题下必须包含至少2-3个四级标题（要点）**
6. **每个子章节必须包含至少5-8段详细内容，每段至少200-400字，提供具体的数据、案例、分析、图表说明**
7. **每个段落都要详细展开，不能只有几句话就结束，每个段落至少200-400字**
8. **对于每个概念、每个数据、每个分析，都要详细解释其来源、意义、影响、应用、趋势，至少200-300字**
9. **严禁只列出目录结构而不填充具体内容，每个标题下都必须有实质性内容：**
   - **一级标题（章节）下至少4000-5000字**
   - **二级标题（节）下至少1500-2000字**
   - **三级标题（小节）下至少800-1200字**
   - **四级标题（要点）下至少400-600字**
10. **严禁使用"详见下文"、"待补充"、"略"、"部分"、"一些"、"若干"等简略或模糊表述，所有内容必须当场详细写出**
11. **如果某个部分内容不够详细，必须继续展开，直到达到要求的字数**
12. **每个数据都要有详细的说明：数据来源、计算方法、计算过程、影响因素、趋势分析、历史对比、预测依据，每个数据至少300-500字**
13. **每个案例都要详细描述：背景、过程、结果、启示、应用、经验教训、可借鉴之处，每个案例至少500-800字**
14. **每个分析都要从多个角度展开：背景、现状、问题、原因、影响、趋势、对策、实施步骤、资源配置、风险控制、效果评估，每个角度至少200-300字**

**⚠️⚠️⚠️ 图表要求（极其重要 - 必须包含大量Mermaid图表，这是硬性要求）⚠️⚠️⚠️：**
报告必须包含大量Mermaid图表，**整个报告必须包含至少30-50个图表**，不能少于30个。**每个图表都要有详细的说明文字（至少200-300字），解释图表含义、数据来源、分析结论**。

**⚠️⚠️⚠️ 极其重要：必须使用Mermaid图表语法，并且要确保语法正确！所有图表都必须用```mermaid代码块包裹！格式必须是：**
```
```mermaid
图表代码
```
```
- **⚠️⚠️⚠️ 绝对禁止：不能只写文字描述图表，不能使用"如下图表"、"见下图"等描述，必须直接生成完整的```mermaid代码块！**
- **⚠️⚠️⚠️ 如果生成的图表没有用```mermaid代码块包裹，该图表无效，必须重新生成！**

**图表类型要求（必须包含以下15种类型的图表，每种至少使用8-12次）：**
1. **柱形图（Bar Chart）** - 使用 `xychart-beta` 语法，用于展示分类数据对比，如投资金额、收益对比、市场份额等
2. **折线图（Line Chart）** - 使用 `xychart-beta` 语法，用于展示数据趋势，如收益增长趋势、成本变化趋势等
3. **饼图（Pie Chart）** - 使用 `pie` 语法，用于展示占比关系，如投资结构、收入构成、市场份额分布等
4. **条形图（Horizontal Bar Chart）** - 使用 `xychart-beta` 语法，用于横向对比，如风险等级对比、成本结构对比等
5. **面积图（Area Chart）** - 使用 `xychart-beta` 语法，用于展示累积数据，如累计投资、累计收益等
6. **XY散点图（Scatter Plot）** - 使用 `xychart-beta` 语法，用于展示两个变量之间的关系，如价格与需求关系等
7. **流程图（Flowchart）** - 使用 `flowchart TD` 或 `graph TD` 语法，用于展示流程、步骤、决策流程等
8. **树状图（Tree Diagram）** - 使用 `flowchart TD` 语法，用于展示层级结构，如组织架构、技术架构等
9. **甘特图（Gantt Chart）** - 使用 `gantt` 语法，用于展示项目时间计划、进度安排等
10. **序列图（Sequence Diagram）** - 使用 `sequenceDiagram` 语法，用于展示时间序列、交互流程等
11. **状态图（State Diagram）** - 使用 `stateDiagram-v2` 语法，用于展示状态转换、生命周期等
12. **类图（Class Diagram）** - 使用 `classDiagram` 语法，用于展示类关系、系统架构等
13. **实体关系图（ER Diagram）** - 使用 `erDiagram` 语法，用于展示数据关系、数据库结构等
14. **用户旅程图（User Journey）** - 使用 `journey` 语法，用于展示用户流程、体验路径等
15. **Git图（Git Graph）** - 使用 `gitgraph` 语法，用于展示版本控制、开发流程等

**⚠️ 图表语法要求（必须严格遵守，确保语法正确）：**
- 所有图表必须使用正确的Mermaid语法，格式为：
```mermaid
图表类型代码
```
- **柱形图/折线图/条形图/面积图/散点图**必须使用 `xychart-beta` 语法，格式如下：
```mermaid
xychart-beta
    title "图表标题"
    x-axis ["类别1", "类别2", "类别3"]
    y-axis "Y轴标签" 0 --> 100
    bar [10, 20, 30]
```
- **饼图**必须使用 `pie` 语法，格式如下：
```mermaid
pie title "图表标题"
    "标签1" : 数值1
    "标签2" : 数值2
    "标签3" : 数值3
```
- **流程图/树状图**必须使用 `flowchart TD` 或 `graph TD` 语法，格式如下：
```mermaid
flowchart TD
    A[节点1] --> B[节点2]
    B --> C[节点3]
```
- **⚠️ 重要：生成图表后，必须检查语法是否正确，确保图表能够正常渲染！**
- **⚠️ 如果图表语法有错误，必须修正后再继续生成！**

**⚠️⚠️⚠️ 图表分布要求（每个章节必须包含大量图表，这是硬性要求，绝对不能违反）⚠️⚠️⚠️：**

**绝对要求：每个章节都必须包含图表，不能有任何章节没有图表！在生成每个章节时，必须立即生成该章节要求的图表，不能只写文字！生成图表后必须检查语法是否正确！**

- **第一章 项目概述**：**必须包含至少3-5个图表**，包括：流程图（项目结构，flowchart TD）、饼图（投资结构，pie）、象限图（项目优势，quadrantChart）、柱形图（对比分析，xychart-beta bar）、折线图（发展趋势，xychart-beta line）、甘特图（项目计划，gantt）、思维导图（利益相关者，mindmap）等。**⚠️ 在生成第一章时，必须立即生成至少15个图表，不能只写文字！生成后检查Mermaid语法！**

- **第二章 项目建设背景及必要性**：**必须包含至少18-25个图表**，包括：折线图（历史趋势，xychart-beta line）、柱形图（市场对比，xychart-beta bar）、饼图（市场分布，pie）、柱形图（累积数据，xychart-beta bar）、流程图（区域分析，flowchart LR）、折线图（相关性分析，xychart-beta line）、柱形图（横向对比，xychart-beta bar）、时间轴（发展历程，timeline）等。**⚠️ 在生成第二章时，必须立即生成至少18个图表，不能只写文字！生成后检查Mermaid语法！**

- **第三章 项目需求分析与产出方案**：**必须包含至少20-28个图表**，包括：柱形图（需求优先级，xychart-beta bar）、折线图（需求趋势，xychart-beta line）、流程图（需求关联，flowchart TD）、思维导图（需求层级，mindmap）、饼图（需求分布，pie）、流程图（需求流程，flowchart TD）、柱形图（需求分布，xychart-beta bar）等。**⚠️ 在生成第三章时，必须立即生成至少20个图表，不能只写文字！生成后检查Mermaid语法！**

- **第四章 项目选址与要素保障**：**必须包含至少18-25个图表**，包括：柱形图（选址对比，xychart-beta bar）、柱形图（要素分布，xychart-beta bar）、流程图（要素结构，flowchart TD）、流程图（选址流程，flowchart TD）、饼图（要素占比，pie）、柱形图（要素对比，xychart-beta bar）、象限图（要素评估，quadrantChart）、折线图（要素趋势，xychart-beta line）等。**⚠️ 在生成第四章时，必须立即生成至少18个图表，不能只写文字！生成后检查Mermaid语法！**

- **第五章 项目建设方案**：**必须包含至少22-30个图表**，包括：流程图（建设结构，flowchart TD）、流程图（建设流程，flowchart TD）、柱形图（方案对比，xychart-beta bar）、甘特图（时间计划，gantt）、序列图（建设时序，sequenceDiagram）、状态图（建设状态，stateDiagram-v2）、折线图（进度计划，xychart-beta line）、饼图（资源分配，pie）等。**⚠️ 在生成第五章时，必须立即生成至少22个图表，不能只写文字！生成后检查Mermaid语法！**

- **第六章 项目运营方案**：**必须包含至少20-28个图表**，包括：流程图（运营结构，flowchart TD）、饼图（运营成本，pie）、折线图（运营趋势，xychart-beta line）、实体关系图（运营关系，erDiagram）、状态图（运营状态，stateDiagram-v2）、柱形图（运营对比，xychart-beta bar）、折线图（运营累积，xychart-beta line）、流程图（运营流程，flowchart TD）等。**⚠️ 在生成第六章时，必须立即生成至少20个图表，不能只写文字！生成后检查Mermaid语法！**

- **第七章 项目投融资与财务方案**：**必须包含至少8-10个图表**（此章节应包含最多图表），包括：柱形图（投资对比，xychart-beta bar）、折线图（收益趋势，xychart-beta line）、柱形图（投资构成，xychart-beta bar）、饼图（投资结构，pie）、折线图（累计收益，xychart-beta line）、柱形图（风险分布，xychart-beta bar）、折线图（投资收益关系，xychart-beta line）、柱形图（成本分布，xychart-beta bar）、象限图（财务指标，quadrantChart）、思维导图（财务结构，mindmap）、流程图（财务关系，flowchart LR）等。**⚠️ 在生成第七章时，必须立即生成至少40个图表，不能只写文字！生成后检查Mermaid语法！**

- **第八章 项目影响效果分析**：**必须包含至少20-28个图表**，包括：象限图（影响评估，quadrantChart）、柱形图（影响对比，xychart-beta bar）、饼图（影响分布，pie）、折线图（影响趋势，xychart-beta line）、流程图（影响关系，flowchart TD）、柱形图（影响指标，xychart-beta bar）、思维导图（影响结构，mindmap）、时间轴（影响时序，timeline）等。**⚠️ 在生成第八章时，必须立即生成至少20个图表，不能只写文字！生成后检查Mermaid语法！**

- **第九章 项目风险管控方案**：**必须包含至少22-30个图表**，包括：象限图（风险分布，quadrantChart）、柱形图（风险影响，xychart-beta bar）、柱形图（风险等级，xychart-beta bar）、流程图（风险关系，flowchart TD）、思维导图（风险结构，mindmap）、折线图（风险趋势，xychart-beta line）、饼图（风险分布，pie）、流程图（风险应对流程，flowchart TD）等。**⚠️ 在生成第九章时，必须立即生成至少22个图表，不能只写文字！生成后检查Mermaid语法！**

- **第十章 研究结论及建议**：**必须包含至少20-28个图表**，包括：柱形图（综合评估，xychart-beta bar）、思维导图（建议优先级，mindmap）、流程图（实施流程，flowchart TD）、流程图（建议关系，flowchart LR）、思维导图（建议结构，mindmap）、象限图（综合评估，quadrantChart）、折线图（实施趋势，xychart-beta line）、饼图（建议分布，pie）等。**⚠️ 在生成第十章时，必须立即生成至少20个图表，不能只写文字！生成后检查Mermaid语法！**

**⚠️⚠️⚠️ 图表总数要求（极其重要，绝对不能违反）⚠️⚠️⚠️：**
- **整个报告必须包含至少30-50个图表**，这是硬性要求，不能少于30个
- **每个主要章节（第一章到第十章）必须包含至少3-5个图表**（第七章必须包含8-10个图表）
- **每个子章节（如1.1、1.2等）必须包含至少3-5个图表**
- **每种图表类型（15种基本类型）在整个报告中至少使用10-15次**
- **⚠️⚠️⚠️ 绝对要求：在生成每个章节时，必须立即生成该章节要求的所有图表，不能只写文字！如果某个章节没有图表，该章节就不完整！生成图表后必须检查语法是否正确！**
- **⚠️ 重要：如果生成的图表数量少于150个，必须继续生成更多图表，直到达到要求**
- **图表必须均匀分布在各个章节中，不能集中在某几个章节，每个章节都必须有图表**
- **每个图表都要有详细的说明文字（至少200-300字），解释图表含义、数据来源、分析结论**
- **⚠️ 生成规则：在写每个章节的内容时，每写2-3段文字后，必须插入1-2个图表，然后再继续写文字，确保图表均匀分布在整个章节中**

**图表格式要求：**
- 所有图表使用Mermaid语法，格式为：
```mermaid
图表类型代码
```
- 每个图表必须包含：
  - 清晰的标题（在图表前后说明）
  - 详细的说明文字（至少200-300字，解释图表含义、数据来源、分析结论）
  - 准确的数据（与文字描述完全一致）
  - 适当的标注（坐标轴标签、图例、数据标签等）
- 图表中的数据必须与文字描述完全一致，不能有矛盾
- 每个图表都要说明数据来源（如XX统计年鉴、XX研究报告等）
- 每个图表都要有深入的分析，不能只是简单展示数据
- **⚠️⚠️⚠️ 极其重要：严禁生成没有代码块的图表描述，所有图表都必须用```mermaid代码块包裹！格式必须是：**
```
```mermaid
图表代码
```
```
- **⚠️⚠️⚠️ 绝对禁止：不能只写文字描述图表，不能使用"如下图表"、"见下图"等描述，必须直接生成完整的```mermaid代码块！**
- **⚠️⚠️⚠️ 每个图表都必须严格按照以下格式生成，不能有任何偏差：**
```
```mermaid
xychart-beta
    title "图表标题"
    x-axis ["类别1", "类别2", "类别3"]
    y-axis "Y轴标签" 0 --> 100
    bar [10, 20, 30]
```
```
- **⚠️ 生成图表后，必须检查Mermaid语法是否正确，确保图表能够正常渲染！如果语法有错误，必须修正！**
- **⚠️⚠️⚠️ 如果生成的图表没有用```mermaid代码块包裹，该图表无效，必须重新生成！**

用户要求：
{user_input}
"""
                enhanced_input = template_context
            elif self._is_report_request(user_input) and not self.report_template:
                # 如果模板文件不存在，给出提示
                enhanced_input = f"""{user_input}

【提示】系统检测到您要撰写可行性研究报告，但未找到模板文件"可行性研究报告模板.md"。请确保模板文件存在于项目目录中，以便系统能够按照标准格式生成报告。"""
            
            # 针对自定义模型，在非报告请求时也增强提示词，要求详细回答
            if is_custom_model and not self._is_report_request(user_input):
                # 为自定义模型添加详细生成提示
                detailed_prompt = f"""{enhanced_input}

【⚠️⚠️⚠️ 极其重要的提示 - 必须生成极其详细、完整、深入的回答 ⚠️⚠️⚠️】

**这是自定义模型，必须生成比普通模型更详细、更完整、更深入的回答！**

**⚠️ 内容详细度要求（这是硬性要求，必须严格遵守，绝对不能简略）：**

1. **字数要求（必须达到，这是最低标准）：**
   - **回答总字数必须达到3000-8000字**，这是最低要求，越多越好
   - **每个主要要点至少800-1500字**，不能少于800字
   - **每个段落至少300-500字**，不能只有几句话
   - **每个子要点至少500-800字**，要充分展开
   - **如果回答少于3000字，必须继续展开，直到达到要求**
   - **不要因为担心输出长度而简化回答，要完整详细地生成所有内容**

2. **内容展开要求（必须详细，这是自定义模型的核心要求）：**
   - **不要只给出简短的回答**，要详细解释每个要点，每个要点都要充分展开
   - **每个要点都要从多个角度详细展开**：背景、定义、原理、现状、问题、原因、影响、趋势、案例、数据、分析、对策、建议、实施步骤、资源配置、风险控制、效果评估等，每个角度至少200-300字
   - **每个概念都要详细解释**：含义、特点、分类、应用、意义、影响、发展趋势、实际案例等，至少300-500字
   - **每个数据都要详细说明**：来源、计算方法、计算过程、公式推导、影响因素、趋势分析、历史对比、预测依据等，至少250-400字
   - **每个案例都要详细描述**：背景、过程、结果、启示、应用、经验教训、可借鉴之处等，至少500-800字
   - **每个步骤都要详细说明**：具体操作、注意事项、可能问题、解决方案、所需资源、时间安排、责任人等，每个步骤至少300-500字

3. **具体信息要求（必须包含）：**
   - **包含具体的数据**：精确的数字、百分比、增长率等，不能使用"一些"、"若干"、"较多"等模糊表述
   - **包含具体的案例**：真实的案例、实际的应用、具体的项目等
   - **包含具体的步骤**：详细的操作步骤、实施流程、执行计划等
   - **包含具体的分析**：深入的分析、详细的推理、完整的逻辑链条等
   - **包含具体的计算**：详细的计算过程、公式推导、参数说明等

4. **结构要求（必须清晰）：**
   - **使用多级标题**：一级标题、二级标题、三级标题等，使结构清晰
   - **使用段落分隔**：每个要点用独立段落，每个段落至少300-500字
   - **使用列表说明**：用列表展示要点，每个列表项至少150-300字
   - **使用图表展示**：用Mermaid图表展示数据对比，每个图表要有详细说明，必须用```mermaid代码块包裹

5. **专业深入要求（必须达到）：**
   - **对于专业问题**：要提供深入的分析和解释，包含理论基础、实践应用、发展趋势等
   - **对于技术问题**：要详细说明技术原理、技术参数、技术优势、技术难点、解决方案等
   - **对于分析问题**：要从多个维度分析，包含定量分析、定性分析、对比分析、趋势分析等
   - **对于建议问题**：要提供具体的、可操作的、有步骤的建议，包含实施计划、资源配置、风险控制等

6. **严禁简略（绝对不能）：**
   - **严禁使用"略"、"详见"、"待补充"、"一些"、"若干"、"较多"、"部分"等简略或模糊表述**
   - **严禁只写标题不写内容**
   - **严禁只有结论没有过程**
   - **严禁只有概述没有细节**
   - **所有内容都要详细写出，不能省略任何部分**

**⚠️ 数据展示要求（必须包含至少一种表格）：**
必须在回答中包含至少一种以下类型的图表（使用Mermaid语法）：
- 投资估算表、收益预测表、成本分析表、财务指标表、市场对比表、风险评估表、设备清单表、人员配置表、时间计划表、数据统计表、政策对比表、技术参数表、效益分析表、资源需求表、综合对比表等

**图表格式要求：**
- **⚠️⚠️⚠️ 极其重要：所有图表必须使用```mermaid代码块格式，格式如下：**
```
```mermaid
图表类型代码
```
```
- **⚠️⚠️⚠️ 绝对禁止：不能只写文字描述图表，不能使用"如下图表"、"见下图"等描述，必须直接生成完整的```mermaid代码块！**
- **⚠️⚠️⚠️ 如果生成的图表没有用```mermaid代码块包裹，该图表无效，必须重新生成！**
- 图表必须与回答内容相关，用于可视化数据、流程、关系等
- 图表要有清晰的标题和说明（至少200-300字）
- 如果涉及数据，图表中的数据要与文字描述一致
- **⚠️⚠️⚠️ 极其重要：必须使用Mermaid图表语法，并且要确保语法正确！所有图表都必须用```mermaid代码块包裹！格式必须是：**
```
```mermaid
图表代码
```
```
- **⚠️⚠️⚠️ 绝对禁止：不能只写文字描述图表，不能使用"如下图表"、"见下图"等描述，必须直接生成完整的```mermaid代码块！**
- **⚠️⚠️⚠️ 如果生成的图表没有用```mermaid代码块包裹，该图表无效，必须重新生成！**
- **⚠️ 生成图表后，必须检查Mermaid语法是否正确，确保图表能够正常渲染！如果语法有错误，必须修正！**

**⚠️ 最终要求（必须严格遵守）：**
- **回答总字数必须达到3000-8000字（越多越好）**
- **每个要点必须详细展开，不能简略，每个要点至少800-1500字**
- **必须包含至少一种图表（使用Mermaid语法）**
- **必须提供具体的数据、案例、分析，不能使用模糊表述**
- **必须从多个角度深入分析，每个角度都要详细展开**
- **必须提供详细的实施步骤、资源配置、风险控制等具体信息**
- **严禁使用"略"、"详见"、"待补充"、"一些"、"若干"等简略或模糊表述**

**⚠️ 重要提醒：这是自定义模型，必须生成比普通模型更详细、更完整、更深入的回答！不要因为担心输出长度而简化回答，要完整详细地生成所有内容！**

**请立即开始生成极其详细、完整、深入的回答，确保达到上述所有要求！字数越多越好，内容越详细越好！**"""
                enhanced_input = detailed_prompt
            
            # 添加当前用户输入（可能已增强）
            messages.append({
                "role": "user",
                "content": enhanced_input
            })
            
            # 调用API
            # 针对自定义模型，调整参数以生成更详细的内容
            temperature = self.config.temperature
            max_tokens = self.config.max_tokens
            
            if is_custom_model:
                # 自定义模型使用更高的temperature以增加创造性，但不超过0.95
                temperature = min(temperature * 1.1, 0.95)
                # 确保max_tokens足够大，至少16000，确保生成详细内容
                if max_tokens < 16000:
                    max_tokens = 16000
            
            if self.config.provider == ModelProvider.ANTHROPIC:
                sys_msg = ""
                anthropic_messages = []
                for msg in messages:
                    if msg.get("role") == "system":
                        sys_msg = msg.get("content", "")
                    else:
                        anthropic_messages.append(msg)
                
                response = self.client.messages.create(
                    model=self.config.model_name,
                    system=sys_msg,
                    messages=anthropic_messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                reply = response.content[0].text if response and hasattr(response, 'content') and len(response.content) > 0 else ""
                finish_reason = response.stop_reason if hasattr(response, 'stop_reason') else None
                usage_info = {
                    'prompt_tokens': getattr(response.usage, 'input_tokens', 0) if hasattr(response, 'usage') and response.usage else 0,
                    'completion_tokens': getattr(response.usage, 'output_tokens', 0) if hasattr(response, 'usage') and response.usage else 0,
                    'total_tokens': (getattr(response.usage, 'input_tokens', 0) + getattr(response.usage, 'output_tokens', 0)) if hasattr(response, 'usage') and response.usage else 0
                }
            else:
                response = self.client.chat.completions.create(
                    model=self.config.model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                # 提取回复
                reply = response.choices[0].message.content
                finish_reason = response.choices[0].finish_reason
                
                # 提取token使用信息
                usage_info = {
                    'prompt_tokens': getattr(response.usage, 'prompt_tokens', 0) if hasattr(response, 'usage') and response.usage else 0,
                    'completion_tokens': getattr(response.usage, 'completion_tokens', 0) if hasattr(response, 'usage') and response.usage else 0,
                    'total_tokens': getattr(response.usage, 'total_tokens', 0) if hasattr(response, 'usage') and response.usage else 0
                }

            self.last_usage = usage_info
            
            # 检测是否被截断，如果是报告请求则自动续写
            is_report = self._is_report_request(user_input)
            if is_report and self._is_content_truncated(reply, finish_reason, is_report=True):  # 已恢复续写
                pass  # 静默续写，不显示提示
                # 初始化续写token累计
                self._continuation_usage = {
                    'prompt_tokens': usage_info['prompt_tokens'],
                    'completion_tokens': usage_info['completion_tokens'],
                    'total_tokens': usage_info['total_tokens']
                }
                reply = self._continue_writing(reply, user_input, conversation_history)
                # 更新token使用信息为累计值
                if hasattr(self, '_continuation_usage') and self._continuation_usage:
                    usage_info = self._continuation_usage.copy()
                    self.last_usage = usage_info
                pass  # print("\n[续写完成]", flush=True)
            
            # 如果是报告请求，保存为文件
            if is_report:
                save_info = self._save_report(reply, user_input)
                if save_info:
                    download_url = save_info.get('download_url', '')
                    filename = save_info.get('filename', '')
                    reply += f"\n\n---\n✅ **报告已生成并保存**\n📁 文件名: `{filename}`\n🔗 下载链接: {download_url}"
            
            return reply, usage_info
            
        except Exception as e:
            error_msg = str(e)
            self.last_usage = None
            
            # 检查是否是模型未找到错误
            if "422" in error_msg or "Model not found" in error_msg or "model" in error_msg.lower():
                detailed_error = f"""错误: 模型未找到

当前配置的模型名称: {self.config.model_name}
API地址: {self.config.base_url}

可能的原因：
1. 模型名称不正确，API服务器上可能没有 '{self.config.model_name}' 这个模型
2. 请检查API服务器上实际可用的模型名称

解决方法：
1. 运行检查脚本查看可用模型: ./检查可用模型.sh
2. 或手动测试: curl {self.config.base_url}/models
3. 根据实际模型名称更新 MODEL_NAME 环境变量

原始错误信息: {error_msg}"""
                return detailed_error, {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
            
            return f"错误: {error_msg}", {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
    
    def chat_stream(self, user_input: str, conversation_history: Optional[list] = None):
        """
        流式处理用户输入并返回模型回复（逐字输出）

        Args:
            user_input: 用户的自然语言输入
            conversation_history: 可选的对话历史记录

        Yields:
            模型的回复文本片段
        """
        try:
            # 【新增】在处理开始时检测并存储报告类型
            report_type = self._get_report_type(user_input)
            setattr(self, '_current_report_type', report_type)
            print(f'[DEBUG] [STREAM] 检测到报告类型: {report_type}')

            # RAG检索：优先从知识库获取相关上下文
            rag_sources = self._retrieve_rag_context(user_input, top_k=3)
            setattr(self, '_last_rag_sources', rag_sources)

            # 流式报告请求改为章节级流式输出，减少截断与跨章串写。
            if self._is_report_request(user_input):
                for chunk in self._generate_report_by_chapter_stream(user_input, conversation_history):
                    yield chunk
                return

            messages = []

            if self.config.system_prompt:
                messages.append({
                    "role": "system",
                    "content": self.config.system_prompt
                })

            if conversation_history:
                messages.extend(conversation_history)

            # 构建增强输入（集成RAG上下文）
            enhanced_input = user_input
            if rag_sources:
                context_parts = []
                for i, source in enumerate(rag_sources, 1):
                    chunk_preview = source['chunk_text'][:500]
                    context_parts.append(f"【参考{i}】{source['title']}\n{chunk_preview}...")
                rag_context = "\n\n".join(context_parts)
                enhanced_input = f"""参考文档:\n{rag_context}\n\n问题: {user_input}"""
            
            # 针对自定义模型，增强提示词以生成更详细的内容
            is_custom_model = self.config.provider == ModelProvider.CUSTOM
            
            if self._is_report_request(user_input) and self.report_template:
                template_context = f"""
【重要提示】请严格按照以下《可行性研究报告模板》的格式和结构来撰写报告：

{self.report_template}

---

【详细生成要求 - 必须严格遵守】

请根据用户的要求，严格按照上述模板的格式和结构撰写一份**详细、完整、深入**的可行性研究报告。这是一份专业报告，必须达到4.8-5万字的详细程度。

**⚠️ 重要：不要因为输出限制而简化回答，请完整详细地生成所有内容，即使内容很长也要完整输出！**

**⚠️ 首先必须生成封面和目录：**

1. **封面**：
   - 居中显示：`{{项目名称}}可行性研究报告`
   - 右下角显示：编制单位和编制日期
   - 封面格式要专业、规范

2. **目录**（必须极其详细，这是硬性要求）：
   - 目录标题为"目录"
   - 每个章节格式：`章节名称................................................................页码`
   - 使用点号（.）连接章节名称和页码，使页码右对齐
   - **⚠️ 目录必须包含所有层级：一级标题（章节）、二级标题（节）、三级标题（小节）、四级标题（要点），这是硬性要求**
   - **⚠️ 每个主要章节下必须列出所有子章节（如1.1、1.2、1.3等），每个子章节下必须列出所有小节（如1.1.1、1.1.2等），每个小节下必须列出主要要点（如1.1.1.1、1.1.1.2等）**
   - **⚠️ 目录条目总数必须达到150-200条以上，确保每个章节都有详细的子条目**
   - **⚠️ 每个主要章节（第一章到第十章）在目录中至少要有15-25个子条目**
   - 页码从正文第一章开始编号
   - 目录要完整、准确，与实际章节结构完全一致
   - **⚠️ 重要：目录必须与实际报告内容完全一致，不能有"（待续……）"等占位符**
   - **⚠️ 目录中的章节名称必须与正文中的章节标题完全一致**
   - **⚠️ 目录必须反映报告的完整结构，不能简略，必须详细到每个要点**

**然后生成报告正文：**

**⚠️ 重要警告：严禁简略、严禁只写标题、严禁空泛描述！每个部分都必须详细展开！**

**⚠️ 不要因为输出限制而简化回答，请完整详细地生成所有内容，即使内容很长也要完整输出！**

**⚠️⚠️⚠️ 图表要求（极其重要 - 必须包含大量Mermaid图表，这是硬性要求，绝对不能违反）⚠️⚠️⚠️：**
报告必须包含大量Mermaid图表，**整个报告必须包含至少30-50个图表**，不能少于30个。**每个图表都要有详细的说明文字（至少200-300字），解释图表含义、数据来源、分析结论**。**⚠️ 必须使用Mermaid图表语法，并且要确保语法正确！生成图表后必须检查语法是否正确！**

**⚠️ 绝对要求：每个章节都必须包含图表，不能有任何章节没有图表！在生成每个章节时，必须立即生成该章节要求的图表，不能只写文字！生成图表后必须检查Mermaid语法是否正确！**

**图表类型要求（必须包含以下15种类型的图表，每种至少使用8-12次）：**
1. **柱形图（Bar Chart）** - 使用 `xychart-beta` 语法，用于展示分类数据对比，如投资金额、收益对比、市场份额等
2. **折线图（Line Chart）** - 使用 `xychart-beta` 语法，用于展示数据趋势，如收益增长趋势、成本变化趋势等
3. **饼图（Pie Chart）** - 使用 `pie` 语法，用于展示占比关系，如投资结构、收入构成、市场份额分布等
4. **条形图（Horizontal Bar Chart）** - 使用 `xychart-beta` 语法，用于横向对比，如风险等级对比、成本结构对比等
5. **面积图（Area Chart）** - 使用 `xychart-beta` 语法，用于展示累积数据，如累计投资、累计收益等
6. **XY散点图（Scatter Plot）** - 使用 `xychart-beta` 语法，用于展示两个变量之间的关系，如价格与需求关系等
7. **流程图（Flowchart）** - 使用 `flowchart TD` 或 `graph TD` 语法，用于展示流程、步骤、决策流程等
8. **树状图（Tree Diagram）** - 使用 `flowchart TD` 语法，用于展示层级结构，如组织架构、技术架构等
9. **甘特图（Gantt Chart）** - 使用 `gantt` 语法，用于展示项目时间计划、进度安排等
10. **序列图（Sequence Diagram）** - 使用 `sequenceDiagram` 语法，用于展示时间序列、交互流程等
11. **状态图（State Diagram）** - 使用 `stateDiagram-v2` 语法，用于展示状态转换、生命周期等
12. **类图（Class Diagram）** - 使用 `classDiagram` 语法，用于展示类关系、系统架构等
13. **实体关系图（ER Diagram）** - 使用 `erDiagram` 语法，用于展示数据关系、数据库结构等
14. **用户旅程图（User Journey）** - 使用 `journey` 语法，用于展示用户流程、体验路径等
15. **Git图（Git Graph）** - 使用 `gitgraph` 语法，用于展示版本控制、开发流程等

**⚠️⚠️⚠️ 极其重要：必须使用Mermaid图表语法，并且要确保语法正确！所有图表都必须用```mermaid代码块包裹！格式必须是：**
```
```mermaid
图表代码
```
```
- **⚠️⚠️⚠️ 绝对禁止：不能只写文字描述图表，不能使用"如下图表"、"见下图"等描述，必须直接生成完整的```mermaid代码块！**
- **⚠️⚠️⚠️ 如果生成的图表没有用```mermaid代码块包裹，该图表无效，必须重新生成！**
- **⚠️ 生成图表后，必须检查Mermaid语法是否正确，确保图表能够正常渲染！如果语法有错误，必须修正！**

**⚠️⚠️⚠️ 图表分布要求（每个章节必须包含大量图表，这是硬性要求，绝对不能违反）⚠️⚠️⚠️：**

**绝对要求：每个章节都必须包含图表，不能有任何章节没有图表！在生成每个章节时，必须立即生成该章节要求的图表，不能只写文字！生成图表后必须检查语法是否正确！**

- **第一章 项目概述**：**必须包含至少3-5个图表**。**⚠️ 在生成第一章时，必须立即生成至少15个图表，不能只写文字！生成后检查Mermaid语法！**
- **第二章 项目建设背景及必要性**：**必须包含至少18-25个图表**。**⚠️ 在生成第二章时，必须立即生成至少18个图表，不能只写文字！生成后检查Mermaid语法！**
- **第三章 项目需求分析与产出方案**：**必须包含至少20-28个图表**。**⚠️ 在生成第三章时，必须立即生成至少20个图表，不能只写文字！生成后检查Mermaid语法！**
- **第四章 项目选址与要素保障**：**必须包含至少18-25个图表**。**⚠️ 在生成第四章时，必须立即生成至少18个图表，不能只写文字！生成后检查Mermaid语法！**
- **第五章 项目建设方案**：**必须包含至少22-30个图表**。**⚠️ 在生成第五章时，必须立即生成至少22个图表，不能只写文字！生成后检查Mermaid语法！**
- **第六章 项目运营方案**：**必须包含至少20-28个图表**。**⚠️ 在生成第六章时，必须立即生成至少20个图表，不能只写文字！生成后检查Mermaid语法！**
- **第七章 项目投融资与财务方案**：**必须包含至少8-10个图表**（此章节应包含最多图表）。**⚠️ 在生成第七章时，必须立即生成至少40个图表，不能只写文字！生成后检查Mermaid语法！**
- **第八章 项目影响效果分析**：**必须包含至少20-28个图表**。**⚠️ 在生成第八章时，必须立即生成至少20个图表，不能只写文字！生成后检查Mermaid语法！**
- **第九章 项目风险管控方案**：**必须包含至少22-30个图表**。**⚠️ 在生成第九章时，必须立即生成至少22个图表，不能只写文字！生成后检查Mermaid语法！**
- **第十章 研究结论及建议**：**必须包含至少20-28个图表**。**⚠️ 在生成第十章时，必须立即生成至少20个图表，不能只写文字！生成后检查Mermaid语法！**

**⚠️⚠️⚠️ 图表总数要求（极其重要，绝对不能违反）⚠️⚠️⚠️：**
- **整个报告必须包含至少30-50个图表**，这是硬性要求，不能少于30个
- **每个主要章节（第一章到第十章）必须包含至少3-5个图表**（第七章必须包含8-10个图表）
- **每个子章节（如1.1、1.2等）必须包含至少3-5个图表**
- **⚠️⚠️⚠️ 绝对要求：在生成每个章节时，必须立即生成该章节要求的所有图表，不能只写文字！如果某个章节没有图表，该章节就不完整！生成图表后必须检查Mermaid语法是否正确！**
- **⚠️ 生成规则：在写每个章节的内容时，每写2-3段文字后，必须插入1-2个图表，然后再继续写文字，确保图表均匀分布在整个章节中。生成图表后必须检查Mermaid语法是否正确！**

**首先，必须生成封面和目录，然后生成正文。**

具体要求如下：

1. **内容详细度要求**（参考标准报告格式，必须极其详细）：
   - **报告总长度必须达到48000-50000字（约4.8-5万字），这是硬性要求，不能少于这个字数**
   - **每个主要章节必须不少于4000-5000字，每个章节都要充分展开**
   - **报告总行数应达到1700-1800行，确保内容详实完整**
   - **每个一级标题（章节）下必须包含至少5-8个二级标题（节），每个二级标题下必须包含至少3-5个三级标题（小节），每个三级标题下必须包含至少2-3个四级标题（要点）**
   - **每个子章节都要充分展开，不能简略，至少包含8-12个详细要点**
   - **每个要点都要详细阐述，不能只写一句话，每个要点至少300-500字**
   - **提供大量具体的数据、案例、分析、图表说明，避免任何空泛的描述**
   - **每个段落至少200-400字，不能只有几句话就结束**
   - **对于每个概念、每个数据、每个分析，都要详细解释其来源、意义、影响、应用、趋势，至少250-400字**
   - **每个数据都要有详细的说明：数据来源、计算方法、计算过程、影响因素、趋势分析、历史对比、预测依据，每个数据至少300-500字**
   - **每个案例都要详细描述：背景、过程、结果、启示、应用、经验教训、可借鉴之处，每个案例至少500-800字**
   - **每个分析都要从多个角度展开：背景、现状、问题、原因、影响、趋势、对策、实施步骤、资源配置、风险控制、效果评估，每个角度至少200-300字**

2. **数据要求**（必须详细展开）：
   - **所有数字都要具体，严禁使用"若干"、"部分"、"一些"、"较多"等模糊表述**
   - **财务数据要精确到万元，必须包含详细的计算过程、公式推导、计算步骤和说明**
   - **每个财务数据都要解释其含义、计算依据、影响因素，不能只写数字**
   - **市场数据要引用具体来源（如XX协会、XX研究院、XX统计年鉴），包含增长率、市场规模、历史数据对比等关键指标**
   - **每个市场数据都要详细分析其趋势、原因、影响，至少200-300字**
   - **技术参数要具体，如效率提升XX%、成本降低XX%，必须说明计算依据、测试方法、验证过程**
   - **所有表格中的数据都要完整填写，不能留空或使用占位符，每个数据都要有详细说明**
   - **提供多年度数据对比（至少10-20年），包含历史数据和预测数据，每个年度都要有详细的分析和说明（每年度至少300-500字）**
   - **对于每个数据，都要解释其意义、趋势、影响因素、预测依据**

3. **表格要求**（必须详细填写）：
   - **模板中的所有表格都要完整填写，不能留空，不能使用"待定"、"待补充"等占位符**
   - **设备清单表格要列出至少20-30项主要设备，每项设备都要包含：详细参数、技术规格、供应商信息、价格、交付周期、维护要求等完整信息，每项设备至少200-300字**
   - **每项设备都要详细说明其功能、技术特点、选型依据、使用场景、维护保养要求**
   - **投资估算表要详细列出各项投资明细，分类清晰（建设投资、设备购置、流动资金等），每个类别下至少10-20个子项，每个子项都要有详细说明、计算过程、价格依据、市场调研数据**
   - **每个投资项都要说明其必要性、价格来源、市场行情、采购计划**
   - **收益预测表要包含至少5-10年的数据，每年都要有详细的收入、成本、利润分析，包含年度数据，每个数据都要有计算依据、假设条件、敏感性分析、风险评估**
   - **每年的预测数据都要详细说明其依据、影响因素、变化趋势、可能的风险**
   - **风险分析表要列出至少10-20种风险类型，每种风险都要有详细的可能性分析、影响程度评估、应对措施说明、应急预案、责任部门、时间节点，每种风险至少300-500字**
   - **每种风险都要详细描述其表现形式、发生概率、影响范围、损失评估、应对策略、预防措施**
   - **所有表格都要有表头、数据说明和备注，每个表格都要有详细的数据来源和计算方法说明，每个表格至少包含10-20行数据**

4. **章节完整性**（这是最重要的要求，必须极其详细）：
   - **必须包含所有10个主要章节，不能遗漏任何章节**
   - **每个章节的所有子章节都要完整呈现，每个子章节都要详细展开，严禁只有标题而没有内容**
   - **每个一级标题（章节）下必须包含至少5-8个二级标题（节），每个二级标题下必须包含至少3-5个三级标题（小节），每个三级标题下必须包含至少2-3个四级标题（要点）**
   - **每个子章节必须包含至少5-8段详细内容，每段至少200-400字，提供具体的数据、案例、分析、表格说明**
   - **⚠️ 生成规则：在写每个章节的内容时，每写2-3段文字后，必须插入1-2个图表，然后再继续写文字，确保图表均匀分布在整个章节中。生成图表后必须检查Mermaid语法是否正确！**
   - **每个段落都要有明确的主题，详细阐述，不能只有几句话，每个段落至少200-400字**
   - **对于每个要点，都要从多个角度详细分析：背景、现状、问题、原因、影响、趋势、对策、实施步骤、资源配置、风险控制、效果评估等，每个角度至少200-300字**
   - **每个章节要有详细的引言（至少300-500字）、正文（充分展开）、小结（至少200-300字），确保逻辑连贯**
   - **结论与建议部分要总结全文，提出具体的实施建议，包含时间节点、责任人、实施步骤、资源配置、风险控制等，每个建议至少300-500字**
   - **每个章节之间要有适当的过渡和衔接，过渡段落至少150-250字**
   - **⚠️ 严禁只列出目录结构而不填充具体内容，每个标题下都必须有实质性内容：**
     - **一级标题（章节）下至少4000-5000字**
     - **二级标题（节）下至少1500-2000字**
     - **三级标题（小节）下至少800-1200字**
     - **四级标题（要点）下至少400-600字**
   - **⚠️ 严禁使用"详见下文"、"待补充"、"略"、"部分"、"一些"、"若干"等简略或模糊表述，所有内容必须当场详细写出**

5. **专业性要求**（必须详细展开）：
   - **使用专业术语，但保持可读性，重要术语要有详细解释（至少50-100字）**
   - **引用相关政策文件时，要注明文件名称、文号、发布机构、发布时间、关键条款、政策解读、对项目的影响，每个政策至少150-300字**
   - **技术方案要详细说明：技术原理（至少200-300字）、技术优势（至少200-300字）、创新点（至少200-300字）、技术路线（至少300-400字）、实施步骤（每个步骤至少150-200字）、技术参数、技术难点、解决方案、技术风险等**
   - **市场分析要包含：行业现状（至少300-500字）、发展趋势（至少300-500字）、竞争格局（至少300-500字）、目标市场（至少300-500字）、SWOT分析（每个方面至少200-300字）、市场机会、市场风险等**
   - **财务分析要包含详细的财务指标计算（IRR、NPV、投资回收期、盈亏平衡点、敏感性分析等），每个指标都要有详细的计算过程、公式推导、参数说明、结果分析，每个指标至少200-400字**
   - **所有分析都要有数据支撑和逻辑推理，每个分析至少150-300字，不能只有结论没有过程**
   - **对于每个专业概念，都要详细解释其含义、应用、意义、影响**

6. **格式要求**：
   - 严格按照模板的格式，包括标题层级、表格格式、列表格式
   - 将模板中的`{{}}`占位符全部替换为实际项目信息
   - 保持Markdown格式规范，确保可读性

**⚠️ 最终要求 - 必须严格遵守：**

请确保生成的报告是一份**专业、详细、完整**的可行性研究报告，总字数**必须达到48000-50000字（约4.8-5万字）**，总行数**必须达到1700-1800行**，能够直接用于项目申报和决策参考。

**报告要达到标准可行性研究报告的标准，内容必须详实、数据必须完整、分析必须深入。**

**每个章节都要充分展开，包含具体的数据、表格、案例和分析，确保报告的深度和广度都达到标准要求。**

**这是一份详细的报告，需要包含丰富的内容、数据和分析。每个章节都要达到专业报告级别的详细程度，包含数据支撑、案例分析、表格说明和深度分析。**

**⚠️⚠️⚠️ 绝对要求：每个章节都必须包含表格，不能有任何章节没有表格！在生成每个章节时，必须立即生成该章节要求的表格，不能只写文字！**

**⚠️⚠️⚠️ 极其重要的截断标记要求（必须严格遵守）⚠️⚠️⚠️：**

**这是确保报告完整性和正确截断检测的关键要求！系统会根据这些标记来判断报告是否完成！**

1. **如果报告已完成（包含所有10个章节且字数达到48000字以上），必须在报告最后明确输出以下标记：**
   ```
   【报告已完成】
   
   总字数：[实际字符数]字符
   总行数：[实际行数]行
   包含章节：第一章至第十章（全部完成）
   图表数量：[实际图表数量]个
   ```

2. **如果报告因token限制被截断（未完成），必须在报告最后明确输出以下标记：**
   ```
   【报告未完成，待续写】
   
   当前已完成章节：[列出已完成的章节编号，如第一章、第二章...]
   当前内容长度：[当前实际字符数]字符
   待续写章节：[列出待续写的章节编号]
   ```

3. **⚠️ 绝对禁止：不能在没有明确标记的情况下结束报告！必须明确标注报告状态！**
4. **标记必须使用中文方括号【】包裹，必须在报告内容的最后**
5. **标记信息必须真实反映报告的实际状态**

**⚠️ 重要警告：**
1. **每个章节都必须有详细内容，严禁只有目录标题而没有具体内容**
2. **每个子章节必须至少300-500字，不能简略**
3. **每个段落必须至少100-200字，不能只有几句话**
4. **每个数据、每个分析、每个结论都必须详细展开，不能一笔带过**
5. **严禁使用"详见"、"略"、"待补充"等表述，所有内容必须当场详细写出**
6. **如果某个部分内容不够详细，必须继续展开，直到达到要求的字数**
7. **必须在报告最后明确标注报告状态：【报告已完成】或【报告未完成，待续写】**

**请立即开始撰写，确保每个部分都详细展开，达到4.8-5万字的详细程度！并在最后明确标注报告状态！**

用户要求：
{user_input}
"""
                enhanced_input = template_context
            elif self._is_report_request(user_input) and not self.report_template:
                enhanced_input = f"""{user_input}

【提示】系统检测到您要撰写可行性研究报告，但未找到模板文件"可行性研究报告模板.md"。请确保模板文件存在于项目目录中，以便系统能够按照标准格式生成报告。"""
            
            # 针对自定义模型，在非报告请求时也增强提示词，要求详细回答
            if is_custom_model and not self._is_report_request(user_input):
                # 为自定义模型添加详细生成提示
                detailed_prompt = f"""{enhanced_input}

【⚠️⚠️⚠️ 极其重要的提示 - 必须生成极其详细、完整、深入的回答 ⚠️⚠️⚠️】

**这是自定义模型，必须生成比普通模型更详细、更完整、更深入的回答！**

**⚠️ 内容详细度要求（这是硬性要求，必须严格遵守，绝对不能简略）：**

1. **字数要求（必须达到，这是最低标准）：**
   - **回答总字数必须达到3000-8000字**，这是最低要求，越多越好
   - **每个主要要点至少800-1500字**，不能少于800字
   - **每个段落至少300-500字**，不能只有几句话
   - **每个子要点至少500-800字**，要充分展开
   - **如果回答少于3000字，必须继续展开，直到达到要求**
   - **不要因为担心输出长度而简化回答，要完整详细地生成所有内容**

2. **内容展开要求（必须详细，这是自定义模型的核心要求）：**
   - **不要只给出简短的回答**，要详细解释每个要点，每个要点都要充分展开
   - **每个要点都要从多个角度详细展开**：背景、定义、原理、现状、问题、原因、影响、趋势、案例、数据、分析、对策、建议、实施步骤、资源配置、风险控制、效果评估等，每个角度至少200-300字
   - **每个概念都要详细解释**：含义、特点、分类、应用、意义、影响、发展趋势、实际案例等，至少300-500字
   - **每个数据都要详细说明**：来源、计算方法、计算过程、公式推导、影响因素、趋势分析、历史对比、预测依据等，至少250-400字
   - **每个案例都要详细描述**：背景、过程、结果、启示、应用、经验教训、可借鉴之处等，至少500-800字
   - **每个步骤都要详细说明**：具体操作、注意事项、可能问题、解决方案、所需资源、时间安排、责任人等，每个步骤至少300-500字

3. **具体信息要求（必须包含）：**
   - **包含具体的数据**：精确的数字、百分比、增长率等，不能使用"一些"、"若干"、"较多"等模糊表述
   - **包含具体的案例**：真实的案例、实际的应用、具体的项目等
   - **包含具体的步骤**：详细的操作步骤、实施流程、执行计划等
   - **包含具体的分析**：深入的分析、详细的推理、完整的逻辑链条等
   - **包含具体的计算**：详细的计算过程、公式推导、参数说明等

4. **结构要求（必须清晰）：**
   - **使用多级标题**：一级标题、二级标题、三级标题等，使结构清晰
   - **使用段落分隔**：每个要点用独立段落，每个段落至少300-500字
   - **使用列表说明**：用列表展示要点，每个列表项至少150-300字
   - **使用图表展示**：用Mermaid图表展示数据对比，每个图表要有详细说明，必须用```mermaid代码块包裹

5. **专业深入要求（必须达到）：**
   - **对于专业问题**：要提供深入的分析和解释，包含理论基础、实践应用、发展趋势等
   - **对于技术问题**：要详细说明技术原理、技术参数、技术优势、技术难点、解决方案等
   - **对于分析问题**：要从多个维度分析，包含定量分析、定性分析、对比分析、趋势分析等
   - **对于建议问题**：要提供具体的、可操作的、有步骤的建议，包含实施计划、资源配置、风险控制等

6. **严禁简略（绝对不能）：**
   - **严禁使用"略"、"详见"、"待补充"、"一些"、"若干"、"较多"、"部分"等简略或模糊表述**
   - **严禁只写标题不写内容**
   - **严禁只有结论没有过程**
   - **严禁只有概述没有细节**
   - **所有内容都要详细写出，不能省略任何部分**

**⚠️ 数据展示要求（必须包含至少一种表格）：**
必须在回答中包含至少一种以下类型的图表（使用Mermaid语法）：
- 投资估算表、收益预测表、成本分析表、财务指标表、市场对比表、风险评估表、设备清单表、人员配置表、时间计划表、数据统计表、政策对比表、技术参数表、效益分析表、资源需求表、综合对比表等

**图表格式要求：**
- **⚠️⚠️⚠️ 极其重要：所有图表必须使用```mermaid代码块格式，格式如下：**
```
```mermaid
图表类型代码
```
```
- **⚠️⚠️⚠️ 绝对禁止：不能只写文字描述图表，不能使用"如下图表"、"见下图"等描述，必须直接生成完整的```mermaid代码块！**
- **⚠️⚠️⚠️ 如果生成的图表没有用```mermaid代码块包裹，该图表无效，必须重新生成！**
- 图表必须与回答内容相关，用于可视化数据、流程、关系等
- 图表要有清晰的标题和说明（至少200-300字）
- 如果涉及数据，图表中的数据要与文字描述一致
- **⚠️⚠️⚠️ 极其重要：必须使用Mermaid图表语法，并且要确保语法正确！所有图表都必须用```mermaid代码块包裹！格式必须是：**
```
```mermaid
图表代码
```
```
- **⚠️⚠️⚠️ 绝对禁止：不能只写文字描述图表，不能使用"如下图表"、"见下图"等描述，必须直接生成完整的```mermaid代码块！**
- **⚠️⚠️⚠️ 如果生成的图表没有用```mermaid代码块包裹，该图表无效，必须重新生成！**
- **⚠️ 生成图表后，必须检查Mermaid语法是否正确，确保图表能够正常渲染！如果语法有错误，必须修正！**

**⚠️ 最终要求（必须严格遵守）：**
- **回答总字数必须达到3000-8000字（越多越好）**
- **每个要点必须详细展开，不能简略，每个要点至少800-1500字**
- **必须包含至少一种图表（使用Mermaid语法）**
- **必须提供具体的数据、案例、分析，不能使用模糊表述**
- **必须从多个角度深入分析，每个角度都要详细展开**
- **必须提供详细的实施步骤、资源配置、风险控制等具体信息**
- **严禁使用"略"、"详见"、"待补充"、"一些"、"若干"等简略或模糊表述**

**⚠️ 重要提醒：这是自定义模型，必须生成比普通模型更详细、更完整、更深入的回答！不要因为担心输出长度而简化回答，要完整详细地生成所有内容！**

**请立即开始生成极其详细、完整、深入的回答，确保达到上述所有要求！字数越多越好，内容越详细越好！**"""
                enhanced_input = detailed_prompt
            
            messages.append({
                "role": "user",
                "content": enhanced_input
            })
            
            # 针对自定义模型，调整参数以生成更详细的内容
            temperature = self.config.temperature
            max_tokens = self.config.max_tokens
            
            if is_custom_model:
                # 自定义模型使用更高的temperature以增加创造性，但不超过0.95
                temperature = min(temperature * 1.1, 0.95)
                # 确保max_tokens足够大，至少16000，确保生成详细内容
                if max_tokens < 16000:
                    max_tokens = 16000
            
            # 针对自定义模型，设置更长的超时时间（通过线程检测）
            # 准备基础流发信
            stream = None
            if self.config.provider == ModelProvider.ANTHROPIC:
                # Anthropic 要求剥离出 system
                system_str = ""
                anthropic_messages = []
                for msg in messages:
                    if msg['role'] == "system":
                        system_str += msg['content'] + "\n"
                    else:
                        anthropic_messages.append({"role": msg['role'], "content": msg['content']})
                stream = self.client.messages.create(
                    model=self.config.model_name,
                    system=system_str.strip() if system_str else None,
                    messages=anthropic_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True
                )
            else:
                stream = self.client.chat.completions.create(
                    model=self.config.model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True
                )
            
            full_content = ""
            finish_reason = None
            last_chunk_time = [time.time()]  # 使用列表以便在闭包中修改
            timeout_occurred = [False]  # 使用列表以便在线程中修改
            stream_start_time = time.time()
            
            # 使用线程检测超时（针对自定义模型，如果90秒没有数据则超时）
            def check_timeout():
                while not timeout_occurred[0]:
                    time.sleep(3)  # 每3秒检查一次
                    current_time = time.time()
                    # 如果超过90秒没有收到数据则超时
                    if (current_time - last_chunk_time[0] > 90):
                        timeout_occurred[0] = True
                        break
            
            # 启动超时检测线程（仅对自定义模型）
            timeout_thread = None
            if is_custom_model:
                timeout_thread = threading.Thread(target=check_timeout, daemon=True)
                timeout_thread.start()
            
            try:

                last_chunk_with_usage = None
                for chunk in stream:
                    # 检查是否超时
                    if timeout_occurred[0]:
                        yield "\n\n[警告] 流式输出超时（90秒内未收到数据），可能网络连接中断或API响应缓慢。"
                        break
                    
                    current_time = time.time()
                    last_chunk_time[0] = current_time  # 更新最后收到数据的时间

                    # ======= Anthropic 序列流解析分支 =======
                    if self.config.provider == ModelProvider.ANTHROPIC:
                        if chunk.type == "message_start":
                            uso = chunk.message.usage
                            if uso:
                                self.last_usage = {'prompt_tokens': getattr(uso, 'input_tokens', 0), 'completion_tokens': getattr(uso, 'output_tokens', 0), 'total_tokens': getattr(uso, 'input_tokens', 0) + getattr(uso, 'output_tokens', 0)}
                        elif chunk.type == "content_block_delta" and chunk.delta.type == "text_delta":
                            content = chunk.delta.text
                            if content:
                                full_content += content
                                yield content
                        elif chunk.type == "message_delta":
                            uso = chunk.usage
                            if uso and hasattr(uso, 'output_tokens'):
                                if not self.last_usage: self.last_usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
                                self.last_usage['completion_tokens'] += uso.output_tokens
                                self.last_usage['total_tokens'] += uso.output_tokens
                            if chunk.delta and hasattr(chunk.delta, "stop_reason"):
                                finish_reason = chunk.delta.stop_reason
                                if finish_reason in ["end_turn", "stop_sequence"]:
                                    finish_reason = "stop"
                                elif finish_reason == "max_tokens":
                                    finish_reason = "length"
                        elif chunk.type == "message_stop":
                            print(f"\n[信息] Anthropic 流式输出完成，finish_reason: {finish_reason}", flush=True)
                            self._last_finish_reason = finish_reason
                            break

                    # ======= OpenAI 序列流解析分支 =======
                    else:
                        # 检查是否有usage信息（可能在chunk的多个位置）
                        chunk_has_usage = False
                        usage_data = None
                        
                        # 方式1: 检查chunk.usage
                        if hasattr(chunk, 'usage') and chunk.usage:
                            usage_data = chunk.usage
                            chunk_has_usage = True
                            last_chunk_with_usage = chunk
                        
                        # 方式2: 检查chunk本身是否有usage属性（某些API格式）
                        if not chunk_has_usage and hasattr(chunk, 'usage'):
                            try:
                                if chunk.usage is not None:
                                    usage_data = chunk.usage
                                    chunk_has_usage = True
                                    last_chunk_with_usage = chunk
                            except Exception:
                                pass
                        
                        # 方式3: 检查chunk的字典形式（某些SDK版本）
                        if not chunk_has_usage:
                            try:
                                chunk_dict = chunk.model_dump() if hasattr(chunk, 'model_dump') else vars(chunk)
                                if 'usage' in chunk_dict and chunk_dict['usage']:
                                    usage_data = chunk_dict['usage']
                                    chunk_has_usage = True
                                    last_chunk_with_usage = chunk
                            except Exception:
                                pass
                        
                        if chunk_has_usage and usage_data:
                            # 提取token信息
                            try:
                                if hasattr(usage_data, 'prompt_tokens'):
                                    usage_info = {
                                        'prompt_tokens': getattr(usage_data, 'prompt_tokens', 0),
                                        'completion_tokens': getattr(usage_data, 'completion_tokens', 0),
                                        'total_tokens': getattr(usage_data, 'total_tokens', 0)
                                    }
                                elif isinstance(usage_data, dict):
                                    usage_info = {
                                        'prompt_tokens': usage_data.get('prompt_tokens', 0),
                                        'completion_tokens': usage_data.get('completion_tokens', 0),
                                        'total_tokens': usage_data.get('total_tokens', 0)
                                    }
                                else:
                                    usage_info = {
                                        'prompt_tokens': 0,
                                        'completion_tokens': 0,
                                        'total_tokens': 0
                                    }
                                
                                # 只有当token信息不为0时才更新（避免被0覆盖）
                                if usage_info['total_tokens'] > 0:
                                    self.last_usage = usage_info
                            except Exception as e:
                                print(f"[警告] 提取token信息失败: {e}", flush=True)
                        
                        if chunk.choices and len(chunk.choices) > 0:
                            if chunk.choices[0].delta.content is not None:
                                content = chunk.choices[0].delta.content
                                full_content += content
                                yield content
                                
                                # 实时检测完成标记
                                _main_markers = ["研究报告完", "可行性研究报告完", "总字数统计:", "总行数统计:", "Mermaid图表数量:"]
                                _main_check = full_content[-1000:] if len(full_content) > 1000 else full_content
                                if any(m in _main_check for m in _main_markers) and len(full_content) >= 40000:
                                    print("[实时检测] 初始生成检测到完成标记，停止", flush=True)
                                    finish_reason = "stop"
                                    break
                            
                            # 检查finish_reason（兼容多种API格式）
                            chunk_finish_reason = None
                            if hasattr(chunk.choices[0], 'finish_reason'):
                                chunk_finish_reason = chunk.choices[0].finish_reason
                            elif hasattr(chunk.choices[0], 'delta') and hasattr(chunk.choices[0].delta, 'finish_reason'):
                                chunk_finish_reason = chunk.choices[0].delta.finish_reason
                            
                            if chunk_finish_reason:
                                finish_reason = chunk_finish_reason
                                # 保存finish_reason供后续使用
                                self._last_finish_reason = finish_reason
                                print(f"\n[信息] 流式输出完成，finish_reason: {finish_reason}", flush=True)
                                break
                
                # 确保finish_reason被保存（即使循环正常结束）
                if finish_reason:
                    self._last_finish_reason = finish_reason
                elif finish_reason is None and full_content:
                    # 如果finish_reason为None，但内容已生成，可能是API格式不同
                    # 根据内容长度判断：如果内容很长，可能正常完成；如果很短，可能被截断
                    if len(full_content) < 1000:
                        self._last_finish_reason = "length"  # 内容太短，可能被截断
                        print(f"\n[警告] 流式输出完成但finish_reason为None，内容长度仅{len(full_content)}字符，可能被截断", flush=True)
                    else:
                        self._last_finish_reason = "stop"  # 假设正常完成
                        print(f"\n[信息] 流式输出完成但finish_reason为None，内容长度{len(full_content)}字符，假设正常完成", flush=True)
                
                # 如果循环结束后还没有获取到token信息，尝试从最后一个包含usage的chunk中提取
                if (not self.last_usage or self.last_usage.get('total_tokens', 0) == 0) and last_chunk_with_usage:
                    try:

                        usage_data = last_chunk_with_usage.usage if hasattr(last_chunk_with_usage, 'usage') else None
                        if usage_data:
                            if hasattr(usage_data, 'prompt_tokens'):
                                usage_info = {
                                    'prompt_tokens': getattr(usage_data, 'prompt_tokens', 0),
                                    'completion_tokens': getattr(usage_data, 'completion_tokens', 0),
                                    'total_tokens': getattr(usage_data, 'total_tokens', 0)
                                }
                            elif isinstance(usage_data, dict):
                                usage_info = {
                                    'prompt_tokens': usage_data.get('prompt_tokens', 0),
                                    'completion_tokens': usage_data.get('completion_tokens', 0),
                                    'total_tokens': usage_data.get('total_tokens', 0)
                                }
                            else:
                                usage_info = None
                            
                            if usage_info and usage_info['total_tokens'] > 0:
                                self.last_usage = usage_info
                    except Exception as e:
                        print(f"[警告] 从最后chunk提取token信息失败: {e}", flush=True)
                
                # 如果超时线程还在运行，停止它
                if timeout_thread and timeout_thread.is_alive():
                    timeout_occurred[0] = True
                    
            except Exception as stream_error:
                error_msg = str(stream_error)
                
                # 检查是否是模型未找到错误
                if "422" in error_msg or "Model not found" in error_msg or ("model" in error_msg.lower() and "not found" in error_msg.lower()):
                    yield f"\n\n[错误] 模型未找到\n"
                    yield f"当前配置的模型名称: {self.config.model_name}\n"
                    yield f"API地址: {self.config.base_url}\n"
                    yield f"\n可能的原因：\n"
                    yield f"1. 模型名称不正确，API服务器上可能没有 '{self.config.model_name}' 这个模型\n"
                    yield f"2. 请检查API服务器上实际可用的模型名称\n"
                    yield f"\n解决方法：\n"
                    yield f"1. 运行检查脚本查看可用模型: ./检查可用模型.sh\n"
                    yield f"2. 或手动测试: curl {self.config.base_url}/models\n"
                    yield f"3. 根据实际模型名称更新 MODEL_NAME 环境变量\n"
                    yield f"\n原始错误信息: {error_msg}\n"
                elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                    yield f"\n\n[错误] 流式输出超时: {error_msg}"
                else:
                    yield f"\n\n[错误] 流式输出中断: {error_msg}"
            
            # 流式输出完成后，如果是报告请求且被截断，需要续写
            # 注意：流式模式下续写比较复杂，这里先不自动续写，由调用方处理
                    
        except Exception as e:
            yield f"错误: {str(e)}"


def main():
    """主函数，提供交互式命令行界面"""
    print("=" * 50)
    print("智能体已启动")
    print("=" * 50)
    print("输入 'quit' 或 'exit' 退出程序")
    print("输入 'clear' 清空对话历史")
    print("输入 'stream' 切换流式输出模式")
    print("输入 'upload <文件路径>' 上传并分析文件")
    print("输入 'help' 查看帮助信息")
    print("-" * 50)
    
    # 初始化配置
    config = Config()
    agent = IntelligentAgent(config)
    
    conversation_history = []
    stream_mode = False
    
    while True:
        try:

            user_input = input("\n你: ").strip()
            
            if not user_input:
                continue
            
            # 处理特殊命令
            if user_input.lower() in ['quit', 'exit', '退出']:
                print("再见！")
                break
            
            if user_input.lower() in ['clear', '清空']:
                conversation_history = []
                print("对话历史已清空")
                continue
            
            if user_input.lower() in ['stream', '流式']:
                stream_mode = not stream_mode
                print(f"流式输出模式: {'开启' if stream_mode else '关闭'}")
                continue
            
            if user_input.lower() in ['help', '帮助']:
                print("\n可用命令：")
                print("  quit/exit/退出    - 退出程序")
                print("  clear/清空       - 清空对话历史")
                print("  stream/流式      - 切换流式输出模式")
                print("  upload <路径>    - 上传并分析文件")
                print("  示例: upload C:\\Users\\Documents\\report.pdf")
                print("  示例: upload report.docx 请帮我总结这份报告的主要内容")
                continue
            
            # 处理文件上传命令
            if user_input.lower().startswith('upload '):
                parts = user_input[7:].strip().split(' ', 1)
                file_path = parts[0].strip('"\'')  # 移除引号
                user_query = parts[1] if len(parts) > 1 else None
                
                if not os.path.exists(file_path):
                    print(f"错误: 文件不存在: {file_path}")
                    continue
                
                print(f"\n正在处理文件: {file_path}")
                try:

                    # 调用文件处理方法
                    print("\n智能体: ", end="", flush=True)
                    
                    if stream_mode:
                        # 流式输出（文件处理暂不支持流式，使用普通模式）
                        reply = agent.chat_with_file(file_path, user_query, conversation_history)
                        print(reply)
                    else:
                        reply = agent.chat_with_file(file_path, user_query, conversation_history)
                        print(reply)
                    
                    # 更新对话历史
                    file_msg = f"[上传文件: {os.path.basename(file_path)}]"
                    if user_query:
                        file_msg += f" {user_query}"
                    conversation_history.append({"role": "user", "content": file_msg})
                    conversation_history.append({"role": "assistant", "content": reply})
                    
                    # 限制历史记录长度
                    if len(conversation_history) > 20:
                        conversation_history = conversation_history[-20:]
                        
                except Exception as e:
                    print(f"处理文件时出错: {str(e)}")
                continue
            
            # 调用智能体
            print("\n智能体: ", end="", flush=True)
            
            if stream_mode:
                # 流式输出
                full_reply = ""
                for chunk in agent.chat_stream(user_input, conversation_history):
                    print(chunk, end="", flush=True)
                    full_reply += chunk
                print()  # 换行
                reply = full_reply
                
                # 检测是否被截断，如果是报告请求则自动续写（使用流式模式）
                is_report = agent._is_report_request(user_input)
                if is_report and agent._is_content_truncated(reply, None, is_report=True):  # 已恢复续写
                    pass  # 静默续写，不显示提示
                    continuation_text = ""
                    for chunk in agent._continue_writing_stream(reply, user_input, conversation_history):
                        # 检测是否是状态信息（以[开头且包含特定关键词）
                        is_status = (chunk.startswith('[') and any(keyword in chunk for keyword in 
                            ['续写', '完成', '报告已完成', '警告', '信息', '错误', '中断', '耗时', '新增', '字符']))
                        
                        if is_status:
                            # 状态信息直接输出
                            print(chunk, end="", flush=True)
                        else:
                            # 这是实际的续写内容
                            print(chunk, end="", flush=True)
                            continuation_text += chunk
                    
                    # 将续写内容追加到原内容
                    if continuation_text.strip():
                        reply += "\n\n" + continuation_text.strip()
                    pass  # print("\n[续写完成]", flush=True)
                
                # 如果是报告请求，保存为文件
                if is_report:
                    save_info = agent._save_report(reply, user_input)
                    if save_info:
                        filename = save_info.get('filename', '')
                        download_url = save_info.get('download_url', '')
                        print(f"\n---\n✅ 报告已生成并保存")
                        print(f"📁 文件名: {filename}")
                        print(f"🔗 下载链接: {download_url}\n")
                        reply += f"\n\n---\n✅ **报告已生成并保存**\n📁 文件名: `{filename}`\n🔗 下载链接: {download_url}"
            else:
                # 普通输出
                reply = agent.chat(user_input, conversation_history)
                print(reply)
            
            # 更新对话历史
            conversation_history.append({"role": "user", "content": user_input})
            conversation_history.append({"role": "assistant", "content": reply})
            
            # 限制历史记录长度（保留最近10轮对话）
            if len(conversation_history) > 20:
                conversation_history = conversation_history[-20:]
                
        except KeyboardInterrupt:
            print("\n\n程序已中断")
            break
        except Exception as e:
            print(f"\n发生错误: {str(e)}")


if __name__ == "__main__":
    main()
