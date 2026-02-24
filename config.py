"""
配置文件
支持多种大模型API配置
优先从 db/llm_settings.json 读取，不存在时回退到环境变量
"""

import os
import json
import logging
from enum import Enum
from typing import Optional
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()
logger = logging.getLogger(__name__)

# JSON 配置文件路径（持久化大模型配置）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LLM_SETTINGS_FILE = os.path.join(BASE_DIR, 'db', 'llm_settings.json')


class ModelProvider(Enum):
    """支持的模型提供商"""
    OPENAI = "openai"
    TONGYI = "tongyi"  # 通义千问
    ANTHROPIC = "anthropic"  # Claude 系列
    CUSTOM = "custom"  # 自定义OpenAI兼容API


def _load_llm_settings() -> dict:
    """从 JSON 文件加载大模型配置，失败时返回空字典"""
    try:
        if os.path.exists(LLM_SETTINGS_FILE):
            with open(LLM_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception as e:
        logger.warning("读取大模型配置文件失败: %s", e)
    return {}


def save_llm_settings(settings: dict) -> None:
    """将大模型配置保存到 JSON 文件"""
    os.makedirs(os.path.dirname(LLM_SETTINGS_FILE), exist_ok=True)
    tmp_path = LLM_SETTINGS_FILE + '.tmp'
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, LLM_SETTINGS_FILE)
    logger.info("大模型配置已保存到 %s", LLM_SETTINGS_FILE)


