"""
配置文件
支持多种大模型API配置
"""

import os
import logging
from enum import Enum
from typing import Optional
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()
logger = logging.getLogger(__name__)


class ModelProvider(Enum):
    """支持的模型提供商"""
    OPENAI = "openai"
    TONGYI = "tongyi"  # 通义千问
    CUSTOM = "custom"  # 自定义OpenAI兼容API


class Config:
    """配置类，管理API密钥和模型参数"""
    
    def __init__(self):
        """从环境变量或默认值初始化配置"""
        # 模型提供商（从环境变量读取，默认为openai）
        provider_str = os.getenv('MODEL_PROVIDER', 'openai').lower()
        try:
            self.provider = ModelProvider(provider_str)
        except ValueError:
            self.provider = ModelProvider.OPENAI
            logger.warning("未知的模型提供商 '%s'，使用默认值 'openai'", provider_str)
        
        # API密钥（优先从环境变量读取）
        if self.provider == ModelProvider.OPENAI:
            self.api_key = os.getenv('OPENAI_API_KEY', '')
        elif self.provider == ModelProvider.TONGYI:
            self.api_key = os.getenv('DASHSCOPE_API_KEY', '')
        else:
            self.api_key = os.getenv('CUSTOM_API_KEY', '')
        
        # API基础URL（可选，用于自定义端点）
        # 如果使用自定义模型且未设置，使用默认值
        if self.provider == ModelProvider.CUSTOM:
            self.base_url = os.getenv('API_BASE_URL', 'http://60.10.230.156:1025/v1')
        elif self.provider == ModelProvider.TONGYI:
            self.base_url = os.getenv('API_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
        else:
            self.base_url = os.getenv('API_BASE_URL', '')
        
        # 模型名称
        if self.provider == ModelProvider.OPENAI:
            self.model_name = os.getenv('MODEL_NAME', 'gpt-3.5-turbo')
        elif self.provider == ModelProvider.TONGYI:
            self.model_name = os.getenv('MODEL_NAME', 'qwen3-max')
        else:
            self.model_name = os.getenv('MODEL_NAME', 'qwen3-32b')
        
        # 系统提示词（优先从文件读取，其次环境变量，最后使用默认值）
        self.system_prompt = self._load_system_prompt()
        
        # 模型参数
        # 针对自定义模型，使用更高的temperature和max_tokens以确保详细生成
        if self.provider == ModelProvider.CUSTOM:
            self.temperature = float(os.getenv('TEMPERATURE', '0.9'))
            # 大幅增加max_tokens以确保生成详细内容（增加到16000，确保足够详细）
            self.max_tokens = int(os.getenv('MAX_TOKENS', '16000'))
        else:
            self.temperature = float(os.getenv('TEMPERATURE', '0.7'))
            # 默认max_tokens增加到32000，确保可以生成非常详细的报告（参考标准：约5万字）
            self.max_tokens = int(os.getenv('MAX_TOKENS', '32000'))
        
        # 验证配置
        if not self.api_key:
            logger.warning("未设置API密钥，请设置相应的环境变量")
            logger.warning("   - OpenAI: OPENAI_API_KEY")
            logger.warning("   - 通义千问: DASHSCOPE_API_KEY")
            logger.warning("   - 自定义: CUSTOM_API_KEY")
    
    def _load_system_prompt(self) -> str:
        """
        加载系统提示词
        优先级：system_prompt.txt文件 > 环境变量 > 默认提示词
        """
        # 默认提示词（超智引擎 - 增强版）
        default_prompt = """# 角色

你是超智引擎，是一个**专业的报告撰写专家和智能体**，专门协助用户完成**极其详细、内容丰富**的可行性研究报告撰写、政策项目申报等工作。

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