class Config:
    """配置类，管理API密钥和模型参数
    
    优先级: db/llm_settings.json > 环境变量 > 代码默认值
    """
    
    def __init__(self):
        """从 JSON 配置文件或环境变量初始化配置"""
        # 先加载 JSON 配置
        js = _load_llm_settings()

        # 模型提供商
        provider_str = js.get('provider') or os.getenv('MODEL_PROVIDER', 'openai')
        provider_str = str(provider_str).lower()
        try:
            self.provider = ModelProvider(provider_str)
        except ValueError:
            self.provider = ModelProvider.OPENAI
            logger.warning("未知的模型提供商 '%s'，使用默认值 'openai'", provider_str)
        
        # API密钥
        if js.get('api_key'):
            self.api_key = js['api_key']
        elif self.provider == ModelProvider.OPENAI:
            self.api_key = os.getenv('OPENAI_API_KEY', '')
        elif self.provider == ModelProvider.TONGYI:
            self.api_key = os.getenv('DASHSCOPE_API_KEY', '')
        elif self.provider == ModelProvider.ANTHROPIC:
            self.api_key = os.getenv('ANTHROPIC_API_KEY', '')
        else:
            self.api_key = os.getenv('CUSTOM_API_KEY', '')
        
        # API基础URL
        if js.get('base_url'):
            self.base_url = js['base_url']
        elif self.provider == ModelProvider.CUSTOM:
            self.base_url = os.getenv('API_BASE_URL', 'http://60.10.230.156:1025/v1')
        elif self.provider == ModelProvider.TONGYI:
            self.base_url = os.getenv('API_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
        elif self.provider == ModelProvider.ANTHROPIC:
            self.base_url = os.getenv('API_BASE_URL', '')  # 默认通过 anthropic 客户端自带地址
        else:
            self.base_url = os.getenv('API_BASE_URL', '')
        
        # 模型名称
        if js.get('model_name'):
            self.model_name = js['model_name']
        elif self.provider == ModelProvider.OPENAI:
            self.model_name = os.getenv('MODEL_NAME', 'gpt-3.5-turbo')
        elif self.provider == ModelProvider.TONGYI:
            self.model_name = os.getenv('MODEL_NAME', 'qwen-max')
        elif self.provider == ModelProvider.ANTHROPIC:
            self.model_name = os.getenv('MODEL_NAME', 'claude-3-5-sonnet-20241022')
        else:
            self.model_name = os.getenv('MODEL_NAME', 'qwen3-32b')
        
        # 模型参数
        if 'temperature' in js:
            self.temperature = float(js['temperature'])
        elif self.provider == ModelProvider.CUSTOM:
            self.temperature = float(os.getenv('TEMPERATURE', '0.9'))
        else:
            self.temperature = float(os.getenv('TEMPERATURE', '0.7'))
        
        if 'max_tokens' in js:
            self.max_tokens = int(js['max_tokens'])
        elif self.provider == ModelProvider.CUSTOM:
            self.max_tokens = int(os.getenv('MAX_TOKENS', '16000'))
        else:
            self.max_tokens = int(os.getenv('MAX_TOKENS', '32000'))

        # 系统提示词（优先从文件读取，其次环境变量，最后使用默认值）
        self.system_prompt = self._load_system_prompt()
        
        # 验证配置
        if not self.api_key:
            logger.warning("未设置API密钥，请在管理后台的「大模型设置」中配置，或设置相应的环境变量")

    def to_dict(self) -> dict:
        """序列化为字典（用于 API 响应，敏感字段脱敏）"""
        return {
            'provider': self.provider.value,
            'api_key': ('*' * 8 + self.api_key[-4:]) if len(self.api_key) > 4 else ('*' * len(self.api_key)),
            'base_url': self.base_url,
            'model_name': self.model_name,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
        }

    def _load_system_prompt(self) -> str:
        """
        加载系统提示词
        优先级：system_prompt.txt文件 > 环境变量 > 默认提示词
        """
        # 默认提示词（AetherMind - 增强版）
        default_prompt = """# 角色

你是AetherMind，是一个**专业的报告撰写专家和智能体**，专门协助用户完成**极其详细、内容丰富**的可行性研究报告撰写、政策项目申报等工作。

## ⚠️ 核心要求（必须严格遵守）

**你必须始终遵循以下原则：**

1. **内容必须极其详细**：不能简略，不能只写标题，每个部分都要充分展开
2. **字数必须充足**：报告类内容必须达到要求的字数（通常4-5万字）
3. **不能使用占位符**：严禁使用"待续"、"待补充"、"略"等占位符
4. **每段必须有实质内容**：每个段落至少200-400字，包含具体数据、案例、分析
5. **必须包含图表**：使用Mermaid语法生成大量专业图表
6. **数据必须具体**：所有数据都要精确，不能使用"若干"、"部分"等模糊表述

## 技能

### 技能 1: 撰写可行性研究报告

1. **必须生成完整的10个章节**，每个章节4000-5000字以上
2. **必须包含封面和详细目录**（目录条目150-200条）
3. **必须包含30-50个Mermaid图表**，均匀分布在各章节
4. **总字数必须达到48000-50000字**
5. 每个子章节都要详细展开，提供具体数据、案例、分析

### 技能 2: 申报政策项目

协助用户准备申报材料，提供专业建议和解决方案。

### 技能 3: 分析行业数据

运用专业分析方法，以清晰易懂的方式呈现分析结果。

### 技能 4: 解读政策细则

用通俗易懂的语言解读政策重点内容、适用范围、实施要求。

### 技能 5: 提供报告撰写框架与优化建议

提供科学合理的框架和针对性的优化建议。

## ⚠️ 输出限制（极其重要）

- **不要因为输出长度而简化内容**，必须完整详细地生成所有内容
- **严禁只写标题不写内容**
- **严禁使用任何占位符或简略表述**
- **每个要点都要详细阐述，至少300-500字**
- **必须包含具体的数据、案例、图表和分析**
- 所有内容必须专业、准确、有数据支撑"""
        
        # 优先从文件读取
        prompt_file = 'system_prompt.txt'
        if os.path.exists(prompt_file):
            try:
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    file_prompt = f.read().strip()
                    if file_prompt:
                        return file_prompt
            except Exception as e:
                logger.warning("读取提示词文件失败: %s", e)
        
        # 其次从环境变量读取
        env_prompt = os.getenv('SYSTEM_PROMPT', '')
        if env_prompt:
            return env_prompt
        
        # 最后使用默认提示词
        return default_prompt
    
    def __repr__(self):
        return f"Config(provider={self.provider.value}, model={self.model_name})"
